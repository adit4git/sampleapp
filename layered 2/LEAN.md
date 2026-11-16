# The lean flow: same four layers, less work per request

Three changes applied on top of the layered proof of concept. The layered flow is still
here, untouched, so the two can be measured on the same screens (`python compare.py`).

## Measured, on six screens

| Screen | Model calls | Decisions while the advisor waits | Checks on the answer | Same output |
| --- | --- | --- | --- | --- |
| Advisory, solutions, eligible with conditions | 6 → 1 | 8 → 0 | 8 → 5 | yes |
| Advisory, solutions, specialist review | 5 → 1 | 5 → 0 | 8 → 5 | yes |
| Advisory, proposal, insider | 6 → 1 | 8 → 0 | 8 → 5 | yes |
| Concentration, solutions, insider | 3 → 1 | 2 → 0 | 8 → 5 | yes |
| Tax-loss harvesting, solutions | 3 → 1 | 2 → 0 | 8 → 5 | yes |
| Large gains, solutions | 3 → 1 | 2 → 0 | 8 → 5 | yes |
| **Average** | **4.3 → 1.0** | **4.5 → 0** | **8 → 5** | |

"Same output" means identical disclosures, citations, figures and actions.

Read the model-call numbers as a direction, not a forecast: the "before" stand-in calls
every tool it is offered, and a real model might call fewer. A what-if question still costs
one extra call in the lean flow.

## 1. The app writes what must be right (`atlas/lean/render.py`)

The model returns narrative with references, plus action ids:

```
{{opportunity.label}} for CLIENT_1: {{opportunity.reason}}. Amount involved: {{opportunity.amount}}.
```

The app substitutes each reference with the tool's value, appends every disclosure the
tools required in the pack's wording, appends the draft label on the proposal step, attaches
citations, and turns action ids into confirm-first buttons from the allowed list.

| Earlier check | Now |
| --- | --- |
| H-DISCLOSE, H-CITE, H-DRAFT, H-CONFIRM | **Gone.** The model does not write these, so it cannot omit or misstate them. A model that writes one sentence still produces a complete answer. |
| H-FIG (match every figure against tool results) | **Replaced** by two simpler checks: H-REF (a reference must name a real field) and H-RAWFIG (the model may not type a figure at all, even a correct one). |
| H-WORDING, H-PII, H-TOKEN | Unchanged, applied to the narrative. |

The rule-based fallback is a template written the same way and passed through the same
renderer, so there is one path to the screen.

## 2. Fetch before the model (`atlas/lean/bundle.py`)

`harness.yaml` says what each screen needs (`lean.prefetch`). The harness gathers it and
hands the model a flat list of fields with ids. A tool refusal is prefetched as a field too,
because a refusal is an answer. The model can still call the what-if tools listed for the
screen (`lean.what_if_tools`); the result is added as more fields.

## 3. Decide once a night (`atlas/records.py`)

`records.build` computes the 13 criteria, eligibility and the strategy ranking per
household and stamps the result with the policy pack version. Tools read the record when a
store is supplied and decide live when it is not, through the same code, and an eval checks
both give identical answers for all 37 households.

- For this book the nightly build is 37 criteria evaluations, 14 eligibility checks and 12
  strategy rankings, once.
- A record built under one pack is never served under another: the store raises, and the
  nightly job rebuilds.
- Advisor inputs are computed live: `opportunity_what_if` (for example the maturity window),
  `transition_schedule`, `fee_estimate` for a different strategy.

## What this does not solve

- **A real field in the wrong place is not caught.** References guarantee a value came from
  a tool. They do not guarantee it is the right value for the sentence: "Tax due now would
  be {{opportunity.amount}}" passes every check. `tests/test_lean.py` pins this as a known
  gap. It needs an eval against a real model, or field types checked against the words
  around them.
- **The model must follow the reference format.** A real model will sometimes type a figure;
  that costs a repair call, and a second failure falls back to the template. How often is
  unknown until measured on your model.
- **Answers are more uniform.** Disclosures always come at the end, in the pack's wording.
- **Prefetch helps expected questions only.** An unexpected question still needs tool calls.
- **Records are as fresh as the last build.** Intraday changes are not reflected, as before.
- **Not applied here:** templates as the default with model drafting on open, dropping
  parent and child skills, and dropping the vector store (points 4 to 6 of the proposal).

## Run it

```bash
python compare.py                 # the table above
python -m atlas.evals             # 64 checks, including 19 for the lean flow
pytest -q                         # 40 tests
```
