"""Stand-in models for the lean flow. Output is structured:

    {"narrative": "... {{field.id}} ...", "actions": ["generate_proposal"]}
    or {"tool": name, "args": {...}}   for a what-if the screen did not anticipate

`good` writes from references and adds one line of judgment. Each other kind misbehaves in
one way. Several kinds that mattered before (omitting a disclosure, dropping citations,
reporting an action as done) are here only to show they no longer matter.
"""
from __future__ import annotations

from .render import template_narrative

KINDS = ("good", "what_if", "types_figure", "copies_figure", "bad_ref", "promise", "leaks_pii",
         "wrong_token", "silent", "unknown_action", "wrong_tool", "cross_client", "loop")


class LeanStub:
    def __init__(self, kind: str = "good"):
        if kind not in KINDS:
            raise ValueError(f"unknown lean stub kind '{kind}'")
        self.kind = kind
        self._step = 0

    def next(self, state: dict) -> dict:
        self._step += 1
        fields, repairing = state["fields"], state["attempt"] > 0
        first = self._step == 1

        if first and self.kind == "what_if" and "strategy.suggested.0.id" in fields:
            return {"tool": "transition_schedule",
                    "args": {"household": "CLIENT_1", "strategy": fields["strategy.suggested.0.id"]["display"],
                             "budget": 500000}}
        if first and self.kind == "wrong_tool":
            return {"tool": "generate_proposal", "args": {"household": "CLIENT_1", "opportunity": state["opportunity"]}}
        if first and self.kind == "cross_client":
            return {"tool": "opportunity_what_if",
                    "args": {"household": "CLIENT_2", "opportunity": state["opportunity"], "settings": {}}}
        if self.kind == "loop" and not any(b["rule"] in ("H-LIMIT", "H-TOOL") for b in state["blocked"]):
            return {"tool": "opportunity_what_if",
                    "args": {"household": "CLIENT_1", "opportunity": state["opportunity"], "settings": {}}}

        text = template_narrative(fields) + " Worth raising at the next review."
        if "whatif.transition_schedule.yearly_budget" in fields:
            text += " With a yearly gain budget of {{whatif.transition_schedule.yearly_budget}} the move can be spread over time."
        actions = [a for a in state["allowed_actions"] if a == "generate_proposal"]

        if self.kind == "silent":
            text, actions = "Here is where things stand for CLIENT_1.", []
        if self.kind == "unknown_action":
            actions = ["place_trade", "generate_proposal"]
        if not repairing:
            if self.kind == "types_figure":
                text += " That should save the client about $123,456 a year."
            if self.kind == "copies_figure":   # right number, typed instead of referenced
                text += f" In short, {fields['opportunity.amount']['display']} is in play."
            if self.kind == "bad_ref":
                text += " Expected return: {{strategy.expected_return}}."
        if self.kind == "promise":
            text += " This strategy will outperform and is guaranteed to reduce risk."
        if self.kind == "leaks_pii":
            text += " The client's tax ID is 912-34-5678."
        if self.kind == "wrong_token":
            text += " This is similar to what we did for CLIENT_7."
        return {"final": {"narrative": text, "actions": actions}}
