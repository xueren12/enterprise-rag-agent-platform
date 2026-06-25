from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.tools.mock_tools import load_mock_data


def script_task_tool(task_name: str, confirm: bool = False) -> dict:
    if confirm is not True:
        raise ValueError("高风险任务缺少 confirm=true，已拒绝执行")

    tasks = load_mock_data("tasks.json")
    task = tasks.get(task_name)
    if not task:
        raise ValueError(f"未找到后台任务 {task_name} 的模拟配置")

    return {
        "task_name": task_name,
        "status": "submitted",
        "task_id": f"task_{uuid4().hex[:12]}",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        **task,
    }
