from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeIndexResponse(BaseModel):
    status: str
    indexed_chunks: int


class HealthResponse(BaseModel):
    status: str


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
    used_llm: bool = False
    embedding_provider: str | None = None
    vector_store_type: str | None = None
    need_tool: bool
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_result: dict[str, Any] | None = None
    error: str | None = None


class TraceResponse(BaseModel):
    trace_id: str
    events: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str
