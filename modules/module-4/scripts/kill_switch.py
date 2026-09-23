#!/usr/bin/env python3
"""MODULE 3 - THE SWITCH ANYONE ON THE TEAM CAN FLIP.

    python3 kill_switch.py off       # refuse new runs; in-flight runs finish (draining)
    python3 kill_switch.py on        # accept work again
    python3 kill_switch.py status

AGENT_ENABLED=false does the same for one command. This file version
exists so you can flip it while runs are already in flight, and watch
them finish while new ones are refused.
"""
from __future__ import annotations

import json
import sys
import time

from budget import SWITCH_FILE, agent_enabled


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("on", "off"):
        SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        SWITCH_FILE.write_text(json.dumps({"enabled": cmd == "on", "changed": time.ctime()}))
    elif cmd != "status":
        print(__doc__)
        return 2
    print(f"agent is {'ON: accepting new runs' if agent_enabled() else 'OFF: refusing new runs'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
