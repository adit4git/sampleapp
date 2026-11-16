# Ask Atlas starter kit

Repo-ready starting files for taking Ask Atlas from prototype to a first production slice,
organized by the stages of the AI-native SDLC playbook.

| Stage | File | What it is |
| --- | --- | --- |
| Plan | `docs/intent/001-advisory-move-step2.md` | Intent for the first slice |
| Plan | `docs/delivery-plan.md` | Phases, team, estimates, assumptions, platform questions, risks |
| Design | `docs/design/001-advisory-move-step2-spec.md` | Requirements, contracts, schema, targets, test plan |
| Build | `CLAUDE.md` | Project rules for Claude Code |
| Build | `.claude/skills/program-rules/SKILL.md` | Program rules extracted from the prototype |
| Build | `.claude/skills/add-action/SKILL.md` | Workflow for adding an agent action |
| Build | `.claude/agents/calc-reviewer.md` | Review subagent for calculation changes |
| Build | `services/tools/atlas_tools/` | Fee rate and transition schedule, ported to Python |
| Test | `tests/golden/advisory_fee_transition.json` | Expected values produced by the prototype's own code |
| Test | `tests/test_golden_parity.py` | 75 parity tests, passing |
| Test | `evals/pii/` | Labeled detector cases from the prototype, and the eval that will gate the PII guard |
| Deploy | `.claude/settings.json`, `.claude/hooks/protect-files.sh` | Permissions and approval-gate hook |
| Deploy | `.github/workflows/ci.yml` | Four CI gates |
| Maintain | `governance/control-bands.yaml` | Bands whose breach opens a new intent |

## Run it

```bash
pip install -e ".[dev]"
pytest -q
chmod +x .claude/hooks/protect-files.sh   # needs jq installed
```

## What is real and what is assumed

- **From the prototype:** the golden values, the program rules, the opportunity thresholds,
  the PII detector cases, the fee tiers and the 23.8% rate (both labeled illustrative there).
- **From the production sequence document:** the layers, modes, token hops and failure behavior.
- **Assumed:** team size, timeline, volumes, latency targets, Postgres, GitHub Actions, and
  the registry's file format. Each is listed in `docs/delivery-plan.md` section 4.
- **Not ported yet:** the conversion-routes logic that decides which holdings are transition
  assets, annual cost, risk analytics and option scoring. The transition test feeds the
  prototype's own transition assets into the Python schedule.
- **Needs the firm's review:** the program rules are the prototype's model of the documents,
  not the documents. Compliance should review the program-rules skill before it guides code.
