from app.tools.tool_plan import plan_tool_call


def test_order_id_generates_sql_query_tool_plan():
    plan = plan_tool_call("查询订单 10001 的退款状态。")
    assert plan.need_tool is True
    assert plan.tool_name == "sql_query_tool"
    assert plan.tool_args == {"order_id": "10001"}


def test_user_id_generates_http_api_tool_plan():
    plan = plan_tool_call("查询用户 U1001 的账号状态。")
    assert plan.need_tool is True
    assert plan.tool_name == "http_api_tool"
    assert plan.tool_args == {"user_id": "U1001"}


def test_task_question_generates_script_task_tool_plan():
    plan = plan_tool_call("触发订单退款状态同步任务。")
    assert plan.need_tool is True
    assert plan.tool_name == "script_task_tool"
    assert plan.tool_args["task_name"] == "refund_status_sync"


def test_plain_rag_question_does_not_trigger_tool():
    plan = plan_tool_call("订单退款流程是什么？")
    assert plan.need_tool is False
    assert plan.tool_name is None
