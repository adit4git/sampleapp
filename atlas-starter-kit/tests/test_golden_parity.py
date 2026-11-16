"""Parity with the prototype. The golden file was produced by running the prototype's
own JavaScript; the Python tools must reproduce it to within one cent."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from atlas_tools.fees import blended_advisory_rate
from atlas_tools.transition import TransitionAsset, transition_schedule

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "advisory_fee_transition.json").read_text()
)
HOUSEHOLDS = GOLDEN["households"]
CENT = Decimal("0.01")
D = lambda x: Decimal(str(x))  # noqa: E731


@pytest.mark.parametrize("h", HOUSEHOLDS, ids=lambda h: h["id"])
def test_fee_rate_matches_prototype(h):
    got = blended_advisory_rate(D(h["aum"]))
    assert abs(got - D(h["fee_rate"])) < Decimal("0.00000001")


TRANSITION_CASES = [
    (h, budget) for h in HOUSEHOLDS if "transition" in h for budget in h["transition"]
]


@pytest.mark.parametrize(
    "h,budget", TRANSITION_CASES, ids=lambda v: v["id"] if isinstance(v, dict) else v
)
def test_transition_schedule_matches_prototype(h, budget):
    want = h["transition"][budget]
    assets = [
        TransitionAsset(a["sym"], D(a["mv"]), D(a["u"]), a["short_term"])
        for a in h["transition_assets"]
    ]
    got = transition_schedule(assets, D(budget), D(GOLDEN["tax_rate"]))

    assert len(got.years) == want["years_count"]
    assert abs(got.total_tax - D(want["total_tax"])) <= CENT
    assert abs(got.tax_without_service - D(want["tax_without_service"])) <= CENT
    for g, w in zip(got.years, want["years"]):
        for field in ("sold", "gains", "losses", "net", "tax", "left"):
            assert abs(getattr(g, field) - D(w[field])) <= CENT, (g.year, field)


def test_budget_is_never_exceeded():
    for h, budget in TRANSITION_CASES:
        assets = [
            TransitionAsset(a["sym"], D(a["mv"]), D(a["u"]), a["short_term"])
            for a in h["transition_assets"]
        ]
        for year in transition_schedule(assets, D(budget)).years:
            assert year.net <= D(budget) + CENT


def test_total_tax_never_exceeds_selling_everything_now_when_no_losses_offset():
    for h, budget in TRANSITION_CASES:
        want = h["transition"][budget]
        assert D(want["total_tax"]) <= D(want["tax_without_service"]) + CENT
