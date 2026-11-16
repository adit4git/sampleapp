"""Evals, by layer.

    policy   the pack is structurally valid
    tools    PARITY: every tool agrees with the prototype for every synthetic household
             (13 criteria, household ranking and heat, eligibility, strategy ranking)
    layers   LINT: no values in skills; no magic numbers in tools; harness config refers
             only to tools and skills that exist
    agent    FLOW and RED-TEAM cases over the harness and skills (evals/cases.yaml)
    coverage every harness rule is targeted by at least one red-team case

Which groups run depends on which layer changed:

    python -m atlas.evals                                   everything
    python -m atlas.evals --changed policy/atlas-policy.yaml
    python -m atlas.evals --changed skills/opportunity/advisory-move/SKILL.md
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import yaml

from . import skills as skills_mod
from .harness.agent import Env, run_turn
from .harness.models import StubModel
from .policy import Policy, validate
from .tools import eligibility as elig
from .tools import opportunities as opp
from .tools import strategies as strat
from .tools.toolbox import Toolbox

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_LITERALS = {0, 1, -1, 1000, 0.5}      # structure and rounding, not policy

# layer of a changed file -> eval groups that must run
IMPACT = {"policy": ["policy", "tools", "agent", "lean"],
          "atlas/tools": ["tools", "layers", "agent", "lean"],
          "skills": ["layers", "agent"],
          "harness": ["layers", "agent", "lean", "coverage"],
          "atlas/harness": ["agent", "coverage"],
          "atlas/lean": ["lean", "coverage"],
          "atlas/records.py": ["lean"],
          "evals": ["agent", "coverage"]}
ALL = ["policy", "tools", "layers", "agent", "lean", "coverage"]


def load_data() -> dict:
    data = json.loads((ROOT / "data" / "households.json").read_text())
    data["by_id"] = {h["id"]: h for h in data["households"]}
    return data


def load_env(policy: Policy | None = None, root: Path = ROOT) -> Env:
    policy = policy or Policy.load(root / "policy" / "atlas-policy.yaml")
    return Env.load(root, policy, load_data()["by_id"], skills_mod.load(root / "skills"))


def _row(group, name, ok, detail=""):
    return {"group": group, "id": name, "ok": bool(ok), "detail": detail}


# ---------------------------------------------------------------- policy
def policy_checks(policy: Policy) -> list[dict]:
    errors = validate(policy, set(strat.RULE_TYPES), opp.ORDER)
    return [_row("policy", "pack-is-valid", not errors, "; ".join(errors) or policy.stamp)]


# ---------------------------------------------------------------- tools: parity
def parity_checks(policy: Policy, data: dict) -> list[dict]:
    hs = data["households"]
    close = lambda a, b: abs(a - b) <= 1e-6 * max(1.0, abs(b))  # noqa: E731
    rows = []
    for k in opp.ORDER:
        bad = []
        for h in hs:
            got, want = opp.evaluate(h["facts"], policy)[k], h["expected"][k]
            if bool(got) != want["flagged"] or (got and not close(got["amount"], want["amount"])):
                bad.append(h["id"])
        rows.append(_row("tools", f"criterion:{k}", not bad, f"{len(hs) - len(bad)}/{len(hs)}" + (f" differs: {bad}" if bad else "")))

    bad = [h["id"] for h in hs if [(o["key"], o["step"]) for o in opp.ranked(opp.evaluate(h["facts"], policy))]
           != [(o["k"], o["step"]) for o in h["expected_ranking"]]]
    rows.append(_row("tools", "household-ranking-and-heat", not bad, f"{len(hs) - len(bad)}/{len(hs)}" + (f" differs: {bad}" if bad else "")))

    bad = []
    for h in hs:
        e, want = elig.check(h["facts"], policy), h["expected_eligibility"]
        if e["status"] != want["status"] or [c["owner"] for c in e["conditions"]] != want["owners"]:
            bad.append(h["id"])
    rows.append(_row("tools", "eligibility-status-and-owners", not bad, f"{len(hs) - len(bad)}/{len(hs)}" + (f" differs: {bad}" if bad else "")))

    with_s = [h for h in hs if h["strategy"] and "expected" in h["strategy"]]
    bad = {"availability": [], "score": [], "order": [], "suggestions": []}
    for h in with_s:
        s = h["strategy"]
        r = strat.rank(h["facts"], s["inputs"], policy)
        if any(strat.availability(policy.strategy(i["id"]), h["facts"]) != i["unavailable_reason"] for i in s["inputs"]):
            bad["availability"].append(h["id"])
        if any(abs(x["score"] - y["score"]) > 1e-9 or abs(x["fit"] - y["fit"]) > 1e-9
               or x["same_as_default"] != y["same"] for x, y in zip(r["ranked"], s["expected"]["rows"])):
            bad["score"].append(h["id"])
        if [x["id"] for x in r["ranked"]] != s["expected"]["order"]:
            bad["order"].append(h["id"])
        if r["suggested"] != s["expected"]["suggested"]:
            bad["suggestions"].append(h["id"])
    for name, b in bad.items():
        rows.append(_row("tools", f"strategy-{name}", not b, f"{len(with_s) - len(b)}/{len(with_s)}" + (f" differs: {b}" if b else "")))
    return rows


# ---------------------------------------------------------------- layers: lint
def magic_numbers(root: Path = ROOT) -> list[str]:
    """Numeric literals in tool code that look like policy values."""
    out = []
    for f in sorted((root / "atlas" / "tools").glob("*.py")):
        src = f.read_text()
        lines = src.splitlines()
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
                    and not isinstance(node.value, bool) and node.value not in ALLOWED_LITERALS
                    and "stub" not in lines[node.lineno - 1]):
                out.append(f"{f.name}:{node.lineno}: literal {node.value!r}. Read it from the policy pack.")
    return out


def layer_checks(env: Env, root: Path = ROOT) -> list[dict]:
    tools = Toolbox(env.policy, env.households).names
    skill_problems = skills_mod.lint(env.skills, tools)
    cfg = []
    for name, s in env.config["screens"].items():
        cfg += [f"screen {name}: unknown skill '{x}'" for x in s.get("skills", []) if x not in env.skills]
        for step, names in (s.get("tools") or {}).items():
            cfg += [f"screen {name} step {step}: unknown tool '{x}'" for x in names if x not in tools]
    nums = magic_numbers(root)
    return [_row("layers", "skills-hold-no-values", not skill_problems, "; ".join(skill_problems) or f"{len(env.skills)} skills"),
            _row("layers", "tools-hold-no-magic-numbers", not nums, "; ".join(nums) or "all values read from the pack"),
            _row("layers", "harness-config-refers-to-real-things", not cfg, "; ".join(cfg))]


# ---------------------------------------------------------------- agent: flow and red-team
def load_cases(root: Path = ROOT) -> dict:
    return yaml.safe_load((root / "evals" / "cases.yaml").read_text())


def _household_for(case: dict, env: Env) -> dict | None:
    if "household" in case:
        return env.households[case["household"]]
    return next((h for _, h in sorted(env.households.items())
                 if opp.evaluate(h["facts"], env.policy)[case["opportunity"]]), None)


def run_case(env: Env, kind: str, case: dict) -> dict:
    h = _household_for(case, env)
    if h is None:
        return _row("agent", case["id"], False, "no synthetic household matches")
    ctx = {"advisor": case.get("advisor", h["advisor"]), "household": h["id"],
           "opportunity": case["opportunity"], "step": case.get("step", 2)}
    t = run_turn(env, ctx, "What do you suggest?", StubModel(case.get("model", "good")))
    exp, low = case.get("expect", {}), t.answer.lower()
    first = [v["rule"] for v in (t.violations[0] if t.violations else [])]
    blocked = [b["rule"] for b in t.blocked]
    refusals = [r["code"] for r in t.tool_refusals]
    checks = {
        "outcome": exp.get("outcome") in (None, t.outcome),
        "skills": exp.get("skills") in (None, t.skills),
        "tools": all(x in t.tools_called for x in exp.get("tools", [])),
        "not_tools": all(x not in t.tools_called for x in exp.get("not_tools", [])),
        "tool_refusals": all(x in refusals for x in exp.get("tool_refusals", [])),
        "disclosures": exp.get("disclosures") is None or (
            all(x in t.disclosures for x in exp["disclosures"]) and (exp["disclosures"] or not t.disclosures)),
        "includes": all(x.lower() in low for x in exp.get("includes", [])),
        "excludes": all(x.lower() not in low for x in exp.get("excludes", [])),
        "cites": all(x in t.citations for x in exp.get("cites", [])),
        "actions": exp.get("actions") is None or [a["action"] for a in t.actions] == exp["actions"],
        "violations": all(x in first for x in exp.get("violations", [])),
        "blocked": all(x in blocked for x in exp.get("blocked", [])),
        "clean": kind != "flow" or (not first and not blocked),
    }
    failed = [k for k, v in checks.items() if not v]
    return _row("agent", case["id"], not failed,
                f"{kind:<7} {h['id']} step {ctx['step']}: {t.outcome}"
                + (f", caught {first}" if first else "") + (f", blocked {blocked}" if blocked else "")
                + (f", tool refused {refusals}" if refusals else "") + (f"  FAILED {failed}" if failed else ""))


def agent_checks(env: Env, cases: dict) -> list[dict]:
    return [run_case(env, kind, c) for kind in ("flow", "redteam") for c in cases.get(kind, [])]


def coverage(env: Env, cases: dict) -> dict[str, list[str]]:
    cov = {r: [] for r in list(env.config["answer_rules"]) + list(env.config["call_rules"])}
    for c in cases.get("redteam", []):
        for target in c.get("targets", []):
            cov.setdefault(target, []).append(c["id"])
    return cov


# ---------------------------------------------------------------- run
def groups_for(changed: str | None) -> list[str]:
    if not changed:
        return list(ALL)
    path = changed.replace("\\", "/")
    for prefix in sorted(IMPACT, key=len, reverse=True):
        if path.startswith(prefix):
            return IMPACT[prefix]
    return list(ALL)


def run(env: Env, data: dict, groups: list[str] | None = None, root: Path = ROOT) -> dict:
    groups = groups or groups_for(None)
    cases = load_cases(root)
    rows = []
    if "policy" in groups:
        rows += policy_checks(env.policy)
    if "tools" in groups:
        rows += parity_checks(env.policy, data)
    if "layers" in groups:
        rows += layer_checks(env, root)
    if "agent" in groups:
        rows += agent_checks(env, cases)
    cov = coverage(env, cases)
    lean_cov: dict = {}
    if "lean" in groups:
        from .lean.evals import lean_checks
        measure = None
        if root == ROOT:                       # the before/after comparison runs on the real tree
            sys.path.insert(0, str(ROOT))
            from compare import measure
        lean_rows, lean_cov = lean_checks(env, measure)
        rows += lean_rows
    uncovered = (sorted(r for r, c in cov.items() if not c)
                 + sorted(f"lean:{r}" for r, c in lean_cov.items() if not c)) if "coverage" in groups else []
    return {"rows": rows, "coverage": cov, "lean_coverage": lean_cov, "uncovered": uncovered, "groups": groups,
            "passed": sum(r["ok"] for r in rows), "total": len(rows)}


def main(argv: list[str]) -> int:
    changed = argv[argv.index("--changed") + 1] if "--changed" in argv else None
    env, data = load_env(), load_data()
    rep = run(env, data, groups_for(changed))
    if changed:
        print(f"Changed: {changed} -> groups: {', '.join(rep['groups'])}\n")
    for r in rep["rows"]:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['group']:<7} {r['id']:<52} {r['detail']}")
    print(f"\n{rep['passed']}/{rep['total']} checks passed  (policy {env.policy.stamp})")
    if "coverage" in rep["groups"]:
        print("\nHarness rule -> red-team cases")
        for rule, cs in rep["coverage"].items():
            print(f"  {'ok  ' if cs else 'NONE'} {rule:<11} {', '.join(cs)}")
        if rep["lean_coverage"]:
            print("\nLean flow: rule still checked -> red-team cases")
            for rule, cs in rep["lean_coverage"].items():
                print(f"  {'ok  ' if cs else 'NONE'} {rule:<11} {', '.join(cs)}")
    return 0 if rep["passed"] == rep["total"] and not rep["uncovered"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
