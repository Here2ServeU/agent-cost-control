"""STEP 3: DETECT THE LOOP BEFORE THE CAP IS REACHED.

The cap is the seatbelt; it works, and it costs you the whole budget to
use. Loop detection is the thing that stops the car before the crash,
and it costs you three or four steps.

Three shapes, and all three are just "the agent is not making progress":

  stuck      the same action on the same target, again and again
  bouncing   A, B, A, B; each one undoing the other
  drifting   never repeats, never converges; new field every time,
             nothing ever finished

Stuck and bouncing are cheap and certain. Drifting needs a progress
signal from your own task, so it is the one you tune. The step ceiling
sits underneath all three: whatever the detector misses, the ceiling
catches.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class LoopDetector:
    stuck_threshold: int = 3            # same signature this many times in a row
    bounce_cycles: int = 3              # A,B repeated this many times
    drift_window: int = 12              # steps allowed with no progress
    enabled: bool = True
    history: deque = field(default_factory=lambda: deque(maxlen=64))
    steps_since_progress: int = 0

    def observe(self, action: dict, made_progress: bool) -> str | None:
        """Return a reason string when the run should stop, else None."""
        sig = f"{action['type']}:{action['target']}"
        self.history.append(sig)
        self.steps_since_progress = 0 if made_progress else self.steps_since_progress + 1
        if not self.enabled:
            return None

        h = list(self.history)

        # stuck
        if len(h) >= self.stuck_threshold and len(set(h[-self.stuck_threshold:])) == 1:
            return f"stuck: '{sig}' repeated {self.stuck_threshold} times"

        # bouncing: the last 2*n steps are an alternating pair
        n = self.bounce_cycles * 2
        if len(h) >= n:
            tail = h[-n:]
            if len(set(tail)) == 2 and all(tail[i] == tail[i % 2] for i in range(n)):
                return f"bouncing: '{tail[0]}' <-> '{tail[1]}' for {self.bounce_cycles} cycles"

        # drifting
        if self.steps_since_progress >= self.drift_window:
            return f"drifting: {self.steps_since_progress} steps with no progress"

        return None
