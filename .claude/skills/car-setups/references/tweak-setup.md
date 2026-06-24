# Workflow: refine a setup based on driving feedback (in-chat loop)

Refine a setup by working the **problem → tweak → test → feedback** cycle conversationally.
Each iteration proposes targeted, legal changes **in chat** and updates an in-chat **working
setup** — **nothing is written to Notion** while iterating. The source setup is never modified.
A single new `Setups` row (the session's final state) is created **only when the user explicitly
asks to save** — see step 7.

Read `notion-structure.md` (structure + schemas) and `setup-tuning-principles.md` (reasoning
base) before starting.

## Inputs
- **Working setup** — the setup being refined. It may be (a) a setup built, loaded, or already
  iterated **earlier in this thread** (use its current in-chat values), or (b) a **named saved
  setup** the user points at. If neither is clearly in scope, **ask what to start from** (step 1).
  Game defaults to `ACR`.
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
  value properties plus `Car`, `Location`, `Stage`, `Surface`, `Mode` (navigate `Car setups →
  {Game} → Setups`; stay within `Car setups` scope — no workspace-wide searches).
- **Multiple plausible matches** → list them (Name / Car / Stage / Date) and ask the user to pick.
- **Nothing in scope** (the user described a problem but nothing has been built or loaded yet) →
  **ask what to start from**: which saved setup to load, or whether to build a baseline first
  (`build-setup.md`). Don't guess a base.

### 2. Load constraints + the car's identity facts
Fetch the car's `Parameters` rows (within `Car setups → {Game} → Parameters`):
`Adjustment`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`, `Surface`. Read the car's identity
facts from the `{Car}` page — `Drivetrain` (FWD/RWD/AWD), `Engine layout`, `Weight bias`, `Weight`
— and feed them into the balance reasoning (same facts a build loads; not drivetrain alone). If a
field is blank, infer the bias from drivetrain + engine layout, or proceed drivetrain-only.
**Resolve each parameter's legal range for the working setup's `Surface`** — use the
surface-specific row if the parameter has one; for `Snow`, fall back to a `Gravel` row before the
baseline (see [notion-rest-read.md](notion-rest-read.md)). If the user **explicitly re-targets the
surface** ("tweak this for gravel"), use that surface instead — it drives resolution and (at save)
the new row's `Surface`. Load this once and reuse it across iterations.

### 3. Load guideline layers
Same precedence chain as `build-setup.md` (lowest → highest):
1. **Base** — `setup-tuning-principles.md`.
2. **Global user guidelines** — Notion `Tuning guidelines` page under `Car setups / {Game}`.
3. **Surface section** — the global guidelines' "Per surface" subsection matching the setup's
   `Surface` (not a separate page).
4. **Per-car guidelines** — the `{Car}` page's "Guidelines" section.
The working setup's own **driving intent/goal** (from its page body, plus the user's feedback this
round) is the most specific layer. Apply only lines tagged `[All]` **or the car's drivetrain**.
**More specific is the default lean**, not an auto-resolution: if an authored layer materially
contradicts the stated intent or feedback, **ask the user** which to follow before proposing the
change. Never read content outside `Car setups`.

### 4. Load stage facts (if the working setup references one)
Fetch the `{Stage}` / `{Location}` page from the catalogue (`notion-structure.md`): surface, key
corners/speeds, character. These are **objective facts, not a guideline** — the driver's goal for
this setup comes from its page body and the user's feedback, not the stage page.

### 5. Refinement iteration (repeat for each round of feedback)
Each time the user gives feedback, run one round — **all in chat, no Notion writes**:

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
- Present a compact **before/after change table** of only the parameters that change:

  | Parameter | Current | Proposed | Reason |
  |---|---|---|---|
  | ARB Front | 5 | 3 | Less front stiffness allows more entry rotation [RWD guideline] |
  | ARB Rear | 3 | 4 | Slight rear stiffness to balance the front change |

  The user may correct any proposed value here — re-validate any user-supplied value against the
  catalog before accepting it.
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
- Create **one new row** in `Setups` DB (never modify or delete the source row or its page):
  - Copy every value property from the source; overwrite the parameters changed across the session
    with the final working values.
  - Set: `Name`, `Car`, `Location` (if the source/feedback names one), `Stage` (likewise),
    `Surface`, `Source = generated`, `Mode` (inherit source mode, default `learn`), `Date` = today,
    **`Model/effort`** (your current model + `/` + effort, e.g. `Sonnet 4.6/normal` — do
    **not** copy from the source; this records the model that ran *this* refinement), and
    **`Skill version`** (per `SKILL.md` → *Skill version* — do not copy from the source; this
    records the skill version that ran *this* refinement). Leave
    **`Learn from this` unchecked** — the user opts in after vetting.
- **Apply the column order** (`notion-structure.md` → *Applying the order*): set the `SHOW` on the
  main `Setups` table view, on this car's linked view, and — if a stage/location is set — on its
  `{Stage}` / `{Location}` linked view, to **`Name`, then value columns** by each parameter's `Order`
  (per-car view hides blanks; stage/location views show all value columns, no per-car filtering),
  **then the full remaining meta columns (including `Model/effort` and `Skill version`)**.
  Idempotent view update — the row write above stays append-only.
- **Ensure the stage facts page exists in the catalogue** (per `notion-structure.md` → *Locations &
  stages catalogue*) if a stage/location is set and didn't already exist; create its filtered
  `Setups[Stage=this]` linked view with `notion-create-view` (never a page-markdown placeholder).
- **Page body** (two toggles, mobile-readable — no wide tables; plus a visible **driving intent**
  bullet above them, since intent has no DB column):
  1. Toggle **"Changes from {source name}"** — each parameter changed over the session: old value →
     new value + one-line rationale.
  2. Toggle **"Full justification"** — per-section reasoning for every parameter (same format as
     `build-setup`: grouped by section and ordered by each parameter's `Order`; short headings +
     bullets), covering changed and unchanged parameters so the reasoning is self-contained.

### 8. Report
In chat: summarise what changed over the session and why, link the new Notion row, and remind the
user to tick `Learn from this` and set a `Rating` after driving if the result is an improvement.

## Rules
- **Iterate in chat — no Notion writes per round.** Refinement rounds (step 5) update only the
  in-chat working setup; nothing is written to Notion until the user explicitly asks to save.
- **Save only on explicit request — one final row.** The whole session culminates in a single new
  `Setups` row capturing the final state (step 7), not one row per tweak.
- **Gentle single nudge** — remind the user once they can save when they're happy; don't nag.
- **Append-only** — the source setup row and page are never touched; only a new row is created.
- **Legal by construction** — discrete picks must be in `Discrete steps`; continuous picks within
  `Min..Max`. Validate every value (including user-corrected ones) before saving.
- **Minimum change set** — don't re-tune uninvolved parameters; only change what the feedback
  requires (plus necessary secondary parameters for coherence).
- **Cite the reason** — every changed parameter must reference the feedback phrase, guideline tag,
  or stage fact driving it.
- **Stay within `Car setups` scope** — same name-resolution rules as every other workflow.
