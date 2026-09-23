# Module 4: Loops, Retries, and the Cost of Failure

Step limits, the three loop shapes, checkpoints, and the failed-run tax.

**Runtime:** ~50 min · 6 sections

## What this module covers

1. Stuck, bouncing, drifting: three ways to not make progress
2. The step ceiling underneath all of them
3. Checkpoints, so stopping stops being expensive
4. The failed-run tax, as a share of spend

## Install what you need

Nothing new beyond module 2: Python 3, a virtual environment and `prometheus-client`.
Full instructions are in the [course README](../../README.md#install-the-tools).

```bash
# macOS / Linux
cd modules/module-4/scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows (PowerShell)
cd modules\module-4\scripts
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Checkpoints are written to files in `checkpoints/`. If you already run Redis you can use
that instead, but you do not need it.

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `run_agent.py` | The module 3 agent (caps and switch still on), plus the step limit, loop detection, checkpoints and retries |
| `loops.py` | `MAX_STEPS`, and a detector that remembers the last four tool calls and stops on a repeat |
| `checkpoint.py` | Saves after every completed step, atomically; on restart it skips ahead |
| `failed_run_tax.py` | Reads your recorded runs and prints the share of spend that bought nothing |
| `budget.py`, `kill_switch.py`, `ledger.py`, `metrics_server.py` | From modules 2 and 3, unchanged |
| `samples/loop.json` | **Stuck**: the same call on the same field, forever |
| `samples/malformed.json` | **Bouncing**: parse, validate, parse, validate |
| `samples/drifting.json` | **Drifting**: never repeats, never finishes. The detector cannot see it; the ceiling catches it |
| `samples/flaky.json` | A good invoice behind a flaky upstream: step 4 fails the first two times |

| Variable / flag | Default | Meaning |
|---|---|---|
| `MAX_STEPS` | `15` | the step ceiling |
| `CHECKPOINTS` | `on` | `off` to measure what checkpoints save |
| `--run-id NAME` | random | a fixed name, so a second run finds the first run's checkpoint |
| `--retries N` | `1` | attempts before giving up |
| `--no-loop-detect` | | turn the detector off, to watch the ceiling work alone |
| `--stop-after N` | | interrupt after N calls: a Ctrl-C you can script |

## Build it: five stages, run after every one

```bash
cd modules/module-4/scripts
```

**Stage 1: the step limit.** Three is deliberately too low, so a normal task trips it. The
message says which limit fired, because a step limit is not a budget cap.

```bash
MAX_STEPS=3 python3 run_agent.py --input samples/normal.json
```

**Stage 2: loop detection.** The detector catches it long before the ceiling.

```bash
python3 run_agent.py --input samples/loop.json          # stuck: caught in 2 calls
python3 run_agent.py --input samples/malformed.json     # bouncing: caught in 3
python3 run_agent.py --input samples/drifting.json      # drifting: only the ceiling catches it
```

**Stage 3: checkpoints. Stop it, then resume it.** `--pace 1` slows it down enough to
press Ctrl-C partway through:

```bash
python3 run_agent.py --input samples/normal.json --run-id test-resume --pace 1
# press Ctrl-C after two or three steps (or add --stop-after 3)
cat checkpoints/test-resume.json                        # Windows: Get-Content checkpoints\test-resume.json
python3 run_agent.py --input samples/normal.json --run-id test-resume
```

The second run prints `resuming test-resume: 3 step(s) already done` and `not re-paid`:
money you did not spend twice.

**Stage 4: prove the saving.** The same failing task, the same retries, the same answer:

```bash
CHECKPOINTS=off python3 run_agent.py --input samples/flaky.json --retries 3
CHECKPOINTS=on  python3 run_agent.py --input samples/flaky.json --retries 3
```

Write down both costs (about $0.168 and $0.099). That pair is the clearest thing you can
show anyone to explain what this module was for.

**Stage 5: calculate your tax.**

```bash
python3 failed_run_tax.py --since 30d
```

That percentage is your number. In module 6 it goes on a dashboard.

### On Windows (PowerShell)

```powershell
$env:MAX_STEPS="3"; py run_agent.py --input samples/normal.json; Remove-Item Env:MAX_STEPS
$env:CHECKPOINTS="off"; py run_agent.py --input samples/flaky.json --retries 3
$env:CHECKPOINTS="on";  py run_agent.py --input samples/flaky.json --retries 3; Remove-Item Env:CHECKPOINTS
```

## Command reference

| Command | What it does |
|---|---|
| `MAX_STEPS=3 python3 run_agent.py …` | Set the step ceiling for one command only |
| `--input samples/loop.json` | An input that repeats the same call, to test your detector |
| `--input samples/flaky.json` | An input that fails partway, so retries and checkpoints have something to do |
| `--retries 3` | Try up to three times before giving up |
| `--run-id test-resume` | A fixed name, so the second run finds the first run's checkpoint |
| Ctrl-C | Stop a run by hand; the checkpoint is already written |
| `CHECKPOINTS=off` / `on` | The same task twice, to compare the cost |
| `python3 failed_run_tax.py --since 30d` | The share of the last 30 days' spend that was wasted |

Delete `ledger/` and `checkpoints/` to start again from zero.

## Panels

`panels/` holds the finished versions of the diagrams drawn live on the iPad during this
module, so you can check your drawing against them.

---

[← Course home](../../README.md) · [← Module 3](../module-3/README.md) · [Next: Module 5 →](../module-5/README.md)
