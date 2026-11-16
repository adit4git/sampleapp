"""Impact report for a proposed policy change: what moves, before anyone approves it.

    python -m atlas.impact opportunities.concentration.threshold=0.15
    python -m atlas.impact eligibility.specialist_review_above=0.40 strategies.weights.overlap=0.30 strategies.weights.fit=0.55

Runs every tool over the synthetic book under the current pack and under a draft with the
changes, and lists the differences. No code changes, no model.
"""
from __future__ import annotations

import sys

import yaml

from .evals import ROOT, load_data
from .policy import Policy, validate
from .tools import eligibility as elig
from .tools import opportunities as opp
from .tools import strategies as strat


def report(base: Policy, draft: Policy, households: list[dict]) -> dict:
    out = {"from": base.stamp, "to": draft.stamp,
           "invalid": validate(draft, set(strat.RULE_TYPES), opp.ORDER),
           "criteria": {}, "eligibility": [], "suggestions": [], "availability": []}
    if out["invalid"]:
        return out
    for k in opp.ORDER:
        before = {h["id"] for h in households if opp.evaluate(h["facts"], base)[k]}
        after = {h["id"] for h in households if opp.evaluate(h["facts"], draft)[k]}
        if before != after:
            out["criteria"][k] = {"before": len(before), "after": len(after),
                                  "enter": sorted(after - before), "leave": sorted(before - after)}
    for h in households:
        a, b = elig.check(h["facts"], base)["status"], elig.check(h["facts"], draft)["status"]
        if a != b:
            out["eligibility"].append({"household": h["id"], "before": a, "after": b})
        s = h.get("strategy")
        if not s or "expected" not in s:
            continue
        ra, rb = strat.rank(h["facts"], s["inputs"], base), strat.rank(h["facts"], s["inputs"], draft)
        if ra["suggested"] != rb["suggested"]:
            out["suggestions"].append({"household": h["id"], "before": ra["suggested"], "after": rb["suggested"]})
        ua, ub = {u["id"] for u in ra["unavailable"]}, {u["id"] for u in rb["unavailable"]}
        if ua != ub:
            out["availability"].append({"household": h["id"], "now_unavailable": sorted(ub - ua),
                                        "now_available": sorted(ua - ub)})
    return out


def main(argv: list[str]) -> int:
    base = Policy.load(ROOT / "policy" / "atlas-policy.yaml")
    changes = {k: yaml.safe_load(v) for k, v in (a.split("=", 1) for a in argv)}
    r = report(base, base.with_changes(changes), load_data()["households"])
    print(f"Policy {r['from']} -> {r['to']}\nChanges: {changes}\n")
    if r["invalid"]:
        print("REJECTED: the draft pack is not valid\n  " + "\n  ".join(r["invalid"]))
        return 1
    for k, c in r["criteria"].items():
        print(f"{opp.LABELS[k]}: {c['before']} -> {c['after']} households"
              + (f"; enter {c['enter']}" if c["enter"] else "") + (f"; leave {c['leave']}" if c["leave"] else ""))
    for e in r["eligibility"]:
        print(f"Eligibility {e['household']}: {e['before']} -> {e['after']}")
    for s in r["availability"]:
        print(f"Availability {s['household']}: now unavailable {s['now_unavailable']}, now available {s['now_available']}")
    for s in r["suggestions"]:
        print(f"Suggestions {s['household']}: {s['before']} -> {s['after']}")
    if not any(r[k] for k in ("criteria", "eligibility", "suggestions", "availability")):
        print("No household is affected.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
