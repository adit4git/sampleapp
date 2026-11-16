"""LAYER 4 (harness): one agent turn.

    context record (ids only)
      -> entitlement                         H-ENTITLE   no model call if it fails
      -> does the opportunity apply? (tool)              no model call if it does not
      -> skills for this opportunity (prose) + tools for this step (allow-list)
      -> model loop; each tool call checked  H-TOOL / H-SCOPE / H-LIMIT
           tools enforce their own prerequisites and return required disclosures
      -> answer checked                      H-FIG / H-DISCLOSE / H-CITE / H-WORDING /
                                             H-DRAFT / H-CONFIRM / H-TOKEN / H-PII
      -> one repair attempt, then a rule-based answer built from the same tool results
      -> names restored for display only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..fmt import money
from ..policy import Policy
from ..skills import Skill
from ..tools import opportunities as opp
from ..tools.toolbox import Toolbox
from . import guardrails as g

MAX_STEPS = 30


@dataclass
class Env:
    policy: Policy
    households: dict[str, dict]
    skills: dict[str, Skill]
    config: dict

    @classmethod
    def load(cls, root: Path, policy: Policy, households: dict, skills: dict) -> "Env":
        return cls(policy, households, skills, yaml.safe_load((root / "harness" / "harness.yaml").read_text()))

    def screen(self, opportunity: str, step: int) -> dict:
        base, own = self.config["screens"]["default"], self.config["screens"].get(opportunity, {})
        merge = lambda key: list(dict.fromkeys(  # noqa: E731
            (base.get(key, {}).get(step, []) or []) + (own.get(key, {}).get(step, []) or [])))
        skill_ids = list(dict.fromkeys(base["skills"] + own.get("skills", [])))
        chain: list[Skill] = []
        for sid in skill_ids:
            chain += [s for s in self.skills[sid].chain if s not in chain]
        return {"skills": chain, "tools": merge("tools"), "actions": merge("actions")}


@dataclass
class Turn:
    outcome: str                  # pass | repaired | fallback | refused | not_applicable
    kind: str                     # ai | rule_based
    answer: str = ""              # as the model sees it: tokens
    display: str = ""             # as the advisor sees it: names restored
    citations: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    skills: list = field(default_factory=list)
    tools_called: list = field(default_factory=list)
    tool_refusals: list = field(default_factory=list)   # prerequisites a TOOL enforced
    blocked: list = field(default_factory=list)         # calls the HARNESS stopped
    violations: list = field(default_factory=list)      # answer-rule failures, per attempt
    disclosures: list = field(default_factory=list)
    policy: str = ""
    prompt: str = ""


def compose_prompt(skills: list[Skill], tools: list[str], actions: list[str]) -> str:
    parts = ["You are Ask Atlas. Follow the skills below. Answer only from tool results."]
    parts += [f"## Skill: {s.id}" + (f" (follows {s.parent.id})" if s.parent else "") + f"\n{s.body}"
              for s in skills]
    parts.append("## Tools on this screen\n" + ", ".join(tools))
    parts.append("## Actions you may propose\n" + (", ".join(actions) or "none"))
    return "\n\n".join(parts)


def run_turn(env: Env, ctx: dict, question: str, model, confirmations: set | None = None) -> Turn:
    policy, hh = env.policy, env.households[ctx["household"]]
    opportunity, step = ctx["opportunity"], ctx["step"]

    if hh["advisor"] != ctx["advisor"]:
        return Turn("refused", "rule_based", display="This household is not in your book.",
                    blocked=[{"rule": "H-ENTITLE", "tool": None}], policy=policy.stamp)

    if not opp.evaluate(hh["facts"], policy)[opportunity]:
        return Turn("not_applicable", "rule_based", policy=policy.stamp,
                    display=f"{opp.LABELS[opportunity]} does not apply to this household under policy {policy.version}.")

    screen = env.screen(opportunity, step)
    rules = env.config["answer_rules"]
    limit = env.config["limits"]["max_tool_calls"]
    toolbox = Toolbox(policy, env.households, confirmations)
    tokens = {"CLIENT_1": ctx["household"]}                       # issued for this request only
    id_to_token = {v: k for k, v in tokens.items()}
    names = {"CLIENT_1": f"the {ctx['household'].capitalize()} household"}

    results: list[dict] = []
    blocked: list[dict] = []
    gctx = {"step": step, "tool_results": [], "tokens": tokens, "allowed_actions": screen["actions"]}

    def must_say() -> list[dict]:
        out = g.required_disclosures(gctx["tool_results"], policy)
        if step in rules["H-DRAFT"]["steps"]:
            out.append({"id": "draft", "text": rules["H-DRAFT"]["text"]})
        return out

    def cite() -> list[str]:
        out = ["opportunity-criteria"]
        for d in g.required_disclosures(gctx["tool_results"], policy):
            if d["source"] not in out:
                out.append(d["source"])
        return out

    turn = Turn("fallback", "rule_based", skills=[s.id for s in screen["skills"]], policy=policy.stamp,
                prompt=compose_prompt(screen["skills"], screen["tools"], screen["actions"]))
    state = {"opportunity": opportunity, "step": step, "question": question, "client_token": "CLIENT_1",
             "allowed_tools": screen["tools"], "allowed_actions": screen["actions"],
             "results": results, "blocked": blocked, "attempt": 0, "violations": []}

    def call(tool: str, args: dict) -> dict:
        real = {**args, **({"household": tokens[args["household"]]} if "household" in args else {})}
        result = g.tokenize(toolbox.call(tool, real), id_to_token)
        results.append({"tool": tool, "result": result})
        gctx["tool_results"].append(result)
        if not result["ok"]:
            turn.tool_refusals.append({"tool": tool, "code": result["refused"]})
        return result

    for _ in range(MAX_STEPS):
        state["must_say"], state["cite"] = must_say(), cite()
        msg = model.next(state)
        if "tool" in msg:
            stop = g.check_call(msg, screen["tools"], tokens, len(results), limit)
            if stop:
                blocked.append({"rule": stop, "tool": msg["tool"]})
            else:
                call(msg["tool"], msg["args"])
            continue
        output = msg["final"]
        found = g.check_answer(output, rules, policy, gctx)
        turn.violations.append(found)
        if not found:
            turn.outcome = "pass" if state["attempt"] == 0 else "repaired"
            turn.kind, turn.answer = "ai", output["answer"]
            turn.citations, turn.actions = output["citations"], output["actions"]
            break
        if state["attempt"] == 0:
            state["attempt"], state["violations"] = 1, found
            continue
        break

    if turn.kind != "ai":                                   # rule-based answer from the same tools
        have = {r["tool"]: r["result"] for r in results}
        for tool, args in [("opportunity_facts", {"household": "CLIENT_1", "opportunity": opportunity}),
                           ("eligibility", {"household": "CLIENT_1"})]:
            if tool in screen["tools"] and tool not in have:
                have[tool] = call(tool, args)
        d = have["opportunity_facts"]["data"]
        text = [f"{d['label']} for CLIENT_1: {d['reason']}. Amount involved: {money(d['amount'])}."]
        if "eligibility" in have and have["eligibility"]["ok"]:
            text.append(f"Program eligibility: {have['eligibility']['data']['label']}.")
        fit = have.get("strategy_fit")
        if fit and not fit["ok"]:
            text.append(f"The strategy comparison is not available: {fit['reason']}")
        if fit and fit["ok"]:
            text.append("Program strategies suggested: " + "; ".join(s["name"] for s in fit["data"]["suggested"]) + ".")
        text += [m["text"] for m in must_say()]
        fallback = {"answer": " ".join(text), "citations": cite(), "actions": []}
        still = g.check_answer(fallback, rules, policy, gctx)
        if still:
            raise AssertionError(f"the rule-based answer breaks {still}")
        turn.outcome, turn.answer, turn.citations = "fallback", fallback["answer"], fallback["citations"]

    turn.display = g.restore(turn.answer, names)
    turn.tools_called = [r["tool"] for r in results]
    turn.blocked = blocked
    turn.disclosures = [d["id"] for d in g.required_disclosures(gctx["tool_results"], policy)]
    return turn
