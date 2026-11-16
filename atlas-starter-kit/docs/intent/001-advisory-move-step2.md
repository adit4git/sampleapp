# Intent 001: Advisory move, step 2, in action mode

**Status:** draft for review · **Owner:** product lead (TBD) · **Slice:** first production slice

## What we want

An advisor opens a household's "Move brokerage assets to the Advisory program" opportunity at
step 2 and sees, for the default strategy and a yearly gain budget:

- the blended advisory fee rate and the annual cost before and after;
- the tax-efficient transition schedule: years, sold per year, net gain per year, tax per year;
- the eligibility status and any conditions, each with its owner;
- the "as of" date of the data.

Changing the budget recalculates the schedule. Nothing is written to any client system.

## Why

- This is the screen where the prototype's value is clearest: it turns a multi-day manual
  analysis into something the advisor can explore in a client meeting.
- It exercises every production layer except the model: sign-in, agent gateway, runtime,
  registry, MCP gateway, entitlements, tools, serving store, operational store. If this slice
  works, chat is an addition, not a rebuild.
- It answers the biggest open platform question early: can the runtime run a named
  deterministic action without a model call, fast enough for a page load?

## Constraints

1. **No model call.** Every figure comes from a deterministic tool. The slice must work with
   the model endpoint switched off.
2. **Same tools for screen and chat.** The fee and transition tools built here are the ones
   chat will call later. No second implementation, ever.
3. **Parity with the prototype.** Python results match `tests/golden/` to within one cent.
4. **Entitlements on every read.** The MCP gateway asks the entitlements service before any
   household data is returned. No client-side filtering.
5. **Synthetic data only** in development, test and demo environments.
6. **Read-only.** The only write is progress ("step 2 opened") to the operational store.
7. **Illustrative inputs are labeled.** The fee tiers and the 23.8% tax rate are placeholders
   until the firm's schedule and tax assumptions are supplied and approved.
8. **Every screen shows the snapshot's "as of" date.**

## Out of scope

- Chat mode, the PII guard and the model endpoint.
- Proposal generation (step 3) and any other write.
- The nightly batch. For this slice the serving store is loaded from the synthetic book.
- The conversion-routes tool (which holdings are transition assets). The slice reads the
  transition assets from the household view; the routing tool is Intent 002.
- Opportunities other than the Advisory move.

## Done means

- An advisor entitled to the household loads step 2 for all 12 transition-eligible synthetic
  households and sees figures equal to the golden file.
- An advisor not entitled gets a 403 and no data.
- With the model endpoint unreachable, the screen still loads.
- Action-mode latency at the agent gateway: p95 at or under 800 ms (assumption A4) on the
  OpenShift test cluster at 30 requests per second.
- One trace ID is visible across SPA, gateways, runtime, tools and stores.

## Control bands (breach writes a new intent)

| Measure | Band |
| --- | --- |
| Golden parity failures in CI | 0 |
| Action-mode p95 latency | at or under 800 ms |
| Entitlement bypass in tests | 0 |
| Unlabeled illustrative figures on screen | 0 |
