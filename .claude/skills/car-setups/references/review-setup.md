# Workflow: review an existing setup

Critique a setup that already exists in the user's Notion `Setups` database — checking it for
constraint violations, guideline alignment, and internal consistency — then print the review in
chat and append a timestamped AI Review section to the setup's Notion page.

Read `notion-structure.md` (structure + schemas) and `setup-tuning-principles.md` (reasoning
base) before starting.

## Inputs
- **Setup name** (e.g. `alsace gpt1`). The user can also provide **Car** and/or **Stage** to
  narrow disambiguation. Game defaults to `ACR`; ask only if the user has setups under multiple
  games and it's unclear which one.

## Procedure

### 1. Identify the setup
Navigate to `Car setups → {Game} → Setups` DB and find the row matching the given name. Stay
within `Car setups` scope — do not issue workspace-wide Notion searches.

- **Unique match:** Load all value properties, plus `Car`, `Stage`, `Surface`, `Mode`, `Notes`,
  `Rating` (a **1–5 Select**, higher = better; blank = unrated).
- **Multiple matches:** List them (Name / Car / Stage / Date) and ask the user to pick one.
- **No match:** Tell the user and stop.

If the loaded row has **no parameter values filled** (all value columns are blank — e.g. an
imported setup with only metadata and no individual parameter values entered), say so and stop.
There is nothing to review without values.

### 2. Load constraints + drivetrain
Fetch the car's `Parameters` rows **via [notion-rest-read.md](notion-rest-read.md)** (stay within
`Car setups → {Game} → Parameters`): `Adjustment`, `Min`, `Max`, `Unit`, `Discrete steps`,
`Order`, `Surface`. Also read the `Drivetrain` (FWD/RWD/AWD) from the `{Car}` page attribute.
When the review lists several parameters together, present them in `Order` sequence
(`notion-structure.md` → *Setups column order*). This workflow is read-only — it never reorders
Notion columns. **Resolve
each parameter's legal range for the setup's `Surface`** (loaded in step 1) — the surface-specific
row if the parameter has one; for `Snow`, fall back to a `Gravel` row before the baseline (see
[notion-rest-read.md](notion-rest-read.md)).

### 3. Load guideline layers
Same precedence chain as `build-setup.md` (lowest → highest priority):
1. **Base** — `setup-tuning-principles.md`.
2. **Global user guidelines** — Notion `Tuning guidelines` page under `Car setups / {Game}`.
3. **Surface section** of those guidelines matching the setup's `Surface`.
4. **Per-car guidelines** — the `{Car}` page's "Guidelines" section.
Apply only lines tagged `[All]` **or the car's drivetrain**. Never read content outside
`Car setups`.

### 4. Load stage context
Fetch the `{stage}` page under the car's setups section: surface description, key
corners/speeds, what the driver was aiming for. This is the most specific context and takes
precedence over general guidelines on any point it speaks to directly.

### 5. Review the setup
Evaluate across three dimensions:

**a. Constraint validation**
For every parameter that has a value in the setup row, check against its **surface-resolved**
range (the row for the setup's `Surface`; `Snow` falls back to `Gravel`, then baseline — step 2):
- If that row has `Discrete steps` filled → the value must be exactly one of those steps.
- Otherwise → the value must be within `Min..Max` (inclusive).
Any violation is a **hard error** — list every one found; do not suppress or soften them.

**b. Guideline alignment**
For each filled parameter, judge whether the value is consistent with the drivetrain-filtered
guidelines for this surface and stage. Classify each notable parameter as:
- **Well-supported** — the choice directly follows a guideline principle.
- **Neutral** — within a reasonable range; no strong guideline signal either way.
- **Concerns** — the value seems at odds with a specific guideline or stage requirement; state
  which guideline and why.

Focus on parameters that matter most for the stage (don't enumerate every neutral choice —
only call out the interesting ones).

**c. Internal consistency**
Check whether parameter choices work together coherently. Examples of tensions to catch:
- Rotation-focused diff settings paired with understeer-biased ARB/suspension on a car that
  needs rotation.
- Very soft springs with very stiff dampers (mismatch in suspension compliance).
- Tyre choice inconsistent with the stage surface.
- Brake bias misaligned with the car's weight distribution tendency on that surface.
Flag 2–4 tensions if found; skip this section entirely if the setup is coherent.

### 6. Produce the review
Structure the review with these sections (omit a section if it has nothing to say):

```
## Overall verdict
[1–2 sentences. State clearly if there are hard violations. Otherwise: is this a solid setup,
a reasonable starting point, or does it have significant alignment issues?]

## Constraint violations  ← omit section if none
- {Parameter}: value {X} is outside {Min..Max} / not in {Discrete steps set}.
  [One per line; be specific.]

## Strengths
- {Parameter}: {chosen value} — {why this aligns well with the stage/guideline}.
  [2–4 bullets. Cite the guideline or stage requirement.]

## Concerns & suggestions
- **{Parameter}** (current: {value}) — {what's misaligned and why}. Consider {suggested value
  or range} instead. _(Guideline: [tag] …)_
  [3–5 bullets. Each must cite the guideline principle or stage requirement driving the concern.
  Give a concrete alternative value, not just "lower it".]

## User notes  ← omit section if Notes field is blank
[Acknowledge what the user recorded in the Notes field. Don't restate it verbatim; connect it
to the review findings where relevant.]
```

### 7. Print in chat
Output the full review as formatted markdown.

### 8. Write to Notion — append only
Add the following block group to the **bottom** of the setup's page body. Never modify,
delete, or reorder existing content.

- **H2 heading:** `AI Review — {YYYY-MM-DD HH:MM} UTC`  
  (the timestamp of when this review runs)
- **Toggle block** (collapsed by default, mobile-readable): the review content from step 6,
  formatted identically — short headings + bullets, no wide tables.

If the Notion write fails, tell the user and show the review text again so they can save it
manually.

## Rules
- **Append-only** — never modify or delete existing page content; only add to the bottom.
- **Stay within `Car setups` scope** — same name-resolution and scope rules as every other
  workflow.
- **Drivetrain-aware** — apply only guideline lines tagged `[All]` or the car's drivetrain.
- **Cite the guideline** — every concern must reference which principle or user guideline it
  comes from.
- **Concrete suggestions** — every concern must include a specific alternative value or range,
  not a vague direction.
- **Hard errors first** — constraint violations are listed before everything else and never
  softened.
