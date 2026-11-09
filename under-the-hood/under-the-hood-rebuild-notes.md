# Under the hood: rebuild notes

**For:** an LLM or developer rebuilding this one feature in the Atlas console prototype (`atlas-console-book-view.html`), or porting it to another app.

**What it is:** a switch in the top bar. When it is on:
- **On Ask Atlas answers:** each answer gets a strip. It opens an inspector showing:
  - what the services retrieved;
  - what a gateway would send to the language model (tokens, not names);
  - which services, rules and documents were used;
  - which guardrails ran, and which evals cover the answer.
- **On the screens:** each part gets a label saying where it comes from:
  - **✦ drafted by the model**;
  - **⚙ calculated, no model**;
  - **▤ published, no model**.

  Selecting a label opens the same inspector.

**Honesty rule:** no model is called. Answers still come from the prototype's rules. The inspector shows what a production gateway **would** send and check, and says so in its header ("simulated: no model is called"). Three things really run on every answer:
- the service-call recording;
- the leak check;
- the answer scan and token checks.

The screenshots are in `under-the-hood-screenshots.md`.

---

## 1. Where it lives

**Three pieces, added to the single HTML file:**
- **CSS:** appended before `</style>` (about 80 lines; class prefix `uh-`).
- **Script part 1 (`uh.js`):** about 340 lines. Covers answers: recording, tokens, the trace, the inspector, the evals.
- **Script part 2 (`uh2.js`):** about 110 lines. Covers the screens: labels, drafted-text traces, traces for calculated and published parts.

**Insertion point:** both scripts are pasted **inside the main script, just before the app's start-up lines** (`if(!loadWork())seedWork(); render();`). Two reasons:
- The wrappers must be in place before the first render, so the first screen's opening message is captured.
- The scripts reassign the app's global function declarations, which only works from the same classic script scope (or a later one).

**The build:** `build.py` reads the base HTML, inserts the CSS and the two scripts, and writes the console. The feature has no state of its own on the server and no external libraries.

## 2. What it needs from the host app

**Globals it reads:**
- data and state: `DATA` (`households`, `advisors`), `S` (`adv`, `chat`, `book`, `lastCtx`), `CK` (criteria), `SRC` (source document names), `ASOF`, `CIO`;
- helpers: `byId`, `HH`, `shortName`, `money`, `esc`, `shortDate`, `parse` (route parts), `ctxOf` (the screen's context record), `W(h,k)` (workflow state), `toast`, `render`, `rerenderKeep`.

**Answer functions it wraps (reassigned):**
- `ask(q)`: the panel and home chat;
- `wfAsk(q)`: the workflow chat;
- `atlasStep(c)`: the opening message per screen;
- `guideRecommend(h,k)`: the decision guide's recommendation;
- `msgHtml(m)` and `wfMsgHtml(m,i,l)`: message rendering, to append the strip.

**Answer functions it calls:** `atlasAnswer(q)`, `wfAnswer(h,k,q)`, `opener(c)`.

**Service functions it records** (each must be a top-level `function` declaration, so it can be reassigned):

| Function | Shown as | Service |
|---|---|---|
| `M` | GET /households/{h}/positions | Positions and balances |
| `GA` | GET /households/{h}/analytics | Portfolio analytics |
| `opps` | GET /households/{h}/opportunities | Opportunity engine |
| `ev` | GET /opportunities/{k}/households/{h} | Opportunity engine |
| `summary` | GET /book/opportunities/{k} | Opportunity engine (book) |
| `latestProposal` | GET /households/{h}/proposals | Proposals |
| `advElig` | POST /advisory/eligibility | Eligibility rules |
| `advMatrix` | POST /advisory/conversion-routes | Conversion rules |
| `allOptions` | POST /proposals/options | Proposal engine |
| `advKey` | POST /analytics/risk-tax-shift | Risk and tax analytics |
| `annualCost` | GET /billing/cost-estimate | Fee and cost estimator |
| `tetPlan` | POST /tax/transition-plan | Transition model |
| `stratRank`, `stratEval` | GET /strategies/fit | Strategy catalog |
| `scoreOptions`, `guideStrategy` | POST /guide/... | Decision guide scoring |
| `kbAnswer` | POST /documents/search | Approved document search |
| `cioAnswer` | GET /research/cio-house-view | Research documents |
| `workItems` | GET /work-items | Work queue |
| `reminderFromText` | POST /reminders | Reminders (writes) |
| `HH` (recorded by hand) | GET /advisors/{a}/households | Client records (CRM) |
| `clientRec` (recorded by hand) | GET /households/{h} | Client records (CRM) |

**`const` functions can't be wrapped.** `HH` and `flagsOf` are `const` arrow functions, so their calls can't be intercepted.
- `HH` is recorded by hand with `uhRec('HH',[S.adv],HH)` where a screen uses it.
- `flagsOf` calls `ev` internally, so it shows up as the opportunity engine.

**Screen generators it wraps** (for ✦ parts):
- `glanceLede(h)`: the portfolio summary;
- `recap(h,k)`: "why this opportunity";
- `proposalSummary(h,k,…)`: the proposal summary.

**Screen functions it calls** to record calculated parts: `workStrip('book')`, `critList(k)`, `viewClients()`.

## 3. Recording service calls

Each service function is replaced by a wrapper. It records only **top-level** calls made while an answer is being computed; a service's internal calls stay hidden, as they would inside a real service.

```js
for (const name of Object.keys(UH_API)) {
  const f = window[name]; if (typeof f !== 'function') continue;
  window[name] = function (...a) {
    if (!UH.rec) return f.apply(this, a);          // not recording: no overhead
    UH.depth++; let r;
    try { r = f.apply(this, a) } finally { UH.depth-- }
    if (UH.depth === 0) UH.rec.push({ fn: name, args: a, ret: r });
    return r;
  };
}
function uhCapture(fn){ UH.rec=[]; UH.depth=0; let out; try{ out=fn() } finally { UH.last=UH.rec; UH.rec=null } return out }
```

**Grouping:** calls are grouped by function. For each group, keep:
- the call count;
- the set of household IDs passed;
- the set of criterion keys passed;
- the first call's arguments, mapped (a household becomes `{h}`, other objects with `id` become the id, small plain objects become compact JSON);
- a summary of the first call's result (`uhRet`, below).

**Leave out:** `kbAnswer` calls that returned nothing, because a search that found no passage isn't a source.

**Display rules:**
- **Many households:** if a group touched more than one, show "N households in one batched request", not the raw call count. The prototype looks the same household up many times while drawing; production would batch.
- **Many criteria:** if a group used more than one, the path shows `{criterion}` and the call shows "each of N criteria".

**Result summaries (`uhRet`)** keep each result small and readable, and send every string through the same redaction:
- `M`: value, weights, target, unrealized loss;
- `tetPlan`: budget, years, transition assets, net gains, year-1 tax, tax without the service;
- `summary`: households, value, top 5 as tokens;
- `HH`: count and the field list;
- **anything else:** up to 6 primitive fields.

## 4. Made-up identifiers

The sample data has names but no tax IDs, addresses or account numbers, so the feature makes them up. They are made **deterministically from the household ID** with an FNV-style hash (`uhHash`), so they stay the same on every load. All are visibly fictional:

| Identifier | Rule | Example |
|---|---|---|
| People | Parsed from `h.contact`: split on `&`; a lone first name takes the last surname; text in brackets and "Board —" prefixes are dropped (a board's chair is taken from the brackets) | "Margaret & Paul Henderson" becomes "Margaret Henderson", "Paul Henderson" |
| Tax ID | 9xx-xx-xxxx (never a real SSN) | 958-77-0921 |
| Date of birth | Year 1946–1975, month and day from the hash | 1958-04-12 |
| Address | Number + one of 8 streets + "Springfield 0xxxx" | 418 Linden Lane, Springfield 08558 |
| Phone | (617) 555-01xx (fictional range) | (617) 555-0142 |
| Email | first.last@example.com (ø becomes o; accents stripped; repeated dots collapsed) | owen.whitaker@example.com |
| Account numbers | One per account type the household holds (brokerage, advisory): letter, letter, digit, dash, 5 digits | KQ1-48213 |
| Employer | Only if a holding is flagged insider: the issuer's name + "(insider)" | |

**Pitfall:** use **unsigned** shifts (`>>>`) on the hash. A signed `>>` gave negative indexes, which showed as "undefined1-90375" accounts and a date of birth of "1974-01--8".

## 5. Tokens and redaction

**The token table:** one per page session, `Map(kind:key → token)`, with kinds `CLIENT`, `PERSON` and `ACCT`, numbered in order of first use (`CLIENT_1`, `PERSON_3`). It never appears in what would be sent. The Prompt tab can show it, but it stays in the page.

**The name list (built once from all households):**
- full household name, short name (`shortName(h)`) and other name words (except generic words: family, trust, household, holdings, LLC, foundation…) → that household's `CLIENT_n`;
- each person's full name → `PERSON_n`;
- each person's **first name alone** → the same `PERSON_n`, **case-sensitive**, so "Grant" matches and "grant" doesn't;
- each account number → `ACCT_n`.

**Matching:** sorted longest first. Each entry is a regex with Unicode-aware boundaries:

```js
new RegExp(`(?<![\\p{L}\\p{N}])${escapeRegex(s)}(?![\\p{L}\\p{N}])`, firstNameOnly ? 'gu' : 'giu')
```

**Patterns, applied before the name list:**

| Type | Regex |
|---|---|
| SSN or tax ID | `\b\d{3}-\d{2}-\d{4}\b` |
| Email | `\b[\w.+-]+@[\w-]+\.[\w.]+\b` |
| Phone | `(?:\+?1[\s.-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b` or `\b555-01\d\d\b` |
| Account number | `\b[A-Z0-9]{3}-\d{5}\b` or `acct/account (no./number/#) 6+ digits` (case-insensitive) |
| Date of birth | `YYYY-MM-DD` or `M/D/YYYY` |
| Street address | 1–5 digits, 1–3 capitalized words, then Street, St, Avenue, Ave, Road, Rd, Lane, Ln, Drive, Dr, Court, Ct, Way, Boulevard or Blvd |

**`uhRedact(text)`** returns the redacted text and what was found. Patterns become `[SSN_OR_TAX_ID_REMOVED]`, `[PHONE_REMOVED]` and so on; names and account numbers become tokens.

## 6. The trace (`uhBuild`)

**Called with:** `(kind, question, context, calls, answerHtml)`. The kinds are `panel`, `wf`, `opener`, `guide` and `draft`.

**Steps:**

1. **Text of the answer:**
   - turn `<li>` into " • ";
   - turn `<br>` and closing block tags into spaces;
   - strip tags;
   - **decode entities** with a `<textarea>` (otherwise "&amp;" shows up);
   - collapse spaces.
2. **Households touched:** those passed to recorded calls, plus the context's household, plus any whose full name appears in the answer.
3. **Focus households:** the context's household; otherwise the only one touched; otherwise the first one named in the answer. Only these get the full field table and profile in the request.
4. **Field rows (retrieved vs sent), per focus household:**

| Field | Retrieved | Sent | Rule |
|---|---|---|---|
| Household name | name | `CLIENT_n` | tokenized |
| Primary contact, second person | name | `PERSON_n` | tokenized |
| Tax ID | 9xx-xx-xxxx | not sent | removed |
| Date of birth | date | "age 60–69" | generalized |
| Home address, phone, email | values | not sent | removed |
| Account numbers | KQ1-48213 | `ACCT_n (brokerage)` | tokenized |
| Employer (insider holders only) | issuer (insider) | "insider: yes" | generalized |
| Entity and segment, risk profile and target, positions | values | same | allowed |
| Advisor notes (free text) | notes + next meeting note | redacted text | redacted if anything was found |

5. **The request that would be sent** (`payload`):
   - `system`: "Answer only from the tool results and documents provided. Never calculate tax or risk yourself: call the services. Refer to clients only by their tokens. Cite the document for every program rule."
   - `context`: screen, client token, criterion, level, filter (redacted), step (workflow only).
   - `clients`: one profile per focus household: token, people tokens, age band, entity, segment, risk profile, target, account tokens, insider flag, the first 8 positions (symbol, value, cost, account token) and redacted notes.
   - `others`: up to 12 tokens for the other households touched.
   - `tool_results`: per service group: the tool name, arguments with households as tokens and strings redacted, the call count and the result summary.
   - `question`: the redacted question, or "(no question: …)" for openers, guide recommendations and drafts.
6. **The model's answer in tokens:** `uhRedact(answerText)`. The answer **shown** is the original text.
7. **Checks** (§7).
8. **Rules and sources:**
   - **Rules:** from `UH_RULES` for each service group, plus a criterion rule for `summary` and `ev` (for "maturing", the dollar threshold and horizon from `S.book`).
   - **Sources:** `SRC` entries for the services' rule sets, plus any `class="kb-src"` source in the answer, plus any `class="cite"` chip (shown as "… (opens the PDF)").

The trace is stored in `UH.T[id]`, and the message keeps `tr: id`.

**Which source goes with which service:**
- eligibility and conversion rules → the conversion rules document;
- fee estimates → the program brochure;
- the transition model → the tax-efficient transition term sheet.

## 7. Guardrail checks (per answer)

| # | Check | How it is decided | Ran or policy |
|---|---|---|---|
| 0 | Names resolved by the app | Lists the names found in the question and their tokens | Ran |
| 1 | Permissions | Every household touched has `advisor === S.adv` | Ran |
| 2 | Approved fields only | Counts of removed, tokenized, generalized and allowed rows | Ran |
| 3 | Free text checked | What patterns found in the question; whether notes were redacted | Ran |
| 4 | Instructions hidden in retrieved text | Regex `ignore (all |the )?(previous|prior) instructions|system prompt|disregard the rules` over notes and service results | Ran |
| 5 | **Leak check on the payload** | Every identifier of every household touched (name, short name, people, tax ID, date of birth, address, phone, email, account numbers, employer), longer than 2 characters, searched with Unicode boundaries, case-insensitive, in `JSON.stringify(payload)`. **Must be 0.** | Ran |
| 6 | Answer scanned on the way back | The patterns from §5 on the model's answer in tokens | Ran |
| 7 | Tokens belong to this request | Every token in the answer exists in the table **and** appears in this request | Ran |
| 8 | Names restored on screen only | No token left in the text shown | Ran |
| 9 | Figures come from services | The number of service results supplied | Policy |
| 10 | Changes need the advisor's confirmation (only when `reminderFromText` ran or the question sets a budget) | Production: the model proposes, the advisor confirms; the prototype applies directly | Policy |

The sweep in §11 reads checks 6, 7 and 8 **by index**, so keep this order.

## 8. Wiring into the answers

- **`ask(q)`:** push the user message and a typing message. Run `uhRun('panel', q, ctxOf(), () => atlasAnswer(q))`. After 380 ms, push the answer with `tr`. Navigate if the answer asks to.
- **`wfAsk(q)`:** the same with `wfAnswer(h,k,q)` and kind `wf`, after 350 ms.
- **`atlasStep(c)`:** only on Book view, the client list and the client page, once per context key. Run `opener(c)` under capture, replace an unanswered automatic message, and set `S.railNew`.
- **`guideRecommend(h,k)`:** run the original under capture, then attach the trace to the newest Atlas message it pushed.
- **`msgHtml` and `wfMsgHtml`:** when `m.tr` is set, the switch is on and the trace exists, insert the strip before the final `</div>`.

**The strip** (monospace, dashed border): "⚙ N services · N sources · n/m checks · 0 identifiers sent". Checks are green when all ran checks passed; any leak is red and bold.

## 9. The inspector

**Layout:** a right-side panel (`#uhp`, `min(620px, 100vw)` wide, full height; full screen on a phone).
- **Header:** "Under the hood · simulated: no model is called", the question in quotes (or "Opening message · …", or "✦ Drafted by the model · …"), and the screen's context line.

**Tabs:**

| Tab | Contents |
|---|---|
| Flow | Seven numbered steps with counts: advisor asks → the screen says what it shows → services retrieve → the gateway prepares the request (removed and tokenized counts, leak check) → the model writes (sample tokens) → the answer is checked (n of m) → names come back on screen only. Steps 4 and 6 are green or red. Ends with a note that the identifiers are made up. |
| Data | A legend of the five rules; the question as typed vs as sent; what the screen published (context fields); per focus household, the field table; the other households touched as tokens; a re-identification warning if a single holding is above 20% of the household or any stock is insider stock |
| Prompt | The full request as JSON with tokens highlighted (blue) and removals (red); the model's answer in tokens; the answer shown; "show the token table" |
| Services and rules | Per group: the method and path, the service name, "The model asks" (call with tokens) vs "The service receives" (internal IDs), and the result sent to the model (collapsible); then the rules applied and the sources cited |
| Guardrails | The checks, each marked "ran on this answer" or "policy", and the order in production |
| Evals | §11 |

**Interaction:**
- **Capturing click listener** (on `document`, capture phase):
  - `data-uhtoggle`: the switch.
  - `data-uh`: a strip. Stop the event so the message underneath doesn't react.
  - `data-uhtab`: change tab.
  - `data-uhclose`: close.
  - `data-uhtoks`: show the token table.
  - `data-uheval`: run an eval. Disable the button and show "Running…" for 30 ms first.
  - A click outside the panel closes it.
- **Esc:** closes the panel, stopping propagation so the app's own Esc doesn't also fire.

**The switch:**
- **Where:** in the top bar after the spacer (`header.top .sp`), as a pill with a sliding switch and the label "Under the hood" (label hidden on a phone).
- **State:** saved in `localStorage['atlas-uh']`, inside try/catch.
- **When it changes:** toggle `body.uh-on`, call `rerenderKeep()` and toast "Under the hood is on: select a label on the screen, or the strip under any Atlas answer." Turning it off closes the panel, and the re-render removes every label.

## 10. Labels on the screens (`uh2.js`)

**Drafted text (✦):**
- `glanceLede`, `recap` and `proposalSummary` are wrapped. When the switch is on and nothing else is recording, each call records its own service calls and builds a `draft` trace.
- The context is the client or workflow, with `plain` set to "Household · Portfolio summary".
- The trace is stored in `UH.drafts[key]`, replacing the previous one. Keys: `glance:<id>`, `recap:<id>:<k>`, `prop:<id>:<k>`.
- `glanceLede` returns HTML; the others return text and are escaped first.
- The inspector opens on the Data tab.

**Calculated (⚙) and published (▤):**
- Selecting one runs that part's `run(h,k)` under capture and builds a short trace (`uhCalcTrace`).
- **Tabs:** only Flow, Services and rules, and Guardrails.
- **Flow:** "No model involved", then three steps: screen opens → services calculate (or the document store and client record answer) → shown as calculated (or quoted with the citation).
- **Checks:**
  - no model call (ran);
  - permissions (ran);
  - figures tested on every release, or current version only for published parts (policy);
  - audit log (policy).
- **"The screen calls"** shows internal IDs; no tokens, because no model is involved.

**Parts by screen** (`uhParts`, matched on `parse()`):

| Screen | Part (selector) | Kind | What it runs |
|---|---|---|---|
| Book view | `.workstrip` Pick up where you left off | ⚙ | `workStrip('book')` |
| | `.heat` Opportunity tiles | ⚙ | `uhRec('HH')`, then `summary` for each criterion |
| | `#crit` Clients for this criterion | ⚙ | `uhRec('HH')`, then `critList(k)` |
| Client list | the `section.card` that contains `.filters` | ⚙ | `uhRec('HH')`, then `viewClients()` (records client records, positions for every household, the opportunity check against 13 criteria, work items) |
| Client page | `.chead` Client record | ▤ | `uhRec('clientRec',[h])` |
| | `#portfolio .ai-z` with "AI-drafted" | ✦ | `glanceLede(h)` |
| | `.gl-kpis` Key figures | ⚙ | `M(h)`, `GA(h)` |
| | `#portfolio .ai-z` with "CIO view" | ▤ | `M(h)`; source "CIO House View · date" |
| | `#opps` Opportunities | ⚙ | `opps(h)` |
| | any other `section.card` | ⚙ | `M(h)`, `GA(h)` |
| Workflow step 1 | the `.ai-z` in the recap section | ✦ | `recap(h,k)` |
| | `.oppg` The facts behind it | ⚙ | `ev(k,h)` and the criterion rule |
| | the first `.card.note` | ⚙ | `allOptions`, plus `advKey(h)` for the Advisory move |
| | other `section.wf-sec` | ⚙ | `advMatrix(h)` for the Advisory move, otherwise `ev` |
| Workflow step 2 | `#strat` Where the assets go | ⚙ | `stratRank(h)` |
| | `#ways` How to get there | ⚙ | `allOptions(h,k)` |
| | the transition panel | ⚙ | `tetPlan(h, W(h,k).budget or 250000, stratOf(h))` |
| | other `section.wf-sec` | ⚙ | `allOptions(h,k)` |
| Workflow step 3 | `#report > section.rs` containing `.ai-z` | ✦ | proposal summary |
| | the section titled "1. …" | ✦ | `recap(h,k)` |
| | other sections (except `.disc`) | ⚙ | `allOptions`, `M`; the term sheet as source when the title mentions the transition |

**Decoration (`uhDecorate`):**
- **Trigger:** a `MutationObserver` on `document.body` (child list, subtree), throttled with `requestAnimationFrame` and only when the switch is on.
- **For each part not yet marked:**
  - set `data-uhp` to the kind;
  - add the classes `uh-host uh-<kind>`;
  - insert a `<button class="uh-prov <kind>" data-uhpart="pN">` as the first child.
- **It runs again harmlessly:** marked parts are skipped, so its own changes don't loop.
- **A legend strip** goes first in `.wf-main` ("Under the hood · ✦ 2 drafted by the model · ⚙ 10 calculated · ▤ 1 published · Select a label…"), leaving out kinds with zero.

**Label styling:**
- **Outline:** `outline: 1.5px dashed` (so the layout doesn't shift), `outline-offset: 3px`.
- **Label:** absolutely positioned at `top:-12px; right:10px`. An absolutely positioned child of a grid doesn't take a grid cell, so it works on tile grids.
- **Colors:**
  - ✦ purple `#7c5cd6`, or `#b6a3f2` in dark mode;
  - ⚙ the theme's blue;
  - ▤ the theme's amber.

**Pitfall:** the legend uses the same `uh-prov` classes, with `static`. Select labels with `.uh-prov[data-uhpart]`, not `.uh-prov.ai`, or you'll click the legend.

## 11. Evals tab

**Two evals run in the page, through the same code as the answers:**

1. **Leak test with planted identifiers** ("Run on Dana's book").
   - **Setup:** for every household in `HH()`, temporarily replace `ctxOf` with a client-page context. Restore it, and `S.book` and `S.lastCtx`, in `finally`.
   - **Questions:** ask 5 panel questions ("How risky is the portfolio?", "What should I raise in the meeting?", "What are the tax opportunities?", "Why is the drift where it is?", "Tell me about <household>").
   - **For households with an Advisory opportunity,** also ask 6 workflow questions: compare the options; the tax impact; the risk shift; the cost; how long the transition takes; what counts toward the budget.
   - **Skip:** questions that set something (reminders, budgets, the guide).
   - **Count:** answers, identifier checks, leaks, answer-scan failures, stray tokens, tokens left on screen. Delete each trace after counting.
   - **Expected:** **no leaks in 191 answers over 25 households (1,855 identifier checks)**; answer scan clean; tokens in scope; names restored every time. About 0.4 seconds.
2. **Free-text detector**: 13 labeled messages, each with its expected types. Count caught, missed and false alarms.

| Message | Expected |
|---|---|
| Call Margaret Henderson at (555) 555-0142 about the gift | Person name, Phone |
| Her SSN is 912-34-5678, please update the file | SSN or tax ID |
| Send the proposal to owen.whitaker@example.com | Email |
| Move account 4X1-48213 into the CIO model | Account number |
| Paul was born 1958-04-12, check the RMD | Person name, Date of birth |
| They moved to 418 Linden Lane last spring | Street address |
| How risky is Kaplan right now? | Client name |
| What is the tax on the Lund Family transition at $250K? | Client name |
| Is a $500K budget too high for this client? | (none) |
| Compare AAPL and MSFT exposure across the book | (none) |
| Call Maggie about the trust before Friday | Person name |
| his social is nine one two three four five six seven eight | SSN or tax ID |
| Email from Jordan Blake (new prospect) about the referral | Person name |

**Expected:** **10 of 13 caught, 0 false alarms, "Below the release bar".** The three misses are on purpose: a nickname, a number written out in words, and a person not in the book. The page explains that patterns plus a name list miss these, and that production adds a trained name recognizer. **Don't "fix" the detector to pass**; the failure is the point.

**Release gates, described but not run:**
- answer scan and token scope, and name restoration (shows this answer's result);
- attack tests;
- accuracy with tokens;
- re-identification review (flags this answer's concentrated or insider households);
- log and vendor audit.

## 12. Styling summary

**Tokens:** uses the host's CSS custom properties (`--paper`, `--line`, `--brand`, `--brand-tint`, `--brand-ink`, `--blue`, `--blue-tint`, `--red`, `--red-tint`, `--amber`, `--amber-tint`, `--inset`, `--muted`, `--fg-2`, `--gain`, `--loss`, `--sh-1`, `--sh-3`), so light and dark come for free.

**Marks:**
- token marks: blue tint;
- removal marks: red tint;
- rule chips: removed (red), tokenized (blue), generalized and redacted (amber), allowed (brand green).

**Phone (≤700px):**
- the switch shows only the slider;
- the inspector is full width;
- two-column comparisons stack;
- the Rule column of the field table is hidden;
- labels shrink.

**Other:** inspector tabs scroll sideways inside their own bar (`scrollbar-width:none`), so the page never does.

## 13. Checks to run after rebuilding

| Check | Expected |
|---|---|
| Switch on, ask on Kaplan: "How risky is the portfolio? Call Rebecca at (617) 555-0142" | Strip: 3 services · 0 sources · 9/9 checks · 0 identifiers sent. Data tab: "Call PERSON_n at [PHONE_REMOVED]"; the tax ID crossed out; insider generalized |
| Workflow: Whitaker, Advisory move, step 2, "What if the budget is $500K?" | Services include POST /tax/transition-plan, with `tetPlan(CLIENT_n, 500000)` vs `whitaker, 500000`; sources include the term sheet |
| Workflow: "What counts toward the budget?" | Approved document search with a passage; source: the term sheet |
| Book view, "Bonds & CDs maturing" | The opening message has a strip; Data shows the first household named, with the others as tokens |
| Decision guide to a recommendation | The recommendation has a strip; services include decision guide scoring with the answers as compact JSON |
| Client list label | Client records (CRM), positions (25 households in one batched request), opportunity engine (each of 13 criteria), work queue |
| Client page labels | 1 drafted, 2 calculated, 2 published |
| Step 3 labels, after choosing the transition | 2 drafted, about 10 calculated |
| Evals | 191 answers, 0 leaks; detector 10 of 13 |
| Switch off | No strips, labels or legend; normal answers still work; the 28-step tour runs on desktop and phone |
| Light, dark, phone (390px) | No page errors; no sideways scrolling, in the inspector or on the page |

## 14. How it maps to production

| Prototype | Production (see `ask-atlas-production-sequence.md`) |
|---|---|
| Recorded service calls | MCP tool calls through the MCP gateway, logged with a trace ID |
| The request in the Prompt tab | What the agent sends to the approved model endpoint after the PII guard |
| Tokens and the name list | The PII guard in the runtime; the name list built from client records per advisor |
| Checks 5–8 | The gateway's and PII guard's checks, logged with each trace |
| ✦ drafted parts | Nightly batch drafts written to the Atlas gold tables, or redrafted on request |
| ⚙ calculated parts | The agent's action mode: deterministic, no model |
| ▤ published parts | The CRM record and the vector store of CIO publications |
| The trace in `UH.T` | The `traces` collection in MongoDB |
| The Evals tab | The release suite run before an agent version takes traffic |

## 15. Files

**In the zip:**
- `under-the-hood-rebuild-notes.md` (this file);
- `under-the-hood-screenshots.md` with `images/`;
- `src/`: `uh.js`, `uh2.js`, `uh.css` and `build.py`, the exact sources inserted into the console.

The built console is `atlas-console-book-view.html`, delivered separately.
