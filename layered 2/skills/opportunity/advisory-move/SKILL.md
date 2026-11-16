---
name: advisory
description: Procedure for discussing a move of brokerage assets into the Advisory program - the order to establish things in, how to explain each eligibility outcome, and how to frame cost against benefit. Use on the "Brokerage to Advisory program" opportunity.
---
# Brokerage to Advisory program

Follows the parent `opportunity` skill. What is specific here is the order of work and how
to explain the outcomes.

## Order

1. Why this household: `opportunity_facts`.
2. Whether the program is open to them: `eligibility`. Always before strategies or fees.
3. Where the assets would go: `strategy_fit`. Follow the `strategy-comparison` skill.
4. What it costs and how fast: `fee_estimate`, then `transition_schedule` if the advisor
   wants to spread the tax.

If you skip step two the later tools will refuse. That is by design.

## Explaining eligibility

- **Eligible in principle.** Say so in one line and move on to strategy.
- **Eligible with conditions.** This is still a yes. For each condition give the owner and
  what they need to do, so the advisor can start it today. Conditions do not block the
  conversation with the client; they block specific holdings.
- **Specialist review.** This is not a no to the client, it is a different first step. Say
  what triggers the review, that the specialist looks at the concentrated position first,
  and that the rest of the brokerage assets can be discussed after. Do not present
  strategies, fees or a schedule, and do not speculate about the outcome of the review.

## Framing

Recommending the program is itself a recommendation. Give both sides: what ongoing advice
would do for this household, based on the reasons it was flagged, and what the client pays
for it compared with today. If commissions are the only reason, say that plainly.

## Questions worth asking

How much tax the client will accept this year. Who should make day-to-day decisions. What
should lead the strategy choice. Whether cash is needed in the coming year.
