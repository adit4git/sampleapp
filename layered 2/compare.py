"""Before and after: the layered turn against the lean turn, on the same screens.

Run:  python compare.py

Counts, per turn:
  model calls         round trips to the model (each tool call the model makes is one)
  decisions           times a criterion set, eligibility or strategy ranking was computed
                      while the advisor waited
  answer checks       rules evaluated on what the model wrote
and confirms both produce the same disclosures, citations and figures.
"""
from __future__ import annotations

import re

from atlas import records
from atlas.evals import load_data, load_env
from atlas.harness import agent as layered
from atlas.harness.models import StubModel
from atlas.lean import agent as lean
from atlas.lean.models import LeanStub
from atlas.tools import eligibility as elig
from atlas.tools import opportunities as opp
from atlas.tools import strategies as strat

FIGURE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[KMB]?|\d+(?:\.\d+)?%")

SCREENS = [
    ("Advisory, solutions, eligible with conditions", "whitaker", "advisory", 2),
    ("Advisory, solutions, specialist review", "ashby", "advisory", 2),
    ("Advisory, proposal, insider", "kaplan", "advisory", 3),
    ("Concentration, solutions, insider", "kaplan", "concentration", 2),
    ("Tax-loss harvesting, solutions", "adeyemi", "harvest", 2),
    ("Large gains, solutions (no skill of its own)", "henderson", "gains", 2),
]


class Counter:
    """Counts calls to the three decision functions, wherever they are called from."""

    def __init__(self):
        self.n = {"criteria": 0, "eligibility": 0, "ranking": 0}
        self._orig = (opp.evaluate, elig.check, strat.rank)

    def __enter__(self):
        def wrap(fn, key):
            def inner(*a, **k):
                self.n[key] += 1
                return fn(*a, **k)
            return inner
        opp.evaluate, elig.check, strat.rank = (wrap(self._orig[0], "criteria"),
                                                wrap(self._orig[1], "eligibility"),
                                                wrap(self._orig[2], "ranking"))
        return self

    def __exit__(self, *exc):
        opp.evaluate, elig.check, strat.rank = self._orig

    @property
    def total(self):
        return sum(self.n.values())


class CountingModel:
    def __init__(self, inner):
        self.inner, self.calls = inner, 0

    def next(self, state):
        self.calls += 1
        return self.inner.next(state)


def measure() -> dict:
    env, data = load_env(), load_data()
    with Counter() as nightly:
        store = records.build(env.households, env.policy, data["as_of"])
    rows = []
    for label, hid, opportunity, step in SCREENS:
        ctx = {"advisor": env.households[hid]["advisor"], "household": hid, "opportunity": opportunity, "step": step}
        with Counter() as c1:
            m1 = CountingModel(StubModel("good"))
            a = layered.run_turn(env, ctx, "What do you suggest?", m1)
        with Counter() as c2:
            b = lean.run_turn(env, store, ctx, "What do you suggest?", LeanStub("good"))
        rows.append({
            "screen": label,
            "layered": {"model_calls": m1.calls, "decisions": c1.total, "checks": len(env.config["answer_rules"]),
                        "outcome": a.outcome},
            "lean": {"model_calls": b.model_calls, "decisions": c2.total, "checks": len(b.checks_run),
                     "outcome": b.outcome},
            "same_disclosures": a.disclosures == b.disclosures,
            "same_citations": set(a.citations) == set(b.citations),
            "same_figures": set(FIGURE.findall(a.answer)) == set(FIGURE.findall(b.answer)),
            "same_actions": a.actions == b.actions,
        })
    return {"rows": rows, "nightly": dict(nightly.n), "households": len(env.households),
            "by_construction": list(env.config["lean"]["by_construction"]),
            "narrative_rules": list(env.config["lean"]["narrative_rules"])}


def main() -> None:
    r = measure()
    print(f"{'Screen':<46} {'model calls':>13} {'decisions':>12} {'answer checks':>15}   same output")
    print(f"{'':<46} {'before after':>13} {'before after':>12} {'before after':>15}")
    tot = {"l": [0, 0, 0], "n": [0, 0, 0]}
    for x in r["rows"]:
        a, b = x["layered"], x["lean"]
        same = all(x[k] for k in ("same_disclosures", "same_citations", "same_figures", "same_actions"))
        print(f"{x['screen']:<46} {a['model_calls']:>6} {b['model_calls']:>6} {a['decisions']:>6} {b['decisions']:>5} "
              f"{a['checks']:>8} {b['checks']:>6}   {'yes' if same else 'NO'}")
        for i, k in enumerate(("model_calls", "decisions", "checks")):
            tot["l"][i] += a[k]
            tot["n"][i] += b[k]
    n = len(r["rows"])
    print(f"{'Average per turn':<46} {tot['l'][0] / n:>6.1f} {tot['n'][0] / n:>6.1f} {tot['l'][1] / n:>6.1f} {tot['n'][1] / n:>5.1f} "
          f"{tot['l'][2] / n:>8.1f} {tot['n'][2] / n:>6.1f}")
    print(f"\nNightly build, once, for {r['households']} households: {r['nightly']}")
    print(f"Checks no longer needed (the app writes these): {', '.join(r['by_construction'])}")
    print(f"Checks left on the model's narrative:          {', '.join(r['narrative_rules'])}")


if __name__ == "__main__":
    main()
