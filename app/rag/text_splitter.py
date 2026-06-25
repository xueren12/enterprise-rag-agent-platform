from __future__ import annotations

from app.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from app.rag.document_loader import Document


class TextSplitter:
    """Split documents into overlapping chunks for stable retrieval."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        for document in documents:
            chunks.extend(self._split_one(document))
        return chunks

    def _split_one(self, document: Document) -> list[Document]:
        text = document.content.strip()
        if not text:
            return []

        source_stem = str(document.metadata["source"]).rsplit(".", 1)[0]
        chunks: list[Document] = []
        start = 0
        chunk_no = 1

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                end = self._move_to_boundary(text, start, end)

            content = text[start:end].strip()
            if content:
                chunk_id = f"{source_stem}_{chunk_no:03d}"
                metadata = {
                    **document.metadata,
                    "chunk_id": chunk_id,
                    "start_index": start,
                    "end_index": end,
                }
                chunks.append(Document(content=content, metadata=metadata))
                chunk_no += 1

            if end >= len(text):
                break
            start = max(0, end - self.chunk_overlap)

        return chunks

    @staticmethod
    def _move_to_boundary(text: str, start: int, proposed_end: int) -> int:
        # Prefer cutting at paragraph/sentence boundaries without creating tiny chunks.
        min_end = start + max(80, (proposed_end - start) // 2)
        boundary_chars = "\n。！？；;.!?"
        for index in range(proposed_end, min_end, -1):
            if text[index - 1] in boundary_chars:
                return index
        return proposed_end
