from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import TRACE_LOG_PATH
from app.schemas.request import AgentChatRequest, KnowledgeIndexRequest
from app.schemas.response import AgentChatResponse, HealthResponse, KnowledgeIndexResponse, TraceResponse
from app.services.log_service import new_trace_id
from app.services.agent_service import AgentService
from app.services.rag_service import RagService


app = FastAPI(
    title="Enterprise RAG Agent Platform",
    description="RAG + Tool Calling Agent API for enterprise knowledge demos.",
    version="0.4.0",
)

RAG_SERVICE = RagService()
AGENT_SERVICE = AgentService(rag_service=RAG_SERVICE)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response("VALIDATION_ERROR", "请求参数校验失败", 422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response("INTERNAL_ERROR", str(exc), 500)


@app.get("/health", response_model=HealthResponse)
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/knowledge/index", response_model=KnowledgeIndexResponse)
def build_knowledge_index(request: KnowledgeIndexRequest) -> dict:
    return RAG_SERVICE.build_index(request.docs_dir)


@app.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(request: AgentChatRequest) -> dict:
    return AGENT_SERVICE.chat(
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


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "trace_id": new_trace_id(),
        },
    )
