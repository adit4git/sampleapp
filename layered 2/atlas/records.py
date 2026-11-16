"""Decide once a night, read many times.

A decision record holds everything deterministic about one household that does not depend
on what the advisor does on screen: the 13 criteria, eligibility, and the strategy ranking.
It is built by the nightly job, stamped with the policy pack version it was built under,
and read by screens, tools and chat. Only advisor inputs (a budget, a different strategy,
the maturity window) are computed live.

A record built under one pack is never served under another: the store refuses, and the
nightly job rebuilds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .policy import Policy
from .tools import eligibility as elig
from .tools import opportunities as opp
from .tools import strategies as strat


class StaleRecords(Exception):
    """The records were built under a different policy pack than the one in force."""


@dataclass
class RecordStore:
    policy_stamp: str
    as_of: str
    records: dict[str, dict] = field(default_factory=dict)
    reads: int = 0

    def get(self, household: str, policy: Policy) -> dict:
        if policy.stamp != self.policy_stamp:
            raise StaleRecords(f"records were built under policy {self.policy_stamp}; "
                               f"policy {policy.stamp} is in force. Rebuild before serving.")
        self.reads += 1
        return self.records[household]


def build_record(household: dict, policy: Policy) -> dict:
    f = household["facts"]
    opps = opp.evaluate(f, policy)
    e = elig.check(f, policy) if f["has_brokerage"] else None
    s = household.get("strategy")
    ranked = (strat.rank(f, s["inputs"], policy)
              if opps["advisory"] and e and e["status"] != "specialist" and s and "inputs" in s else None)
    return {"household": household["id"], "policy": policy.stamp,
            "opportunities": opps, "eligibility": e, "strategy": ranked}


def build(households: dict[str, dict], policy: Policy, as_of: str = "") -> RecordStore:
    """The deterministic part of the nightly build."""
    return RecordStore(policy.stamp, as_of, {hid: build_record(h, policy) for hid, h in households.items()})
