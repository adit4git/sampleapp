"""LAYER 1: the policy pack. Values and governed wording, versioned.

Nothing here decides anything. Tools ask for a value by its dotted key; the pack answers
and stamps its version on every result, so a figure on screen can be traced to the exact
values that produced it.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import yaml

REQUIRED = [
    "version", "effective", "opportunities", "heat.household_share_steps",
    "heat.book_share_steps", "eligibility.specialist_review_above",
    "eligibility.condition_owners", "strategies.catalog", "strategies.weights",
    "strategies.fit_weights", "strategies.default", "transition.budgets",
    "disclosures", "sources",
]
SHARES = [  # values that must be a share between 0 and 1
    "opportunities.concentration.threshold", "opportunities.cash.over_target",
    "opportunities.drift.max_group_drift", "opportunities.gains.min_share",
    "opportunities.advisory.commission_ratio", "eligibility.specialist_review_above",
    "strategies.top_stock_counts_above", "strategies.tax_scale_share",
]


class PolicyError(Exception):
    pass


class Policy:
    def __init__(self, raw: dict):
        self.raw = raw
        self.version = str(raw.get("version", "?"))
        self.hash = hashlib.sha256(yaml.safe_dump(raw, sort_keys=True).encode()).hexdigest()[:10]

    @classmethod
    def load(cls, path: Path) -> "Policy":
        return cls(yaml.safe_load(Path(path).read_text()))

    @property
    def stamp(self) -> str:
        return f"{self.version}#{self.hash}"

    def __getitem__(self, key: str):
        node = self.raw
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                raise PolicyError(f"policy pack {self.version} has no value '{key}'")
            node = node[part]
        return node

    def with_changes(self, changes: dict) -> "Policy":
        """A draft pack for what-if runs: the same pack with some values replaced."""
        raw = copy.deepcopy(self.raw)
        for key, value in changes.items():
            node = raw
            parts = key.split(".")
            for part in parts[:-1]:
                node = node[part]
            if parts[-1] not in node:
                raise PolicyError(f"cannot change unknown value '{key}'")
            node[parts[-1]] = value
        raw["version"] = f"{self.version}+draft"
        return Policy(raw)

    def strategy(self, sid: str) -> dict:
        return next(s for s in self["strategies.catalog"] if s["id"] == sid)

    def disclosure(self, did: str) -> dict:
        return {"id": did, **self[f"disclosures.{did}"]}


def validate(policy: Policy, known_rule_types: set[str], known_criteria: list[str]) -> list[str]:
    """Structural checks a pack must pass before any tool will run on it."""
    errors: list[str] = []
    for key in REQUIRED:
        try:
            policy[key]
        except PolicyError as e:
            errors.append(str(e))
    if errors:
        return errors
    for key in SHARES:
        v = policy[key]
        if not (isinstance(v, (int, float)) and 0 < v < 1):
            errors.append(f"{key} must be a share between 0 and 1, got {v!r}")
    for name in ("weights", "fit_weights"):
        total = sum(policy[f"strategies.{name}"].values())
        if abs(total - 1) > 1e-9:
            errors.append(f"strategies.{name} must add up to 1, got {total}")
    for name in ("household_share_steps", "book_share_steps"):
        steps = policy[f"heat.{name}"]
        if steps != sorted(steps):
            errors.append(f"heat.{name} must be ascending")
    missing = [k for k in known_criteria if k not in policy["opportunities"]]
    if missing:
        errors.append(f"no values for criteria: {missing}")
    for reason in policy["opportunities.advisory.reasons"]:
        if reason not in known_criteria:
            errors.append(f"advisory reason '{reason}' is not a criterion")
    ids = [s["id"] for s in policy["strategies.catalog"]]
    if len(ids) != len(set(ids)):
        errors.append("strategy ids must be unique")
    if policy["strategies.default"] not in ids:
        errors.append("strategies.default is not in the catalog")
    for s in policy["strategies.catalog"]:
        for req in s.get("requires", []):
            if req["rule"] not in known_rule_types:
                errors.append(f"strategy {s['id']}: unknown rule type '{req['rule']}' "
                              f"(known: {sorted(known_rule_types)}). A new rule type needs a tool change.")
            if "reason" not in req:
                errors.append(f"strategy {s['id']}: requirement '{req['rule']}' has no reason")
        for d in s.get("disclosures", []):
            if d not in policy["disclosures"]:
                errors.append(f"strategy {s['id']}: unknown disclosure '{d}'")
    for did, d in policy["disclosures"].items():
        if d.get("source") not in policy["sources"]:
            errors.append(f"disclosure {did}: unknown source '{d.get('source')}'")
        if not any(m in d["text"].lower() for m in d["match"]):
            errors.append(f"disclosure {did}: its own text does not satisfy its match")
    return errors
