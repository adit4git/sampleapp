# Design spec 001: Advisory move, step 2, action mode

Implements `docs/intent/001-advisory-move-step2.md`. Source material: the Atlas prototype and
"Ask Atlas in production: how a request flows". Items marked **(assumed)** need confirmation.

## 1. Requirements

| ID | Requirement |
| --- | --- |
| R1 | `load_screen(screen="advisory", household, step=2, budget?)` returns everything the panel renders, in one response. |
| R2 | No model call on this path. |
| R3 | Fee rate, annual cost, eligibility and transition schedule equal the golden file to one cent. |
| R4 | Budget defaults to 250,000 and accepts 50,000 to 5,000,000 **(assumed range)**. |
| R5 | Unentitled advisor: 403, no household fields in the body. |
| R6 | Response carries `as_of`, `trace_id`, and an `illustrative` flag per figure that uses placeholder inputs. |
| R7 | Progress "step 2 opened" is saved; failure to save does not fail the screen. |
| R8 | A tool timeout returns the rest of the screen plus a `missing` list. |

## 2. Components and where they run

| Component | Tech | Runs on | Owner |
| --- | --- | --- | --- |
| Ask Atlas UI | React SPA, static bundle | OpenShift | App team |
| Agent gateway | Existing **(assumed)** | Platform | Platform team |
| Ask Atlas agent + action catalog | Proprietary agentic runtime | Platform | App team writes config; platform team runs it |
| MCP gateway | Existing **(assumed)** | Platform | Platform team |
| Client data MCP server | Python, FastAPI | OpenShift | App team |
| Calc tools MCP server (fee, transition) | Python, FastAPI | OpenShift | App team |
| Entitlements service | Existing **(source TBD)** | Firm | TBD |
| Serving store | Postgres **(assumed)** | Firm | App team schema |
| Operational store | Postgres **(assumed)** | Firm | App team schema |

FastAPI hosts the MCP servers and tools. There is no separate backend-for-frontend: the SPA
calls only the agent endpoint.

## 3. Agent contract

```
POST /agents/{agentId}/invoke
Authorization: Bearer <advisor JWT, aud = agent gateway>
X-Client-Id: <client id, must match the token>
traceparent: <W3C>

{ "mode": "action",
  "action": "load_screen",
  "args": { "screen": "advisory", "household_id": "whitaker", "step": 2, "budget": 250000 } }
```

Response `200`:

```json
{
  "as_of": "2026-11-02",
  "trace_id": "…",
  "household": { "id": "whitaker", "aum": "7201000.00", "brokerage": "7201000.00" },
  "eligibility": { "status": "conditions", "conditions": [ { "text": "…", "owner": "Operations" } ] },
  "fee": { "rate": "0.00966644", "illustrative": true },
  "transition": {
    "eligible": true, "budget": "250000", "rate": "0.238", "illustrative": true,
    "gross_gain": "640000.00", "total_tax": "152320.00", "tax_without_service": "152320.00",
    "years": [ { "year": 1, "sold": "825816.79", "gains": "265000.00", "losses": "-15000.00",
                 "net": "250000.00", "tax": "59500.00", "left": "600183.21" } ]
  },
  "missing": []
}
```

Money is a decimal string. Errors: `401` (token), `403` (entitlement), `404` (unknown
household or action), `422` (bad args), `429` (rate limit).

## 4. Action catalog entry (registry)

```yaml
agentId: ask-atlas
actions:
  load_screen:
    deterministic: true        # no model call
    needs_confirmation: false
    tools: [client_data.get_screen_data, calc.fee_rate, calc.transition_schedule]
    writes: [operational.progress]
    timeout_ms: 1500
  generate_proposal:           # not in this slice; listed so the flag is reviewed early
    deterministic: true
    needs_confirmation: true
```

The exact registry format is the runtime's; this is the content it must hold.

## 5. MCP tools

| Tool | Input | Output | Notes |
| --- | --- | --- | --- |
| `client_data.get_screen_data` | `household_id`, `screen`, `step` | household summary, eligibility, transition assets (sym, mv, unrealized, short_term), `as_of` | Reads the serving store. Approved fields only. |
| `calc.fee_rate` | `household_value` | `rate` | `atlas_tools.fees.blended_advisory_rate` |
| `calc.transition_schedule` | `assets[]`, `budget`, `rate?` | schedule | `atlas_tools.transition.transition_schedule` |

Every tool call arrives with an exchanged token (aud = MCP gateway, sub = advisor, scoped to
this agent). The gateway checks the token, that the tool is allowed for the agent, and
entitlements, then logs the call.

## 6. Data

Serving store, one row per household per snapshot:

```sql
create table household_view (
  snapshot_date date        not null,
  household_id  text        not null,
  view          jsonb       not null,   -- figures, opportunities, eligibility, transition assets
  drafts        jsonb,                  -- nightly model drafts; null in this slice
  primary key (snapshot_date, household_id)
);
create table live_snapshot (only_row boolean primary key default true check (only_row),
                            snapshot_date date not null);
```

Reads join on `live_snapshot`, so the nightly switch is one update.

Operational store:

```sql
create table progress (
  advisor_id text not null, household_id text not null, opportunity text not null,
  step int not null, opened_at timestamptz not null default now(), trace_id text not null
);
```

## 7. Non-functional targets (assumptions to confirm)

| ID | Assumption | Value |
| --- | --- | --- |
| A1 | Advisors at full rollout | 500 |
| A2 | Households per advisor | 150 (75,000 total) |
| A3 | Peak action-mode load | 30 requests per second |
| A4 | Action-mode latency, p95 at the agent gateway | 800 ms |
| A5 | Availability of runtime and both gateways | 99.9% in business hours |
| A6 | Tool timeout | 1,000 ms per tool, 1,500 ms per action |

Budget for the 800 ms: gateway 50, runtime and registry 100, MCP gateway and entitlements 150,
serving-store read 100, calculations 50, progress write (async) 0, network and margin 350.

## 8. Test plan

- **Unit and parity:** `tests/test_golden_parity.py` (already passing for fee rate and schedule).
- **Contract:** schema tests for the three tools and the agent response.
- **Entitlements:** own book, team, coverage, and none; the last must return 403.
- **Degraded:** model endpoint blocked; one tool timing out; operational store down.
- **Load:** 30 rps for 15 minutes on the test cluster; record p50, p95, p99.
- **End to end:** Playwright loads step 2 for the 12 eligible households and compares the
  rendered figures to the golden file.

## 9. Open questions that block this slice

1. Does the runtime support a named deterministic action with no model call? If not, the
   fallback is a thin FastAPI service behind the same gateways for action mode, with the
   runtime used for chat and batch only. That breaks "everything through one agent", so it
   needs an architecture decision.
2. Does the identity provider support token exchange for the runtime to MCP gateway hop?
3. Which service is the entitlements source for teams and coverage?
4. Can the app team run a local stub of the runtime for development and CI?
