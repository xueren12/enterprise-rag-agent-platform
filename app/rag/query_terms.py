from __future__ import annotations

import re


GENERIC_CJK_TERMS = {
    "什么",
    "怎么",
    "如何",
    "流程",
    "说明",
    "查询",
    "可以",
    "哪些",
    "告诉",
    "根据",
    "知识",
    "业务",
    "处理",
    "操作",
}


def extract_query_terms(text: str) -> set[str]:
    words = set(re.findall(r"[A-Za-z]+[0-9]+|[A-Za-z_]+|[0-9]+", text.lower()))
    cjk_bigrams = {
        text[index : index + 2]
        for index in range(len(text) - 1)
        if all("\u4e00" <= char <= "\u9fff" for char in text[index : index + 2])
    }
    return words | {term for term in cjk_bigrams if term not in GENERIC_CJK_TERMS}


def keyword_coverage(text: str, terms: set[str]) -> float:
    if not terms:
        return 0.0
    lower = text.lower()
    hits = sum(1 for term in terms if term in lower)
    return hits / len(terms)
