"""MODULE 4 - THE STEP CEILING, AND LOOP DETECTION (THE SIMPLE KIND).

Three ways for an agent to not make progress:

  stuck      the same call on the same thing, again and again
  bouncing   A, B, A, B; each one undoing the other
  drifting   never repeats, never finishes

The detector below catches the first two cheaply: it keeps the last few
tool calls - the name and the argument together as one string - and
stops when the agent proposes one it has only just made. Drifting never
repeats, so the detector cannot see it; the step ceiling underneath
catches whatever the detector misses.

  MAX_STEPS         the ceiling, in model calls           (default 15)
"""
from __future__ import annotations

import os
from collections import deque


class StepLimitReached(Exception):
    pass


class LoopDetected(Exception):
    pass


def max_steps() -> int:
    return int(os.environ.get("MAX_STEPS", 15))


def check_ceiling(steps_taken: int, ceiling: int) -> None:
    """Checked before each call. A step limit is not a budget cap; say which one fired."""
    if steps_taken >= ceiling:
        raise StepLimitReached(
            f"step limit reached: {steps_taken} model calls against MAX_STEPS={ceiling}. "
            f"Raise MAX_STEPS if this task genuinely needs more.")


class LoopDetector:
    def __init__(self, window: int = 4, enabled: bool = True) -> None:
        self.recent: deque[str] = deque(maxlen=window)
        self.enabled = enabled

    def check(self, action: dict) -> None:
        """Before acting on the call the model proposed, look for it in the recent ones."""
        signature = f"{action['type']}({action['target']})"
        if self.enabled and signature in self.recent:
            raise LoopDetected(
                f"loop detected: {signature} was proposed again; recent calls were "
                f"{' -> '.join(self.recent)}")
        self.recent.append(signature)
