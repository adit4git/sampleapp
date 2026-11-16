# Claude Code: Learn It, Set It Up, and Build a Wealth Management App from 0 to 1

*Checked against the official Claude Code docs (code.claude.com/docs) on 12 Nov 2026. Claude Code ships updates almost daily, so when a command here disagrees with your install, trust the docs and `claude doctor`.*

---

## How to use this guide

| If you have... | Read |
| --- | --- |
| 30 minutes | Parts 1-3, then start building |
| A weekend | Parts 1-7, doing each exercise in a throwaway repo |
| A real project starting Monday | Everything, then follow Part 9 phase by phase |

The fastest way to learn Claude Code is to use it on real work and add one feature at a time when you feel a specific pain. Part 11 gives you a four-week order to do that in.

---

## Part 1. The mental model

Claude Code is an agent, not a chatbot. It reads your files, runs commands, edits code, and iterates on its own. You describe outcomes; it explores, plans, and implements.

Four ideas explain almost every best practice:

1. **Context is the scarce resource.** Everything Claude reads (messages, files, command output) fills its context window, and quality drops as it fills. Most habits in this guide exist to keep context clean.
2. **Verification closes the loop.** Without a check it can run (tests, build, linter, screenshot), Claude stops when the work *looks* done and you become the test suite. With a check, it iterates until it passes.
3. **Instructions are advisory; hooks are enforcement.** `CLAUDE.md` and skills are requests Claude usually follows. A hook is a script that always runs. Anything that must never happen in a finance codebase belongs in a hook or a permission rule.
4. **Fresh context beats long context.** A new session with a good spec outperforms a long session full of corrections. A reviewer in a fresh context catches what the author missed.

---

## Part 2. Install and first-run setup

### 2.1 Requirements

- macOS 13+, Windows 10 1809+, Ubuntu 20.04+, Debian 10+, or Alpine 3.19+
- 4 GB+ RAM, x64 or ARM64
- A paid account: Pro, Max, Team, Enterprise, or an API (Console) account. The free claude.ai plan does not include Claude Code. Bedrock, Google Cloud, and Microsoft Foundry are also supported.

### 2.2 Install (native installer, recommended, auto-updates)

```bash
# macOS, Linux, WSL
curl -fsSL https://claude.ai/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

Alternatives (these do not auto-update by default):

```bash
brew install --cask claude-code          # Homebrew, stable channel
winget install Anthropic.ClaudeCode      # WinGet
npm install -g @anthropic-ai/claude-code # npm (never use sudo)
```

**Windows note:** native Windows works, but sandboxing is only supported under WSL 2. For a finance project where you want sandboxed command execution, use WSL 2. On native Windows, install Git for Windows so Claude can use Bash.

### 2.3 Verify and log in

```bash
claude --version   # prints a version number
claude doctor      # read-only diagnostics of install and settings
cd your-project
claude             # first run opens the browser login
```

### 2.4 Choose your surface

Same engine, different front ends. Start with the terminal plus your IDE.

| Surface | Use it for |
| --- | --- |
| Terminal CLI | The full feature set; where new features land first |
| VS Code / JetBrains extension | Inline diffs, mode switcher, file context |
| Desktop app | Visual management of multiple parallel sessions |
| Cloud (claude.ai/code) and mobile | Long tasks that run without your laptop |
| GitHub Actions / GitLab CI | Automated PR review and CI tasks |

### 2.5 Tools to install alongside

- `git` and the GitHub CLI `gh` (Claude uses `gh` for issues and PRs; it is the most context-efficient way to reach GitHub)
- `jq` (the standard hook examples use it)
- Your language toolchain, formatter, linter, and test runner, all runnable from the command line
- A code intelligence plugin for your typed language: run `/plugin` and install the one for TypeScript, Python, etc. It gives Claude jump-to-definition and live type errors after each edit.

---

## Part 3. The core loop

Use this for any change you could not describe as a one-sentence diff.

1. **Explore** in plan mode. Press `Shift+Tab` until the status bar shows plan mode (or start with `claude --permission-mode plan`). Claude reads and answers without changing anything.
2. **Plan.** Ask for an implementation plan. Press `Ctrl+G` to open and edit the plan in your editor.
3. **Implement.** Approve the plan; tell Claude to write tests, run them, and fix failures.
4. **Verify.** Ask for evidence (test output, the command and its result), not a claim of success. Run `/verify` to check the change against the running app.
5. **Commit.** "Commit with a descriptive message and open a PR."

Skip planning for typos, renames, and one-liners.

### Prompting that works

| Weak | Strong |
| --- | --- |
| "add tests for the ledger" | "write tests for `ledger/post.ts` covering a transfer where the debit account has insufficient funds. no mocks. run them." |
| "fix the rounding bug" | "portfolio total is off by 1 cent when holdings include fractional shares. write a failing test reproducing it in `valuation.test.ts`, then fix the root cause." |
| "add a holdings endpoint" | "look at how `GET /accounts` is built in `api/accounts/`. follow that pattern to add `GET /accounts/:id/holdings` with pagination." |

Feed Claude rich input: `@path/to/file` to reference files, paste screenshots, give doc URLs, or pipe data (`cat error.log | claude -p "explain this"`).

### For big features: let Claude interview you

```text
I want to build [feature]. Interview me in detail using the AskUserQuestion tool.
Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs.
Don't ask obvious questions; dig into the hard parts I might not have considered.
Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```

Then start a **fresh session** to implement the spec. Good specs name files and interfaces, state what is out of scope, and end with an end-to-end verification step.

---

## Part 4. Cheat sheet

### Keys

| Key | Action |
| --- | --- |
| `Shift+Tab` | Cycle permission modes (manual, accept edits, plan, auto) |
| `Esc` | Stop Claude mid-action; context is kept |
| `Esc Esc` | Open the rewind menu |
| `Ctrl+G` | Edit the current plan in your text editor |
| `@` | Reference a file |

### Slash commands

| Command | Purpose |
| --- | --- |
| `/init` | Generate a starter CLAUDE.md from your project |
| `/clear` | Reset context between unrelated tasks |
| `/compact <focus>` | Summarize the conversation, keeping what you name |
| `/context` | See what is loaded and what it costs |
| `/btw` | Ask a side question that never enters history |
| `/rewind` | Restore conversation and/or code to a checkpoint |
| `/rename` | Name the session so you can resume it later |
| `/memory` | View and edit memory files; toggle auto memory |
| `/permissions` | Manage allow and deny rules |
| `/sandbox` | Enable OS-level isolation for commands |
| `/hooks` | Browse configured hooks |
| `/mcp` | MCP server status |
| `/plugin` | Browse and install plugins |
| `/config` | Settings UI |
| `/doctor` | Audit your config; proposes CLAUDE.md cuts |
| `/goal` | Keep Claude working until a condition is met |
| `/verify` | Check a change against the running app |
| `/code-review` | Review the current diff in a fresh subagent |
| `/batch <instruction>` | Split a large change across 5-30 subagents in worktrees |
| `/debug` | Bundled debugging skill |

### CLI

```bash
claude                          # interactive session
claude --continue               # resume the most recent session
claude --resume                 # pick a session to resume
claude --permission-mode plan   # start in plan mode
claude -p "prompt"              # non-interactive (scripts, CI)
claude -p "..." --output-format json
claude mcp add --transport http <name> <url>
claude agents                   # background sessions in one view (research preview)
claude update                   # update now
claude doctor                   # diagnostics
```

---

## Part 5. Context management

- `/clear` between unrelated tasks. This is the single most valuable habit.
- **Two-correction rule:** if you have corrected the same issue twice, `/clear` and write a better prompt with what you learned.
- Delegate research: "use subagents to investigate how X works." They read in their own context and return a summary.
- `/compact Focus on the ledger changes` when you need to keep going in one session.
- `/btw` for quick questions you do not need remembered.
- Checkpoints: every prompt creates one. `Esc Esc` restores code, conversation, or both. They only track edits made by Claude's file tools, not Bash side effects, so they do not replace git.
- Name sessions (`/rename ledger-v1`) and treat them like branches.

---

## Part 6. Configuration: what Claude knows and what it may do

### 6.1 The `.claude` directory at a glance

```text
your-repo/
├── CLAUDE.md                  # team instructions, loaded every session
├── CLAUDE.local.md            # your private notes (gitignore it)
├── .mcp.json                  # project-shared MCP servers
└── .claude/
    ├── settings.json          # shared: permissions, hooks, env
    ├── settings.local.json    # personal overrides (gitignored)
    ├── rules/                 # path-scoped instruction files
    ├── skills/<name>/SKILL.md # on-demand knowledge and /commands
    ├── agents/<name>.md       # custom subagents
    └── hooks/                 # hook scripts

~/.claude/                     # the same, user-wide, for all projects
```

### 6.2 CLAUDE.md

Run `/init`, then prune hard. Target **under 200 lines**. For each line ask: "would removing this cause a mistake?" If not, delete it.

Include: commands Claude cannot guess, style rules that differ from defaults, test instructions, repo etiquette, architectural decisions, gotchas. Exclude: anything readable from the code, standard conventions, long tutorials, file-by-file descriptions.

Starter for a wealth app (adapt the stack to yours):

```markdown
# Project: wealth platform
Monorepo: apps/web (Next.js), apps/api (NestJS), packages/domain, packages/ledger. Postgres.

# Commands
- Install: pnpm install
- Test one file: pnpm test <path>   (prefer this over the full suite)
- Typecheck: pnpm typecheck         (run after every series of edits)
- Migrations: pnpm db:migrate:new <name>   (never edit an applied migration)

# Money rules (IMPORTANT)
- Never use floating point for money or quantities. Use the Money and Decimal types in packages/domain.
- Every monetary amount carries a currency. No bare numbers.
- Ledger entries are append-only. Corrections are reversing entries, never updates or deletes.
- All write endpoints take an idempotency key.

# Security
- Never log PII, account numbers, or tokens. Use the redacting logger.
- Every query is scoped by tenant_id and checked against the caller's role.
- Use synthetic data from packages/fixtures. Never real client data.

# Workflow
- Branch per feature; PR required; tests and typecheck must pass.
- When compacting, preserve the list of modified files and test commands.
```

Locations: `./CLAUDE.md` (team), `~/.claude/CLAUDE.md` (you, all projects), `./CLAUDE.local.md` (you, this project). Files are additive, and nested `CLAUDE.md` files in subdirectories load when Claude works there. Import other files with `@path/to/file`. If the repo already has an `AGENTS.md` and no `CLAUDE.md`, Claude reads that instead.

### 6.3 Path-scoped rules

Keep CLAUDE.md small by moving area-specific rules into `.claude/rules/`. With a `paths` field they load only when Claude touches matching files.

```markdown
---
paths:
  - "packages/ledger/**/*.ts"
---
# Ledger rules
- Every posting must balance: sum of debits equals sum of credits per currency.
- Add a property-based test for any new posting type.
```

### 6.4 Auto memory

Claude also keeps its own notes from your corrections (a `MEMORY.md` index plus topic files), loaded each session. View, edit, or toggle with `/memory`. Review it occasionally; treat it as helpful context, not as rules.

### 6.5 Permission modes

| Mode | Runs without asking | Use for |
| --- | --- | --- |
| Manual (`default`) | Reads only | Sensitive work, reviewing every action |
| Accept edits (`acceptEdits`) | Reads, file edits, common file commands in the project | Iterating on code you will review |
| Plan (`plan`) | Reads | Exploring before changing |
| Auto (`auto`) | Everything, with a classifier model reviewing actions | Long tasks with fewer prompts |
| `dontAsk` | Only pre-approved tools; everything else denied | Locked-down CI and scripts |
| Bypass (`bypassPermissions`) | Everything | Isolated containers and VMs only |

On recent versions, auto mode is the starting mode for interactive terminal and VS Code sessions. Deny rules apply in every mode, including bypass. Writes to sensitive paths such as `.git`, `.claude`, shell rc files, and `.mcp.json` are never silently auto-approved outside bypass.

### 6.6 Permission rules and sandboxing

Pre-approve what is safe and deny what is not in `.claude/settings.json` (check the permissions docs for exact rule syntax on your version):

```json
{
  "permissions": {
    "allow": [
      "Bash(pnpm test *)",
      "Bash(pnpm typecheck)",
      "Bash(pnpm lint *)",
      "Bash(git commit *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  }
}
```

Then turn on `/sandbox` so commands run with restricted filesystem and network access. For a finance codebase, allowlist plus sandbox plus deny rules on secrets is the baseline.

---

## Part 7. Extending Claude Code

### 7.1 Which feature for which job

| You notice... | Add |
| --- | --- |
| Claude gets a convention wrong twice | A line in CLAUDE.md |
| You paste the same procedure a third time | A skill |
| You keep copying data from a system Claude cannot see | An MCP server |
| Claude reads many files to find a symbol | A code intelligence plugin |
| A side task floods your conversation | A subagent |
| Something must happen every time | A hook |
| A second repo needs the same setup | A plugin |

Context cost matters: CLAUDE.md is paid on every request; skills cost only their description until used; MCP tools load names up front and schemas on demand; subagents use their own window; hooks cost nothing unless they return output.

### 7.2 Skills

A skill is a folder with a `SKILL.md`. Claude loads it when the description matches the task, or you invoke it as `/name`.

Reference skill (domain knowledge):

```markdown
<!-- .claude/skills/portfolio-math/SKILL.md -->
---
name: portfolio-math
description: Formulas and conventions for portfolio performance, cost basis, and rebalancing in this codebase
---
# Portfolio math conventions
- Time-weighted return: chain-link daily sub-period returns; cash flows at start of day.
- Money-weighted return: XIRR on dated cash flows; see packages/domain/irr.ts.
- Cost basis: tax lots, FIFO by default, specific-lot when the account opts in.
- Rounding: banker's rounding at presentation only; never round stored values.
- Golden test vectors live in packages/domain/__fixtures__/performance/.
```

Workflow skill (you trigger it; `disable-model-invocation` stops Claude running it on its own):

```markdown
<!-- .claude/skills/new-migration/SKILL.md -->
---
name: new-migration
description: Create a safe database migration
disable-model-invocation: true
---
Create a migration for: $ARGUMENTS

1. Generate with `pnpm db:migrate:new`.
2. Make it backward compatible (expand, then contract). No destructive change in one step.
3. Write the down migration.
4. Run against the test database and run the affected tests.
5. Summarize locking behavior and expected runtime on large tables.
```

Other skills worth having for this project: `api-conventions`, `add-endpoint`, `fix-issue`, `release-checklist`, `threat-model`.

### 7.3 Subagents

Specialized workers with their own context, tools, and model, defined in `.claude/agents/`.

```markdown
<!-- .claude/agents/ledger-auditor.md -->
---
name: ledger-auditor
description: Reviews changes touching money movement, ledger postings, or balances
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior engineer reviewing financial code. Check for:
- Floating point used for money or quantities
- Postings that can fail to balance; missing currency
- Non-idempotent writes; missing transaction boundaries; race conditions on balances
- Updates or deletes on ledger tables
- Missing tenant scoping or authorization checks
- PII or secrets in logs
Report only issues affecting correctness or stated requirements, with file and line.
```

Use them explicitly: "use the ledger-auditor subagent on this diff." Add a `security-reviewer` the same way. Tell reviewers to flag only real gaps, since a reviewer asked to find problems will always find some.

### 7.4 Hooks

Scripts that run on lifecycle events (`PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `Notification`, and others). Exit code 0 means no objection; exit code 2 blocks the action and sends your stderr message back. Besides shell commands, hooks can be HTTP requests, prompts, or agents. You can ask Claude to write them: "write a hook that blocks edits to applied migrations."

Format after every edit, and block edits to protected files:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh" }
        ]
      }
    ]
  }
}
```

```bash
#!/bin/bash
# .claude/hooks/protect-files.sh   (chmod +x)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PROTECTED_PATTERNS=(".env" "pnpm-lock.yaml" ".git/" "db/migrations/applied/")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

Hooks worth adding for a wealth app: a `Stop` hook that runs typecheck and the affected tests so a turn cannot end red; a `PreToolUse` hook on Bash that blocks commands pointed at production; a secret scanner on edits.

### 7.5 MCP servers

MCP connects Claude to external systems: your database, issue tracker, Figma, Sentry, browser.

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

Scopes are local, project (shared through `.mcp.json`), and user; local wins over project, which wins over user. Check status with `/mcp`.

For this project: connect a **read-only** database user on a dev database with synthetic data, your issue tracker, and your error monitor. Never connect production data stores or live brokerage or custodian credentials to an agent session. Prefer CLIs (`gh`, `aws`, `psql`) where they exist; they are cheaper on context than MCP.

### 7.6 Plugins

A plugin bundles skills, hooks, subagents, and MCP servers into one install. Browse with `/plugin`. Install the code intelligence plugin for your language first. Once your own setup stabilizes, package it as a plugin so every repo and teammate gets it. Vet third-party plugins before installing; they run with your permissions.

---

## Part 8. Scaling up

| Technique | What it does |
| --- | --- |
| Git worktrees | Separate checkouts so parallel sessions do not collide |
| Desktop app sessions | Manage several local sessions visually |
| Cloud sessions | Run on Anthropic-managed infrastructure while you are away |
| `claude agents` | Dispatch and watch background sessions (research preview) |
| Writer / reviewer | One session builds, a fresh one reviews |
| `/batch` | Fan one change out across many subagents |
| Dynamic workflows | Claude scripts many subagents and cross-checks findings |
| `/goal` | An evaluator re-checks a condition each turn until it is met |
| Scheduled tasks | Run prompts on a schedule |
| Agent teams | Coordinated multi-session teams (experimental, off by default) |

### Headless mode and CI

```bash
claude -p "List all API endpoints" --output-format json

# locked-down batch run
claude -p "Migrate $file to the new Money type. Return OK or FAIL." \
  --allowedTools "Edit,Bash(git commit *)" \
  --permission-mode dontAsk
```

Set up Claude Code GitHub Actions (or GitLab CI) for automatic PR review, and use `/code-review` locally before pushing. For a finance app, make AI review an addition to human review on anything touching money movement, auth, or migrations, never a replacement.

---

## Part 9. The 0-to-1 playbook for a wealth management app

One principle runs through every phase: **build the verification before the feature.** In finance, the tests are the product spec.

### Phase 0: Product and domain spec (no code)

Run the interview prompt from Part 3 for the whole product, then per bounded context. Have Claude produce:

- `docs/SPEC.md`: users (advisor, client, ops, compliance), core journeys, explicit non-goals
- `docs/DOMAIN.md`: glossary and entities (household, client, account, custodian, security, holding, tax lot, transaction, portfolio, model, benchmark, fee schedule)
- `docs/ARCHITECTURE.md`: modules, data flow, tenancy, a diagram
- `docs/adr/`: one short decision record per major choice
- `docs/THREAT_MODEL.md`: assets, actors, trust boundaries

Decide the regulated parts with qualified people, not with an AI: licensing and registration, custody, KYC/AML, suitability, record retention, data residency. Claude can draft checklists and questions for your compliance counsel; it cannot be your compliance counsel.

### Phase 1: Repo scaffold and guardrails

Prompt: "Scaffold the monorepo per ARCHITECTURE.md. Set up typecheck, lint, format, unit and integration test runners, a dockerized Postgres, and CI. Prove each works by running it."

Then, before any feature work: `/init` and prune CLAUDE.md; add permission allow and deny rules; enable `/sandbox`; add the format and protect-files hooks; install the code intelligence plugin; commit `.claude/`.

### Phase 2: Domain core (highest rigor)

Build `Money`, `Decimal`, `Currency`, and the double-entry ledger first, test-first:

```text
Write property-based tests for packages/ledger first: every posting balances per
currency, balances equal the sum of entries, replaying entries is deterministic,
and a repeated idempotency key creates no second entry. Show me the tests before
implementing. Then implement until they pass and show the output.
```

Run the `ledger-auditor` subagent on every diff here. Use manual or accept-edits mode and read every line; this is the code where a subtle bug costs real money.

### Phase 3: Data model and migrations

Plan mode first: have Claude propose the schema, indexes, and tenancy strategy (row-level security or schema per tenant) and argue the tradeoffs in an ADR. Create migrations only through your `/new-migration` skill. Include an append-only audit log table from day one.

### Phase 4: Auth, tenancy, and audit

Use a proven identity provider rather than hand-rolling auth. Build role-based access (advisor, client, ops, compliance, admin) and a test matrix that proves every endpoint rejects the wrong tenant and the wrong role. Ask Claude to generate the matrix from the route list so new endpoints cannot be forgotten.

### Phase 5: Vertical slices

One slice per session, each in its own worktree or branch, each following explore, plan, implement, verify, commit:

1. Client and household onboarding
2. Accounts and holdings view
3. Transaction ingestion (start with CSV import of synthetic data)
4. Portfolio valuation and allocation
5. Performance (TWR, IRR) against golden test vectors you verified by hand or in a spreadsheet
6. Model portfolios, drift, and rebalancing proposals (proposals only; a human approves trades)
7. Fees and billing
8. Reporting and statements
9. Client portal

For UI: paste a design or screenshot, have Claude implement it, then screenshot the result with the browser integration and list differences.

### Phase 6: External integrations

Market data, account aggregation, and custodian feeds. For each: write an adapter interface, record sandbox responses as fixtures, build against the fixtures, and add contract tests. Keep vendor API keys out of the repo and out of Claude's reach (deny rules on secret files; use a secrets manager). Read each vendor's terms on data use before sending their data through any AI tool.

### Phase 7: Hardening

- Run the `security-reviewer` subagent and the security scanning features across the codebase
- Use a dynamic workflow or `/batch` for codebase-wide audits (float usage, missing tenant scoping, unlogged writes)
- Load test valuation and reporting; add reconciliation jobs that compare ledger balances against custodian positions and alert on breaks
- Have Claude draft runbooks and an incident checklist from the architecture docs
- Commission an independent penetration test and a human security review before real client data arrives

### Phase 8: Release

CI gates: typecheck, lint, tests, migration check, AI review, human approval on sensitive paths. Staged rollout behind feature flags. A `/release-checklist` skill keeps the steps consistent.

---

## Part 10. Finance-specific guardrails

**Correctness**
- Decimal types for money and quantities; currency always attached; rounding only at presentation
- Append-only ledger; corrections by reversal; idempotency keys on every write
- Golden vectors for every calculation, verified independently of Claude
- Explicit time handling: trade date versus settlement date, market calendars, time zones

**Data and privacy**
- Develop only on synthetic data. Do not paste real client data, account numbers, or credentials into a session.
- Read the Data usage, Security, and Zero data retention docs pages and pick the account type that matches your obligations before any regulated data is involved.
- Deny rules on `.env` and secret paths; sandbox on; read-only database credentials for MCP

**Process**
- Enforce the non-negotiables with hooks and permission rules, not CLAUDE.md prose
- Human review required for ledger, auth, migrations, and anything that moves money
- Keep ADRs and the audit trail of AI-assisted changes in git; clear commit messages and PR descriptions help later audits
- Never let an agent session hold production credentials or execute trades

**Judgment**
- Claude can produce plausible code that mishandles an edge case. If you cannot verify it, do not ship it.
- Regulatory conclusions need a qualified professional. Use Claude to prepare, not to decide.

---

## Part 11. Four-week learning path

**Week 1: fundamentals.** Install; run `/init`; do ten small tasks using explore, plan, implement, verify. Practice `Esc`, `Esc Esc`, `/clear`, `/compact`, `@files`, `--continue`. Exercise: build the `Money` type test-first.

**Week 2: configuration.** Prune CLAUDE.md under 200 lines; add two path-scoped rules; set permission allow and deny rules; enable the sandbox; install code intelligence; write the format and protect-files hooks. Exercise: try to make Claude edit `.env` and confirm it is blocked.

**Week 3: extension.** Write two skills (one reference, one workflow) and two subagents (ledger auditor, security reviewer); connect one MCP server; run the interview-to-spec flow for a real feature. Exercise: ship one vertical slice end to end.

**Week 4: scale.** Run two worktree sessions in parallel; use writer / reviewer; run `claude -p` in a script; set up GitHub Actions review; try `/goal`, `/batch`, and a dynamic workflow on an audit. Exercise: codebase-wide check for float usage in money paths.

After that, read the changelog weekly. Features marked research preview or experimental change quickly.

---

## Part 12. Common failure patterns

| Pattern | Fix |
| --- | --- |
| Kitchen-sink session mixing unrelated tasks | `/clear` between tasks |
| Correcting the same thing repeatedly | After two tries, `/clear` and rewrite the prompt |
| Bloated CLAUDE.md that Claude ignores | Prune; move content to rules, skills, or hooks |
| Trusting output that looks right | Always give a runnable check; ask for evidence |
| Unscoped "investigate this" | Narrow the scope or use a subagent |
| Over-engineering from reviewer findings | Fix only correctness and requirement gaps |
| One giant "build the app" prompt | Spec first, then one vertical slice per session |

---

## Part 13. Where to go deeper

All under `https://code.claude.com/docs/en/`:

| Topic | Page |
| --- | --- |
| Start here | `quickstart`, `how-claude-code-works`, `best-practices` |
| Workflows and prompts | `common-workflows`, `prompt-library` |
| Memory and instructions | `memory`, `claude-directory`, `context-window` |
| Settings and safety | `settings`, `permissions`, `permission-modes`, `sandboxing`, `security`, `data-usage` |
| Extending | `features-overview`, `skills`, `sub-agents`, `hooks-guide`, `mcp`, `plugins/overview` |
| Parallel and automated | `worktrees`, `agents`, `workflows`, `goal`, `headless`, `github-actions`, `code-review` |
| Large repos | `large-codebases` |
| Reference | `cli-reference`, `commands`, `settings-reference`, `changelog` |
| Full index | `https://code.claude.com/docs/llms.txt` |
