from __future__ import annotations

from typing import Any

from app.services.log_service import LogService, new_trace_id
from app.services.rag_service import RagService
from app.tools.tool_plan import execute_tool_call, plan_tool_call


class AgentService:
    """Lightweight RAG + Tool composition before LangGraph is introduced."""

    def __init__(
        self,
        rag_service: RagService | None = None,
        log_service: LogService | None = None,
    ) -> None:
        self.rag_service = rag_service or RagService()
        self.log_service = log_service or LogService()

    def chat(self, question: str, top_k: int = 5, confirm: bool = False) -> dict[str, Any]:
        trace_id = new_trace_id()

        try:
            rag_result = self.rag_service.answer(question, top_k=top_k)
            self.log_service.log_event(
                trace_id=trace_id,
                node_name="rag_answer",
                question=question,
                success=rag_result.get("status") == "success",
                extra={
                    "rag_status": rag_result.get("status"),
                    "retrieved_count": len(rag_result.get("retrieved_chunks", [])),
                    "citation_count": len(rag_result.get("citations", [])),
                },
            )
        except Exception as exc:
            rag_result = {
                "status": "error",
                "answer": "",
                "citations": [],
                "retrieved_chunks": [],
                "prompt": "",
            }
            self.log_service.log_event(
                trace_id=trace_id,
                node_name="rag_answer",
                question=question,
                success=False,
                error=str(exc),
            )

        plan = plan_tool_call(question, confirm=confirm)
        self.log_service.log_event(
            trace_id=trace_id,
            node_name="tool_plan",
            question=question,
            tool_name=plan.tool_name,
            tool_args=plan.tool_args,
            success=True,
            extra={"need_tool": plan.need_tool, "reason": plan.reason},
        )

        tool_payload = {
            "success": True,
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "error": None,
        }
        if plan.need_tool:
            tool_payload = execute_tool_call(plan)
            self.log_service.log_event(
                trace_id=trace_id,
                node_name="tool_execute",
                question=question,
                tool_name=tool_payload.get("tool_name"),
                tool_args=tool_payload.get("tool_args"),
                success=tool_payload.get("success", False),
                error=tool_payload.get("error"),
            )

        tool_error = tool_payload.get("error")
        status = _merge_status(rag_result.get("status"), tool_payload)
        return {
            "trace_id": trace_id,
            "status": status,
            "answer": rag_result.get("answer", ""),
            "citations": rag_result.get("citations", []),
            "need_tool": plan.need_tool,
            "tool_name": plan.tool_name,
            "tool_args": tool_payload.get("tool_args") if plan.need_tool else plan.tool_args,
            "tool_result": tool_payload.get("tool_result"),
            "error": tool_error,
        }


def _merge_status(rag_status: str | None, tool_payload: dict[str, Any]) -> str:
    if tool_payload.get("tool_result") is not None:
        return "success"
    if rag_status == "success":
        return "success"
    if tool_payload.get("error"):
        return "partial_success" if rag_status == "success" else "error"
    return rag_status or "success"
