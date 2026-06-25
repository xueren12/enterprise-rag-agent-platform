from app.tools.tool_plan import ToolCallPlan, validate_tool_call


def test_high_risk_tool_without_confirm_is_rejected():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="script_task_tool",
        tool_args={"task_name": "refund_status_sync"},
        reason="test",
    )
    validated = validate_tool_call(plan)
    assert validated.valid is False
    assert "confirm=true" in validated.error


def test_high_risk_tool_with_confirm_is_valid():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="script_task_tool",
        tool_args={"task_name": "refund_status_sync", "confirm": True},
        reason="test",
    )
    validated = validate_tool_call(plan)
    assert validated.valid is True


def test_missing_tool_returns_friendly_error():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="missing_tool",
        tool_args={},
        reason="test",
    )
    validated = validate_tool_call(plan)
    assert validated.valid is False
    assert "工具不存在" in validated.error


def test_missing_args_returns_friendly_error():
    plan = ToolCallPlan(
        need_tool=True,
        tool_name="sql_query_tool",
        tool_args={},
        reason="test",
    )
    validated = validate_tool_call(plan)
    assert validated.valid is False
    assert "工具参数校验失败" in validated.error
