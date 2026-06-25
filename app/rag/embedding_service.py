from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


class HashEmbeddingService:
    """Small local embedding interface that can later be replaced by real models."""

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

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
        cjk_bigrams = [lower[i : i + 2] for i in range(len(lower) - 1) if _is_cjk_pair(lower[i : i + 2])]
        return word_tokens + cjk_chars + cjk_bigrams


def _is_cjk_pair(value: str) -> bool:
    return len(value) == 2 and all("\u4e00" <= char <= "\u9fff" for char in value)
