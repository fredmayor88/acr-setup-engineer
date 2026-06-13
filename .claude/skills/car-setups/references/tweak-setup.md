# Workflow: tweak a setup based on driving feedback

Refine an existing setup in the Notion `Setups` database by applying targeted changes driven
by verbal driving feedback. Produces a **new setup row** derived from the source — the source
is never modified. History is fully preserved.

Read `notion-structure.md` (structure + schemas) and `setup-tuning-principles.md` (reasoning
base) before starting.

## Inputs
- **Source setup name** (e.g. `alsace gpt1`). The user may also provide **Car** and/or
  **Stage** to disambiguate. Game defaults to `ACR`.
- **Feedback** — free-form description of what felt wrong or what to change, e.g. *"understeers
  on entry"*, *"too stiff on bumps"*, *"needs more mid-corner rotation"*, or even a direct
  request like *"soften the front ARB by one step"*.
- **New setup name** — optional. Defaults to `{source name} v2` (increment if v2 already
  exists, etc.).

## Procedure

### 1. Identify the source setup
Navigate to `Car setups → {Game} → Setups` DB and find the row matching the given name. Stay
within `Car setups` scope — no workspace-wide Notion searches.

- **Unique match:** Load all value properties, plus `Car`, `Stage`, `Surface`, `Mode`.
- **Multiple matches:** List them (Name / Car / Stage / Date) and ask the user to pick one.
- **No match:** Tell the user and stop.

### 2. Load constraints + drivetrain
Fetch the car's `Parameters` rows (within `Car setups → {Game} → Parameters`):
`Adjustment`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`, `Surface`. Read `Drivetrain` (FWD/RWD/AWD)
from the `{Car}` page attribute. **Resolve each parameter's legal range for the source setup's
`Surface`** (loaded in step 1) — use the surface-specific row if the parameter has one; for
`Snow`, fall back to a `Gravel` row before the baseline (see
[notion-rest-read.md](notion-rest-read.md)). If the user **explicitly re-targets the surface**
("tweak this for gravel"), use that surface instead — it drives resolution and the new row's
`Surface`.

### 3. Load guideline layers
Same precedence chain as `build-setup.md` (lowest → highest):
1. **Base** — `setup-tuning-principles.md`.
2. **Global user guidelines** — Notion `Tuning guidelines` page under `Car setups / {Game}`.
3. **Surface section** matching the setup's `Surface`.
4. **Per-car guidelines** — the `{Car}` page's "Guidelines" section.
Apply only lines tagged `[All]` **or the car's drivetrain**. Never read content outside
`Car setups`.

### 4. Load stage context
Fetch the `{stage}` page under the car: surface description, key corners/speeds, driver goal.
This is the most specific context and takes precedence on any point it addresses directly.

### 5. Interpret feedback → parameter changes
Map the verbal feedback to specific parameters using the tuning principles, guidelines, and
stage context. For each parameter to change:

- State the **current value**.
- Reason about the **direction and magnitude** of the change, citing the relevant guideline or
  the user's feedback directly.
- Propose a **new legal value**: must be a member of `Discrete steps` (if filled) or within
  `Min..Max`. Never go outside the catalog.
- Call out any **secondary parameters** that should move in concert — e.g. adjusting one ARB
  often implies revisiting the other; softening springs may warrant retuning slow-bump dampers.
  Propose those secondary changes too (they appear in the same diff).

**Make the smallest targeted change set** that addresses the feedback. Do not re-optimise
parameters unrelated to the complaint — untouched parameters carry over verbatim from the
source.

### 6. Show the diff and confirm
Present a compact table of only the parameters that change:

| Parameter | Current | Proposed | Reason |
|---|---|---|---|
| ARB Front | 5 | 3 | Less front stiffness allows more entry rotation [RWD guideline] |
| ARB Rear | 3 | 4 | Slight rear stiffness to balance the front change |

Then ask: *"Apply these changes and create `{new name}`?"*

Wait for the user's confirmation before writing anything to Notion. The user may also correct
a proposed value at this point — re-validate any user-supplied value against the catalog before
accepting it.

### 7. Write to Notion — new row only
Never modify the source setup row or its page body.

- Create a **new row** in `Setups` DB:
  - Copy every value property from the source setup.
  - Overwrite only the changed parameters with the confirmed new values.
  - Set: `Name`, `Car`, `Stage`, `Surface` (all inherited from source), `Source = generated`,
    `Mode` (inherit source mode, default `learn`), `Date` = today.
  - Leave **`Learn from this` unchecked** — the user opts in after vetting.
- **Apply the column order** (`notion-structure.md` → *Applying the order*): set the `SHOW` on the
  main `Setups` table view and on this setup's stage/per-car linked view to the meta columns + value
  columns by each parameter's `Order` (linked view hides blanks). Idempotent view update — the row
  write above stays append-only.
- **Page body** (two toggles, mobile-readable — no wide tables):
  1. Toggle **"Changes from {source name}"** — list each changed parameter: old value → new
     value + one-line rationale. This is the quick-reference for what was actually different.
  2. Toggle **"Full justification"** — per-section reasoning for every parameter (same format
     as `build-setup`: grouped by section and ordered by each parameter's `Order`, short headings +
     bullets). This covers both changed and unchanged parameters so the full reasoning is
     self-contained.

### 8. Report
In chat: summarise what changed and why, link the new Notion row, and remind the user to tick
`Learn from this` after driving if the tweak is an improvement.

## Rules
- **Append-only** — source setup row and page are never touched; only a new row is created.
- **Legal by construction** — discrete picks must be in `Discrete steps`; continuous picks
  within `Min..Max`. Validate every value (including user-corrected ones) before writing.
- **Minimum change set** — don't re-tune uninvolved parameters; only change what the feedback
  requires (plus necessary secondary parameters for coherence).
- **Cite the reason** — every changed parameter must reference the feedback phrase, guideline
  tag, or stage requirement driving it.
- **Stay within `Car setups` scope** — same name-resolution rules as every other workflow.
