from app.tools.tool_plan import ToolCallPlan, execute_tool_call


def test_execute_sql_query_tool_successfully():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="sql_query_tool",
        tool_args={"order_id": "10001"},
        reason="test",
    )
    result = execute_tool_call(plan)
    assert result["success"] is True
    assert result["tool_result"]["refund_status"] == "processing"


def test_execute_script_task_requires_confirm():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="script_task_tool",
        tool_args={"task_name": "refund_status_sync"},
        reason="test",
    )
    result = execute_tool_call(plan)
    assert result["success"] is False
    assert result["tool_result"] is None
    assert "confirm=true" in result["error"]


def test_execute_script_task_with_confirm():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="script_task_tool",
        tool_args={"task_name": "refund_status_sync", "confirm": True},
        reason="test",
    )
    result = execute_tool_call(plan)
    assert result["success"] is True
    assert result["tool_result"]["status"] == "submitted"
    assert result["tool_result"]["task_id"].startswith("task_")
