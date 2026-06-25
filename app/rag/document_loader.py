from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {".md", ".txt"}


@dataclass(slots=True)
class Document:
    content: str
    metadata: dict


class DocumentLoader:
    """Load local knowledge documents while preserving source metadata."""

    def load(self, docs_dir: str | Path) -> list[Document]:
        root = Path(docs_dir)
        if not root.exists():
            raise FileNotFoundError(f"docs_dir not found: {root}")

        documents: list[Document] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            content = path.read_text(encoding="utf-8")
            documents.append(
                Document(
                    content=content,
                    metadata={
                        "source": path.name,
                        "path": str(path),
                        "title": self._extract_title(content, path),
                    },
                )
            )
        return documents

    @staticmethod
    def _extract_title(content: str, path: Path) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.removeprefix("# ").strip()
        return path.stem.replace("_", " ").title()
