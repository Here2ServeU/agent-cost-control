# The Agent Cost Problem

A seven-session course on why AI agents cost what they cost, and how to build one you
can leave running overnight.

An agent can spend four figures in a night while every dashboard stays green. Not because
anything broke, but because nothing in it was watching. This course fixes that, in order,
and ends with a repo where every mechanism is proven by running it with the mechanism
turned off and then turned on.

```bash
git clone https://github.com/Here2ServeU/agent-cost-control
cd agent-cost-control/modules/capstone
pip install -r requirements.txt
python3 verify.py
```

---

## The course

| | Module | What it gives you | Runtime |
|---|---|---|---|
| **1** | [Why Agent Cost Is Different](modules/module-1/README.md) | Why the bill behaves unlike any other line on your invoice | ~45 min |
| **2** | [Making Cost Visible](modules/module-2/README.md) | The usage block, the envelope, and four labels | ~50 min |
| **3** | [Budget Caps and Kill Switches](modules/module-3/README.md) | Per-run and per-day caps, and the behaviour you choose | ~50 min |
| **4** | [Loops, Retries, and the Cost of Failure](modules/module-4/README.md) | Step limits, loop shapes, checkpoints, the failed-run tax | ~50 min |
| **5** | [Cost Per Successful Task](modules/module-5/README.md) | The only number that catches a change making things worse | ~50 min |
| **6** | [Operating It](modules/module-6/README.md) | Four panels, two alerts, routing, caching, a weekly habit | ~50 min |
| **★** | [**The Capstone**](modules/capstone/README.md) | All six on one agent, each one proven by running it | ~45 min |

Each module folder holds two decks and, from module 2 on, the finished versions of the
diagrams drawn live during the session.

---

## What the capstone proves

The capstone is not a summary slide. It is a runnable repo with a check that fails if any
of the six stops being true:

```
$ python3 verify.py

  1. Instrumented: cost, tokens, labels             PASS   $0.0671 / 6 steps
  2. Capped: per run and per day, deliberately      PASS   capped at $0.0446
  3. Loop caught before the cap is reached          PASS   6 steps vs 14
  4. Checkpointed: a kill wastes nothing            PASS   $0.0291 not re-paid
  5. Cost per successful task, failures on top      PASS   129% above per-request
  6. Alerted on burn rate, proven by triggering it  PASS   $9,145/mo vs $300

  All six hold.
```

Every one of those proofs works by turning the mechanism off first. That is not only how
the tests work; it is how you get this work approved. "Trust me" gets no budget. "Here is
the same run with the cap off" does.

Nothing calls a paid API. The model is simulated, so the whole repo runs offline, free and
deterministic. Swapping in a real client touches one class.

---

## The six steps, and what each one buys

| | Step | Buys you |
|---|---|---|
| 1 | Instrument it | you can see it |
| 2 | Cap it | it is bounded |
| 3 | Detect the loop | 6 steps, not 14 |
| 4 | Checkpoint | stopping is cheap |
| 5 | Cost per successful task | the true number |
| 6 | Alert on burn rate | you find out while it is happening |

Each one is close to useless alone. Instrumentation with no cap means watching the money
leave in high resolution. A cap with no checkpointing means every stop throws away work.
They only work together, and together they are boring — which is the goal. An agent nobody
has to watch is the deliverable.

The whole safety layer is under four hundred lines. It is not hard. It is just never the
thing anybody does first, because it is not the demo.

---

## Two decks per module

- **Presenter** — hidden reference pages for the segments drawn live on the iPad, with the
  finished panel rendered beside the drawing steps, plus the full script in the speaker
  notes. These are not for students.
- **Student** — the same session with the hidden pages, the production marks and the notes
  stripped out.

---

## Before you start

Git, Python 3.10+, VS Code, and Docker Desktop for the last two sessions.

- **macOS** — https://youtu.be/8ZIiXg4XOY0
- **Windows** — https://youtu.be/3e2-GRBibWc

---

## The idea worth keeping

Every one of the six is a decision moved earlier. A cap is deciding what a task is worth
before it runs instead of after. A step limit is deciding how long is too long while you
are calm rather than during an incident. A definition of success is deciding what you mean
before you report a number rather than in a meeting.

None of those are hard in advance. All of them are hard at three in the morning.

That is what cost control actually is. Not cleverness — deciding early, writing it down,
and letting a machine enforce it while you sleep.

---

Built by [Emmanuel Naweji](https://github.com/Here2ServeU). Licensed under the MIT License.
