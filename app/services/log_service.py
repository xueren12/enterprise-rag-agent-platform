from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import TRACE_LOG_PATH


def new_trace_id() -> str:
    return uuid4().hex


class LogService:
    def __init__(self, log_path: str | Path = TRACE_LOG_PATH) -> None:
        self.log_path = Path(log_path)

    def log_event(
        self,
        *,
        trace_id: str,
        node_name: str,
        question: str,
        tool_name: str | None = None,
        tool_args: dict | None = None,
        success: bool = True,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "node_name": node_name,
            "question": question,
            "tool_name": tool_name,
            "tool_args": _summarize_tool_args(tool_args or {}),
            "success": success,
            "error": error,
        }
        if extra:
            event.update(extra)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")


def _summarize_tool_args(tool_args: dict) -> dict:
    summary = {}
    for key, value in tool_args.items():
        text = str(value)
        summary[key] = text if len(text) <= 80 else f"{text[:77]}..."
    return summary
