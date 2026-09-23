#!/usr/bin/env python3
"""STEP 0 - THE BEFORE PICTURE.

This is the agent you start with. It is honest about nothing.

It has no cost accounting, no cap, no loop detection, no checkpoints,
no definition of success and no alert. It will happily run until you
notice, which on a Tuesday night means until the morning.

Run it against the looping input and watch it never stop:

    timeout 20 python3 naive_agent.py --input samples/malformed.json

You will see steps go by. You will not see a single number that tells
you what those steps cost. That is the whole problem.
"""
import argparse
import json
import time

from agent.llm import SimulatedModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    task = json.loads(open(args.input).read())
    model = SimulatedModel(task)

    step = 0
    while True:                       # no ceiling. none. this is the bug.
        step += 1
        action, _usage = model.next_action()
        print(f"step {step:>4}  {action['type']}:{action['target']}")
        if action["type"] == "final":
            print("done")
            return
        time.sleep(0.05)


if __name__ == "__main__":
    main()
