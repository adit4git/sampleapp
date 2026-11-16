"""Advisory fee rate. Deterministic; never call a model from this module.

Ported from the prototype's `advRate`. The tier schedule is ILLUSTRATIVE (it is the
prototype's) and must be replaced by the firm's schedule from the billing system of
record before any client-facing use.
"""
from __future__ import annotations

from decimal import Decimal

# (tier size, annual rate). None = no upper bound.
ILLUSTRATIVE_TIERS: tuple[tuple[Decimal | None, Decimal], ...] = (
    (Decimal("1000000"), Decimal("0.0120")),
    (Decimal("4000000"), Decimal("0.0100")),
    (Decimal("5000000"), Decimal("0.0080")),
    (None, Decimal("0.0060")),
)
ADVISORY_FEE_MAX = Decimal("0.0175")


def blended_advisory_rate(
    household_value: Decimal,
    tiers: tuple[tuple[Decimal | None, Decimal], ...] = ILLUSTRATIVE_TIERS,
) -> Decimal:
    """Blended annual advisory fee rate for a household value.

    Returns the first tier's rate when the value is zero, as the prototype does.
    """
    if not isinstance(household_value, Decimal):
        raise TypeError("household_value must be Decimal")
    if household_value < 0:
        raise ValueError("household_value must not be negative")
    if household_value == 0:
        return tiers[0][1]

    left = household_value
    fee = Decimal(0)
    for size, rate in tiers:
        part = left if size is None else min(left, size)
        fee += part * rate
        left -= part
        if left <= 0:
            break
    return fee / household_value
