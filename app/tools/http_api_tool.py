from __future__ import annotations

from app.tools.mock_tools import load_mock_data


def http_api_tool(user_id: str) -> dict:
    users = load_mock_data("users.json")
    user = users.get(user_id.upper())
    if not user:
        raise ValueError(f"未找到用户 {user_id} 的模拟账号数据")
    return {"user_id": user_id.upper(), **user}
