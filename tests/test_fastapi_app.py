from pathlib import Path

from fastapi.testclient import TestClient

from app.config import DOCS_DIR
from app.main import app


client = TestClient(app)


def test_knowledge_index_endpoint_builds_index():
    response = client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["indexed_chunks"] > 0


def test_agent_chat_endpoint_returns_rag_answer():
    client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})

    response = client.post(
        "/agent/chat",
        json={"question": "订单退款流程是什么？", "top_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["answer"]
    assert payload["need_tool"] is False
    assert payload["trace_id"]


def test_agent_chat_endpoint_returns_tool_result():
    client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})

    response = client.post(
        "/agent/chat",
        json={"question": "查询订单 10001 的退款状态。", "top_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["need_tool"] is True
    assert payload["tool_name"] == "sql_query_tool"
    assert payload["tool_result"]["refund_status"] == "processing"


def test_agent_chat_endpoint_honors_confirm_for_high_risk_tool():
    client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})

    rejected = client.post(
        "/agent/chat",
        json={"question": "触发订单退款状态同步任务。", "confirm": False},
    ).json()
    accepted = client.post(
        "/agent/chat",
        json={"question": "触发订单退款状态同步任务。", "confirm": True},
    ).json()

    assert rejected["tool_name"] == "script_task_tool"
    assert rejected["tool_result"] is None
    assert "confirm=true" in rejected["error"]
    assert accepted["tool_result"]["status"] == "submitted"
    assert accepted["error"] is None


def test_trace_endpoint_filters_events_by_trace_id():
    client.post("/knowledge/index", json={"docs_dir": str(DOCS_DIR)})
    chat_payload = client.post(
        "/agent/chat",
        json={"question": "查询用户 U1001 的账号状态。"},
    ).json()

    response = client.get(f"/trace/{chat_payload['trace_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] == chat_payload["trace_id"]
    assert payload["events"]
    assert all(event["trace_id"] == chat_payload["trace_id"] for event in payload["events"])


def test_trace_endpoint_returns_empty_events_for_missing_trace():
    response = client.get("/trace/not-exist-trace-id")

    assert response.status_code == 200
    assert response.json() == {"trace_id": "not-exist-trace-id", "events": []}
