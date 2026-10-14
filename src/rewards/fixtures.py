"""Load synthetic task fixtures from JSON."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Task


def load_tasks(path: str | Path) -> list[Task]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Task(t["task_id"], t["user_id"], t["status"], datetime.fromisoformat(t["completed_at"]))
        for t in data["tasks"]
    ]
