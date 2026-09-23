# Module 1: Why Agent Cost Is Different

Why an agent's bill behaves unlike any other line on your cloud invoice, and why the dashboard stayed green all night.

**Runtime:** ~45 min · 6 sections

## What this module covers

1. A single agent can spend four figures overnight without tripping anything
2. Cost scales with decisions, not with requests
3. The four questions you cannot answer today
4. What the rest of the course builds

## Install what you need

Python 3, Git and a terminal (the one inside VS Code is fine). No packages: module 1 uses
only the Python standard library. Full instructions for macOS, Windows and Linux are in the
[course README](../../README.md#install-the-tools).

```bash
# macOS
brew install python git
brew install --cask visual-studio-code
```

```powershell
# Windows (PowerShell)
winget install Python.Python.3.12
winget install Git.Git
winget install Microsoft.VisualStudioCode
```

```bash
# Linux (Ubuntu/Debian)
sudo apt install -y python3 git
```

Check with `python3 --version` (Windows: `py --version`) and `git --version`.

Videos: [macOS](https://youtu.be/8ZIiXg4XOY0) · [Windows](https://youtu.be/3e2-GRBibWc)

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `run_agent.py` | The course agent as you find it: no cost accounting, no cap, no ceiling. `--verbose` prints the raw usage block from every model call |
| `price_run.py` | Checks your hand arithmetic, then extrapolates two minutes of the runaway into your overnight number |
| `sim_model.py` | The simulated model. It returns realistic token usage without calling anything, so this costs nothing |
| `samples/normal.json` | A healthy invoice. Finishes in six calls |
| `samples/malformed.json` | The record from the 3am runaway. It never finishes |

## Build it: price your own agent

```bash
cd modules/module-1/scripts
```

**1. Run a healthy input and read the usage blocks.**

```bash
python3 run_agent.py --input samples/normal.json --verbose
```

Every step prints `input_tokens` and `output_tokens`: the two numbers you care about.

**2. Do the arithmetic by hand.** Add up the input tokens and the output tokens separately.
Multiply each by its rate (the course uses $3.00 per million input tokens and $15.00 per
million output tokens) and add the two together. Write the number down.

**3. Count the model calls.** That is your step count.

```bash
python3 run_agent.py --input samples/normal.json --verbose | grep -c 'usage'
```

```powershell
# Windows
(py run_agent.py --input samples/normal.json --verbose | Select-String 'usage').Count
```

**4. Check your arithmetic.**

```bash
python3 run_agent.py --input samples/normal.json --verbose | python3 price_run.py
```

If your number does not match, you have a rate wrong. It is better to find that now than
in a report.

**5. Run the one that cannot finish, with a hard time limit.** It will not stop on its own.
Never remove the limit.

```bash
python3 run_agent.py --input samples/malformed.json --verbose --max-seconds 120
```

`--max-seconds` works everywhere. On Linux you can use `timeout 120 python3 run_agent.py …`
instead. macOS does not ship a `timeout` command; `brew install coreutils` adds one called
`gtimeout`.

**6. Extrapolate your own $4,200.**

```bash
python3 run_agent.py --input samples/malformed.json --verbose --max-seconds 120 \
  | python3 price_run.py --seconds 120 --hours 9.5
```

```powershell
# Windows
py run_agent.py --input samples/malformed.json --verbose --max-seconds 120 | py price_run.py --seconds 120 --hours 9.5
```

That multiplies calls in two minutes × cost per call × 30 to get one hour, then × 9.5
hours, which is how long it took anyone to notice. The result is what one unnoticed loop
costs you. Every control in the next five modules is measured against it.

To price your own agent instead, use its real rates: `--input-rate 0.80 --output-rate 4.00`.

## Exercises before module 2

1. Price one healthy run by hand. Keep input and output separate.
2. Divide total cost by model calls to get cost per step. Module 4 uses it.
3. Compare the input:output **token** ratio with the input:output **cost** ratio.
   `price_run.py` prints both.
4. Watch input grow: the tokens sent on call 6 are more than double those on call 1,
   because each call resends the history.
5. Take your overnight number to whoever owns the budget and ask: *"Is that an acceptable
   worst case?"*

---

[← Course home](../../README.md) · [Next: Module 2 →](../module-2/README.md)
