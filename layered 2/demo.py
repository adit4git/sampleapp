"""Walk through the four layers. Run:  python demo.py"""
from __future__ import annotations

import textwrap

from atlas.evals import ROOT, load_data, load_env
from atlas.fmt import money, pct
from atlas.harness.agent import run_turn
from atlas.harness.models import StubModel
from atlas.impact import report
from atlas.tools import eligibility as elig
from atlas.tools import opportunities as opp
from atlas.tools import strategies as strat
from atlas.tools.toolbox import Toolbox

env, data = load_env(), load_data()
P, HH = env.policy, data["by_id"]


def h1(t):
    print(f"\n{'=' * 84}\n{t}\n{'=' * 84}")


def wrap(t):
    return textwrap.fill(t, 100, initial_indent="   ", subsequent_indent="   ")


h1("LAYER 1  Policy pack: the values, versioned")
print(f"   {P.stamp}   effective {P['effective']}   status: {P['status']}")
print(f"   concentration threshold {pct(P['opportunities.concentration.threshold'], 0)}"
      f" | specialist review above {pct(P['eligibility.specialist_review_above'], 0)}"
      f" | strategy weights {P['strategies.weights']}")
print(f"   {len(P['strategies.catalog'])} strategies in the catalog, "
      f"{sum(1 for s in P['strategies.catalog'] if s.get('requires'))} with availability requirements; "
      f"{len(P['disclosures'])} disclosures")

h1("LAYER 2  Tools: the logic, as code, reading the pack")
dana = [h for h in data["households"] if h["advisor"] == "dana"]
print("   Book view for Dana (13 criteria):")
for k, t in opp.book_summary(dana, P).items():
    if t["n"]:
        print(f"      heat {t['heat']}  {t['label']:<32} {t['n']:>2} clients  {money(t['amount']):>8}")
print("\n   Whitaker, opportunities in display order:")
for o in opp.ranked(opp.evaluate(HH["whitaker"]["facts"], P)):
    print(f"      step {o['step']}  {o['label']:<32} {o['reason'][:70]}")
print("\n   Eligibility, three outcomes:")
for hid in ("henderson", "whitaker", "kaplan", "ashby"):
    e = elig.check(HH[hid]["facts"], P)
    print(f"      {hid:<10} {e['label']:<40} " + "; ".join(f"{c['kind']} -> {c['owner']}" for c in e["conditions"]))
print("\n   Strategy ranking for Whitaker (overlap, fit, tax now -> score):")
r = strat.rank(HH["whitaker"]["facts"], HH["whitaker"]["strategy"]["inputs"], P)
for x in r["ranked"][:6]:
    mark = "*" if x["id"] in r["suggested"] else " "
    note = x["unavailable_reason"] or ("same as the default" if x["same_as_default"] else "")
    print(f"    {mark} {x['score']:.3f}  {x['name']:<44} overlap {pct(x['overlap'], 0):>4}  tax {money(x['tax_now']):>6}  {note}")
print(f"      suggested (* above): {r['suggested']}")

h1("Tools enforce their own prerequisites")
tb = Toolbox(P, HH)
for label, res in [
    ("strategy_fit under specialist review (Ashby)", tb.strategy_fit("ashby")),
    ("fee_estimate for a strategy the household cannot have", tb.fee_estimate("novak", "alts")),
    ("transition_schedule with direct indexing", tb.transition_schedule("henderson", "di")),
    ("transition_schedule with a budget off the list", tb.transition_schedule("whitaker", "cio", 300000)),
    ("generate_proposal without the advisor's confirmation", tb.generate_proposal("whitaker", "advisory", "cio")),
]:
    print(f"   {label}\n      -> {res.get('refused', 'ok')}: {res.get('reason', '')[:110]}")

h1("A policy change is a pack change: impact report, no code")
for changes in ({"opportunities.concentration.threshold": 0.15},
                {"eligibility.specialist_review_above": 0.25},
                {"strategies.weights": {"overlap": 0.20, "fit": 0.65, "tax_now": 0.15}}):
    rep = report(P, P.with_changes(changes), data["households"])
    print(f"   {changes}")
    for k, c in rep["criteria"].items():
        print(f"      {opp.LABELS[k]}: {c['before']} -> {c['after']}  leave {c['leave']}")
    for e in rep["eligibility"]:
        print(f"      eligibility {e['household']}: {e['before']} -> {e['after']}")
    for s in rep["suggestions"]:
        print(f"      suggestions {s['household']}: {s['before']} -> {s['after']}")

h1("LAYER 3  Skills: procedure and judgment only")
def show(s, depth=0):
    print(f"   {'    ' * depth}{s.id:<{24 - 4 * depth}} {len(s.body.split()):>4} words   {s.description[:60]}...")
    for c in s.children:
        show(c, depth + 1)


for root in (s for s in env.skills.values() if s.parent is None):
    show(root)

h1("LAYER 4  Harness: one turn (Advisory move, step 2, Whitaker)")
ctx = {"advisor": "dana", "household": "whitaker", "opportunity": "advisory", "step": 2}
t = run_turn(env, ctx, "Where should the assets go?", StubModel("good"))
print(f"   skills        : {' > '.join(t.skills)}")
print(f"   tools called  : {', '.join(t.tools_called)}")
print(f"   disclosures   : {', '.join(t.disclosures)}   <- decided by tools, worded by the pack")
print(f"   outcome       : {t.outcome} ({t.kind})   policy {t.policy}")
print(f"   citations     : {t.citations}")
print("   model wrote   :")
print(wrap(t.answer[:330] + " ..."))
print("   advisor sees  :")
print(wrap(t.display[:120] + " ..."))

print("\n   Same harness, specialist review (Ashby): the TOOL refuses, the skill explains")
t2 = run_turn(env, dict(ctx, household="ashby"), "Where should the assets go?", StubModel("good"))
print(f"   tool refusals : {t2.tool_refusals}")
print(wrap(t2.display))

print("\n   Models that misbehave:")
for kind, what in [("invents_figure", "adds a number no tool supplied"), ("omit_disclosure", "drops a required disclosure"),
                   ("promise", "promises an outcome"), ("leaks_pii", "writes a tax ID"),
                   ("wrong_tool", "calls generate_proposal itself"), ("cross_client", "asks about another client")]:
    t = run_turn(env, ctx, "?", StubModel(kind))
    caught = [v["rule"] for v in (t.violations[0] if t.violations else [])] + [b["rule"] for b in t.blocked]
    print(f"      {what:<36} caught by {', '.join(caught):<11} -> {t.outcome} ({t.kind})")

print(f"\nNext: python -m atlas.evals   |   python -m atlas.impact opportunities.cash.min_excess=500000   |   pytest -q")
print(f"Files: {ROOT}")
