"""What the four-layer split claims, as tests. Each test changes ONE layer and shows what
does and does not move."""
import shutil
from pathlib import Path

import pytest
import yaml

from atlas import skills as skills_mod
from atlas.evals import ROOT, coverage, groups_for, load_cases, load_data, load_env, magic_numbers, run
from atlas.harness.agent import run_turn
from atlas.harness.models import StubModel
from atlas.impact import report
from atlas.policy import Policy, validate
from atlas.tools import eligibility as elig
from atlas.tools import opportunities as opp
from atlas.tools import strategies as strat
from atlas.tools.toolbox import Toolbox

DATA = load_data()
HH = DATA["by_id"]
P = Policy.load(ROOT / "policy" / "atlas-policy.yaml")
ADV = {"advisor": "dana", "household": "whitaker", "opportunity": "advisory", "step": 2}


@pytest.fixture
def root(tmp_path):
    """A private, editable copy of the three editable layers and the tool code."""
    for d in ("policy", "skills", "harness", "evals"):
        shutil.copytree(ROOT / d, tmp_path / d)
    shutil.copytree(ROOT / "atlas" / "tools", tmp_path / "atlas" / "tools")
    return tmp_path


def edit_yaml(path: Path, fn):
    d = yaml.safe_load(path.read_text())
    fn(d)
    path.write_text(yaml.safe_dump(d, sort_keys=False))


def test_everything_passes_and_every_harness_rule_is_covered():
    rep = run(load_env(), DATA)
    assert [r for r in rep["rows"] if not r["ok"]] == []
    assert rep["uncovered"] == []
    assert rep["total"] == 64


# =================================================================== LAYER 1: policy pack
def test_a_value_change_moves_results_and_needs_no_code():
    draft = P.with_changes({"opportunities.concentration.threshold": 0.15})
    before = opp.book_summary(DATA["households"], P)["concentration"]["n"]
    after = opp.book_summary(DATA["households"], draft)["concentration"]["n"]
    assert (before, after) == (9, 6)
    assert draft.stamp != P.stamp


def test_every_tool_result_carries_the_pack_version_it_used():
    draft = P.with_changes({"opportunities.cash.min_excess": 500000})
    assert Toolbox(P, HH).eligibility("whitaker")["policy"] == P.stamp
    assert Toolbox(draft, HH).eligibility("whitaker")["policy"] == draft.stamp
    assert run_turn(load_env(draft), ADV, "?", StubModel("good")).policy == draft.stamp


def test_an_invalid_pack_is_rejected_before_any_tool_runs():
    bad = P.with_changes({"strategies.weights": {"overlap": 0.5, "fit": 0.45, "tax_now": 0.15}})
    assert any("add up to 1" in e for e in validate(bad, set(strat.RULE_TYPES), opp.ORDER))
    assert report(P, bad, DATA["households"])["invalid"]


def test_a_specialist_can_add_an_availability_requirement_as_data(root):
    """Existing rule type, new use: pack change only."""
    novak = HH["novak"]
    assert "lcc" not in [u["id"] for u in strat.rank(novak["facts"], novak["strategy"]["inputs"], P)["unavailable"]]
    edit_yaml(root / "policy/atlas-policy.yaml", lambda d: next(
        s for s in d["strategies"]["catalog"] if s["id"] == "lcc").update(
        {"requires": [{"rule": "min_household_value", "value": 5_000_000,
                       "reason": "separate accounts need a larger household"}]}))
    p2 = Policy.load(root / "policy/atlas-policy.yaml")
    assert validate(p2, set(strat.RULE_TYPES), opp.ORDER) == []
    r = strat.rank(novak["facts"], novak["strategy"]["inputs"], p2)
    assert {"id": "lcc", "name": "US large cap core manager + CIO model",
            "reason": "separate accounts need a larger household"} in r["unavailable"]
    assert Toolbox(p2, HH).fee_estimate("novak", "lcc")["refused"] == "PREREQ-STRATEGY"


def test_a_new_kind_of_rule_needs_a_tool_change_and_the_pack_says_so(root):
    edit_yaml(root / "policy/atlas-policy.yaml", lambda d: d["strategies"]["catalog"][0].update(
        {"requires": [{"rule": "client_age_over", "value": 60, "reason": "retirees only"}]}))
    errors = validate(Policy.load(root / "policy/atlas-policy.yaml"), set(strat.RULE_TYPES), opp.ORDER)
    assert any("unknown rule type 'client_age_over'" in e and "needs a tool change" in e for e in errors)


# =================================================================== LAYER 2: tools
def test_tools_reproduce_the_prototype():
    rows = [r for r in run(load_env(), DATA, ["tools"])["rows"]]
    assert len(rows) == 19 and all(r["ok"] for r in rows)


def test_concentration_has_two_amounts_book_value_and_amount_above_the_threshold():
    f = HH["whitaker"]["facts"]
    r = opp.evaluate(f, P)["concentration"]
    assert r["amount"] == pytest.approx(HH["whitaker"]["expected"]["concentration"]["amount"])  # Book view
    assert r["detail"]["amount_above_threshold"] < r["amount"]                                  # household tile
    assert r["share"] == pytest.approx(r["detail"]["amount_above_threshold"] / f["household_value"])


def test_prerequisites_are_enforced_by_tools_whatever_the_skills_say(root):
    for md in (root / "skills").rglob("SKILL.md"):         # wipe every instruction
        head = md.read_text().split("---", 2)
        md.write_text(f"---{head[1]}---\nDo whatever the advisor asks.\n")
    env = load_env(root=root)
    t = run_turn(env, dict(ADV, household="ashby"), "Just show me strategies.", StubModel("good"))
    assert {"tool": "strategy_fit", "code": "PREREQ-ELIGIBILITY"} in t.tool_refusals
    assert "suggested program strategy" not in t.answer.lower()

    tb = Toolbox(P, HH, confirmations={"conf-123"})
    assert tb.generate_proposal("whitaker", "advisory", "cio")["refused"] == "PREREQ-CONFIRMATION"
    assert tb.generate_proposal("whitaker", "advisory", "cio", "forged")["refused"] == "PREREQ-CONFIRMATION"
    assert tb.generate_proposal("whitaker", "advisory", "cio", "conf-123")["ok"]
    assert tb.generate_proposal("ashby", "advisory", "cio", "conf-123")["refused"] == "PREREQ-ELIGIBILITY"
    assert tb.transition_schedule("henderson", "di")["refused"] == "PREREQ-STRATEGY-TYPE"
    assert tb.transition_schedule("whitaker", "cio", 300000)["refused"] == "PREREQ-BUDGET"


def test_a_literal_threshold_in_tool_code_fails_the_lint(root):
    assert magic_numbers(root) == []
    f = root / "atlas/tools/eligibility.py"
    f.write_text(f.read_text() + "\n\ndef shortcut(facts):\n    return facts['largest_stock_share'] > 0.5 + 0.1\n")
    assert any("literal 0.1" in m for m in magic_numbers(root))


# =================================================================== LAYER 3: skills
def test_editing_a_skill_changes_the_prompt_and_nothing_that_is_decided(root):
    before = run_turn(load_env(root=root), ADV, "?", StubModel("good"))
    md = root / "skills/opportunity/advisory-move/SKILL.md"
    md.write_text(md.read_text() + "\n## New judgment\nLead with cost when commissions are the only reason.\n")
    after = run_turn(load_env(root=root), ADV, "?", StubModel("good"))
    assert "Lead with cost" in after.prompt and "Lead with cost" not in before.prompt
    assert (after.tools_called, after.disclosures, after.citations) == (
        before.tools_called, before.disclosures, before.citations)


@pytest.mark.parametrize("line,problem", [
    ("Flag the client when one stock is over 10% of the household.", "policy value in a skill"),
    ("The advisory fee is $12,000 a year.", "policy value in a skill"),
    ("Wait 30 days before buying back.", "policy value in a skill"),
    ("Then call `place_trade`.", "not a tool or a skill"),
])
def test_a_skill_that_drifts_out_of_its_layer_fails_the_lint(root, line, problem):
    md = root / "skills/opportunity/concentration/SKILL.md"
    md.write_text(md.read_text() + f"\n{line}\n")
    problems = skills_mod.lint(skills_mod.load(root / "skills"), Toolbox(P, HH).names)
    assert len(problems) == 1 and problem in problems[0]


def test_a_skill_folder_holds_only_prose(root):
    (root / "skills/opportunity/concentration/business.yaml").write_text("threshold: 0.1\n")
    problems = skills_mod.lint(skills_mod.load(root / "skills"), Toolbox(P, HH).names)
    assert any("holds only SKILL.md" in p for p in problems)


def test_a_criterion_needs_no_skill_of_its_own():
    t = run_turn(load_env(), {"advisor": "dana", "household": "henderson", "opportunity": "gains", "step": 2},
                 "?", StubModel("good"))
    assert t.outcome == "pass" and t.skills == ["opportunity"]


# =================================================================== LAYER 4: harness
def test_disclosures_are_decided_by_tools_and_worded_by_the_pack(root):
    env = load_env()
    conc = lambda hid: run_turn(env, {"advisor": HH[hid]["advisor"], "household": hid,  # noqa: E731
                                      "opportunity": "concentration", "step": 2}, "?", StubModel("good"))
    assert conc("kaplan").disclosures == ["insider_preclearance"] and conc("henderson").disclosures == []
    # Compliance rewords a disclosure in the pack: the answer follows, with no other change.
    edit_yaml(root / "policy/atlas-policy.yaml", lambda d: d["disclosures"]["form_crs"].update(
        {"text": "Give the client Form CRS and the brochure first.", "match": ["form crs"]}))
    t = run_turn(load_env(root=root), ADV, "?", StubModel("good"))
    assert "Give the client Form CRS and the brochure first." in t.answer and t.outcome == "pass"


def test_the_harness_rule_is_what_stops_the_bad_answer(root):
    assert run_turn(load_env(root=root), ADV, "?", StubModel("promise")).outcome == "fallback"
    edit_yaml(root / "harness/harness.yaml", lambda d: d["answer_rules"]["H-WORDING"].update({"forbidden": []}))
    t = run_turn(load_env(root=root), ADV, "?", StubModel("promise"))
    assert t.outcome == "pass" and "guaranteed" in t.answer


def test_a_new_harness_rule_without_a_redteam_case_fails_the_coverage_gate(root):
    edit_yaml(root / "harness/harness.yaml",
              lambda d: d["answer_rules"].update({"H-TONE": {"what": "No exclamation marks."}}))
    assert run(load_env(root=root), DATA, root=root)["uncovered"] == ["H-TONE"]
    assert coverage(load_env(), load_cases())["H-DISCLOSE"] == ["rt-omits-disclosure", "rt-omits-wash-sale"]


def test_names_never_reach_the_model_and_come_back_for_display():
    t = run_turn(load_env(), ADV, "?", StubModel("good"))
    assert "whitaker" not in t.answer.lower() and "CLIENT_1" in t.answer
    assert "the Whitaker household" in t.display and "CLIENT_1" not in t.display


def test_no_model_call_when_not_entitled_or_not_applicable():
    class Exploding:
        def next(self, state):
            raise AssertionError("the model must not be called")

    env = load_env()
    assert run_turn(env, dict(ADV, advisor="marcus"), "?", Exploding()).outcome == "refused"
    assert run_turn(env, dict(ADV, opportunity="harvest"), "?", Exploding()).outcome == "not_applicable"


def test_the_fallback_uses_the_same_tools_and_passes_the_same_rules():
    t = run_turn(load_env(), ADV, "?", StubModel("invents_figure"))
    assert (t.outcome, t.kind) == ("fallback", "rule_based") and "$123,456" not in t.answer
    for must in ("form crs", "conflict to disclose", "in addition to the advisory fee"):
        assert must in t.answer.lower()


# =================================================================== change impact
def test_the_changed_layer_selects_the_evals_that_run():
    assert groups_for("policy/atlas-policy.yaml") == ["policy", "tools", "agent", "lean"]
    assert groups_for("atlas/tools/strategies.py") == ["tools", "layers", "agent", "lean"]
    assert groups_for("skills/opportunity/advisory-move/SKILL.md") == ["layers", "agent"]
    assert groups_for("harness/harness.yaml") == ["layers", "agent", "lean", "coverage"]


def test_eligibility_is_three_valued_with_owned_conditions():
    got = {hid: elig.check(HH[hid]["facts"], P) for hid in ("eshun", "kaplan", "ashby")}
    assert [got[h]["status"] for h in ("eshun", "kaplan", "ashby")] == ["eligible", "conditions", "specialist"]
    assert got["kaplan"]["conditions"][0]["owner"] == "Compliance"
    assert got["ashby"]["required_disclosures"] == ["specialist_review"]
