from __future__ import annotations

from app.tools.mock_tools import load_mock_data


def sql_query_tool(order_id: str) -> dict:
    orders = load_mock_data("orders.json")
    order = orders.get(order_id)
    if not order:
        raise ValueError(f"未找到订单 {order_id} 的模拟业务数据")
    return {"order_id": order_id, **order}
