"""LAYER 2 (tools): the 13 opportunity criteria, as code.

The LOGIC is here. Every VALUE comes from the policy pack. A criterion returns None, or
what the screens need: the amount shown, the household share and heat step, and the reason
in plain words. The nightly build, the Book view and the agent all call these functions.
"""
from __future__ import annotations

from ..fmt import money, pct
from ..policy import Policy

# Display order when two opportunities have the same step and share.
ORDER = ["advisory", "downgrades", "maturing", "concentration", "cash", "drift", "harvest",
         "gains", "basis", "behind", "meetings", "cio", "programs"]

LABELS = {
    "advisory": "Brokerage to Advisory program", "downgrades": "Downgraded holdings",
    "maturing": "Bonds and CDs maturing", "concentration": "Single-stock concentration",
    "cash": "Excess cash", "drift": "Allocation drift", "harvest": "Tax-loss harvesting",
    "gains": "Large embedded gains", "basis": "Missing cost basis",
    "behind": "Behind benchmark", "meetings": "Meetings", "cio": "Off the CIO house view",
    "programs": "Program opportunities",
}


def share_step(share: float, steps: list[float]) -> int:
    if share <= 0:
        return 0
    for i, limit in enumerate(steps, start=1):
        if share <= limit:
            return i
    return len(steps) + 1


def _hit(amount, share, step, reason, **detail) -> dict:
    return {"amount": amount, "share": share, "step": step, "reason": reason, "detail": detail}


def _sized(f, steps, amount, reason, floor=0, **detail):
    share = amount / f["household_value"]
    return _hit(amount, share, max(floor, share_step(share, steps)), reason, **detail)


# ---- one function per criterion: (facts, values for this criterion, steps, flagged) ----
def downgrades(f, v, steps, flagged):
    if f["downgraded_count"] <= 0:
        return None
    return _sized(f, steps, f["downgraded_value"],
                  f"Holds a security Research downgraded in the last {v['lookback_days']} days")


def maturing(f, v, steps, flagged):
    due = [m for m in f["maturing"] if m["within_months"] <= v["horizon_months"]]
    total = sum(m["mv"] for m in due)
    if not due or total < v["min_amount"]:
        return None
    first = min(m["days"] for m in due)
    floor = v["urgent_step"] if first <= v["urgent_within_days"] else 0
    return _sized(f, steps, total,
                  f"Bonds or CDs maturing in the next {v['horizon_months']} months add up to "
                  f"at least {money(v['min_amount'])}", floor, first_maturity_days=first)


def concentration(f, v, steps, flagged):
    over = [s for s in f["stock_positions"] if s["share"] > v["threshold"]]
    if not over:
        return None
    amount = sum(s["mv"] for s in over)                       # Book view shows the positions
    trim = sum(max(0.0, s["mv"] - v["threshold"] * f["household_value"]) for s in over)
    share = trim / f["household_value"]                       # heat uses the amount above the limit
    return _hit(amount, share, max(v["min_step"], share_step(share, steps)),
                f"A single stock is more than {pct(v['threshold'], 0)} of the household",
                amount_above_threshold=trim, stocks=[s["sym"] for s in over])


def cash(f, v, steps, flagged):
    if not (f["cash_over_target"] > v["over_target"] and f["cash_excess_value"] >= v["min_excess"]):
        return None
    return _sized(f, steps, f["cash_excess_value"],
                  f"Cash is more than {pct(v['over_target'], 0)} of the household above target and "
                  f"the excess is at least {money(v['min_excess'])}")


def drift(f, v, steps, flagged):
    if f["max_group_drift"] <= v["max_group_drift"]:
        return None
    return _sized(f, steps, f["drift_value"],
                  f"An asset group is more than {pct(v['max_group_drift'], 0)} of the household from target")


def behind(f, v, steps, flagged):
    gap = f["ytd_return"] - f["benchmark_ytd"]
    if not f["ytd_return"] < f["benchmark_ytd"] - v["gap_pts"]:
        return None
    step = (v["severe_step"] if gap < v["severe_gap_pts"]
            else v["wide_step"] if gap < v["wide_gap_pts"] else v["base_step"])
    return _hit(f["household_value"], None, step,
                f"Year-to-date return is more than {v['gap_pts']} points behind the benchmark", gap_pts=gap)


def harvest(f, v, steps, flagged):
    if f["unrealized_losses"] < v["min_losses"]:
        return None
    return _sized(f, steps, f["unrealized_losses"],
                  f"Unrealized losses add up to at least {money(v['min_losses'])}")


def gains(f, v, steps, flagged):
    if not f["unrealized_gains"] > v["min_share"] * f["household_value"]:
        return None
    return _sized(f, steps, f["unrealized_gains"],
                  f"Unrealized gains are more than {pct(v['min_share'], 0)} of the household")


def basis(f, v, steps, flagged):
    if f["missing_basis_count"] <= 0:
        return None
    return _sized(f, steps, f["missing_basis_value"],
                  "At least one position has no cost basis on file", v["min_step"])


def meetings(f, v, steps, flagged):
    d = f["meeting_in_days"]
    if d is None or d > v["within_days"]:
        return None
    step = (v["imminent_step"] if d <= v["imminent_days"]
            else v["soon_step"] if d <= v["soon_days"] else v["base_step"])
    return _hit(f["household_value"], None, step,
                f"A client meeting is within {v['within_days']} days", in_days=d)


def cio(f, v, steps, flagged):
    if f["cio_alignment"] not in v["flag_when"]:
        return None
    return _hit(f["household_value"], None, v["step"], "Furthest from the CIO house view")


def programs(f, v, steps, flagged):
    n = f["programs_eligible"]
    if n < v["min_eligible"]:
        return None
    return _hit(f["household_value"], None,
                v["many_step"] if n >= v["many_eligible"] else v["base_step"],
                f"Eligible for {n} programs or overlays not yet in use", eligible=n)


def advisory(f, v, steps, flagged):
    b = f["brokerage_value"]
    if not f["has_brokerage"] or b < v["min_brokerage"]:
        return None
    reasons = [r for r in v["reasons"] if flagged(r)]
    costly = f["commissions_12m"] / b >= v["commission_ratio"]
    if not reasons and not costly:
        return None
    why = (f"At least {money(v['min_brokerage'])} in brokerage and a reason for ongoing advice: "
           + ", ".join(LABELS[r].lower() for r in reasons)) if reasons else (
        f"At least {money(v['min_brokerage'])} in brokerage and commissions of "
        f"{pct(v['commission_ratio'], 1)} or more of brokerage assets a year")
    return _sized(f, steps, b, why, v["min_step"], reasons=reasons, high_commissions=costly)


CRITERIA = {"downgrades": downgrades, "maturing": maturing, "concentration": concentration,
            "cash": cash, "drift": drift, "behind": behind, "harvest": harvest, "gains": gains,
            "basis": basis, "meetings": meetings, "cio": cio, "programs": programs,
            "advisory": advisory}


def evaluate(facts: dict, policy: Policy, advisor_settings: dict | None = None) -> dict[str, dict | None]:
    """All 13 criteria for one household. `advisor_settings` are on-screen changes to the
    values a criterion lets the advisor adjust (the maturing window and minimum)."""
    steps = policy["heat.household_share_steps"]
    done: dict[str, dict | None] = {}

    def run(key: str):
        if key not in done:
            values = {**policy[f"opportunities.{key}"], **(advisor_settings or {}).get(key, {})}
            done[key] = CRITERIA[key](facts, values, steps, lambda other: run(other) is not None)
        return done[key]

    for key in ORDER:
        run(key)
    return done


def ranked(results: dict[str, dict | None]) -> list[dict]:
    """Household opportunities in display order: heat step, then household share."""
    hits = [{"key": k, "label": LABELS[k], **results[k]} for k in ORDER if results[k]]
    return sorted(hits, key=lambda o: (-o["step"], -(o["share"] or 0)))


def book_summary(households: list[dict], policy: Policy, advisor_settings: dict | None = None) -> dict:
    """Book view tiles: clients meeting each criterion, amount, share of the book, heat."""
    out = {k: {"label": LABELS[k], "n": 0, "amount": 0.0, "households": []} for k in ORDER}
    for h in households:
        for k, r in evaluate(h["facts"], policy, advisor_settings).items():
            if r:
                out[k]["n"] += 1
                out[k]["amount"] += r["amount"]
                out[k]["households"].append(h["id"])
    for t in out.values():
        t["share"] = t["n"] / len(households) if households else 0
        t["heat"] = share_step(t["share"], policy["heat.book_share_steps"])
    return out
