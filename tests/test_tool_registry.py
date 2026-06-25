from app.tools.tool_registry import TOOL_REGISTRY


def test_tool_registry_contains_three_required_tools():
    assert set(TOOL_REGISTRY) == {
        "sql_query_tool",
        "http_api_tool",
        "script_task_tool",
    }
    for name, item in TOOL_REGISTRY.items():
        assert item["name"] == name
        assert item["description"]
        assert item["args_schema"]
        assert callable(item["handler"])
        assert item["risk_level"] in {"low", "medium", "high"}
