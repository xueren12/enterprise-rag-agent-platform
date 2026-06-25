from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import DEFAULT_TOP_K


class KnowledgeIndexRequest(BaseModel):
    docs_dir: str = "data/docs"


class AgentChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20)
    confirm: bool = False
