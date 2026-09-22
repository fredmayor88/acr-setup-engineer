# Workflow: refine a setup based on driving feedback (in-chat loop)

Refine a setup by working the **problem → tweak → test → feedback** cycle conversationally.
Each iteration proposes targeted, legal changes **in chat** and updates an in-chat **working
setup** — **nothing is written to Notion** while iterating, except the dated `Log` entry each
round of feedback leaves on the car (step 5). The source setup is never modified.
A single new `Setups` row (the session's final state) is created **only when the user explicitly
asks to save** — see step 7.

Read `notion-structure.md` (structure + schemas) and `setup-tuning-principles.md` (reasoning
base) before starting.

## Inputs
- **Working setup** — the setup being refined. It may be (a) a setup built, loaded, or already
  iterated **earlier in this thread** (use its current in-chat values), or (b) a **named saved
  setup** the user points at. If neither is clearly in scope, **ask what to start from** (step 1).
- **Feedback** — free-form description of what felt wrong or what to change, e.g. *"understeers
  on entry"*, *"too stiff on bumps"*, *"needs more mid-corner rotation"*, or even a direct
  request like *"soften the front ARB by one step"*.
- **New setup name** — only needed **at save time** (step 7). Defaults to `{source name} v2`
  (increment if v2 already exists, etc.) — the full name including the `vN` suffix must stay
  **≤15 chars** (the in-game limit); compact the base name first if the suffix would overflow it
  (per `SKILL.md` core rules).

## Procedure

### 1. Establish the working setup
Decide what the iteration starts from — **don't immediately write anything**:
- **One setup clearly in scope** (just built/loaded in this thread, or unambiguously named) → use
  its current in-chat values as the working setup and say which one. For a saved setup, load all
  value properties plus `Car`, `Location`, `Stage`, `Surface`, `Conditions` (may be blank), `Mode` (navigate
  `ACR Setup Engineer → Setups`; stay within that scope — no workspace-wide searches).
- **Multiple plausible matches** → list them (Name / Car / Stage / Date) and ask the user to pick.
- **Nothing in scope** (the user described a problem but nothing has been built or loaded yet) →
  **ask what to start from**: which saved setup to load, or whether to run `build-setup.md` — which
  will itself start from the game's captured default for this car/stage, or recommend driving it
  (`build-setup.md` steps 4–6). Don't guess a base.

### 2. Load constraints + the car's identity facts
> **Load steps 2–4 as one batched read** (`SKILL.md` → *Read efficiently*): once the structure is
> resolved, issue the independent reads together (parallel tool calls) and run the REST queries in
> one code-execution block, fetching the car's `Catalog` page (identity facts, this step), **the
> car's `Parameters` page for a screenshot car**, and its
> `Guidelines` and `Log` pages (step 3) once each, in the same batch. Skip any read whose data is already in the thread.

**Load the car's catalog per [catalog-read.md](catalog-read.md)** — a bundled file for a template
car, the car's `Parameters` page (fetched in this same batch) for a screenshot car; one
`load_catalog.py` call either way, `--surface {Surface}` when the workflow resolves a surface.
Here the surface is the working setup's, so pass it. Read the car's identity
facts from the car's `Catalog` page — `Drivetrain` (FWD/RWD/AWD), `Engine layout`, `Weight bias`, `Weight`
— and feed them into the balance reasoning (same facts a build loads; not drivetrain alone). If a
field is blank, infer the bias from drivetrain + engine layout, or proceed drivetrain-only.
**Resolve each parameter's legal range for the working setup's `Surface`** — use the
surface-specific row if the parameter has one; for `Snow`, fall back to a `Gravel` row before the
baseline (see [notion-rest-read.md](notion-rest-read.md); `load_catalog.py --surface {Surface}`
does it for you). If the user **explicitly re-targets the
surface** ("tweak this for gravel"), use that surface instead — it drives resolution and (at save)
the new row's `Surface`. Load this once and reuse it across iterations.
If a value the user reports for a **template car** falls outside the template, that's trigger (b)
of `onboard-car.md` → *When the template may be stale*: say the one line and carry on.

### 3. Load guideline layers
Same precedence chain as `build-setup.md` (lowest → highest):
1. **Base** — `setup-tuning-principles.md`.
2. **Bundled car troubleshooting** — check the `car-troubleshooting/` folder for a file whose name
   matches this car (same match rule as a bundled template — `onboard-car.md` step 1 →
   *Matching a car name* — e.g. `car-troubleshooting/lancia-037-evoluzione-2-1984.md`). **If one exists, read
   it and apply its symptom→fix entries — they override the base principles** for the symptoms they
   name. This is the main path for handling problems like "the brakes lock as soon as I touch them".
   If no file matches, skip this layer.
3. **Global user guidelines** — Notion `Tuning guidelines` page under `ACR Setup Engineer`.
4. **Surface section** — the global guidelines' "Per surface" subsection matching the setup's
   `Surface` (not a separate page).
5. **Per-car guidelines** — the car's `Guidelines` page.
The working setup's own **driving intent/goal** (from its page body, plus the user's feedback this
round) is the most specific layer. Apply only lines tagged `[All]` **or the car's drivetrain**.
**More specific is the default lean**, not an auto-resolution: if an authored layer materially
contradicts the stated intent or feedback, **ask the user** which to follow before proposing the
change. Never read content outside `ACR Setup Engineer`.

**Also fetch the car's `Log` page in this same batch — but it is not a guideline layer.** Resolve
it by name: `Log`, falling back to a legacy `Feedback` page (`notion-structure.md` → *Resolving
the page (`Log`, and the legacy `Feedback` name)*). **A read never renames anything** — if you
read the legacy page, just say so; the rename happens on a write or a refresh. If neither page
exists, **skip it silently and create nothing**. Read the whole page — the skill's dated entries
**and** the user's own notes — as **context and evidence** about how this driver describes this
car; past sessions on the same car are often the fastest route to what's wrong now. It does
**not** enter the precedence chain above: `Guidelines` outranks it. When a user note on `Log` is
really a **standing tuning rule** for this car rather than a one-off observation, **offer once**
to move it to `Guidelines`, written exactly as they'd paste it — the user pastes it, the skill
never writes `Guidelines`.

### 4. Load stage facts (if the working setup references one)
Fetch the `{Stage}` / `{Location}` page from the catalogue (`notion-structure.md`): surface, key
corners/speeds, character. These are **objective facts, not a guideline** — the driver's goal for
this setup comes from its page body and the user's feedback, not the stage page.

### 5. Refinement iteration (repeat for each round of feedback)
Each time the user gives feedback, run one round — **all in chat, no Notion writes**:

- **If the feedback is vague, contradictory, or the user says they can't tell what's wrong** ("it
  felt off", "I dunno, it was weird", "it just isn't fast"), **run
  [driving-feedback-interview.md](driving-feedback-interview.md) before proposing anything.** Most
  drivers feel the problem correctly but don't have the words for it, and a wrong diagnosis sends
  the whole round in the wrong direction. Use its opening triage and symptom families in small
  batches, plain language, defining each term as it comes up; accept "not sure" and move on. A
  clear, specific complaint ("soften the front ARB by one step", "understeers on entry") needs no
  interview — act on it directly.
  **Every round writes one `Log` entry as it ends** — one dated collapsed toggle
  (`Driving feedback — {date}`) at the top of the car's `Log` page, whether or not an interview
  ran. **If an interview ran**, that entry is the interview's record, per
  [driving-feedback-interview.md](driving-feedback-interview.md) → *Recording the outcome* — one
  block, not two. **If not**, the entry holds the user's feedback **in their own words**, which
  setup it was about (the source setup's name, or *"working setup, round N"* after the first
  round), and the changes proposed in answer (`parameter: old → new`). Page rules as for the
  interview's entry: resolve `Log` by name first, add this one block directly below the
  maintenance line, touch nothing else. This
  is **the single exception** to this workflow's "no Notion writes while iterating" rule: it is
  add-only history of what the driver said, it belongs to the car rather than to any setup, and a
  session that never saves a row would otherwise lose it. It is **not** permission to write
  anything else — no setup row, no `Notes`, no row toggle, and nothing on `Guidelines`. The
  row-level records wait for step 7.
- Map the verbal feedback to specific parameters using the tuning principles, guidelines, and
  stage facts. For each parameter to change:
  - State the **current value** (from the working setup).
  - Reason about the **direction and magnitude**, citing the relevant guideline or the user's
    feedback directly.
  - Propose a **new legal value**: a member of `Discrete steps` (if filled) or within `Min..Max`.
    Never go outside the catalog.
  - Call out any **secondary parameters** that should move in concert — e.g. adjusting one ARB
    often implies revisiting the other; softening springs may warrant retuning slow-bump dampers.
    Propose those too (they appear in the same change table).
- **Make the smallest targeted change set** that addresses the feedback. Don't re-optimise
  parameters unrelated to the complaint — untouched parameters carry over verbatim.
- **Fix the major thing first.** When the feedback implicates more than one area, order the change
  set by the **fix-order ladder** ([driving-feedback-interview.md](driving-feedback-interview.md) →
  *Fix-order ladder*): tyre type → differential (preload → ramps → plates) → ride height/springs →
  ARBs → dampers → alignment → brake bias, with gearing as a parallel track. Don't fine-tune
  alignment while the differential is wrong — it hides cause and effect. **What the user actually
  asks for outranks the ladder.** **Tyre pressure sits outside it**: leave it alone unless a symptom
  points directly at it (ACR's pressure model isn't physically sensible — see
  `setup-tuning-principles.md` → *Tyre pressure*).
- Present a compact **before/after change table** of only the parameters that change:

  | Parameter | Current | Proposed | Reason |
  |---|---|---|---|
  | ARB Front | 5 | 3 | Less front stiffness allows more entry rotation [RWD guideline] |
  | ARB Rear | 3 | 4 | Slight rear stiffness to balance the front change |

  The user may correct any proposed value here — re-validate any user-supplied value against the
  catalog before accepting it.
- **Toe changes — the game's sign is inverted** (`SKILL.md` → *ACR's toe sign is inverted*).
  Decide the direction physically (more front toe-out to sharpen turn-in, more rear toe-in to
  steady the exit), then express it as the **setup-screen number**: toe-out ⇒ **positive**, toe-in
  ⇒ **negative**; more toe-out = number **up**, more toe-in = number **down**. Read the working
  setup's current toe the same way (positive = toe-out) and never convert a stored value. Whenever
  a round's change table contains a toe row, append the one-line warning under it: *"Note: ACR
  shows toe with an **inverted sign** — the proposed `{value}` is toe-**{out/in}**. Enter it
  exactly as given."*
- **Apply the changes to the in-chat working setup** — the proposed values become the new current
  values, so the **next** round's "Current" column reflects everything so far. Then tell the user
  to **test in-game and report back**, and iterate. **Do not write to Notion.**

### 6. Gentle nudge to save
When the user signals satisfaction ("that feels great", "perfect now", "I'm happy with this"),
**remind them once** that they can ask you to save the finished setup to Notion. Don't repeat the
reminder every turn.

### 7. Save — only on the user's explicit request
When the user asks to save (and not before):
- **Validate** every value in the working setup against the catalog for the build surface
  (surface-resolved range — `Snow` falls back to `Gravel`, then baseline): discrete picks must be
  in `Discrete steps`; continuous picks within `Min..Max`. Fix any violation before writing.
- **Completeness:** confirm the row about to be saved carries an explicit value for **every**
  parameter the car has (except `FFB Multiplier`) — there is no "use the default" / leave-it-
  blank option (`SKILL.md` → *Core rules*). Since saving copies the source row's values
  (below), if the **source** row was itself incomplete, derive and fill the missing parameters
  now (as in `build-setup.md` → *Choose values*) rather than carrying the blank forward.
- Confirm/derive the **new setup name** (default `{source} v2`, increment if taken) — **≤15
  chars** including the suffix; compact the base name first if needed.
- **Legacy template car? Check the `Setups` value columns first.** If this car is a template car
  whose `Catalog` page carried **no `Catalog source:` line** (step 2), its columns were created
  by an older skill version and the current template may name columns the `Setups` DB doesn't
  have. Before writing the row, run the check in `notion-structure.md` → *Legacy template car —
  check the `Setups` columns before the first write*: add the missing columns in one call, never
  rename or remove anything, and say the one line it gives. You already hold both sides of the
  comparison, so this adds no read.
- Create **one new row** in `Setups` DB (never modify or delete the source row or its page):
  - Copy every value property from the source; overwrite the parameters changed across the session
    with the final working values.
  - Set: `Name`, `Car`, `Location` (if the source/feedback names one), `Stage` (likewise),
    `Surface`, `Conditions` (inherit from the source row; update it if the user re-targeted the
    conditions this session — **optional**, leave blank if the source's was blank),
    `Source = generated`, `Mode` (inherit source mode, default `learn`), `Date`
    (current date/time — per `notion-structure.md` → `Date`: run the Python one-liner, don't guess),
    **`Model`** (just your current model name + version, e.g. `Opus 4.8`; do
    **not** copy from the source; this records the model that ran *this* refinement), and
    **`Skill version`** (per `SKILL.md` → *Skill version* — do not copy from the source; this
    records the skill version that ran *this* refinement). Leave
    **`Learn from this` unchecked** — the user opts in after vetting.
- **Apply the column order — MANDATORY, never skip (even on a quick / low-effort run); the save is
  not done until you've done it** (`notion-structure.md` → *Applying the order*), **after the row is
  written**. Get the `SHOW` list from the bundled script — **never build or merge one by hand**
  — by running the form that *Applying the order* gives, and set `SHOW`
  (`notion-update-view`) to its output on the main `Setups` table view (one `--from-template` per onboarded
  car), this car's linked view (this car's file only, which hides blanks in the same step), and
  — if a stage/location is set — its `{Stage}` / `{Location}` linked view (one `--from-template`
  per onboarded car, no per-car filtering). The script lists `Name`,
  value columns by `Order`, then the full meta columns (including `Model` and `Skill version`).
  Idempotent view update — the row write above stays append-only.
- **Add the new row to the car's `Setup index`** — `notion-structure.md` →
  *Adding a line to `Setup index`*: `scripts/setups_list.py --line` with the new row's `Name`,
  page URL, `Source = generated`, `Stage`, `Surface`, `Conditions`, `Date`; insert it under the
  heading on the car's `Setups` page. On every plan.
- **Ensure the stage facts page exists in the catalogue** (per `notion-structure.md` → *Locations &
  stages catalogue*) if a stage/location is set and didn't already exist; create its filtered
  `Setups[Stage=this]` linked view with `notion-create-view` (never a page-markdown placeholder).
- **Page body** (two toggles, mobile-readable — no wide tables; plus a visible **driving intent**
  bullet above them, since intent has no DB column):
  1. Toggle **"Changes from {source name}"** — each parameter changed over the session: old value →
     new value + one-line rationale.
  Plus, **if an interview ran this session** (step 5), that interview's **row-level records** on
  this new row, per [driving-feedback-interview.md](driving-feedback-interview.md) → *Recording
  the outcome*: the **one-line dated verdict in `Notes`**, and the full record in a dated
  collapsed **"Driving feedback — {date}"** toggle in this page body. (Its car-level `Log` entry
  was already written when the interview ended — don't write it again.)
  Plus, when the car has toe parameters, the same **visible** toe-sign warning line a build writes
  (`build-setup.md` step 11): positive = toe-out, negative = toe-in, enter exactly as stored.
  2. Toggle **"Full justification"** — per-section reasoning for every parameter (same format as
     `build-setup`: grouped by section and ordered by each parameter's `Order`; short headings +
     bullets), covering changed and unchanged parameters so the reasoning is self-contained.

### 8. Report
In chat: summarise what changed over the session and why, link the new Notion row, and remind the
user to tick `Learn from this` and set a `Rating` after driving if the result is an improvement.

If the working setup includes **both** a `Brake Discs` and a `Brake Calipers` selection (front
and/or rear), add this one-line caveat: *"Note: the in-game **calipers available depend on the
selected brake disc**, so this exact disc+caliper combination may not be selectable. If so, keep
the recommended calipers and pick the closest available disc size — the caliper carries the bigger
braking effect."* Omit it when the car has no brake disc/caliper params.

## Rules
- **Iterate in chat — no Notion writes per round.** Refinement rounds (step 5) update only the
  in-chat working setup; nothing is written to Notion until the user explicitly asks to save.
  **One named exception:** every round writes one dated entry on the car's **`Log`** page as it ends —
  the interview's record if one ran, otherwise the user's feedback and the changes proposed (step
  5). That one block per round is the whole exception — no setup row, no `Notes`, no row toggle,
  nothing on `Guidelines`, and nothing else at any other moment.
- **Save only on explicit request — one final row.** The whole session culminates in a single new
  `Setups` row capturing the final state (step 7), not one row per tweak.
- **Gentle single nudge** — remind the user once they can save when they're happy; don't nag.
- **Append-only** — the source setup row and page are never touched; only a new row is created.
- **Legal by construction** — discrete picks must be in `Discrete steps`; continuous picks within
  `Min..Max`. Validate every value (including user-corrected ones) before saving.
- **Minimum change set** — don't re-tune uninvolved parameters; only change what the feedback
  requires (plus necessary secondary parameters for coherence).
- **Interview on vague feedback** — when the user can't pin down what's wrong, run
  `driving-feedback-interview.md` before proposing values; a wrong diagnosis wastes the whole round.
- **Major before fine** — order changes by the fix-order ladder; the user's own words override it.
- **Toe sign is inverted** — toe-out ⇒ positive, toe-in ⇒ negative; read stored toe the same way,
  never convert it, and warn the user whenever a toe value is proposed or saved.
- **Cite the reason** — every changed parameter must reference the feedback phrase, guideline tag,
  or stage fact driving it.
- **Stay within `ACR Setup Engineer` scope** — same name-resolution rules as every other workflow.
