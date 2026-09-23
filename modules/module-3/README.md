# Module 3: Budget Caps and Kill Switches

Per-run and per-day caps, the behaviour you choose at the edge, and draining instead of killing.

**Runtime:** ~50 min · 6 sections

## What this module covers

1. A cap without a chosen behaviour is a surprise, not a cap
2. Per run and per day, and why you need both
3. Drain, stop, kill: pick one on purpose
4. The kill switch anyone on the team can flip

## Install what you need

Nothing new beyond module 2: Python 3, a virtual environment and `prometheus-client`.
Full instructions are in the [course README](../../README.md#install-the-tools).

```bash
# macOS / Linux
cd modules/module-3/scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows (PowerShell)
cd modules\module-3\scripts
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The daily total is kept in a small file, `ledger/day-YYYY-MM-DD.jsonl`, with one line per
charge so that runs happening at the same time cannot overwrite each other. In production
you would use Redis or a database row instead. You do not need Redis for this course; if
you want to try it, see the [Redis getting-started guide](https://redis.io/docs/latest/get-started).

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `run_agent.py` | The module 2 agent with caps and a switch inside the envelope |
| `budget.py` | `BudgetExceeded`, the per-run and per-day checks, and the three behaviours at the edge |
| `kill_switch.py` | `on` / `off` / `status`. A switch anyone on the team can flip while runs are in flight |
| `ledger.py`, `metrics_server.py` | From module 2, unchanged |
| `sim_model.py`, `samples/` | The simulated model and the two inputs |

All the settings are environment variables, so you can change them without editing code:

| Variable | Default | Meaning |
|---|---|---|
| `RUN_BUDGET_USD` | `0.50` | per-run cap |
| `DAILY_BUDGET_USD` | `10.00` | per-day cap, across all runs |
| `ON_BREACH` | `stop` | `stop`, `drain` or `kill` |
| `AGENT_ENABLED` | `true` | `false` refuses all new runs |

## Build it: five stages, run after every one

```bash
cd modules/module-3/scripts
```

**Stage 1: the per-run cap.** Two cents is deliberately too low, so a normal task trips it.
Read the message as if you were someone else finding it in a log.

```bash
RUN_BUDGET_USD=0.02 python3 run_agent.py --input samples/normal.json
```

**Stage 2: decide what happens.** The same trip, with each behaviour:

```bash
ON_BREACH=stop  RUN_BUDGET_USD=0.02 python3 run_agent.py --input samples/normal.json
ON_BREACH=drain RUN_BUDGET_USD=0.02 python3 run_agent.py --input samples/normal.json   # saves ledger/partial/
ON_BREACH=kill  RUN_BUDGET_USD=0.02 python3 run_agent.py --input samples/normal.json
```

**Stage 3: the daily cap.** Run this four or five times in a row. The first ones work.
Then one is refused before it makes a single model call, which costs nothing.

```bash
DAILY_BUDGET_USD=0.10 python3 run_agent.py --input samples/normal.json
```

**Stage 4: cap the runaway.** This is the one to watch. The time limit is only a backstop;
the cap fires first.

```bash
RUN_BUDGET_USD=0.50 python3 run_agent.py --input samples/malformed.json --max-seconds 120
```

It stops by itself, in about four seconds, at a cost you chose in advance. Compare that
with the overnight number you worked out in module 1.

**Stage 5: the kill switch.**

```bash
AGENT_ENABLED=false python3 run_agent.py --input samples/normal.json
```

It is refused instantly and spends nothing. Now test draining: start several runs in the
background, flip the switch while they are in flight, and check that the running ones
finish while new ones are refused.

```bash
for i in 1 2 3; do python3 run_agent.py --input samples/normal.json --pace 2 --quiet & done
python3 kill_switch.py off
python3 run_agent.py --input samples/normal.json      # refused
jobs; wait                                            # the three in flight finish
python3 kill_switch.py on
```

Delete `ledger/` to reset today's total.

### On Windows (PowerShell)

Set a variable, run the agent, then remove the variable:

```powershell
$env:RUN_BUDGET_USD="0.02"; py run_agent.py --input samples/normal.json; Remove-Item Env:RUN_BUDGET_USD
$env:AGENT_ENABLED="false"; py run_agent.py --input samples/normal.json; Remove-Item Env:AGENT_ENABLED
```

For the draining test, start the runs in two or three extra terminals with `--pace 2`,
then run `py kill_switch.py off` in another one.

## Command reference

| Command | What it does |
|---|---|
| `NAME=value python3 run_agent.py …` | Set a variable for this one command only |
| `export NAME=value` / `$env:NAME="value"` | Set it for the whole session (macOS/Linux, then PowerShell) |
| `echo $RUN_BUDGET_USD` / `echo $env:RUN_BUDGET_USD` | Check that it is set |
| `python3 run_agent.py … &` | Run in the background, so you can start several |
| `jobs` / `Get-Job` | List what you started in the background |
| `python3 kill_switch.py off` | Refuse new runs; the ones in flight finish |

## Panels

`panels/` holds the finished versions of the diagrams drawn live on the iPad during this
module, so you can check your drawing against them.

---

[← Course home](../../README.md) · [← Module 2](../module-2/README.md) · [Next: Module 4 →](../module-4/README.md)
