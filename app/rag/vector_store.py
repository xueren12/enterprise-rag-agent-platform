from __future__ import annotations

import json
from pathlib import Path

from app.config import VECTOR_INDEX_PATH
from app.rag.document_loader import Document
from app.rag.embedding_service import HashEmbeddingService
from app.rag.query_terms import extract_query_terms, keyword_coverage


class VectorStoreService:
    """Persisted vector index with TopK cosine similarity search."""

    def __init__(
        self,
        index_path: str | Path = VECTOR_INDEX_PATH,
        embedding_service: HashEmbeddingService | None = None,
    ) -> None:
        self.index_path = Path(index_path)
        self.embedding_service = embedding_service or HashEmbeddingService()
        self._items: list[dict] = []

    def build_index(self, docs: list[Document]) -> int:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._items = [
            {
                "content": doc.content,
                "metadata": doc.metadata,
                "embedding": self.embedding_service.embed(doc.content),
            }
            for doc in docs
        ]
        payload = {
            "version": 1,
            "dimensions": self.embedding_service.dimensions,
            "items": self._items,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(self._items)

    def load_index(self) -> None:
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"vector index not found: {self.index_path}. Run build_index first."
            )
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self._items = payload.get("items", [])

    def similarity_search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._items:
            self.load_index()

        query_embedding = self.embedding_service.embed(query)
        query_terms = extract_query_terms(query)
        ranked = []
        for item in self._items:
            vector_score = _dot(query_embedding, item["embedding"])
            coverage = keyword_coverage(item["content"], query_terms)
            score = min(1.0, (0.7 * vector_score) + (0.3 * coverage))
            metadata = item["metadata"]
            ranked.append(
                {
                    "content": item["content"],
                    "source": metadata["source"],
                    "title": metadata["title"],
                    "chunk_id": metadata["chunk_id"],
                    "start_index": metadata["start_index"],
                    "end_index": metadata["end_index"],
                    "score": round(score, 4),
                    "keyword_coverage": round(coverage, 4),
                }
            )
        ranked.sort(key=lambda row: row["score"], reverse=True)
        return ranked[:top_k]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
