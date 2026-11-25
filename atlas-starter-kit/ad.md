# Atlas in production: team plan (AI-DLC)

## Core pod: roles, headcount and skills

| Role | Group | Headcount (scale phase, FTE) | Headcount (run phase, FTE) | What they own | Skills that matter |
|---|---|---|---|---|---|
| Product owner | Core pod | 1 | 1 | Intent, which units to build, acceptance, adoption measures | Advisory workflow knowledge; crisp intents and acceptance criteria; saying no |
| Domain lead: advisory and programs | Core pod | 1 | 1 | Turns advisor judgment into skills and golden eval cases; signs off answers | Practicing advisor or investment specialist; writes procedures plainly |
| Domain lead: tax and transition | Core pod | 0.5 | 0.5 | Skills and golden cases for tax-efficient transition and year-end tax | Tax lots, gain budgets, wash-sale rules; writes procedures plainly |
| Agent architect / tech lead | Core pod | 1 | 1 | Single loop, three modes (action, chat, batch), tool contracts, policy snapshot, write gates | Agent design, API design, security basics, cost and latency trade-offs; reviews AI-generated designs |
| AI engineer | Core pod | 2 | 1 | Skills, system prompt, tool descriptions, skill loading and tool search, cost tuning, hill-climbing on evals | Context engineering, model APIs, Python; knows when a fix belongs in a skill, a tool or policy |
| Backend engineer | Core pod | 2 | 1 | MCP tools over gold views; fee, transition and proposal services; rule engine; operational store; nightly batch | Python/FastAPI, domain math (tax lots, fees, rebalancing), idempotent jobs, tests |
| Data engineer | Core pod | 1 | 0.5 | Gold-view contracts, snapshot ID and atomic switch, CIO library ingestion and hybrid search, entitlements feed | Lakehouse modeling, data-quality checks, vector and keyword search |
| Front-end engineer | Core pod | 1 | 0.5 | React SPA, streamed plan, tool and citation events, confirm cards, Under the hood, accessibility | React, streaming UIs, design systems |
| Eval and quality engineer | Core pod | 1 | 0.5 | End-to-end and per-skill eval sets, release gates, flipped-case review, red-teaming, PII leak sweep | Test design, statistics on noisy results, adversarial thinking; independent of the builders |
| UX designer | Core pod | 0.5 | 0 | Advisor flows; explaining drafted vs calculated vs published parts; error and handoff states | Research with advisors, explainable-UI patterns |
| SRE / platform engineer | Core pod | 0.75 | 0.5 | Container deploys, traces, cost and turn budgets, per-mode rollout switch, on-call | Observability, CI/CD, incident response |
| Total |  | 11.75 | 7.5 |  |  |

*Blue numbers are estimates you can edit; totals recalculate. Headcounts are planning assumptions, not benchmarks.*

## Named partners outside the pod

| Partner | Involvement | Responsibility |
|---|---|---|
| Security and privacy engineer | Part-time, every checkpoint | PII guard and tokenization, token exchange, prompt-injection threat model; signs off what the model can see |
| Model risk and validation (independent) | Part-time, before each release | Validates evals, limits and monitoring; usually decides whether you can go live |
| Compliance and supervision | Part-time, every checkpoint | Disclosures, retention of traces and proposals, supervisory review of advisor-facing output, policy-pack change process |
| Business owners of policy packs | As needed | Thresholds, fee tiers, tax assumptions: versioned data, not engineering work |
| Source-system data owners | As needed | CRM, positions, research ratings, proposal system: gold-view contracts and write-back |

## Who owns what in the restructured design

| Component | Accountable | Responsible | Consulted | Informed |
|---|---|---|---|---|
| System prompt | Agent architect | AI engineers | Domain leads, Compliance | Product owner |
| Harness (auth, context, PII, budgets, traces, action mode) | Agent architect | Backend engineers, Security | Model risk | Product owner |
| Skills (one owner per skill) | Domain leads | AI engineers | Eval engineer | Product owner |
| Policy packs | Business policy owners | Data engineer | Compliance, Model risk | Domain leads |
| MCP tools and services | Agent architect | Backend engineers | Domain leads | Eval engineer |
| Gold views and snapshot switch | Data engineer | Data engineer | Source-system owners | Backend engineers |
| Eval sets and release gates | Eval engineer | Eval engineer, Domain leads | Model risk | Whole pod |
| React SPA and Under the hood | Product owner | Front-end engineer, UX | Security | Domain leads |
| Production operations and on-call | SRE / platform | SRE, Backend engineers | Agent architect | Product owner |
| Go-live decision | Product owner | Agent architect | Model risk, Compliance, Security | Business stakeholders |

## AI-DLC ways of working

| Stage | Cadence | Who | What happens | Output |
|---|---|---|---|---|
| Inception: mob elaboration | Per unit of work | PO, domain lead, architect, eval engineer, compliance, with the AI | AI drafts user stories, tool contracts, skill outline and eval cases; the room corrects them | Unit spec plus its eval set, before any code |
| Construction: bolts | Hours to days (not two-week sprints) | Builders plus reviewers | AI generates design, code and tests; architect reviews design, domain lead reviews answers, eval engineer reviews scores | Merged change that passed the eval gate |
| Operations | Continuous | SRE, eval engineer, PO | Monitor traces, cost, flipped cases and advisor feedback; per-mode switch can turn off chat without losing action mode | Findings that feed the next mob elaboration |

## Suggested ramp

| Phase | Duration | Team | Work | Exit criteria |
|---|---|---|---|---|
| 1. Foundation | About 6-8 weeks | Architect, 2 AI engineers, 1 backend engineer, eval engineer, 1 domain lead | Evals first; split policy out of skills; regroup tools; single loop for advisory-conversion run next to the current path | Eval baseline; side-by-side comparison of flipped cases |
| 2. Scale | Next about 3 months | Full pod plus partners | Fold one skill area at a time; nightly batch, gold views and operational store; security and model-risk sign-offs | Production release by mode (action, then chat, then batch) |
| 3. Run | Ongoing | Pod of about 6; domain teams add skills | Domain teams add skills through the review path; policy changes run evals, not code releases | Steady releases gated by evals |

## Gaps that sink these projects

| Risk | Effect | Mitigation |
|---|---|---|
| Domain leads given about 10% of their time | Skills and golden cases never get written | Protect their time; name one owner per skill |
| Builders grade their own work | Scores look good, production does not | Separate eval owner; show evals to model risk early |
| AI treated as a separate team | Decisions made without the people who own them | Decision-makers sit in every mob elaboration |
| Nobody owns the agent in production | Incidents and cost overruns go unnoticed | Named on-call; cost and turn budget per mode |
| A step is skipped once the model sets the order | Proposal produced without a required check | Preconditions inside tools; completion checks in proposal generation |
