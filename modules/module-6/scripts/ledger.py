"""The receipts: two append-only files, one line per record, never edited.

  ledger/calls.jsonl   one line per model call   (what it cost, and for whom)
  ledger/runs.jsonl    one line per run          (how it ended, and what it cost)

Prometheus answers "what is happening right now". These files answer
"what happened, exactly, and what did it cost"; that is the question
you get asked in a meeting three weeks later. The run id lives here,
where it costs nothing, and never on a Prometheus label.

They are JSONL files. They are boring on purpose. Delete the ledger/
folder to start again from zero.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

LEDGER_DIR = Path("ledger")
CALLS = LEDGER_DIR / "calls.jsonl"
RUNS = LEDGER_DIR / "runs.jsonl"


def _append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"ts": round(time.time(), 3), **record}) + "\n")


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_call(record: dict[str, Any]) -> None:
    _append(CALLS, record)


def append_run(record: dict[str, Any]) -> None:
    _append(RUNS, record)


def read_calls() -> list[dict[str, Any]]:
    return _read(CALLS)


def read_runs() -> list[dict[str, Any]]:
    return _read(RUNS)


def parse_window(text: str) -> float:
    """'30d', '7d', '12h', '15m', '90s' -> seconds."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd])", text.strip())
    if not m:
        raise ValueError(f"window must look like 30d, 12h, 15m or 90s; got {text!r}")
    return float(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
