"""STEP 4 - CHECKPOINT, SO A KILL DOES NOT WASTE COMPLETED WORK.

Without this, every safety mechanism you just built has a cost: each
time a cap fires or a loop is caught, you throw away everything that
already worked and pay for it again on the retry.

With it, stopping is cheap. That is what makes you willing to set the
cap tight enough to matter.

Write after every completed step, not at the end. A checkpoint written
at the end is a log file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Checkpoint:
    task_id: str
    state_dir: Path = Path("ledger/checkpoints")
    enabled: bool = True

    def __post_init__(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.state_dir / f"{self.task_id}.json"

    def save(self, completed: list[dict[str, Any]], spent_usd: float) -> None:
        if not self.enabled:
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"completed": completed, "spent_usd": spent_usd}, indent=2))
        tmp.replace(self.path)          # atomic; a half-written checkpoint is worse than none

    def load(self) -> tuple[list[dict[str, Any]], float]:
        if not self.enabled or not self.path.exists():
            return [], 0.0
        d = json.loads(self.path.read_text())
        return d.get("completed", []), d.get("spent_usd", 0.0)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
