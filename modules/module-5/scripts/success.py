"""MODULE 5 - SUCCESS.md, TURNED INTO A FUNCTION.

One place, in code, and printed next to the number every single time.
A number without its definition is not a measurement; it is a rumour.
"""
from __future__ import annotations

from typing import Any

SUCCESS_DEFINITION = "finished with an amount between $0.01 and $50,000 and a non-empty vendor"
AMOUNT_RANGE = (0.01, 50_000.00)


def is_success(output: dict[str, Any] | None) -> bool:
    """True or false. Right shape, required fields present, numbers plausible."""
    if not isinstance(output, dict):
        return False
    amount, vendor = output.get("amount"), output.get("vendor")
    if not isinstance(amount, (int, float)) or not AMOUNT_RANGE[0] <= amount <= AMOUNT_RANGE[1]:
        return False
    return isinstance(vendor, str) and bool(vendor.strip())
