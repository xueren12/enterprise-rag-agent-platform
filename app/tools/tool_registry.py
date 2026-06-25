from __future__ import annotations

from app.tools.http_api_tool import http_api_tool
from app.tools.script_task_tool import script_task_tool
from app.tools.sql_query_tool import sql_query_tool
from app.tools.tool_plan import HttpApiInput, ScriptTaskInput, SqlQueryInput


TOOL_REGISTRY = {
    "sql_query_tool": {
        "name": "sql_query_tool",
        "description": "查询模拟订单、退款等业务数据",
        "args_schema": SqlQueryInput,
        "handler": sql_query_tool,
        "risk_level": "low",
    },
    "http_api_tool": {
        "name": "http_api_tool",
        "description": "模拟调用企业内部 HTTP API 查询用户或账号状态",
        "args_schema": HttpApiInput,
        "handler": http_api_tool,
        "risk_level": "medium",
    },
    "script_task_tool": {
        "name": "script_task_tool",
        "description": "模拟触发后台脚本任务",
        "args_schema": ScriptTaskInput,
        "handler": script_task_tool,
        "risk_level": "high",
    },
}
