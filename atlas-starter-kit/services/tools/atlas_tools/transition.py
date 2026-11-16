"""Tax-efficient transition schedule. Deterministic; never call a model from this module.

Ported from the scheduling loop of the prototype's `tetPlan`. This module covers the
schedule only. Deciding WHICH holdings are transition assets (the nine conversion
routes, strategy overlap, eligibility) is a separate tool and is not ported yet.

Rules implemented (source: tax-efficient transition term sheet, as modeled in the prototype):
- The client sets a yearly NET LONG-TERM gain budget. The short-term budget is 0, so a
  lot held under a year waits one year.
- Each year: sell every loss (and zero-gain) asset first, which makes room in the budget,
  then sell gains in order of lowest gain per dollar until the budget is used.
- Tax = max(0, net gain) x rate. The default rate is ILLUSTRATIVE (23.8% federal
  long-term including NIIT; state tax excluded).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ILLUSTRATIVE_LT_RATE = Decimal("0.238")
_DUST = Decimal(1)  # positions of 1 currency unit or less are treated as fully sold
_MAX_YEARS = 200


@dataclass(frozen=True)
class TransitionAsset:
    sym: str
    market_value: Decimal
    unrealized: Decimal  # market value minus cost basis; negative = loss
    short_term: bool = False


@dataclass(frozen=True)
class TransitionYear:
    year: int
    sold: Decimal
    gains: Decimal
    losses: Decimal  # zero or negative
    net: Decimal
    tax: Decimal
    left: Decimal  # market value still waiting to transition


@dataclass(frozen=True)
class TransitionSchedule:
    budget: Decimal
    rate: Decimal
    gross_gain: Decimal
    years: tuple[TransitionYear, ...]
    total_tax: Decimal
    tax_without_service: Decimal


def _order_key(a: dict) -> Decimal:
    ratio = a["u"] / a["mv"]
    return ratio - 9 if a["u"] < 0 else ratio


def transition_schedule(
    assets: list[TransitionAsset],
    budget: Decimal,
    rate: Decimal = ILLUSTRATIVE_LT_RATE,
) -> TransitionSchedule:
    if not isinstance(budget, Decimal) or not isinstance(rate, Decimal):
        raise TypeError("budget and rate must be Decimal")
    if budget <= 0:
        raise ValueError("budget must be positive")
    if any(a.market_value <= 0 for a in assets):
        raise ValueError("every transition asset needs a positive market value")

    rem = sorted(
        ({"mv": a.market_value, "u": a.unrealized, "st": a.short_term} for a in assets),
        key=_order_key,
    )
    gross = sum((a.unrealized for a in assets), Decimal(0))
    years: list[TransitionYear] = []

    for y in range(1, _MAX_YEARS + 1):
        if not any(r["mv"] > _DUST for r in rem):
            break
        net = gains = losses = sold = Decimal(0)
        sells = 0

        for r in rem:  # losses first
            if r["mv"] <= _DUST or r["u"] > 0:
                continue
            net += r["u"]
            losses += r["u"]
            sold += r["mv"]
            r["mv"] = Decimal(0)
            r["u"] = Decimal(0)
            sells += 1

        cap = budget - net
        for r in rem:  # then gains, lowest gain per dollar first
            if r["mv"] <= _DUST or r["u"] <= 0 or cap <= 0 or r["st"]:
                continue
            ratio = r["u"] / r["mv"]
            amount = min(r["mv"], cap / ratio)
            gain = amount * ratio
            net += gain
            gains += gain
            cap -= gain
            sold += amount
            r["mv"] -= amount
            r["u"] -= gain
            sells += 1

        for r in rem:  # a short-term lot turns long-term after a year
            r["st"] = False

        left = sum((r["mv"] for r in rem), Decimal(0))
        years.append(
            TransitionYear(y, sold, gains, losses, net, max(Decimal(0), net) * rate, left)
        )
        if sells == 0 and y > 1:
            break

    return TransitionSchedule(
        budget=budget,
        rate=rate,
        gross_gain=gross,
        years=tuple(years),
        total_tax=sum((t.tax for t in years), Decimal(0)),
        tax_without_service=max(Decimal(0), gross) * rate,
    )
