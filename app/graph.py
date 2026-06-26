from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.services.log_service import LogService, new_trace_id
from app.services.rag_service import RagService
from app.state import AgentState
from app.tools.tool_plan import ToolCallPlan, execute_tool_call, plan_tool_call


class AgentGraph:
    """LangGraph orchestration for the RAG + Tool agent flow."""

    def __init__(
        self,
        rag_service: RagService | None = None,
        log_service: LogService | None = None,
    ) -> None:
        self.rag_service = rag_service or RagService()
        self.log_service = log_service or LogService()
        self.graph = self._build_graph()

    def invoke(self, state: AgentState) -> AgentState:
        return self.graph.invoke(state)

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("init_node", self.init_node)
        builder.add_node("retrieve_node", self.retrieve_node)
        builder.add_node("tool_plan_node", self.tool_plan_node)
        builder.add_node("tool_execute_node", self.tool_execute_node)
        builder.add_node("final_node", self.final_node)
        builder.add_node("fallback_node", self.fallback_node)

        builder.set_entry_point("init_node")
        builder.add_conditional_edges(
            "init_node",
            self._route_error_or_next("retrieve_node"),
            {"fallback_node": "fallback_node", "retrieve_node": "retrieve_node"},
        )
        builder.add_conditional_edges(
            "retrieve_node",
            self._route_error_or_next("tool_plan_node"),
            {"fallback_node": "fallback_node", "tool_plan_node": "tool_plan_node"},
        )
        builder.add_conditional_edges(
            "tool_plan_node",
            self._route_after_tool_plan,
            {
                "fallback_node": "fallback_node",
                "tool_execute_node": "tool_execute_node",
                "final_node": "final_node",
            },
        )
        builder.add_conditional_edges(
            "tool_execute_node",
            self._route_error_or_next("final_node"),
            {"fallback_node": "fallback_node", "final_node": "final_node"},
        )
        builder.add_edge("final_node", END)
        builder.add_edge("fallback_node", END)
        return builder.compile()

    def init_node(self, state: AgentState) -> AgentState:
        trace_id = state.get("trace_id") or new_trace_id()
        updated: AgentState = {
            **state,
            "trace_id": trace_id,
            "need_tool": False,
            "tool_result": None,
            "error": None,
            "status": "running",
        }
        self._log(updated, "init_node", success=True)
        return updated

    def retrieve_node(self, state: AgentState) -> AgentState:
        try:
            rag_result = self.rag_service.answer(
                state["question"],
                top_k=state.get("top_k", 5),
            )
            updated: AgentState = {
                **state,
                "rag_result": rag_result,
                "answer": rag_result.get("answer", ""),
                "citations": rag_result.get("citations", []),
            }
            self._log(
                updated,
                "retrieve_node",
                success=rag_result.get("status") == "success",
                extra={
                    "legacy_node_name": "rag_answer",
                    "rag_status": rag_result.get("status"),
                    "retrieved_count": len(rag_result.get("retrieved_chunks", [])),
                    "citation_count": len(rag_result.get("citations", [])),
                },
            )
            return updated
        except Exception as exc:
            updated = {**state, "error": f"RAG 检索/回答失败：{exc}", "status": "error"}
            self._log(updated, "retrieve_node", success=False, error=updated["error"])
            return updated

    def tool_plan_node(self, state: AgentState) -> AgentState:
        try:
            plan = plan_tool_call(
                state["question"],
                confirm=state.get("confirm", False),
            )
            updated: AgentState = {
                **state,
                "tool_plan": plan.model_dump(),
                "need_tool": plan.need_tool,
            }
            self._log(
                updated,
                "tool_plan_node",
                tool_name=plan.tool_name,
                tool_args=plan.tool_args,
                success=True,
                extra={"need_tool": plan.need_tool, "reason": plan.reason},
            )
            return updated
        except Exception as exc:
            updated = {**state, "error": f"工具规划失败：{exc}", "status": "error"}
            self._log(updated, "tool_plan_node", success=False, error=updated["error"])
            return updated

    def tool_execute_node(self, state: AgentState) -> AgentState:
        try:
            plan = ToolCallPlan.model_validate(state.get("tool_plan", {}))
            payload = execute_tool_call(plan)
            updated: AgentState = {
                **state,
                "tool_result": payload.get("tool_result"),
                "error": payload.get("error"),
                "status": _merge_status(state.get("rag_result", {}).get("status"), payload),
            }
            updated["tool_plan"] = {
                **state.get("tool_plan", {}),
                "tool_args": payload.get("tool_args", plan.tool_args),
                "tool_name": payload.get("tool_name", plan.tool_name),
            }
            self._log(
                updated,
                "tool_execute_node",
                tool_name=payload.get("tool_name"),
                tool_args=payload.get("tool_args"),
                success=payload.get("success", False),
                error=payload.get("error"),
            )
            return updated
        except Exception as exc:
            updated = {**state, "error": f"工具执行节点异常：{exc}", "status": "error"}
            self._log(updated, "tool_execute_node", success=False, error=updated["error"])
            return updated

    def final_node(self, state: AgentState) -> AgentState:
        response = self._build_response(state, fallback=False)
        updated: AgentState = {
            **state,
            "status": response["status"],
            "final_response": response,
        }
        self._log(updated, "final_node", success=response["error"] is None, error=response["error"])
        return updated

    def fallback_node(self, state: AgentState) -> AgentState:
        response = self._build_response(state, fallback=True)
        updated: AgentState = {
            **state,
            "status": response["status"],
            "final_response": response,
        }
        self._log(updated, "fallback_node", success=False, error=response["error"])
        return updated

    def _build_response(self, state: AgentState, fallback: bool) -> dict[str, Any]:
        rag_result = state.get("rag_result", {})
        tool_plan = state.get("tool_plan", {})
        tool_error = state.get("error")
        if fallback:
            status = "partial_success" if state.get("answer") else "error"
        else:
            status = state.get("status") or rag_result.get("status") or "success"
            if status == "running":
                status = rag_result.get("status") or "success"

        return {
            "trace_id": state.get("trace_id"),
            "status": status,
            "answer": state.get("answer", ""),
            "citations": state.get("citations", []),
            "used_llm": rag_result.get("used_llm", False),
            "embedding_provider": rag_result.get("embedding_provider"),
            "vector_store_type": rag_result.get("vector_store_type"),
            "need_tool": state.get("need_tool", False),
            "tool_name": tool_plan.get("tool_name"),
            "tool_args": tool_plan.get("tool_args", {}),
            "tool_result": state.get("tool_result"),
            "error": tool_error,
        }

    def _route_after_tool_plan(
        self, state: AgentState
    ) -> Literal["fallback_node", "tool_execute_node", "final_node"]:
        if state.get("error"):
            return "fallback_node"
        if state.get("need_tool"):
            return "tool_execute_node"
        return "final_node"

    @staticmethod
    def _route_error_or_next(next_node: str):
        def route(state: AgentState) -> str:
            if state.get("error"):
                return "fallback_node"
            return next_node

        return route

    def _log(
        self,
        state: AgentState,
        node_name: str,
        *,
        tool_name: str | None = None,
        tool_args: dict | None = None,
        success: bool = True,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.log_service.log_event(
            trace_id=state.get("trace_id") or "",
            node_name=node_name,
            question=state.get("question", ""),
            tool_name=tool_name,
            tool_args=tool_args,
            success=success,
            error=error,
            extra=extra,
        )


def _merge_status(rag_status: str | None, tool_payload: dict[str, Any]) -> str:
    if tool_payload.get("tool_result") is not None:
        return "success"
    if rag_status == "success":
        return "success"
    if tool_payload.get("error"):
        return "partial_success" if rag_status == "success" else "error"
    return rag_status or "success"
