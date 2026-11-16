"""The lean turn. Same four layers, less work per request.

    context record
      -> entitlement                                   no model call if it fails
      -> read the household's DECISION RECORD          built last night, policy-stamped
      -> not applicable?                               no model call
      -> PREFETCH the fields this screen needs         harness, from the record
      -> ONE model call: narrative with references     (more only for a what-if tool)
      -> check the narrative                           H-REF H-RAWFIG H-WORDING H-PII H-TOKEN
      -> one repair attempt, then the template narrative
      -> RENDER: the app inserts figures, appends disclosures and the draft label,
         attaches citations, builds confirm-first actions, restores names
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..harness import guardrails as g
from ..harness.agent import Env, compose_prompt
from ..records import RecordStore
from ..tools import opportunities as opp
from ..tools.toolbox import Toolbox
from .bundle import Bundle, prefetch
from .render import BY_CONSTRUCTION, NARRATIVE_RULES, check_narrative, render, template_narrative

MAX_STEPS = 30


@dataclass
class LeanTurn:
    outcome: str                  # pass | repaired | fallback | refused | not_applicable
    kind: str                     # ai | rule_based
    narrative: str = ""           # what the model wrote, with references
    answer: str = ""              # rendered, tokens
    display: str = ""             # rendered, names restored
    citations: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    dropped_actions: list = field(default_factory=list)
    skills: list = field(default_factory=list)
    prefetched: list = field(default_factory=list)
    model_calls: int = 0
    what_if_calls: list = field(default_factory=list)
    tool_refusals: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    violations: list = field(default_factory=list)
    disclosures: list = field(default_factory=list)
    checks_run: list = field(default_factory=lambda: list(NARRATIVE_RULES))
    by_construction: list = field(default_factory=lambda: list(BY_CONSTRUCTION))
    policy: str = ""


def _screen(env: Env, opportunity: str, step: int) -> dict:
    lean = env.config["lean"]
    pick = lambda section: list(dict.fromkeys(  # noqa: E731
        (lean[section]["default"].get(step) or []) + (lean[section].get(opportunity, {}).get(step) or [])))
    return {"parts": pick("prefetch"), "what_if": pick("what_if_tools")}


def run_turn(env: Env, store: RecordStore, ctx: dict, question: str, model,
             confirmations: set | None = None) -> LeanTurn:
    policy, hh = env.policy, env.households[ctx["household"]]
    opportunity, step = ctx["opportunity"], ctx["step"]

    if hh["advisor"] != ctx["advisor"]:
        return LeanTurn("refused", "rule_based", display="This household is not in your book.",
                        blocked=[{"rule": "H-ENTITLE", "tool": None}], policy=policy.stamp)

    record = store.get(ctx["household"], policy)            # raises if built under another pack
    if not record["opportunities"][opportunity]:
        return LeanTurn("not_applicable", "rule_based", policy=policy.stamp,
                        display=f"{opp.LABELS[opportunity]} does not apply to this household under policy {policy.version}.")

    base = env.screen(opportunity, step)                    # skills and actions, as before
    screen = _screen(env, opportunity, step)
    rules = env.config["answer_rules"]
    limit = env.config["limits"]["max_tool_calls"]
    toolbox = Toolbox(policy, env.households, confirmations, records=store)
    tokens = {"CLIENT_1": ctx["household"]}
    id_to_token = {v: k for k, v in tokens.items()}
    names = {"CLIENT_1": f"the {ctx['household'].capitalize()} household"}

    # ---- prefetch: the harness gathers what the screen needs --------------------
    raw = prefetch(toolbox, ctx["household"], opportunity, screen["parts"])
    bundle = Bundle(g.tokenize(raw.fields, id_to_token), raw.disclosures, raw.refusals, raw.parts)

    turn = LeanTurn("fallback", "rule_based", skills=[s.id for s in base["skills"]],
                    prefetched=bundle.parts, policy=policy.stamp)
    state = {"opportunity": opportunity, "step": step, "question": question,
             "prompt": compose_prompt(base["skills"], screen["what_if"], base["actions"]),
             "fields": bundle.fields, "allowed_tools": screen["what_if"],
             "allowed_actions": base["actions"], "blocked": turn.blocked, "attempt": 0, "violations": []}
    narrative, action_ids = None, []

    for _ in range(MAX_STEPS):
        msg = model.next(state)
        turn.model_calls += 1
        if "tool" in msg:                                   # a what-if the screen did not anticipate
            stop = g.check_call(msg, screen["what_if"], tokens, len(turn.what_if_calls), limit)
            if stop:
                turn.blocked.append({"rule": stop, "tool": msg["tool"]})
                continue
            args = {**msg["args"], "household": tokens[msg["args"]["household"]]}
            env_ = g.tokenize(toolbox.call(msg["tool"], args), id_to_token)
            bundle.add(f"whatif.{msg['tool']}", env_, msg["tool"])
            turn.what_if_calls.append(msg["tool"])
            continue
        found = check_narrative(msg["final"]["narrative"], bundle.fields, rules, tokens)
        turn.violations.append(found)
        if not found:
            turn.outcome = "pass" if state["attempt"] == 0 else "repaired"
            turn.kind, narrative, action_ids = "ai", msg["final"]["narrative"], msg["final"].get("actions", [])
            break
        if state["attempt"] == 0:
            state["attempt"], state["violations"] = 1, found
            continue
        break

    if narrative is None:                                   # template; same renderer, same checks
        narrative = template_narrative(bundle.fields)
        assert not check_narrative(narrative, bundle.fields, rules, tokens)
        turn.outcome = "fallback"

    out = render(narrative, bundle.fields, bundle.disclosures, policy, step, rules["H-DRAFT"],
                 action_ids, base["actions"])
    turn.narrative, turn.answer = narrative, out["answer"]
    turn.citations, turn.actions, turn.dropped_actions = out["citations"], out["actions"], out["dropped_actions"]
    turn.display = g.restore(out["answer"], names)
    turn.disclosures, turn.tool_refusals = bundle.disclosures, bundle.refusals
    return turn
