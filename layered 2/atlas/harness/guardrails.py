"""LAYER 4 (harness): checks around every model call. Generic: no opportunity, strategy or
threshold is named here. What must be disclosed comes from tool results; the wording comes
from the policy pack; the rule list comes from harness.yaml.
"""
from __future__ import annotations

import re

from ..fmt import money, pct
from ..policy import Policy

FIGURE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[KMB]?|\d+(?:\.\d+)?%")
TOKEN = re.compile(r"\bCLIENT_\d+\b")


# ------------------------------------------------------------------ before a tool runs
def check_call(call: dict, allowed: list[str], tokens: dict[str, str], used: int, limit: int) -> str | None:
    if call["tool"] not in allowed:
        return "H-TOOL"
    if "household" in call["args"] and call["args"]["household"] not in tokens:
        return "H-SCOPE"
    if used >= limit:
        return "H-LIMIT"
    return None


# ------------------------------------------------------------------ figures
def _walk(obj, key=""):
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        yield "n", key, float(obj)
    elif isinstance(obj, str):
        yield "s", key, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, key)


def allowed_figures(tool_results: list[dict]) -> set[str]:
    out: set[str] = set()
    for kind, key, v in _walk(tool_results):
        if kind == "s":
            out |= set(FIGURE.findall(v))
        elif key.endswith("_bp"):
            out.add(f"{v / 100:.2f}%")
        else:
            out |= {money(v), pct(v, 0), pct(v, 1), pct(v, 2)}
    return out


# ------------------------------------------------------------------ after the answer
def required_disclosures(tool_results: list[dict], policy: Policy) -> list[dict]:
    """The union of what the tools called this turn said must be disclosed."""
    ids: list[str] = []
    for r in tool_results:
        ids += [d for d in r.get("required_disclosures", []) if d not in ids]
    return [policy.disclosure(d) for d in ids]


def check_answer(output: dict, rules: dict, policy: Policy, ctx: dict) -> list[dict]:
    text = output.get("answer", "")
    low = text.lower()
    cites = output.get("citations", [])
    found = []

    def fail(rule, detail):
        found.append({"rule": rule, "detail": detail})

    stray = [m for m in FIGURE.findall(text) if m not in allowed_figures(ctx["tool_results"])]
    if stray:
        fail("H-FIG", f"not in any tool result: {', '.join(stray)}")

    needed = required_disclosures(ctx["tool_results"], policy)
    for d in needed:
        if not any(m in low for m in d["match"]):
            fail("H-DISCLOSE", f"missing disclosure '{d['id']}'")

    known = set(policy["sources"])
    if any(c not in known for c in cites):
        fail("H-CITE", "citation to a source that is not approved")
    elif any(t in low for t in rules["H-CITE"]["when_mentions"]) and not cites:
        fail("H-CITE", "states a rule without a citation")
    else:
        uncited = [d["id"] for d in needed if any(m in low for m in d["match"]) and d["source"] not in cites]
        if uncited:
            fail("H-CITE", f"disclosures without their source: {uncited}")

    hit = [p for p in rules["H-WORDING"]["forbidden"] if re.search(p, low)]
    if hit:
        fail("H-WORDING", f"forbidden wording: {hit}")

    draft = rules["H-DRAFT"]
    if ctx["step"] in draft["steps"] and not any(m in low for m in draft["match"]):
        fail("H-DRAFT", "proposal text without the draft label")

    for a in output.get("actions", []):
        if a["action"] in rules["H-CONFIRM"]["actions"] and (a.get("executed") or not a.get("needs_confirmation")):
            fail("H-CONFIRM", f"{a['action']} without the advisor's confirmation")
        if a["action"] not in ctx["allowed_actions"]:
            fail("H-CONFIRM", f"{a['action']} is not offered on this step")

    foreign = [t for t in TOKEN.findall(text) if t not in ctx["tokens"]]
    if foreign:
        fail("H-TOKEN", f"client token not issued for this request: {foreign}")

    leaked = [name for name, pat in rules["H-PII"]["patterns"].items() if re.search(pat, text)]
    if leaked:
        fail("H-PII", f"identifier pattern in the answer: {leaked}")
    return found


def tokenize(obj, id_to_token: dict[str, str]):
    """Replace household ids with client tokens in anything sent to the model."""
    if isinstance(obj, str):
        for hid, tok in id_to_token.items():
            obj = obj.replace(hid, tok)
        return obj
    if isinstance(obj, dict):
        return {k: tokenize(v, id_to_token) for k, v in obj.items()}
    if isinstance(obj, list):
        return [tokenize(v, id_to_token) for v in obj]
    return obj


def restore(text: str, token_to_name: dict[str, str]) -> str:
    """Names go back in for display only. The model never sees this table."""
    for tok, name in token_to_name.items():
        text = text.replace(tok, name)
    return text
