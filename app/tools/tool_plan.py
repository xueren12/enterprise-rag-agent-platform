from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class SqlQueryInput(BaseModel):
    order_id: str = Field(min_length=1)


class HttpApiInput(BaseModel):
    user_id: str = Field(min_length=1)


class ScriptTaskInput(BaseModel):
    task_name: str = Field(min_length=1)
    confirm: bool = False


class ToolCallPlan(BaseModel):
    need_tool: bool
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    reason: str


class ValidatedToolCall(BaseModel):
    valid: bool
    need_tool: bool
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


def plan_tool_call(question: str, confirm: bool = False) -> ToolCallPlan:
    order_id = _extract_order_id(question)
    user_id = _extract_user_id(question)
    task_name = _extract_task_name(question)

    if _looks_like_task_question(question):
        args: dict[str, Any] = {"confirm": confirm}
        if task_name:
            args["task_name"] = task_name
        return ToolCallPlan(
            need_tool=True,
            tool_name="script_task_tool",
            tool_args=args,
            reason="用户问题包含触发、同步任务或后台任务意图，需要调用脚本任务工具。",
        )

    if _looks_like_user_question(question):
        args = {"user_id": user_id} if user_id else {}
        return ToolCallPlan(
            need_tool=True,
            tool_name="http_api_tool",
            tool_args=args,
            reason="用户问题包含用户账号状态查询意图，需要调用内部 API 工具。",
        )

    if _looks_like_order_question(question):
        args = {"order_id": order_id} if order_id else {}
        return ToolCallPlan(
            need_tool=True,
            tool_name="sql_query_tool",
            tool_args=args,
            reason="用户问题包含订单或退款状态查询意图，需要调用业务数据查询工具。",
        )

    return ToolCallPlan(
        need_tool=False,
        tool_name=None,
        tool_args={},
        reason="未识别到需要业务工具处理的意图。",
    )


def validate_tool_call(plan: ToolCallPlan) -> ValidatedToolCall:
    if not plan.need_tool:
        return ValidatedToolCall(valid=True, need_tool=False)

    if not plan.tool_name:
        return ValidatedToolCall(
            valid=False,
            need_tool=True,
            error="工具调用计划缺少 tool_name。",
        )

    from app.tools.tool_registry import TOOL_REGISTRY

    registry_item = TOOL_REGISTRY.get(plan.tool_name)
    if not registry_item:
        return ValidatedToolCall(
            valid=False,
            need_tool=True,
            tool_name=plan.tool_name,
            tool_args=plan.tool_args,
            error=f"工具不存在：{plan.tool_name}。",
        )

    schema = registry_item["args_schema"]
    try:
        parsed = schema.model_validate(plan.tool_args)
    except ValidationError as exc:
        message = _format_validation_error(exc)
        return ValidatedToolCall(
            valid=False,
            need_tool=True,
            tool_name=plan.tool_name,
            tool_args=plan.tool_args,
            error=f"工具参数校验失败：{message}",
        )

    parsed_args = parsed.model_dump()
    if registry_item["risk_level"] == "high" and parsed_args.get("confirm") is not True:
        return ValidatedToolCall(
            valid=False,
            need_tool=True,
            tool_name=plan.tool_name,
            tool_args=parsed_args,
            error="高风险工具必须显式设置 confirm=true 后才能执行。",
        )

    return ValidatedToolCall(
        valid=True,
        need_tool=True,
        tool_name=plan.tool_name,
        tool_args=parsed_args,
    )


def execute_tool_call(plan: ToolCallPlan) -> dict[str, Any]:
    validated = validate_tool_call(plan)
    if not validated.need_tool:
        return {
            "success": True,
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "error": None,
        }
    if not validated.valid:
        return {
            "success": False,
            "tool_name": validated.tool_name,
            "tool_args": validated.tool_args,
            "tool_result": None,
            "error": validated.error,
        }

    from app.tools.tool_registry import TOOL_REGISTRY

    registry_item = TOOL_REGISTRY[validated.tool_name or ""]
    try:
        result = registry_item["handler"](**validated.tool_args)
    except Exception as exc:  # Keep tool failure from crashing the Agent flow.
        return {
            "success": False,
            "tool_name": validated.tool_name,
            "tool_args": validated.tool_args,
            "tool_result": None,
            "error": f"工具执行失败：{exc}",
        }

    return {
        "success": True,
        "tool_name": validated.tool_name,
        "tool_args": validated.tool_args,
        "tool_result": result,
        "error": None,
    }


def _extract_order_id(question: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", question)
    return match.group(0) if match else None


def _extract_user_id(question: str) -> str | None:
    match = re.search(r"\bU\d+\b", question, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def _extract_task_name(question: str) -> str | None:
    match = re.search(r"\b[a-z]+(?:_[a-z0-9]+)+\b", question, flags=re.IGNORECASE)
    if match:
        return match.group(0).lower()
    if "退款" in question and ("同步" in question or "任务" in question):
        return "refund_status_sync"
    if "错误码" in question and ("刷新" in question or "任务" in question):
        return "error_code_refresh"
    return None


def _looks_like_order_question(question: str) -> bool:
    return ("订单" in question or "退款状态" in question) and (
        "查询" in question or "查看" in question or _extract_order_id(question) is not None
    )


def _looks_like_user_question(question: str) -> bool:
    return ("用户" in question or "账号" in question) and (
        "查询" in question or "查看" in question or _extract_user_id(question) is not None
    )


def _looks_like_task_question(question: str) -> bool:
    task_keywords = ("触发", "同步任务", "后台任务", "执行任务", "refund_status_sync", "error_code_refresh")
    return any(keyword in question for keyword in task_keywords)


def _format_validation_error(exc: ValidationError) -> str:
    errors = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", ()))
        msg = item.get("msg", "参数不合法")
        errors.append(f"{loc}: {msg}" if loc else msg)
    return "；".join(errors)
