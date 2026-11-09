# Under the hood: screenshots

**What it is:** a switch in the Atlas console's top bar that shows how each part of the screen and each Ask Atlas answer would work in production:
- what was retrieved;
- what the model would see;
- which services, rules and documents were used;
- which guardrails and evals apply.

**Prototype:** no model is called. The checks marked "ran on this answer" really run in the page.

**How to read the screenshots:**
- **Sample data:** the households are made up, and so are the identifiers: 555 phone numbers, example.com emails, tax IDs starting with 9.
- **Rebuild details:** in `under-the-hood-rebuild-notes.md`.

---

## 1. The switch

**Off (the default):** the console looks and works as before.

![Switch off](images/uth-01-switch-off.jpg)

**On:** a legend appears at the top of the screen, and each part gets a dashed outline and a label.
- **✦ Drafted by the model:** purple.
- **⚙ Calculated · no model:** blue.
- **▤ Published · no model:** amber.

Atlas answers also get a strip. On Book view, the "Pick up where you left off" cards and the opportunity tiles are calculated, and the opening message in the panel has its strip ("6 services · 1 source · 9/9 checks · 0 identifiers sent").

![Book view with labels](images/uth-02-book-labels.jpg)

## 2. Labels on the screens

**Client page:**
- **▤ Published:** the client record (header) and the CIO view, quoted from the published document.
- **✦ Drafted by the model:** the portfolio summary.
- **⚙ Calculated:** the key figures and the opportunities.

The legend counts them: 1 drafted, 2 calculated, 2 published.

![Client page labels](images/uth-04-client-labels.jpg)

**A calculated part** (the key figures) says plainly that no model is involved, and shows the three steps and the services behind it.

![Calculated part](images/uth-07-calculated-flow.jpg)

**The client list** lists the real calls behind it:
- client records (CRM);
- positions for all 25 households in one batched request;
- the opportunity engine checking each of the 13 criteria;
- the work queue.

Sorting and filtering happen on the page.

![Client list services](images/uth-03-client-list-services.jpg)

**A published part** (the CIO view) cites the CIO House View and says only the current version is served.

![Published part](images/uth-08-published-cio.jpg)

**A drafted part** (the portfolio summary) opens the full inspector on its Data tab. Its Prompt tab shows the request, with the household as a token and no instructions to calculate anything.

![Drafted part: data](images/uth-05-drafted-data.jpg)

![Drafted part: request](images/uth-06-drafted-prompt.jpg)

**Step 3, the proposal:** two drafted parts (the proposal summary and "Why we are recommending this"). Everything else is calculated.

![Proposal labels](images/uth-16-proposal-labels.jpg)

## 3. An Ask Atlas answer, tab by tab

The question, on the Kaplan page, deliberately includes a name and a phone number: "How risky is the portfolio? Call Rebecca at (617) 555-0142". The answer's strip reads "3 services · 0 sources · 9/9 checks · 0 identifiers sent".

![Answer with its strip](images/uth-09-chat-strip.jpg)

**Flow:** seven steps from the question to the screen, with this answer's counts. The gateway step and the check step are green because the leak check and every check passed.

![Flow](images/uth-10-flow.jpg)

**Data:** the question as typed vs as sent ("Call PERSON_5 at [PHONE_REMOVED]"). Then what the screen published, and every client field as retrieved vs sent:
- names tokenized;
- tax ID, address, phone and email removed;
- date of birth generalized to an age band;
- account numbers tokenized;
- the insider employer generalized to "insider: yes".

At the bottom, a warning that a large single position can identify a client even without a name.

![Data](images/uth-11-data.jpg)

**Prompt:** the request as JSON, with tokens in blue and removals in red. Then the model's answer in tokens next to the answer shown, and the token table, which stays in the page.

![Prompt](images/uth-12-prompt.jpg)

**Guardrails:** ten checks, each marked "ran on this answer" or "policy". The leak check reports "0 of 11 identifiers from 1 household appear in what would be sent".

![Guardrails](images/uth-13-guardrails.jpg)

**Evals:** two run in the page.
- **Leak test with planted identifiers:** no leaks in 191 answers over 25 households (1,855 identifier checks).
- **Free-text detector:** 10 of 13 caught, so it is below the release bar on purpose. It misses a nickname, a number written out in words and a person not in the book, which shows why production needs a trained name recognizer.

The other evals are release gates for production.

![Evals](images/uth-14-evals.jpg)

## 4. In the workflow

"What if the budget is $500K?" on Whitaker's Advisory move, step 2, Services and rules tab:
- **The model's call:** `tetPlan(CLIENT_12, 500000)`, next to what the service receives (`whitaker, 500000`).
- **Rules applied:** the transition model's yearly budget, losses first, and bonds outside the budget.
- **Sources:** the conversion rules, the program brochure and the tax-efficient transition term sheet.

![Workflow services and rules](images/uth-15-workflow-services.jpg)

## 5. Switch off, dark mode and phone

**Switching off** removes every label, strip and the legend.

![Switched off again](images/uth-17-switch-off-again.jpg)

**Dark mode:** the labels use lighter colors.

![Dark](images/uth-18-dark.jpg)

**Phone:** the switch shows only its slider, the labels shrink, and the inspector fills the screen. The field table drops its Rule column, and nothing scrolls sideways at 390px. Here the question includes a phone number and an account number, and both are removed.

![Phone labels](images/uth-19-phone-labels.jpg)

![Phone inspector](images/uth-20-phone-data.jpg)
