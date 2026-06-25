from __future__ import annotations

from typing import Any

from app.graph import AgentGraph
from app.services.log_service import LogService
from app.services.rag_service import RagService


class AgentService:
    """Public Agent API backed by the LangGraph orchestration."""

    def __init__(
        self,
        rag_service: RagService | None = None,
        log_service: LogService | None = None,
    ) -> None:
        self.rag_service = rag_service or RagService()
        self.log_service = log_service or LogService()
        self.agent_graph = AgentGraph(self.rag_service, self.log_service)

    def chat(self, question: str, top_k: int = 5, confirm: bool = False) -> dict[str, Any]:
        final_state = self.agent_graph.invoke(
            {
                "question": question,
                "top_k": top_k,
                "confirm": confirm,
            }
        )
        return final_state["final_response"]
