"""The model writes narrative with references; the app writes everything that must be right.

    model:   "{{opportunity.label}} for CLIENT_1. Amount involved: {{opportunity.amount}}."
    app:     substitutes each reference with the tool's value
             appends every disclosure the tools required, in the pack's wording
             appends the draft label on the proposal step
             attaches the citations
             turns action ids into buttons that need the advisor's confirmation

So four of the earlier answer checks have nothing left to check: the model cannot omit a
disclosure, a citation or the draft label, or report an action as done, because it does not
write them. What remains is checking the narrative itself.
"""
from __future__ import annotations

import re

from ..policy import Policy

REF = re.compile(r"\{\{\s*([a-z0-9_.]+)\s*\}\}")
FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?[KMB]?|\d+(?:\.\d+)?\s?%")
TOKEN = re.compile(r"\bCLIENT_\d+\b")

NARRATIVE_RULES = ["H-REF", "H-RAWFIG", "H-WORDING", "H-PII", "H-TOKEN"]
BY_CONSTRUCTION = ["H-DISCLOSE", "H-CITE", "H-DRAFT", "H-CONFIRM"]


def check_narrative(narrative: str, fields: dict, rules: dict, tokens: dict) -> list[dict]:
    """The only checks left: all on what the model itself wrote."""
    found = []
    unknown = [r for r in REF.findall(narrative) if r not in fields]
    if unknown:
        found.append({"rule": "H-REF", "detail": f"refers to fields that do not exist: {unknown}"})
    prose = REF.sub("", narrative)
    typed = FIGURE.findall(prose)
    if typed:
        found.append({"rule": "H-RAWFIG", "detail": f"typed a figure instead of referring to a field: {typed}"})
    low = prose.lower()
    hit = [p for p in rules["H-WORDING"]["forbidden"] if re.search(p, low)]
    if hit:
        found.append({"rule": "H-WORDING", "detail": f"forbidden wording: {hit}"})
    leaked = [n for n, pat in rules["H-PII"]["patterns"].items() if re.search(pat, prose)]
    if leaked:
        found.append({"rule": "H-PII", "detail": f"identifier pattern: {leaked}"})
    foreign = [t for t in TOKEN.findall(prose) if t not in tokens]
    if foreign:
        found.append({"rule": "H-TOKEN", "detail": f"client token not issued for this request: {foreign}"})
    return found


def template_narrative(fields: dict) -> str:
    """The rule-based narrative. Also the fallback. Built from references, like the model's."""
    has = lambda k: k in fields  # noqa: E731
    out = ["{{opportunity.label}} for CLIENT_1: {{opportunity.reason}}. Amount involved: {{opportunity.amount}}."]
    if has("eligibility.label"):
        out.append("Program eligibility: {{eligibility.label}}.")
        i = 0
        while has(f"eligibility.conditions.{i}.text"):
            out.append(f"{{{{eligibility.conditions.{i}.text}}}} (owner: {{{{eligibility.conditions.{i}.owner}}}}).")
            i += 1
    if has("strategy.refused_reason"):
        out.append("The strategy comparison is not available: {{strategy.refused_reason}}")
    if has("strategy.suggested.0.name"):
        out.append("Suggested program strategy: {{strategy.suggested.0.name}} (manager fee "
                   "{{strategy.suggested.0.manager_fee_bp}}): {{strategy.suggested.0.overlap}} of what the "
                   "client holds can stay, with {{strategy.suggested.0.tax_now}} of tax now.")
        alts, i = [], 1
        while has(f"strategy.suggested.{i}.name"):
            alts.append(f"{{{{strategy.suggested.{i}.name}}}}")
            i += 1
        if alts:
            out.append("Alternatives of a different kind: " + "; ".join(alts) + ".")
        i = 0
        while has(f"strategy.unavailable.{i}.name"):
            out.append(f"Not available: {{{{strategy.unavailable.{i}.name}}}} ({{{{strategy.unavailable.{i}.reason}}}}).")
            i += 1
    if has("fee.advisory_fee_rate"):
        out.append("Advisory fee: {{fee.advisory_fee_rate}}.")
    return " ".join(out)


def render(narrative: str, fields: dict, disclosure_ids: list[str], policy: Policy, step: int,
           draft_rule: dict, action_ids: list[str], allowed_actions: list[str]) -> dict:
    """Assemble what the advisor sees. Everything below the narrative is the app's."""
    body = REF.sub(lambda m: fields[m.group(1)]["display"], narrative)
    disclosures = [policy.disclosure(d) for d in disclosure_ids]
    tail = [d["text"] for d in disclosures]
    if step in draft_rule["steps"]:
        tail.append(draft_rule["text"])
    citations = ["opportunity-criteria"]
    for d in disclosures:
        if d["source"] not in citations:
            citations.append(d["source"])
    dropped = [a for a in action_ids if a not in allowed_actions]
    actions = [{"action": a, "needs_confirmation": True} for a in action_ids if a in allowed_actions]
    return {"answer": " ".join([body] + tail), "citations": citations, "actions": actions,
            "dropped_actions": dropped}
