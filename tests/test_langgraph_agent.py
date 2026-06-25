from app.config import DOCS_DIR
from app.services.agent_service import AgentService
from app.services.log_service import LogService
from app.services.rag_service import RagService


class BrokenRagService(RagService):
    def answer(self, question: str, top_k: int = 5) -> dict:
        raise RuntimeError("forced retrieve failure")


def _service(tmp_path, rag_service=None):
    rag = rag_service or RagService()
    if rag_service is None:
        rag.build_index(DOCS_DIR)
    return AgentService(
        rag_service=rag,
        log_service=LogService(tmp_path / "agent_trace.jsonl"),
    )


def _log_text(tmp_path):
    return (tmp_path / "agent_trace.jsonl").read_text(encoding="utf-8")


def test_plain_rag_question_does_not_enter_tool_execute(tmp_path):
    service = _service(tmp_path)

    result = service.chat("订单退款流程是什么？")

    assert result["status"] == "success"
    assert result["need_tool"] is False
    assert result["tool_result"] is None
    logs = _log_text(tmp_path)
    assert "retrieve_node" in logs
    assert "tool_plan_node" in logs
    assert "tool_execute_node" not in logs
    assert "final_node" in logs


def test_order_question_enters_sql_query_tool(tmp_path):
    service = _service(tmp_path)

    result = service.chat("查询订单 10001 的退款状态。")

    assert result["need_tool"] is True
    assert result["tool_name"] == "sql_query_tool"
    assert result["tool_result"]["refund_status"] == "processing"
    assert "tool_execute_node" in _log_text(tmp_path)


def test_user_question_enters_http_api_tool(tmp_path):
    service = _service(tmp_path)

    result = service.chat("查询用户 U1001 的账号状态。")

    assert result["need_tool"] is True
    assert result["tool_name"] == "http_api_tool"
    assert result["tool_result"]["status"] == "normal"
    assert result["tool_result"]["risk_level"] == "low"


def test_high_risk_task_without_confirm_returns_failure_result(tmp_path):
    service = _service(tmp_path)

    result = service.chat("触发订单退款状态同步任务。")

    assert result["need_tool"] is True
    assert result["tool_name"] == "script_task_tool"
    assert result["tool_result"] is None
    assert "confirm=true" in result["error"]
    assert "fallback_node" in _log_text(tmp_path)


def test_high_risk_task_with_confirm_can_execute(tmp_path):
    service = _service(tmp_path)

    result = service.chat("触发订单退款状态同步任务。", confirm=True)

    assert result["need_tool"] is True
    assert result["tool_name"] == "script_task_tool"
    assert result["tool_result"]["status"] == "submitted"
    assert result["tool_result"]["task_id"].startswith("task_")
    assert result["error"] is None


def test_node_exception_enters_fallback(tmp_path):
    service = _service(tmp_path, rag_service=BrokenRagService())

    result = service.chat("订单退款流程是什么？")

    assert result["status"] == "error"
    assert "forced retrieve failure" in result["error"]
    assert "fallback_node" in _log_text(tmp_path)
