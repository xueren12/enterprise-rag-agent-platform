from app.config import DOCS_DIR
from app.services.agent_service import AgentService
from app.services.log_service import LogService
from app.services.rag_service import RagService


def test_agent_service_returns_rag_answer_and_tool_result(tmp_path):
    rag_service = RagService()
    rag_service.build_index(DOCS_DIR)
    service = AgentService(
        rag_service=rag_service,
        log_service=LogService(tmp_path / "agent_trace.jsonl"),
    )

    result = service.chat("根据知识库说明，查询订单 10001 的退款状态。")

    assert result["status"] == "success"
    assert result["need_tool"] is True
    assert result["tool_name"] == "sql_query_tool"
    assert result["tool_result"]["refund_status"] == "processing"
    assert result["answer"]
    assert result["trace_id"]


def test_agent_service_does_not_trigger_tool_for_plain_rag_question(tmp_path):
    rag_service = RagService()
    rag_service.build_index(DOCS_DIR)
    service = AgentService(
        rag_service=rag_service,
        log_service=LogService(tmp_path / "agent_trace.jsonl"),
    )

    result = service.chat("订单退款流程是什么？")

    assert result["status"] == "success"
    assert result["need_tool"] is False
    assert result["tool_result"] is None
    assert result["error"] is None


def test_agent_service_logs_rag_and_tool_events(tmp_path):
    rag_service = RagService()
    rag_service.build_index(DOCS_DIR)
    log_path = tmp_path / "agent_trace.jsonl"
    service = AgentService(rag_service=rag_service, log_service=LogService(log_path))

    service.chat("查询用户 U1001 的账号状态。")

    content = log_path.read_text(encoding="utf-8")
    assert "rag_answer" in content
    assert "tool_plan" in content
    assert "tool_execute" in content
