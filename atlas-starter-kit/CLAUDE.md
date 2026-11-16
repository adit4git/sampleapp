# Ask Atlas

Advisor console with one agent behind it. React SPA, Python 3.11 + FastAPI tools exposed as
MCP servers, deployed to OpenShift. The agent runs on the firm's agentic runtime, which this
repo does not contain. Read `docs/design/` before changing a contract.

# Commands
- Install: `pip install -e ".[dev]"`
- Test one file: `pytest tests/test_golden_parity.py -q` (prefer single files)
- All tests and evals: `pytest -q`
- Lint and format: `ruff check . && ruff format .`
- UI (in `apps/web`): `pnpm test`, `pnpm typecheck`

# Rules that must hold (IMPORTANT)
- Figures never come from a model. Fees, tax, schedules, drift and eligibility are computed
  in `services/tools/atlas_tools/` and nowhere else. The UI and chat call the same tools.
- Nothing in `atlas_tools/` imports a model client or does network I/O.
- Money and quantities are `Decimal`, built from strings. No `float` in `atlas_tools/`.
- Never edit `tests/golden/`. It is the prototype's output. If a test fails, fix the code.
- Fee tiers and the 23.8% tax rate are illustrative. Keep the `illustrative` flag until the
  firm's values replace them.
- Every data read goes through the MCP gateway and the entitlements check. No direct store
  access from the agent or the UI.
- Only synthetic data. Never add real names, account numbers, tax IDs or addresses to code,
  fixtures, prompts or logs. Fixture identifiers use 555 phones, example.com, tax IDs
  starting with 9.
- Logs and traces hold tokenized values only (`CLIENT_7`, not a name).
- Actions that write to a client-facing artifact have `needs_confirmation: true`.

# Workflow
- Start from an `intent.md` in `docs/intent/`. No intent, no feature.
- Use plan mode for anything touching more than one file.
- A change to a calculation needs: a failing test first, the term-sheet or rule reference in
  the PR description, and the calc-reviewer subagent run on the diff.
- Program rules live in the `program-rules` skill. Adding an action: use `/add-action`.
- When compacting, keep the list of modified files and the test commands.
