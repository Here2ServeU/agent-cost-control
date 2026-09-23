"""The ledger: one line per run, appended, never edited.

Prometheus answers "what is happening right now". The ledger answers
"what happened, exactly, and what did it cost" - which is the question
you get asked in a meeting three weeks later.

It is a JSONL file. It is boring on purpose.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

LEDGER = Path("ledger/runs.jsonl")


def append(record: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": time.time(), **record}
    with LEDGER.open("a") as f:
        f.write(json.dumps(record) + "\n")


def read_all() -> list[dict[str, Any]]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
