from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from app.config import EMBEDDING_MODEL, EMBEDDING_PROVIDER


class EmbeddingProvider(ABC):
    name: str
    model_name: str
    dimensions: int | None

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class HashEmbeddingProvider(EmbeddingProvider):
    """Small deterministic embedding provider for tests and offline fallback."""

    name = "hash"

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions
        self.model_name = f"hash-{dimensions}"

    def embed(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dimensions

        counts = Counter(tokens)
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            index = self._bucket(token)
            vector[index] += 1.0 + math.log(count)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _bucket(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % self.dimensions

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lower = text.lower()
        word_tokens = re.findall(r"[a-z0-9_]+", lower)
        cjk_chars = re.findall(r"[\u4e00-\u9fff]", lower)
        cjk_bigrams = [
            lower[index : index + 2]
            for index in range(len(lower) - 1)
            if _is_cjk_pair(lower[index : index + 2])
        ]
        return word_tokens + cjk_chars + cjk_bigrams


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Sentence-Transformers provider loaded lazily to avoid test-time downloads."""

    name = "sentence_transformer"

    def __init__(self, model_name: str = EMBEDDING_MODEL, model: object | None = None) -> None:
        self.model_name = model_name
        self._model = model
        self.dimensions: int | None = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. Install it or set EMBEDDING_PROVIDER=hash."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        vector = self.model.encode(text, normalize_embeddings=True)
        result = [float(value) for value in vector]
        self.dimensions = len(result)
        return result

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        result = [[float(value) for value in vector] for vector in vectors]
        if result:
            self.dimensions = len(result[0])
        return result


def create_embedding_provider(
    provider_name: str | None = None,
    model_name: str | None = None,
) -> EmbeddingProvider:
    provider = (provider_name or EMBEDDING_PROVIDER or "hash").strip().lower()
    if provider == "hash":
        return HashEmbeddingProvider()
    if provider in {"sentence_transformer", "sentence-transformer", "sentence"}:
        return SentenceTransformerEmbeddingProvider(model_name or EMBEDDING_MODEL)
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def _is_cjk_pair(value: str) -> bool:
    return len(value) == 2 and all("\u4e00" <= char <= "\u9fff" for char in value)


# Backward-compatible alias for older tests/imports.
HashEmbeddingService = HashEmbeddingProvider
