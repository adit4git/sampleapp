# Ask Atlas: delivery plan, estimates and assumptions

Draft for review. Every number here is an estimate built on the assumptions in section 4.
The largest swings are the runtime's answers (section 5) and how quickly real data access
and entitlements are granted.

## 1. Headline

- **About 24 weeks from kickoff to a pilot** with roughly 20 advisors; plausible range 20 to 30.
- **Team of about 8 full-time equivalents**, plus named partners in platform, security and compliance.
- **First demo on production layers in week 8**: Advisory move step 2, action mode, no model.

## 2. Phases

| # | Phase | Weeks | Exit |
| --- | --- | --- | --- |
| 0 | Foundations | 1-3 | Runtime questions answered; repo, CI gates, OpenShift namespaces, synthetic book loaded; intents 001-003 approved |
| 1 | Slice 1: Advisory step 2, action mode | 3-8 | Intent 001 "done means" met; latency measured on the test cluster |
| 2 | Remaining screens in action mode + nightly, deterministic part | 6-12 | Book view, client list, deep dive, steps 1-3 read paths; nightly builds household views from the warehouse and switches snapshots in one step |
| 3 | Chat mode | 10-17 | PII guard, model endpoint, research MCP over the CIO library; leak and detector evals at band; citations on every rule answer |
| 4 | Nightly drafts and proposal generation | 15-20 | Summaries and openers drafted through the guard; proposal action with advisor confirmation; draft stored, never sent |
| 5 | Hardening and pilot | 19-24 | Independent security test; failure drills (model down, runtime down, tool timeout); supervision review of traces; pilot go/no-go |

Phases overlap because the SPA, the tools and the batch can be built in parallel sessions
against agreed contracts.

## 3. Team

| Role | FTE | Main responsibility |
| --- | --- | --- |
| Tech lead | 1 | Contracts, calc review, architecture decisions |
| Backend engineers (Python, FastAPI, MCP) | 2 | Tools, MCP servers, stores |
| Frontend engineers (React) | 2 | SPA: port screens from the prototype |
| Platform / DevOps | 1 | OpenShift, CI/CD, observability, runtime integration |
| Eval and quality engineer | 1 | Golden vectors, evals in CI, load and failure tests |
| Data engineer | 0.5 | Warehouse queries, serving store, nightly batch |
| Product lead | 0.5 | Intents, acceptance, advisor feedback |
| Partners (not on the team): runtime platform, identity, security, compliance, CIO office | as needed | Answers, reviews and approvals |

## 4. Assumptions

| ID | Assumption | If wrong |
| --- | --- | --- |
| A1 | 500 advisors at full rollout, 150 households each (75,000 households) | Sizing and the nightly window change proportionally |
| A2 | Peak action-mode load about 30 requests per second | Resize runtime and gateways |
| A3 | Action-mode p95 target 800 ms; chat first token 3 s | Targets are renegotiated, or a cache is added in front of the serving store |
| A4 | The runtime supports named deterministic actions with no model call | Add 3-5 weeks and an architecture decision (section 5, Q1) |
| A5 | Agent gateway, MCP gateway, identity provider and an approved model endpoint already exist | Each missing piece is its own project; pilot date moves |
| A6 | Serving and operational stores are Postgres | Schema work is redone for the chosen store |
| A7 | The warehouse already holds positions, lots, cost basis, accounts and fee schedules, loaded nightly | Add data-sourcing work before phase 2 |
| A8 | Nightly window of 4 hours after the load lands | See the sizing note below |
| A9 | Firm fee schedule, tax assumptions and program rules are supplied by week 6 | Figures stay flagged illustrative; no pilot with clients present |
| A10 | Claude Code is approved for this repo with synthetic data only | Build speed drops; estimates roughly double for phases 1-2 |
| A11 | The prototype's rules are an acceptable baseline until compliance reviews them | Rework in phase 5 |
| A12 | CI is GitHub Actions or equivalent that can run the four gates | Translate the workflow |

**Nightly sizing note.** At 75,000 households with about five model drafts each (one summary,
four openers), a full redraft is about 375,000 model calls, or 26 a second across a 4-hour
window. That is likely the tightest constraint in the design. Plan to redraft only households
whose facts changed since the previous snapshot, and measure the changed share in phase 2
before committing to a window.

## 5. Questions for the platform teams, with fallbacks

| # | Question | Needed by | Fallback |
| --- | --- | --- | --- |
| Q1 | Named deterministic actions with no model call, at page-load latency? | Week 2 | Action mode on a FastAPI service behind the same gateways; runtime for chat and batch only |
| Q2 | Token exchange for the runtime to MCP gateway hop? | Week 3 | Gateway-issued signed assertion carrying the advisor subject, reviewed by security |
| Q3 | Entitlements source for teams, client associates and coverage? | Week 4 | Pilot limited to advisors' own books |
| Q4 | How long may the nightly batch run, including model drafts? | Week 8 | Changed-households-only redraft; drafts on first open for the rest |
| Q5 | Do both gateways pass server-sent events without buffering? | Week 10 | Non-streamed chat answers for the pilot |
| Q6 | Can the app team run a local stub of the runtime? | Week 2 | Contract tests against a shared dev runtime; slower loop |

## 6. Top risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Runtime cannot do action mode | Medium | High | Ask in week 1; slice 1 proves it by week 8 |
| A figure differs between screen and chat | Low | High | One tool per calculation; `answer-figures-from-tools` band |
| PII reaches the model | Low | Very high | Guard in the runtime; leak test on every household in CI and nightly |
| Name detection misses nicknames and non-book people | High | Medium | Trained recognizer on top of patterns; labeled set grows from supervision review |
| Nightly window too short | Medium | Medium | Changed-only redraft; measure early |
| Rules in the prototype differ from approved documents | Medium | High | Compliance review of the program-rules skill in phase 0 |
| Runtime outage takes down every screen | Low | High | Same availability target as a core API; failure drill in phase 5 |

## 7. How the work is run

Each slice follows the same loop: an `intent.md`, a design spec written in one working
session, plan mode, tests and evals before the implementation, agentic review on every PR,
and human review on calculators, the PII guard, entitlements and the action catalog. Hooks
block edits to the golden file, the control bands and the labeled eval set. A breached band
in `governance/control-bands.yaml` becomes the next intent.

## 8. Next three intents to write

- **002** Conversion routes tool: which holdings are transition assets (ports `advMatrix`).
- **003** Book view and client deep dive in action mode from the serving store.
- **004** PII guard: tokenization, free-text detection, answer scan, name restoration.
