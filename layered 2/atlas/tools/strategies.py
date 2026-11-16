"""LAYER 2 (tools): which program strategies to present, and in what order.

The method is the prototype's:

    fit   = w_te * improvement(tracking error) + w_sector * improvement(sector gap)
            + w_top * reduction(largest stock)          (only when it is above the limit)
    score = w_overlap * overlap + w_fit * max(0, fit) + w_tax * (1 - tax now / scale)

    sort: available first, different from the default first, higher score, lower fee,
          the default as the last tiebreak
    suggest: the best fit, then the best of other strategy types

Weights, floors, the catalog and its availability requirements come from the policy pack.
The analytics inputs (overlap, tracking error, sector gap, tax now) come from the firm's
analytics; in this proof of concept they are the values the prototype computed.
"""
from __future__ import annotations

import math

from ..policy import Policy

# Availability rule TYPES. The policy pack chooses which apply to which strategy and with
# what value; adding a new type is a code change here.
RULE_TYPES = {
    "taxable_only": lambda facts, req: bool(facts["taxable"]),
    "min_brokerage": lambda facts, req: facts["brokerage_value"] >= req["value"],
    "min_household_value": lambda facts, req: facts["household_value"] >= req["value"],
    "entity_in": lambda facts, req: facts["entity"] in req["value"],
    "segment_in": lambda facts, req: facts["segment"] in req["value"],
}


def availability(strategy: dict, facts: dict) -> str | None:
    """None if the strategy is available, else the reason from the first failed requirement."""
    for req in strategy.get("requires", []):
        if not RULE_TYPES[req["rule"]](facts, req):
            return req["reason"]
    return None


def _improvement(before: float, after: float, floor: float) -> float:
    return max(-1.0, min(1.0, (before - after) / max(before, floor)))


def _score(a: dict, facts: dict, policy: Policy) -> tuple[float, float]:
    w, fw, fl = (policy[f"strategies.{k}"] for k in ("weights", "fit_weights", "fit_floors"))
    top = (_improvement(a["top_stock_before"], a["top_stock_after"], fl["top_stock"])
           if a["top_stock_before"] > policy["strategies.top_stock_counts_above"] else 0.0)
    fit = (fw["tracking_error"] * _improvement(a["tracking_error_before"], a["tracking_error_after"], fl["tracking_error"])
           + fw["sector_gap"] * _improvement(a["sector_gap_before"], a["sector_gap_after"], fl["sector_gap"])
           + fw["top_stock"] * top)
    tax_scale = max(1.0, policy["strategies.tax_scale_share"] * facts["household_value"])
    score = (w["overlap"] * a["overlap"] + w["fit"] * max(0.0, fit)
             + w["tax_now"] * (1 - min(1.0, a["tax_now"] / tax_scale)))
    return fit, score


def rank(facts: dict, analytics: list[dict], policy: Policy) -> dict:
    """Rank every strategy in the catalog for one household."""
    by_id = {a["id"]: a for a in analytics}
    default_id = policy["strategies.default"]
    tol = policy["strategies.same_as_default_tolerance"]
    rows = []
    for order, s in enumerate(policy["strategies.catalog"]):
        a = by_id.get(s["id"])
        if not a or not a["evaluated"]:
            continue
        fit, score = _score(a, facts, policy)
        rows.append({"id": s["id"], "name": s["name"], "type": s["type"],
                     "manager_fee_bp": s["manager_fee_bp"], "fit": fit, "score": score,
                     "unavailable_reason": availability(s, facts), "same_as_default": False,
                     "overlap": a["overlap"], "tax_now": a["tax_now"],
                     "tracking_error_before": a["tracking_error_before"],
                     "tracking_error_after": a["tracking_error_after"],
                     "disclosures": s.get("disclosures", []), "_order": order, "_a": a})

    default = next((r for r in rows if r["id"] == default_id), None)
    if default:
        d = default["_a"]
        for r in rows:
            a = r["_a"]
            r["same_as_default"] = r["id"] != default_id and (
                a["trade_signature"] == d["trade_signature"]
                or (a["vehicle_buys"] < tol and abs(a["overlap_value"] - d["overlap_value"]) < tol))

    rows.sort(key=lambda r: (r["unavailable_reason"] is not None, r["same_as_default"],
                             -math.floor(r["score"] * 1000 + 0.5), r["manager_fee_bp"],
                             r["id"] != default_id, r["_order"]))

    usable = [r for r in rows if not r["unavailable_reason"] and not r["same_as_default"]]
    limit, suggested = policy["strategies.suggestions"], []
    for r in usable:                                   # best fit, then other strategy types
        if len(suggested) < limit and all(x["type"] != r["type"] for x in suggested):
            suggested.append(r)
    for r in usable:                                   # then fill up
        if len(suggested) < limit and r not in suggested:
            suggested.append(r)

    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return {"ranked": clean, "suggested": [r["id"] for r in suggested],
            "unavailable": [{"id": r["id"], "name": r["name"], "reason": r["unavailable_reason"]}
                            for r in clean if r["unavailable_reason"]]}
