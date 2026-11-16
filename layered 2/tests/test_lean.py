"""The three efficiency changes, as tests: decide nightly, fetch before the model, and let
the app write what must be right."""
import pytest

from atlas import records
from atlas.evals import ROOT, load_data, load_env
from atlas.lean.agent import run_turn
from atlas.lean.models import LeanStub
from atlas.lean.render import check_narrative
from atlas.policy import Policy
from atlas.tools.toolbox import Toolbox
from compare import Counter, measure

DATA = load_data()
ENV = load_env()
STORE = records.build(ENV.households, ENV.policy)
ADV = {"advisor": "dana", "household": "whitaker", "opportunity": "advisory", "step": 2}


# ------------------------------------------------------------ the comparison
def test_one_model_call_no_request_time_decisions_and_the_same_output():
    r = measure()
    for x in r["rows"]:
        assert x["lean"]["model_calls"] == 1 < x["layered"]["model_calls"]
        assert x["lean"]["decisions"] == 0 < x["layered"]["decisions"]
        assert x["same_disclosures"] and x["same_citations"] and x["same_figures"] and x["same_actions"]
    assert r["nightly"] == {"criteria": 37, "eligibility": 14, "ranking": 12}


# ------------------------------------------------------------ 3. decide once a night
def test_tools_answer_from_the_record_without_deciding_again():
    tb = Toolbox(ENV.policy, ENV.households, records=STORE)
    with Counter() as c:
        tb.opportunity_facts("whitaker", "advisory")
        tb.eligibility("whitaker")
        tb.strategy_fit("whitaker")
        tb.fee_estimate("whitaker", "cio")
    assert c.total == 0


def test_prerequisites_still_hold_when_reading_records():
    tb = Toolbox(ENV.policy, ENV.households, records=STORE)
    assert tb.strategy_fit("ashby")["refused"] == "PREREQ-ELIGIBILITY"
    assert tb.generate_proposal("whitaker", "advisory", "cio")["refused"] == "PREREQ-CONFIRMATION"


def test_records_built_under_another_pack_are_never_served():
    draft = ENV.policy.with_changes({"opportunities.concentration.threshold": 0.15})
    with pytest.raises(records.StaleRecords, match="Rebuild before serving"):
        STORE.get("whitaker", draft)
    rebuilt = records.build(ENV.households, draft)
    assert STORE.get("whitaker", ENV.policy)["opportunities"]["concentration"] is not None
    assert rebuilt.get("whitaker", draft)["opportunities"]["concentration"] is None


def test_advisor_inputs_are_computed_live():
    tb = Toolbox(ENV.policy, ENV.households, records=STORE)
    with Counter() as c:
        base = tb.opportunity_what_if("whitaker", "maturing", {})
        wider = tb.opportunity_what_if("whitaker", "maturing", {"horizon_months": 36})
    assert c.n["criteria"] == 2
    assert wider["data"]["amount"] >= base["data"]["amount"]
    assert tb.opportunity_what_if("whitaker", "maturing", {"min_amount": 10**9})["data"]["applies"] is False


# ------------------------------------------------------------ 2. fetch before the model
def test_the_harness_fetches_what_the_screen_needs():
    t = run_turn(ENV, STORE, ADV, "?", LeanStub("good"))
    assert t.prefetched == ["opportunity", "eligibility", "strategy", "fee"] and t.model_calls == 1
    step1 = run_turn(ENV, STORE, dict(ADV, step=1), "?", LeanStub("good"))
    assert step1.prefetched == ["opportunity", "eligibility"]
    conc = run_turn(ENV, STORE, {"advisor": "dana", "household": "henderson", "opportunity": "concentration", "step": 2},
                    "?", LeanStub("good"))
    assert conc.prefetched == ["opportunity"]


def test_a_what_if_costs_one_extra_call_and_its_result_becomes_a_field():
    t = run_turn(ENV, STORE, ADV, "What if we spread it with a bigger budget?", LeanStub("what_if"))
    assert t.model_calls == 2 and t.what_if_calls == ["transition_schedule"]
    assert "yearly gain budget of $500K" in t.answer


def test_a_refusal_is_prefetched_as_an_answer():
    t = run_turn(ENV, STORE, dict(ADV, household="ashby"), "?", LeanStub("good"))
    assert t.outcome == "pass" and t.tool_refusals == [{"tool": "strategy_fit", "code": "PREREQ-ELIGIBILITY"}]
    assert "specialist reviews" in t.answer and "Suggested program strategy" not in t.answer


# ------------------------------------------------------------ 1. the app writes what must be right
def test_a_model_that_writes_almost_nothing_cannot_omit_anything():
    t = run_turn(ENV, STORE, dict(ADV, step=3), "?", LeanStub("silent"))
    assert t.outcome == "pass" and t.violations == [[]]
    for must in ("Form CRS", "Conflict to disclose", "in addition to the advisory fee", "draft for advisor review"):
        assert must in t.answer
    assert t.citations == ["opportunity-criteria", "form-crs", "program-brochure"]


def test_the_model_cannot_report_or_invent_an_action():
    t = run_turn(ENV, STORE, dict(ADV, step=3), "?", LeanStub("unknown_action"))
    assert t.actions == [{"action": "generate_proposal", "needs_confirmation": True}]
    assert t.dropped_actions == ["place_trade"]


def test_even_a_correct_figure_must_be_a_reference():
    t = run_turn(ENV, STORE, ADV, "?", LeanStub("copies_figure"))
    assert t.violations[0][0]["rule"] == "H-RAWFIG" and t.outcome == "repaired"


def test_the_fallback_is_the_template_through_the_same_renderer():
    t = run_turn(ENV, STORE, ADV, "?", LeanStub("promise"))
    assert (t.outcome, t.kind) == ("fallback", "rule_based")
    assert "Worth raising" not in t.answer and "Form CRS" in t.answer and "$7.2M" in t.answer


def test_no_model_call_when_not_entitled_or_not_applicable():
    class Exploding:
        def next(self, state):
            raise AssertionError("the model must not be called")

    assert run_turn(ENV, STORE, dict(ADV, advisor="marcus"), "?", Exploding()).outcome == "refused"
    assert run_turn(ENV, STORE, dict(ADV, opportunity="harvest"), "?", Exploding()).outcome == "not_applicable"


# ------------------------------------------------------------ what this does NOT solve
def test_known_gap_a_real_field_used_in_the_wrong_place_is_not_caught():
    """References guarantee the VALUE is a tool's. They do not guarantee it is the right
    value for the sentence. That needs an eval against a real model, not a structural check."""
    fields = {"opportunity.amount": {"kind": "money", "display": "$7.2M"},
              "strategy.suggested.0.tax_now": {"kind": "money", "display": "$152K"}}
    wrong = "Tax due now would be {{opportunity.amount}}."
    assert check_narrative(wrong, fields, ENV.config["answer_rules"], {"CLIENT_1": "whitaker"}) == []


def test_layered_flow_is_untouched():
    from atlas.harness.agent import run_turn as layered_turn
    from atlas.harness.models import StubModel
    assert layered_turn(ENV, ADV, "?", StubModel("good")).outcome == "pass"
    assert Policy.load(ROOT / "policy" / "atlas-policy.yaml").stamp == ENV.policy.stamp
