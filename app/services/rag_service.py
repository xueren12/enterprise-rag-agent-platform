from __future__ import annotations

from pathlib import Path
import re

from app.config import DOCS_DIR, NO_ANSWER_TEXT
from app.rag.document_loader import DocumentLoader
from app.rag.prompt_builder import RagPromptBuilder
from app.rag.query_terms import extract_query_terms
from app.rag.retriever import Retriever
from app.rag.text_splitter import TextSplitter
from app.rag.vector_store import VectorStoreService
from app.services.llm_service import LLMService


class RagService:
    """Orchestrates first-stage RAG indexing, retrieval and grounded answering."""

    def __init__(
        self,
        vector_store: VectorStoreService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.loader = DocumentLoader()
        self.splitter = TextSplitter()
        self.vector_store = vector_store or VectorStoreService()
        self.retriever = Retriever(self.vector_store)
        self.prompt_builder = RagPromptBuilder()
        self.llm_prompt_builder = RagPromptBuilder()
        self.llm_prompt_builder.template_path = self.llm_prompt_builder.template_path.with_name(
            "rag_llm_answer_prompt.txt"
        )
        self.llm_service = llm_service or LLMService()

    def build_index(self, docs_dir: str | Path = DOCS_DIR) -> dict:
        documents = self.loader.load(docs_dir)
        chunks = self.splitter.split_documents(documents)
        indexed_chunks = self.vector_store.build_index(chunks)
        return {"status": "success", "indexed_chunks": indexed_chunks}

    def answer(self, question: str, top_k: int = 5) -> dict:
        chunks = self.retriever.retrieve(question, top_k=top_k)
        exact_ids = _exact_identifiers(question)
        selected = [
            chunk
            for chunk in chunks
            if chunk["score"] >= 0.14 and chunk.get("keyword_coverage", 0.0) >= 0.2
        ]
        if selected:
            top_score = selected[0]["score"]
            selected = [chunk for chunk in selected if chunk["score"] >= top_score * 0.75]
        if exact_ids:
            exact_selected = [
                chunk
                for chunk in selected
                if any(identifier in chunk["content"].lower() for identifier in exact_ids)
            ]
            if exact_selected:
                selected = exact_selected

        if not selected:
            return self._no_answer(chunks, self.prompt_builder.build(question, chunks))

        prompt = self.llm_prompt_builder.build(question, selected)
        citations = self._dedupe_citations(selected)

        try:
            llm_response = self.llm_service.chat(prompt)
            answer = llm_response.content.strip()
            if answer and answer != NO_ANSWER_TEXT:
                return {
                    "status": "success",
                    "answer": answer,
                    "citations": citations,
                    "retrieved_chunks": chunks,
                    "prompt": prompt,
                    "used_llm": llm_response.used_llm,
                    "embedding_provider": self.vector_store.embedding_provider_name,
                    "vector_store_type": self.vector_store.vector_store_type,
                }
        except Exception:
            pass

        answer = self._extract_grounded_answer(question, selected)
        if not answer:
            return self._no_answer(chunks, prompt)

        return {
            "status": "success",
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": chunks,
            "prompt": prompt,
            "used_llm": False,
            "embedding_provider": self.vector_store.embedding_provider_name,
            "vector_store_type": self.vector_store.vector_store_type,
        }

    def _no_answer(self, chunks: list[dict], prompt: str) -> dict:
        return {
            "status": "no_answer",
            "answer": NO_ANSWER_TEXT,
            "citations": [],
            "retrieved_chunks": chunks,
            "prompt": prompt,
            "used_llm": False,
            "embedding_provider": self.vector_store.embedding_provider_name,
            "vector_store_type": self.vector_store.vector_store_type,
        }

    def _extract_grounded_answer(self, question: str, chunks: list[dict]) -> str:
        query_terms = extract_query_terms(question)
        exact_ids = _exact_identifiers(question)
        lines: list[str] = []

        for chunk in chunks:
            if exact_ids:
                lines.extend(_extract_identifier_section(chunk["content"], exact_ids))
                if lines:
                    continue
            for raw_line in chunk["content"].splitlines():
                line = _clean_line(raw_line)
                if not line or line.startswith("#"):
                    continue
                if _line_matches(line, query_terms):
                    lines.append(line)

        if not lines:
            lines = _fallback_summary_lines(chunks)
        if not lines:
            return ""

        unique_lines = []
        for line in lines:
            if line not in unique_lines:
                unique_lines.append(line)
            if len(unique_lines) >= 8:
                break

        return "\n".join(f"{index}. {line}" for index, line in enumerate(unique_lines, start=1))

    @staticmethod
    def _dedupe_citations(chunks: list[dict]) -> list[dict]:
        citations = []
        seen = set()
        for chunk in chunks:
            key = (chunk["source"], chunk["chunk_id"])
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                {
                    "source": chunk["source"],
                    "title": chunk["title"],
                    "chunk_id": chunk["chunk_id"],
                    "score": chunk["score"],
                }
            )
        return citations


def _line_matches(line: str, query_terms: set[str]) -> bool:
    lower = line.lower()
    hits = sum(1 for term in query_terms if term and term in lower)
    return hits >= 1


def _fallback_summary_lines(chunks: list[dict]) -> list[str]:
    lines = []
    for chunk in chunks:
        for raw_line in chunk["content"].splitlines():
            line = _clean_line(raw_line)
            if line and not line.startswith("#"):
                lines.append(line)
                break
    return lines


def _exact_identifiers(question: str) -> set[str]:
    return set(re.findall(r"\b[a-z]+[0-9]+\b|\b[0-9]{4,}\b", question.lower()))


def _extract_identifier_section(content: str, identifiers: set[str]) -> list[str]:
    raw_lines = content.splitlines()
    start = None
    for index, line in enumerate(raw_lines):
        lower = line.lower()
        if any(identifier in lower for identifier in identifiers):
            start = index
            break
    if start is None:
        return []

    section_lines: list[str] = []
    for raw_line in raw_lines[start : start + 12]:
        if section_lines and raw_line.startswith("### "):
            break
        line = _clean_line(raw_line)
        if not line:
            continue
        if line.startswith("#"):
            line = line.strip("# ").strip()
        section_lines.append(line)
    return section_lines


def _clean_line(raw_line: str) -> str:
    line = raw_line.strip(" -\t")
    line = re.sub(r"^\d+\.\s*", "", line)
    return line.strip()
