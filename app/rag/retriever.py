from __future__ import annotations

from app.config import DEFAULT_TOP_K
from app.rag.vector_store import VectorStoreService


class Retriever:
    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or VectorStoreService()

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        return self.vector_store.similarity_search(query=query, top_k=top_k)
