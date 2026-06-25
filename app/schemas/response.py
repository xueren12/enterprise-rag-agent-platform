from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeIndexResponse(BaseModel):
    status: str
    indexed_chunks: int


class Citation(BaseModel):
    source: str
    title: str | None = None
    chunk_id: str
    score: float | None = None


class AgentChatResponse(BaseModel):
    trace_id: str | None = None
    status: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    need_tool: bool
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_result: dict[str, Any] | None = None
    error: str | None = None


class TraceResponse(BaseModel):
    trace_id: str
    events: list[dict[str, Any]]
