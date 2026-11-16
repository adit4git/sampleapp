"""Stand-ins for the model, so runs are offline and repeatable.

`StubModel("good")` behaves like a model that follows its skills: it works in the order the
skill gives, writes only from tool results, includes the disclosures it is handed and
treats a refusal as an answer. Each other kind misbehaves in ONE way, to prove that one
harness rule catches it.

A real model plugs in by implementing next(state) -> {"tool", "args"} | {"final": {...}}.
"""
from __future__ import annotations

from ..fmt import money, pct

KINDS = ("good", "invents_figure", "promise", "no_citation", "auto_action", "omit_disclosure",
         "omit_draft", "wrong_tool", "cross_client", "loop", "wrong_token", "leaks_pii")


class StubModel:
    def __init__(self, kind: str = "good"):
        if kind not in KINDS:
            raise ValueError(f"unknown stub model kind '{kind}'")
        self.kind = kind
        self._misbehaved = False

    def next(self, state: dict) -> dict:
        me, opp = state["client_token"], state["opportunity"]
        res = {r["tool"]: r["result"] for r in state["results"]}
        done = set(res) | {b["tool"] for b in state["blocked"] if b["rule"] in ("H-TOOL", "H-LIMIT")}

        if not self._misbehaved:
            self._misbehaved = True
            if self.kind == "wrong_tool":
                return {"tool": "generate_proposal", "args": {"household": me, "opportunity": opp}}
            if self.kind == "cross_client":
                return {"tool": "opportunity_facts", "args": {"household": "CLIENT_2", "opportunity": opp}}

        plan = [("opportunity_facts", {"household": me, "opportunity": opp}),
                ("eligibility", {"household": me}),
                ("strategy_fit", {"household": me})]
        fit = res.get("strategy_fit")
        if fit and fit["ok"] and fit["data"]["suggested"]:
            plan.append(("fee_estimate", {"household": me, "strategy": fit["data"]["suggested"][0]["id"]}))
        plan.append(("document_search", {"query": state["question"]}))
        for tool, args in plan:
            if tool in state["allowed_tools"] and tool not in done:
                return {"tool": tool, "args": args}
        if self.kind == "loop" and not any(b["rule"] == "H-LIMIT" for b in state["blocked"]):
            return {"tool": "document_search", "args": {"query": f"again {len(state['results'])}"}}
        return {"final": self._write(state, res)}

    def _write(self, state: dict, res: dict) -> dict:
        repairing = state["attempt"] > 0
        me, parts = state["client_token"], []

        f = res.get("opportunity_facts")
        if f and f["ok"] and f["data"]["applies"]:
            d = f["data"]
            parts.append(f"{d['label']} for {me}: {d['reason']}. Amount involved: {money(d['amount'])}.")
        e = res.get("eligibility")
        if e and e["ok"]:
            parts.append(f"Program eligibility: {e['data']['label']}.")
            parts += [f"{c['text']} (owner: {c['owner']})." for c in e["data"]["conditions"]]
        fit = res.get("strategy_fit")
        if fit and not fit["ok"]:
            parts.append(f"The strategy comparison is not available: {fit['reason']}")
        if fit and fit["ok"]:
            top, rest = fit["data"]["suggested"][0], fit["data"]["suggested"][1:]
            parts.append(f"Suggested program strategy: {top['name']} (manager fee "
                         f"{top['manager_fee_bp'] / 100:.2f}%): {pct(top['overlap'], 0)} of what the client "
                         f"holds can stay, with {money(top['tax_now'])} of tax now.")
            if rest:
                parts.append("Alternatives of a different kind: " + "; ".join(r["name"] for r in rest) + ".")
            parts += [f"Not available: {u['name']} ({u['reason']})." for u in fit["data"]["unavailable"]]
        fee = res.get("fee_estimate")
        if fee and fee["ok"]:
            parts.append(f"Advisory fee: {pct(fee['data']['advisory_fee_rate'], 2)}.")

        must = list(state["must_say"])
        if not repairing:
            if self.kind == "omit_disclosure":
                first = next((m for m in must if m["id"] != "draft"), None)
                must = [m for m in must if m is not first]
            if self.kind == "omit_draft":
                must = [m for m in must if m["id"] != "draft"]
        parts += [m["text"] for m in must]

        cites = [] if (self.kind == "no_citation" and not repairing) else list(state["cite"])
        actions = [{"action": a, "needs_confirmation": True}
                   for a in state["allowed_actions"] if a == "generate_proposal"]

        if self.kind == "invents_figure":
            parts.append("That should save the client about $123,456 a year.")
        if self.kind == "promise":
            parts.append("This strategy will outperform and is guaranteed to reduce risk.")
        if self.kind == "auto_action":
            actions = [{"action": "generate_proposal", "executed": True}]
        if self.kind == "wrong_token":
            parts.append("This is similar to what we did for CLIENT_7.")
        if self.kind == "leaks_pii":
            parts.append("The client's tax ID is 912-34-5678.")
        return {"answer": " ".join(parts), "citations": cites, "actions": actions}
