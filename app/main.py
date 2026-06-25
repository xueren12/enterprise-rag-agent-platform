from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from app.config import TRACE_LOG_PATH
from app.schemas.request import AgentChatRequest, KnowledgeIndexRequest
from app.schemas.response import AgentChatResponse, KnowledgeIndexResponse, TraceResponse
from app.services.agent_service import AgentService
from app.services.rag_service import RagService


app = FastAPI(
    title="Enterprise RAG Agent Platform",
    description="RAG + Tool Calling Agent API for enterprise knowledge demos.",
    version="0.4.0",
)


@app.post("/knowledge/index", response_model=KnowledgeIndexResponse)
def build_knowledge_index(request: KnowledgeIndexRequest) -> dict:
    return RagService().build_index(request.docs_dir)


@app.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(request: AgentChatRequest) -> dict:
    return AgentService().chat(
        request.question,
        top_k=request.top_k,
        confirm=request.confirm,
    )


@app.get("/trace/{trace_id}", response_model=TraceResponse)
def get_trace(trace_id: str) -> dict:
    return {
        "trace_id": trace_id,
        "events": _read_trace_events(trace_id),
    }


def _read_trace_events(trace_id: str, log_path: str | Path = TRACE_LOG_PATH) -> list[dict]:
    path = Path(log_path)
    if not path.exists():
        return []

    events = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("trace_id") == trace_id:
                events.append(event)
    return events
