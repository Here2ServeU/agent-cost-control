# The Capstone: Safe to Leave Running Overnight

**Sections:** 6 · **The module where all six mechanisms land on one agent.**

## Install what you need

Python 3.10+ and `prometheus-client` for steps 0 to 5. Step 6 also needs **Docker Desktop**
(Prometheus, the Pushgateway and Grafana run in containers). Full instructions for macOS,
Windows and Linux are in the [course README](../../README.md#install-the-tools).

```bash
# macOS
brew install python git
brew install --cask docker            # open Docker Desktop once to finish setup
```

```powershell
# Windows (PowerShell)
winget install Python.Python.3.12
winget install Docker.DockerDesktop   # restart when it asks
```

```bash
# Linux (Ubuntu/Debian)
sudo apt install -y python3 python3-venv git
curl -fsSL https://get.docker.com | sudo sh
```

Then, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`timeout` in step 0 is a Linux command. On macOS use `gtimeout` (from
`brew install coreutils`), or just press Ctrl-C after twenty seconds.

## The code

Everything below is the repo the session builds. It runs offline, for free, and gives the
same numbers every time.

---

You start with an uninstrumented agent and an input that makes it loop.
Six steps later, that same agent stops on its own, in seconds, at a cost
you chose in advance.

Nothing here calls a paid API. The model is simulated so the whole thing
runs offline, for free, and gives the same numbers every time. Swap one
class for a real client and every other file keeps working; that is the
point of putting the usage block behind one interface.

```bash
pip install -r requirements.txt
python3 verify.py
```

`verify.py` is the capstone check. Six steps, six proofs, each one running
the agent for real and asserting on what came back.

---

## Step 0: the before picture

```bash
timeout 20 python3 naive_agent.py --input samples/malformed.json
```

Steps scroll by. Not one number tells you what they cost. It will not
stop, because nothing in it can stop. That is the whole problem, and it
is worth watching for twenty seconds before you fix it.

---

## Step 1: instrument it

**`agent/metrics.py`, `agent/pricing.py`**

Cost, tokens split by direction, and four labels chosen once: **agent,
team, run, result**.

```bash
python3 run_agent.py --input samples/good.json
```

Every step now prints what it cost and what the run has cost so far.

One thing worth getting right the first time: `run` is **not** a
Prometheus label. A label with one value per run is a cardinality bomb;
Prometheus falls over long before your agent does. The run id lives in
the ledger, where it costs nothing and is still there in three weeks
when somebody asks.

**Proof:** cost is greater than zero, the counters moved, and $3.00 per
million input tokens prices out to exactly $3.00.

---

## Step 2: cap it

**`agent/budget.py`**

Per run and per day, with the behaviour at the edge chosen on purpose.
A cap without a chosen behaviour is not a cap; it is a surprise.

| behaviour | what happens | when |
|---|---|---|
| `drain` | stop starting steps, finish the current one, save, exit clean | almost always |
| `stop` | finish the step, mark it capped, do not save | when partial output is worthless |
| `kill` | stop mid-step | when one more step costs more than the work |

```bash
python3 run_agent.py --input samples/malformed.json --no-loop-detect --per-run-usd 0.05
```

Loop detection off, so the only thing that can stop it is the cap. It
stops at the cap.

The daily total lives in `ledger/day-YYYY-MM-DD.json` so it survives a
restart. In production that file is a row in a database; the logic does
not change.

**Proof:** result is `capped`, and spend never crosses the number you set.

---

## Step 3: detect the loop before the cap is reached

**`agent/loops.py`**

The cap is the seatbelt. It works, and it costs you the entire budget to
use. Loop detection is what stops the car before the crash, and it costs
you three or four steps.

Three shapes, all of them just "not making progress":

- **stuck**: the same action on the same target, again and again
- **bouncing**: A, B, A, B; each one undoing the other
- **drifting**: never repeats, never converges, new field every time

```bash
python3 run_agent.py --input samples/malformed.json          # caught, ~6 steps
python3 run_agent.py --input samples/stuck.json              # caught, ~3 steps
python3 run_agent.py --input samples/drifting.json           # the expensive one
```

Stuck and bouncing are cheap and certain. Drifting needs a progress
signal from your own task, so it is the one you tune. The step ceiling
sits underneath all three: whatever the detector misses, the ceiling
catches.

**Proof:** the detector stops the same input in **6 steps / $0.067**
where the cap alone takes **14 steps / $0.146**. Less than half, and it
tells you *why* it stopped.

---

## Step 4: checkpoint, so a kill wastes nothing

**`agent/checkpoint.py`**

Without this, every safety mechanism you just built has a price: each
time a cap fires, you throw away the work that already succeeded and pay
for it again on the retry. With it, stopping is cheap; that is what
makes you willing to set the cap tight enough to matter.

```bash
python3 run_agent.py --input samples/good.json --step-ceiling 3   # dies partway
python3 run_agent.py --input samples/good.json --resume           # picks up
```

The resumed run prints `not re-paid: $0.0291`: the finished work it did
not buy twice.

Write after every completed step, not at the end. A checkpoint written
at the end is a log file. The write is atomic (`.tmp` then rename); a
half-written checkpoint is worse than none.

**Proof:** the resumed run succeeds, and carries over at least what the
killed run spent.

---

## Step 5: cost per successful task, including the failures

**`report.py`, `SUCCESS_DEFINITION` in `agent/runner.py`**

```bash
python3 report.py
```

```
  runs started            17
  succeeded                7      <- the denominator
  did not                 10      <- still counts on top
  total spend             $4.2243
  cost per request        $0.2485   (pays by the mile)
  cost per SUCCESSFUL     $0.6035   (pays for arrival)
  the gap                 143% higher, and it is the true number
  failed-run tax          $3.7971  (90% of spend)
```

The failures go on the **top**. That is the whole idea, and it is the
only number in this repo that can tell you a change made things worse
while spending less money.

The definition of success is written down in code, in one place, and
printed with the number every single time. A number without its
definition is not a measurement; it is a rumour.

**Proof:** cost per success exceeds cost per request, failures are
counted, and the definition travels with the number.

---

## Step 6: alert on burn rate, proven by triggering the loop

**`prometheus/rules/agent_alerts.yml`**

Two rules, two windows, two speeds of response:

- **fast**, one-hour window, fires in minutes; worth waking someone for
- **slow**, twenty-four-hour window, fires in hours; mention it at standup

One alert cannot do both. Fast enough to catch a runaway means waking
you for every busy afternoon.

```bash
docker compose up -d
python3 run_agent.py --input samples/malformed.json --no-caps --no-loop-detect \
  --step-ceiling 300 --push --quiet
```

Then Prometheus on **:9090**, Grafana on **:3000** (admin / admin), where
four panels are already provisioned; each is titled with the question
somebody asks out loud, not with the metric name.

Because the caps from step 2 are still there in normal operation, this
alert is not your only protection. The cap stops the bleeding whether or
not anyone answers the page. **The cap is the seatbelt; the alert is the
dashboard light.**

**Proof:** a real runaway projects **$9,145/month** against a $300 budget
at a realistic pace: well past the fast rule's threshold.

---

## The bill that never arrived

```
$ python3 verify.py

  1. Instrumented: cost, tokens, labels            PASS
  2. Capped: per run and per day, deliberately     PASS
  3. Loop caught before the cap is reached         PASS
  4. Checkpointed: a kill wastes nothing           PASS
  5. Cost per successful task, failures on top     PASS
  6. Alerted on burn rate, proven by triggering it PASS

  All six hold.
```

Take the number the uncapped runaway reaches in 300 steps and extrapolate
it over a night. Then take what the same input costs now: **six steps,
under seven cents, stopped with a reason attached.** That difference is
the bill that never arrived, and it is the thing to show anyone who asks
what this work was for.

---

## Layout

```
agent/metrics.py      step 1   what it cost, and who pays
agent/pricing.py      step 1   tokens into dollars, in one file
agent/budget.py       step 2   per run, per day, behaviour chosen
agent/loops.py        step 3   stuck, bouncing, drifting
agent/checkpoint.py   step 4   save after every completed step
agent/ledger.py       step 5   one line per run, appended, never edited
agent/runner.py       all six, in one readable loop
report.py             step 5   the arithmetic
verify.py             the capstone check
prometheus/rules/     step 6   fast and slow burn rate
grafana/dashboards/   step 6   four panels, not fourteen
```

Read `agent/runner.py` top to bottom. Every mechanism in this course
appears exactly once, in the order it has to fire: record the step, save
the checkpoint, check for a loop, then check the cap. That order is not
an accident; you want the cost of the step that killed you, and you want
the cheap stop to fire before the expensive one.

---

## Knobs

`config.json`:

```json
{
  "step_ceiling": 40,
  "per_run_usd": 0.15,
  "per_day_usd": 10.0,
  "on_breach": "drain",
  "caps_enabled": true,
  "loop_detection": true,
  "checkpoints": true
}
```

The three `*_enabled` flags exist so you can turn a mechanism off and
measure what it was buying you. That is how step 3's proof works, and it
is how you should argue for any of this to someone who has to approve it.

---

[← Course home](../../README.md) · [← Module 6](../module-6/README.md)
