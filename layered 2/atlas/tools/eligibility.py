"""LAYER 2 (tools): Advisory program eligibility. Three outcomes, checked in order.

    specialist   one stock is above the specialist-review share: nothing moves in
    conditions   eligible in principle, with conditions, each with an owner
    eligible     eligible in principle

The tool also says which disclosures its result makes necessary. The wording of each
disclosure is in the policy pack; the harness checks that it appears in the answer.
"""
from __future__ import annotations

from ..fmt import pct
from ..policy import Policy

LABELS = {"specialist": "Requires specialist review",
          "conditions": "Eligible in principle, with conditions",
          "eligible": "Eligible in principle"}


def check(facts: dict, policy: Policy) -> dict:
    owners = policy["eligibility.condition_owners"]
    limit = policy["eligibility.specialist_review_above"]

    if facts["largest_stock_share"] > limit:
        return {"status": "specialist", "label": LABELS["specialist"],
                "conditions": [{"kind": "specialist", "owner": owners["specialist"],
                                "text": f"{facts['largest_stock']} is {pct(facts['largest_stock_share'])} "
                                        f"of the household (above {pct(limit, 0)})"}],
                "required_disclosures": ["specialist_review"]}

    conditions, disclosures = [], ["form_crs", "conflict"]
    if facts["brokerage_missing_basis"]:
        conditions.append({"kind": "missing_basis", "owner": owners["missing_basis"],
                           "text": "Cost basis missing for " + ", ".join(facts["brokerage_missing_basis"])})
        disclosures.append("missing_basis")
    if facts["brokerage_insider"]:
        conditions.append({"kind": "insider", "owner": owners["insider"],
                           "text": "Insider holding: " + ", ".join(facts["brokerage_insider"])
                                   + " needs pre-clearance before any sale"})
        disclosures.append("insider_preclearance")
    if facts["brokerage_excluded"]:
        conditions.append({"kind": "excluded_assets", "owner": owners["excluded_assets"],
                           "text": "Excluded assets stay in brokerage: " + ", ".join(facts["brokerage_excluded"])})

    status = "conditions" if conditions else "eligible"
    return {"status": status, "label": LABELS[status], "conditions": conditions,
            "required_disclosures": disclosures}
