from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import MOCK_DATA_DIR


def load_mock_data(filename: str) -> dict[str, Any]:
    path = Path(MOCK_DATA_DIR) / filename
    return json.loads(path.read_text(encoding="utf-8"))
