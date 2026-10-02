"""STEP 1a: turning tokens into dollars.

Prices are per one million tokens, in US dollars. They change; this is
one file so that when they change you edit one file. Input and output
are priced differently, which is why the usage block has two numbers
and why you must never average them into one.
"""
from __future__ import annotations

PRICES_USD_PER_MTOK: dict[str, dict[str, float]] = {
    # model         input   output
    "haiku":  {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus":   {"input": 15.00, "output": 75.00},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICES_USD_PER_MTOK[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
