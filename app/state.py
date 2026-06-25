from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    trace_id: str
    question: str
    top_k: int
    confirm: bool
    rag_result: dict[str, Any]
    answer: str
    citations: list[dict[str, Any]]
    tool_plan: dict[str, Any]
    tool_result: dict[str, Any] | None
    need_tool: bool
    error: str | None
    status: str
    final_response: dict[str, Any]
