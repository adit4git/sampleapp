"""Fetch before the model, not during.

The screen already determines what the model will need. The harness gathers it from the
decision record (and the prebuilt fee tool) and hands the model a flat set of FIELDS, each
with an id. The model refers to fields by id; it never types their values.

    opportunity.amount                    money   $7.2M
    eligibility.label                     text    Eligible in principle, with conditions
    strategy.suggested.0.manager_fee_bp   bp      0.10%
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..fmt import money, pct

MONEY = {"amount", "amount_above_threshold", "tax_now", "yearly_budget"}
PCT = {"household_share", "overlap", "advisory_fee_rate", "tracking_error_before", "tracking_error_after"}
SKIP = {"source", "applies", "status", "settings"}


def _display(key: str, v) -> tuple[str, str]:
    if isinstance(v, str):
        return "text", v
    if key.endswith("_bp"):
        return "bp", f"{v / 100:.2f}%"
    if key in MONEY:
        return "money", money(v)
    if key in PCT:
        return "pct", pct(v, 2 if key == "advisory_fee_rate" else 0)
    return "number", f"{v:g}"


def flatten(prefix: str, obj, out: dict) -> None:
    if obj is None or isinstance(obj, bool):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in SKIP:
                flatten(f"{prefix}.{k}", v, out)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, str) for x in obj):
            out[prefix] = {"kind": "text", "display": ", ".join(obj)}
        else:
            for i, v in enumerate(obj):
                flatten(f"{prefix}.{i}", v, out)
    else:
        kind, display = _display(prefix.rsplit(".", 1)[-1], obj)
        out[prefix] = {"kind": kind, "display": display}


@dataclass
class Bundle:
    fields: dict[str, dict] = field(default_factory=dict)
    disclosures: list[str] = field(default_factory=list)
    refusals: list[dict] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)

    def add(self, prefix: str, envelope: dict, tool: str) -> dict:
        """Add one tool result. A refusal becomes a field too: it is an answer."""
        if envelope["ok"]:
            flatten(prefix, envelope["data"], self.fields)
            self.disclosures += [d for d in envelope["required_disclosures"] if d not in self.disclosures]
        else:
            self.fields[f"{prefix}.refused_reason"] = {"kind": "text", "display": envelope["reason"]}
            self.refusals.append({"tool": tool, "code": envelope["refused"]})
        self.parts.append(prefix)
        return envelope


def prefetch(toolbox, household: str, opportunity: str, parts: list[str]) -> Bundle:
    """Everything this screen needs, gathered by the harness. No model involved."""
    b = Bundle()
    b.add("opportunity", toolbox.opportunity_facts(household, opportunity), "opportunity_facts")
    fit = None
    if "eligibility" in parts:
        b.add("eligibility", toolbox.eligibility(household), "eligibility")
    if "strategy" in parts:
        fit = b.add("strategy", toolbox.strategy_fit(household), "strategy_fit")
    if "fee" in parts and fit and fit["ok"] and fit["data"]["suggested"]:
        b.add("fee", toolbox.fee_estimate(household, fit["data"]["suggested"][0]["id"]), "fee_estimate")
    return b
