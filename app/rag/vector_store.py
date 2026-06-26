from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.config import CHROMA_COLLECTION_NAME, VECTOR_INDEX_PATH, VECTOR_STORE_DIR, VECTOR_STORE_TYPE
from app.rag.document_loader import Document
from app.rag.embedding_service import EmbeddingProvider, create_embedding_provider
from app.rag.query_terms import extract_query_terms, keyword_coverage


class VectorStoreService:
    """Vector index facade. Uses Chroma when available, with local fallback."""

    def __init__(
        self,
        index_path: str | Path = VECTOR_INDEX_PATH,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store_type: str | None = None,
        collection_name: str = CHROMA_COLLECTION_NAME,
    ) -> None:
        self.index_path = Path(index_path)
        self.persist_dir = Path(VECTOR_STORE_DIR)
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.requested_vector_store_type = (vector_store_type or VECTOR_STORE_TYPE or "chroma").lower()
        self.collection_name = collection_name
        self._items: list[dict[str, Any]] = []
        self._collection = None
        self.vector_store_type = "local"
        self.fallback_reason: str | None = None

    @property
    def embedding_provider_name(self) -> str:
        return self.embedding_provider.name

    def build_index(self, docs: list[Document]) -> int:
        if self.requested_vector_store_type == "chroma":
            try:
                self.fallback_reason = None
                return self._build_chroma_index(docs)
            except Exception as exc:
                self.vector_store_type = "local_fallback"
                self.fallback_reason = _fallback_reason(exc)
        return self._build_local_index(docs)

    def load_index(self) -> None:
        if self.requested_vector_store_type == "chroma" and self.vector_store_type != "local_fallback":
            try:
                self._get_chroma_collection()
                self.vector_store_type = "chroma"
                self.fallback_reason = None
                return
            except Exception as exc:
                self.vector_store_type = "local_fallback"
                self.fallback_reason = _fallback_reason(exc)

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"vector index not found: {self.index_path}. Run build_index first."
            )
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self._items = payload.get("items", [])

    def similarity_search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.requested_vector_store_type == "chroma" and self.vector_store_type != "local_fallback":
            try:
                self.fallback_reason = None
                return self._chroma_similarity_search(query, top_k)
            except Exception as exc:
                self.vector_store_type = "local_fallback"
                self.fallback_reason = _fallback_reason(exc)

        return self._local_similarity_search(query, top_k)

    def _build_chroma_index(self, docs: list[Document]) -> int:
        chromadb = _import_chromadb()
        chroma_dir = self.persist_dir / "chroma"
        if chroma_dir.exists():
            shutil.rmtree(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(chroma_dir))
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(name=self.collection_name)

        contents = [doc.content for doc in docs]
        embeddings = self.embedding_provider.embed_documents(contents)
        ids = [doc.metadata["chunk_id"] for doc in docs]
        metadatas = [self._flatten_metadata(doc.metadata) for doc in docs]
        if docs:
            collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        self._collection = collection
        self.vector_store_type = "chroma"

        # Keep a local JSON copy as a transparent fallback for offline tests.
        self._write_local_copy(docs, embeddings)
        return len(docs)

    def _chroma_similarity_search(self, query: str, top_k: int) -> list[dict]:
        collection = self._get_chroma_collection()
        query_embedding = self.embedding_provider.embed(query)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        rows = []
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for content, metadata, distance in zip(documents, metadatas, distances):
            score = max(0.0, 1.0 - float(distance))
            rows.append(self._format_row(content, metadata, score))
        self.vector_store_type = "chroma"
        return rows

    def _get_chroma_collection(self):
        if self._collection is not None:
            return self._collection
        chromadb = _import_chromadb()
        client = chromadb.PersistentClient(path=str(self.persist_dir / "chroma"))
        self._collection = client.get_or_create_collection(name=self.collection_name)
        return self._collection

    def _build_local_index(self, docs: list[Document]) -> int:
        embeddings = self.embedding_provider.embed_documents([doc.content for doc in docs])
        if self.vector_store_type != "local_fallback":
            self.vector_store_type = "local"
            self.fallback_reason = None
        self._write_local_copy(docs, embeddings)
        return len(self._items)

    def _write_local_copy(self, docs: list[Document], embeddings: list[list[float]]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._items = [
            {
                "content": doc.content,
                "metadata": doc.metadata,
                "embedding": embedding,
            }
            for doc, embedding in zip(docs, embeddings)
        ]
        payload = {
            "version": 2,
            "embedding_provider": self.embedding_provider.name,
            "embedding_model": self.embedding_provider.model_name,
            "vector_store_type": self.vector_store_type,
            "items": self._items,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _local_similarity_search(self, query: str, top_k: int) -> list[dict]:
        if not self._items:
            self.load_index()

        query_embedding = self.embedding_provider.embed(query)
        query_terms = extract_query_terms(query)
        ranked = []
        for item in self._items:
            vector_score = _dot(query_embedding, item["embedding"])
            coverage = keyword_coverage(item["content"], query_terms)
            score = min(1.0, (0.7 * vector_score) + (0.3 * coverage))
            ranked.append(self._format_row(item["content"], item["metadata"], score, coverage))
        ranked.sort(key=lambda row: row["score"], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _format_row(
        content: str,
        metadata: dict[str, Any],
        score: float,
        keyword_score: float | None = None,
    ) -> dict:
        row = {
            "content": content,
            "source": metadata["source"],
            "title": metadata["title"],
            "chunk_id": metadata["chunk_id"],
            "start_index": int(metadata.get("start_index", 0)),
            "end_index": int(metadata.get("end_index", 0)),
            "score": round(float(score), 4),
        }
        if keyword_score is not None:
            row["keyword_coverage"] = round(keyword_score, 4)
        return row

    @staticmethod
    def _flatten_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _import_chromadb():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("chromadb is not installed. Falling back to local vector store.") from exc
    return chromadb


def _fallback_reason(exc: Exception) -> str:
    reason = str(exc).strip() or exc.__class__.__name__
    return reason[:200]
