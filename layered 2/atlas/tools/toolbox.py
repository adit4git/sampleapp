"""LAYER 2 (tools): what the agent, the screens and the nightly build can call.

Each tool ENFORCES ITS OWN PREREQUISITES. The model cannot get a strategy comparison for a
household under specialist review, or a proposal without the advisor's confirmation, no
matter what a skill says or forgets to say: the tool refuses, with a reason.

Every result carries the policy pack version it was computed with, and the ids of the
disclosures that result makes necessary.

Stubs: fee_estimate, transition_schedule and generate_proposal stand in for the firm's
prebuilt tools. Their prerequisites are real; their figures are placeholders.
"""
from __future__ import annotations

from ..policy import Policy
from . import eligibility as elig
from . import opportunities as opp
from . import strategies as strat


class Toolbox:
    def __init__(self, policy: Policy, households: dict[str, dict], confirmations: set | None = None,
                 records=None):
        self.policy = policy
        self.households = households
        self.records = records       # nightly decision records; None = decide live on every call
        self.confirmations = confirmations if confirmations is not None else set()
        self.names = [n for n in dir(self) if not n.startswith("_") and callable(getattr(self, n))
                      and n not in ("call",)]

    # ---- envelope ------------------------------------------------------
    def _ok(self, data: dict, disclosures: list[str] | None = None) -> dict:
        return {"ok": True, "data": data, "required_disclosures": disclosures or [],
                "policy": self.policy.stamp}

    def _refuse(self, code: str, reason: str) -> dict:
        return {"ok": False, "refused": code, "reason": reason, "policy": self.policy.stamp}

    def call(self, name: str, args: dict) -> dict:
        return getattr(self, name)(**args)

    def _facts(self, household: str) -> dict:
        return self.households[household]["facts"]

    # ---- decisions: read the nightly record when there is one, else decide now ----
    def _opps(self, household: str) -> dict:
        if self.records:
            return self.records.get(household, self.policy)["opportunities"]
        return opp.evaluate(self._facts(household), self.policy)

    def _elig(self, household: str) -> dict:
        if self.records:
            return self.records.get(household, self.policy)["eligibility"]
        return elig.check(self._facts(household), self.policy)

    def _rank(self, household: str) -> dict:
        if self.records and self.records.get(household, self.policy)["strategy"]:
            return self.records.get(household, self.policy)["strategy"]
        return strat.rank(self._facts(household), self.households[household]["strategy"]["inputs"], self.policy)

    # ---- shared prerequisites -------------------------------------------
    def _needs_program_access(self, household: str) -> dict | None:
        if not self._opps(household)["advisory"]:
            return self._refuse("PREREQ-OPPORTUNITY",
                                "The Advisory program opportunity does not apply to this household.")
        e = self._elig(household)
        if e["status"] == "specialist":
            return self._refuse("PREREQ-ELIGIBILITY",
                                f"{e['label']}: {e['conditions'][0]['text']}. "
                                "Program strategies, fees and transition are not available until the review is done.")
        return None

    def _needs_strategy(self, household: str, strategy: str) -> dict | None:
        ids = [s["id"] for s in self.policy["strategies.catalog"]]
        if strategy not in ids:
            return self._refuse("PREREQ-STRATEGY", f"Unknown strategy '{strategy}'.")
        why = strat.availability(self.policy.strategy(strategy), self._facts(household))
        if why:
            return self._refuse("PREREQ-STRATEGY", f"{self.policy.strategy(strategy)['name']}: {why}.")
        return None

    # ---- tools ----------------------------------------------------------
    def household_opportunities(self, household: str) -> dict:
        ranked = opp.ranked(self._opps(household))
        return self._ok({"opportunities": [{k: o[k] for k in ("key", "label", "amount", "step", "reason")}
                                           for o in ranked]})

    def opportunity_facts(self, household: str, opportunity: str) -> dict:
        f = self._facts(household)
        r = self._opps(household)[opportunity]
        if not r:
            return self._ok({"label": opp.LABELS[opportunity], "applies": False})
        disclosures = []
        if opportunity == "harvest":
            disclosures.append("wash_sale")
        if opportunity == "concentration" and set(r["detail"]["stocks"]) & set(f["brokerage_insider"]):
            disclosures.append("insider_preclearance")
        return self._ok({"label": opp.LABELS[opportunity], "applies": True, "amount": r["amount"],
                         "household_share": r["share"], "step": r["step"], "reason": r["reason"],
                         **r["detail"]}, disclosures)

    def eligibility(self, household: str) -> dict:
        f = self._facts(household)
        if not f["has_brokerage"]:
            return self._refuse("PREREQ-OPPORTUNITY", "This household has no brokerage account.")
        e = self._elig(household)
        return self._ok({"status": e["status"], "label": e["label"], "conditions": e["conditions"]},
                        e["required_disclosures"])

    def strategy_fit(self, household: str) -> dict:
        refusal = self._needs_program_access(household)
        if refusal:
            return refusal
        r = self._rank(household)
        by_id = {x["id"]: x for x in r["ranked"]}
        suggested = [{k: by_id[i][k] for k in ("id", "name", "type", "manager_fee_bp", "overlap", "tax_now",
                                               "tracking_error_before", "tracking_error_after")}
                     for i in r["suggested"]]
        disclosures = ["manager_fee"] + [d for i in r["suggested"] for d in by_id[i]["disclosures"]]
        return self._ok({"suggested": suggested, "unavailable": r["unavailable"],
                         "same_as_default": [x["name"] for x in r["ranked"] if x["same_as_default"]]},
                        disclosures)

    def fee_estimate(self, household: str, strategy: str) -> dict:
        refusal = self._needs_program_access(household) or self._needs_strategy(household, strategy)
        if refusal:
            return refusal
        return self._ok({"source": "prebuilt fee calculator (stub)", "advisory_fee_rate": 0.0100,
                         "manager_fee_bp": self.policy.strategy(strategy)["manager_fee_bp"]}, ["indicative"])

    def transition_schedule(self, household: str, strategy: str, budget: float | None = None) -> dict:
        refusal = self._needs_program_access(household) or self._needs_strategy(household, strategy)
        if refusal:
            return refusal
        budget = self.policy["transition.default_budget"] if budget is None else budget
        if not self._facts(household)["taxable"]:
            return self._refuse("PREREQ-TAXABLE", "The transition service is for taxable accounts only.")
        s = self.policy.strategy(strategy)
        if s["type"] in self.policy["transition.not_available_for_types"]:
            return self._refuse("PREREQ-STRATEGY-TYPE", f"The transition service is not available with {s['type'].lower()} strategies.")
        if budget not in self.policy["transition.budgets"]:
            return self._refuse("PREREQ-BUDGET", f"The yearly budget must be one of {self.policy['transition.budgets']}.")
        return self._ok({"source": "prebuilt transition model (stub)", "yearly_budget": budget}, ["indicative"])

    def generate_proposal(self, household: str, opportunity: str, strategy: str | None = None,
                          confirmation_ref: str | None = None) -> dict:
        if opportunity == "advisory":
            refusal = self._needs_program_access(household) or (
                self._needs_strategy(household, strategy) if strategy else
                self._refuse("PREREQ-STRATEGY", "Choose a program strategy before generating the proposal."))
            if refusal:
                return refusal
        if confirmation_ref not in self.confirmations:
            return self._refuse("PREREQ-CONFIRMATION",
                                "A proposal is generated only after the advisor confirms on screen.")
        return self._ok({"document_id": f"draft-{household}-{opportunity}", "status": "draft for advisor review"})

    def opportunity_what_if(self, household: str, opportunity: str, settings: dict) -> dict:
        """Live: the same criterion under on-screen settings the advisor changed."""
        r = opp.evaluate(self._facts(household), self.policy, {opportunity: settings})[opportunity]
        if not r:
            return self._ok({"label": opp.LABELS[opportunity], "applies": False, "settings": settings})
        return self._ok({"label": opp.LABELS[opportunity], "applies": True, "amount": r["amount"],
                         "reason": r["reason"], "step": r["step"], "settings": settings})

    def document_search(self, query: str = "") -> dict:
        return self._ok({"passages": [{"id": k, "title": v} for k, v in self.policy["sources"].items()]})
