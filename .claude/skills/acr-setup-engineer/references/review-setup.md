# Workflow: review an existing setup

Review a setup that already exists in the user's Notion `Setups` database **the way an experienced
rally mechanic would at the service park before the stage**: read the sheet, think about the road
the car is about to drive, and say plainly whether it's ready — and what they'd change before the
start if it isn't. Print the review in chat and append it, timestamped, to the setup's Notion page.

The review is built around **the stage**, not around the parameter list. The question it answers is
*"will this car work on this road for this driver?"* — not *"did this setup follow the rules?"*.

Read `notion-structure.md` (structure + schemas), `setup-tuning-principles.md` (reasoning base) and
`driving-feedback-interview.md` → *Fix-order ladder* before starting.

## Inputs
- **Setup name** (e.g. `alsace dry fast`). The user can also provide **Car**, **Location**, and/or
  **Stage** to narrow disambiguation.

## Procedure

> **Load steps 1–4 as one batched read** (`SKILL.md` → *Read efficiently*): after resolving the
> structure, issue the independent reads together (parallel tool calls) and run the REST queries in
> one code-execution block — fetching the car's `Catalog` page (`Drivetrain`/identity facts,
> step 2), **the car's `Parameters` page for a screenshot car**, its `Guidelines` page (step 3),
> its `Log` page (step 3) and the stage page (step 4) once
> each, in the same batch.

### 1. Identify the setup
Navigate to `ACR Setup Engineer → Setups` DB and find the row matching the given name. Stay
within `ACR Setup Engineer` scope — do not issue workspace-wide Notion searches.

**In offline mode** (`egress: none` this chat — `notion-rest-read.md` → *Offline mode*) look the
name up in the car's `Setup index` first: [setups-list-read.md](setups-list-read.md) →
*Finding one setup by name* (`scripts/setups_list.py --find`), then `notion-fetch` the matched
page — its properties are the row. If the name isn't in the index, don't search the
database — say the setup isn't in the {Car}'s index and offer to add it: *"Paste its Notion
link here and I'll add it to the index and use it"* (`setups-list-read.md` → *Adding a setup
by link*). The lookup above is for `egress: ok` only.

- **Unique match:** Load all value properties, plus `Car`, `Location`, `Stage`, `Surface`,
  `Conditions` (may be blank — don't treat that as an error), `Mode`,
  `Notes`, `Rating` (a **1–5 Select**, higher = better; blank = unrated), and the page body's
  **driving intent** bullet (the setup summary at the top of the page).
- **Multiple matches:** List them (Name / Car / Stage / Date) and ask the user to pick one.
- **No match:** Tell the user and stop.

If the loaded row has **no parameter values filled** (all value columns are blank — e.g. an
imported setup with only metadata and no individual parameter values entered), say so and stop.
There is nothing to review without values.

### 2. Load constraints + drivetrain
**Load the car's catalog per [catalog-read.md](catalog-read.md)** — a bundled file for a template
car, the car's `Parameters` page (fetched in this same batch) for a screenshot car; one
`load_catalog.py` call either way, `--surface {Surface}` when the workflow resolves a surface.
Here it is the reviewed setup's `Surface` (loaded in step 1), so pass it. Also read the `Drivetrain`
(FWD/RWD/AWD), weight bias and engine facts from the car's `Catalog` page — the same fetch that
gave you the source line. This workflow is read-only on the database — it never reorders Notion
columns. **Resolve each parameter's legal range for the setup's `Surface`** (loaded in step 1) —
the surface-specific row if the parameter has one; for `Snow`, fall back to a `Gravel` row before
the baseline (see [notion-rest-read.md](notion-rest-read.md)).

### 3. Load the guideline layers — and the driver's history
Same precedence chain as `build-setup.md` (lowest → highest priority):
1. **Base** — `setup-tuning-principles.md`.
2. **Game version notes** — run `python scripts/load_game_version_notes.py` and read the file it
   prints (the tuning notes for the current game version, `game-versions/<version>.md`); when it
   prints a second `note:` line, say it in one line. **They override the base principles** for the
   rules they name (in 0.6: tarmac tyre pressure and tyre type by stage length). If it exits 1,
   skip this layer and say so in one line.
3. **Bundled car troubleshooting** — check the `car-troubleshooting/` folder for a file whose name
   matches this car (same match rule as a bundled template — `onboard-car.md` step 1 →
   *Matching a car name* — e.g. `car-troubleshooting/lancia-037-evoluzione-2-1984.md`). **If one exists, read
   it and apply its symptom→fix entries — they override the base principles** for the symptoms they
   name. If no file matches, skip this layer.
4. **Global user guidelines** — Notion `Tuning guidelines` page under `ACR Setup Engineer`.
5. **Surface section** — the global guidelines' "Per surface" subsection matching the setup's
   `Surface` (not a separate page).
6. **Per-car guidelines** — the car's `Guidelines` page.
The setup's own **driving intent** is the most specific layer. Apply only lines tagged `[All]` **or
the car's drivetrain**. If two authored layers really contradict each other on something that
matters here, say so in the review rather than silently picking a side. Never read content outside
`ACR Setup Engineer`.

**Also read the car's `Log` page** — the way a mechanic asks the driver how the car has been
feeling. Resolve it by name (`Log`, falling back to a legacy `Feedback` page, per
`notion-structure.md` → *Resolving the page (`Log`, and the legacy `Feedback` name)*); **a read
never renames anything**, and if neither page exists, skip it silently. Read the whole page — the
skill's dated feedback entries **and** the user's own notes. It is **evidence, not a guideline
layer**: `Guidelines` still outranks it. Use it to spot a complaint this setup doesn't answer (the
driver has reported a loose rear on corner exit twice and this setup softens the front ARB — that
makes it worse), or one it already answers.

### 4. Load the stage
Fetch the `{Stage}` / `{Location}` page from the catalogue (`notion-structure.md`): surface, length,
key corners and speeds, character. **This is the centre of the review** — the road the car is
about to drive.

**No stage on the setup?** Ask once which stage it's for (*"Which stage is this setup for? I can
review it against the surface and your intent without one, but it's a better review with the
road."*). If the user names one that's in the catalogue, load it; if they don't have one, review
against the `Surface`, `Conditions` and the driving intent only, and **say at the top of the
review** that it was done without a stage.

### 5. Think like the mechanic

> **A `Source = default` row is the game's own stock setup, not something the skill built.** Review
> it as a *reference* — say how it sits for this stage and this driver, and where it's likely to
> need moving — but never present it as a poorly-built setup, and never flag a value as a mistake
> someone made. A shown value outside the catalog's captured range means the **catalog range is
> stale**, not that the setup is illegal. For a **screenshot car**, the fix is re-onboarding it —
> the exact request is *"onboard the {Car} from my screenshots"*. For a **template car**, say the
> stale-template line (`onboard-car.md` → *When the template may be stale*), which carries its own
> way out: *"re-onboard the {Car} from my screenshots"*. A bare "re-onboard" is a template refresh
> and would take the same template again.

Work through it in this order:

**a. Legality — the only hard check.** For every parameter that has a value, check it against its
**surface-resolved** range (step 2): one of the `Discrete steps` when the row has them, else inside
`Min..Max` (inclusive). Any violation is a **hard error** — list every one; never soften them. The
game won't accept the value, so nothing else in the review matters until it's fixed.

**b. Walk the stage.** From the stage facts, name the **3–5 things this road asks of the car** — for
example: grip level and how it changes (tarmac → damp → gravel sections, snow ruts); tight hairpins
vs fast flowing sections; jumps, crests and landings; bumps, cuts and kerbs; long braking zones;
long straights. For each one, judge how **this setup** meets it, looking at the parameters that
decide it (ride height and springs for bumps and landings; diff and ARBs for rotation in hairpins;
gearing for the straights and the slow corners; brake bias and hardware for the braking zones; tyre
choice for grip). Reason from the car's drivetrain and weight bias, the tuning principles and the
car's troubleshooting file.

**c. Check the driver.** Put the driving intent, `Notes`, `Rating` and the `Log` history next to
what you found in (b). A setup can suit the stage and still fight the driver — say so.

**d. Decide what you'd change before the start.** At most **3–5 changes**, ordered by the
fix-order ladder (`driving-feedback-interview.md` → *Fix-order ladder*: tyres → differential →
suspension → ARBs → dampers → wheel angles → brake bias; gearing is a parallel track; tyre pressure
sits outside the ladder). Each change has a **concrete legal screen value** (surface-resolved, a
member of `Discrete steps` when the row has them) and a one-line reason **in plain words tied to the
stage or the driver** (*"the rear steps out landing the jumps after the ford — one step softer on
the rear springs"*), not a rule citation. A setup that's right needs no changes — don't invent
them.

**e. Respect the user's own guidelines.** Cite a guideline when it's the reason for a change. And
if a change you'd make goes **against** one of the user's guidelines, say so in the change itself
(*"this goes against your 'prefer understeer on entry' guideline — your call"*). A concern no longer
needs a citation to be raised; the mechanic's judgement of the stage is reason enough.

> **Toe values read inverted** (`SKILL.md` → *ACR's toe sign is inverted*): a **positive** stored
> toe is toe-**out**, a **negative** one is toe-**in**. Judge a toe value by that direction, say the
> direction in words whenever the review mentions a toe number, and add the one-line inversion
> warning. Any suggested value is likewise given as a screen number.

### 6. Produce the review
Talk like a mechanic to their driver: direct, plain words, no jargon the user hasn't used, no
hedging. Structure it like this, and drop any section that has nothing to say:

```
## Verdict
**Ready to go** / **Fix these first** / **Wrong setup for this stage** — then 1–2 sentences on why.
[Hard violations always make it "Fix these first". Without a stage, say so here.]

## Won't load in the game  ← only when there are violations
- {Parameter}: {value} isn't allowed — the range is {Min..Max} / the options are {Discrete steps}.

## The stage
- **{What the road asks — e.g. "Two hairpins after the bridge"}** — {how this setup copes, and why}.
  [3–5 bullets, in the order the driver meets them on the stage where the facts say so.]

## What I'd change before the start
1. **{Parameter}**: {current} → {new} — {plain reason tied to the stage or the driver}.
  [At most 3–5, in fix-order-ladder order. Omit the section when nothing needs changing.]

## What's right
- {Parameter or group}: {why it suits this stage or this driver}.  [2–3 bullets, short.]

## From your notes  ← only when Notes or the Log has something relevant
[What the driver has reported and how this setup answers it — or doesn't. Don't restate it verbatim.]
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

The review writes **nothing to the `Log` page** — it records what the driver said, and a review is
the mechanic talking, not the driver. If the user answers the review with how the car has actually
been driving, that's feedback: switch to `tweak-setup.md`, which logs it.

If the Notion write fails, tell the user and show the review text again so they can save it
manually.

## Rules
- **The stage comes first.** Every judgement is about this road, this car and this driver — not
  about whether a value matches a rule in the abstract.
- **Legality is the only hard check** — violations are listed first and never softened.
- **Few, concrete changes** — at most 3–5, fix-order-ladder order, each with a legal screen value.
  None when the setup is right.
- **The user's guidelines are respected, not required** — a change that goes against one says so;
  a concern doesn't need a citation to be raised.
- **Append-only** — never modify or delete existing page content; only add to the bottom.
- **Stay within `ACR Setup Engineer` scope** — same name-resolution and scope rules as every other
  workflow.
- **Drivetrain-aware** — apply only guideline lines tagged `[All]` or the car's drivetrain.
- **Toe sign is inverted** — positive = toe-out, negative = toe-in; say which direction a toe value
  actually gives and warn about the inversion whenever the review quotes one.
