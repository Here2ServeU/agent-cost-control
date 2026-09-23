"""MODULE 4 - CHECKPOINTS, SO STOPPING STOPS BEING EXPENSIVE.

After every completed step, write down the run id, the step number and
its result. At the start of a run, look for a checkpoint with the same
run id and skip ahead. Without this, every cap, every loop stop and
every retry throws away the work that already succeeded and pays for it
again.

Write after every step, not at the end. A checkpoint written at the end
is a log file. And write it atomically - to a .tmp file, then rename -
because a half-written checkpoint is worse than none.

  CHECKPOINTS=on|off     (default on) - off exists so you can measure
                         what it saves

Files live in checkpoints/<run-id>.json. In production this is Redis or
a table; the logic is the same.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DIR = Path("checkpoints")


def enabled() -> bool:
    return os.environ.get("CHECKPOINTS", "on").lower() not in ("off", "false", "0", "no")


class Checkpoint:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.on = enabled()
        self.path = DIR / f"{run_id}.json"

    def load(self) -> tuple[list[dict[str, Any]], float]:
        """(completed steps, dollars already spent on them)."""
        if not self.on or not self.path.exists():
            return [], 0.0
        d = json.loads(self.path.read_text())
        return d["completed"], d["spent_usd"]

    def save(self, completed: list[dict[str, Any]], spent_usd: float) -> None:
        if not self.on:
            return
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"run_id": self.run_id, "step": len(completed),
                                   "spent_usd": round(spent_usd, 8),
                                   "completed": completed}, indent=2))
        tmp.replace(self.path)

    def clear(self) -> None:
        """On success: nothing left to resume, so do not leave a stale one."""
        self.path.unlink(missing_ok=True)
