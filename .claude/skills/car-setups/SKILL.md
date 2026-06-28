---
name: car-setups
description: A complete system for the whole lifecycle of a personalized car setup for Assetto Corsa Rally (and other rally/racing games), saved to the user's Notion. Setups are tailored to the user's driving style and preferences and get more personal as they rate and learn from past setups. Use when the user wants to onboard a car (capture its tunable parameters from min/max setup-screen screenshots or a bundled template), generate or tweak a setup for a stage from its description and their driving style (optionally starting from an existing setup as a reference, including one from another car), review or share an existing setup from Notion, import existing setups from a save file, export an onboarded car as a shareable community template, or ask questions about setups and tuning (why a setup uses a value, what a parameter does, how to think about ARBs/diffs/springs/etc.). Reads and writes through the user's Notion connection and keeps every value within the car's legal ranges.
---

# car-setups

A **complete system for the whole lifecycle of a personalized car setup** for rally games (built
for **Assetto Corsa Rally**, ACR) — onboard, build, tweak, review, share, import, and explain —
storing everything in the user's **Notion** via their Notion connection. Setups are **tailored to the
user's driving style and preferences** and get more personal as the user rates and learns from
past setups. The **game is chosen at onboarding** (ACR or another game) and data is filed under a
per-game page; other games are supported with the same workflows, except **save-file import is
ACR-only**. The bundled glossary and tuning principles are written for ACR but serve as the base
for **all** games — no game-specific knowledge is shipped.

A **community template library** lives in `car-templates/` — one YAML file per car with all
tunable parameters, Min/Max ranges, and Discrete steps pre-filled. When onboarding a car that
has a bundled template, the skill offers to auto-populate Notion from it (skipping screenshots).
Users can export their own onboarded car's parameters as a template to contribute back.

Pick the matching workflow and read its file before acting:

| If the user wants to… | Follow |
|---|---|
| Onboard a car / capture its tunable parameters (from min & max screenshots) | `references/onboard-car.md` |
| Build a setup for a stage | `references/build-setup.md` |
| Tweak / refine a setup, or describe a handling problem to work through (problem → tweak → test loop) | `references/tweak-setup.md` |
| Review an existing setup from Notion | `references/review-setup.md` |
| Ask a question / explain a setup or a tuning concept (read-only) | `references/ask-setups.md` |
| Share a setup as a plain-text snippet (copy-paste) | `references/share-setup.md` |
| Import existing setups from a save file | `references/import-savegame.md` |
| Export a car's parameters as a community template file | `references/export-car-template.md` |

Shared knowledge (read as needed):
- `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions, the
  create-if-missing (resolve-by-name) rules, and the shared `Locations`/`Stages` facts catalogue
  (a stage is created once, centrally, and referenced — never duplicated — by any setup).
- `references/notion-rest-read.md` — **the reliable way to read a car's `Parameters` rows (or a
  filtered slice of `Setups`)**; the connector can't list rows, so query the data source over
  REST. Follow this wherever a workflow says "fetch the car's rows".
- `references/setup-tuning-principles.md` — the tuning reasoning base (drivetrain-tagged).
- `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- `car-templates/` — bundled YAML parameter templates, one file per car (see
  `references/export-car-template.md` for the file format).
- `VERSION` — the skill's own version (or `dev` for a source checkout); see *Skill version* below.

Bundled tools (stdlib Python, run via code execution):
- `scripts/parse_acr_save.py` — import workflow: parse ACR `.sav` files into JSON. **Version-aware**:
  reports the save-format fingerprint (`save_format`), the per-setup game version(s)
  (`game_versions`), and which handler ran (`handler_used` — a small registry dispatches by format;
  `parse_structural` for v0.4-style saves, `parse_nul_tolerant` for saves delivered without NUL
  terminators). `ok: false` ⇒ caller falls back to AI extraction.
- `scripts/query_notion_parameters.py` — all read workflows: fetch a car's rows from a Notion
  data source via the REST API. Call as `python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>"` (add `--learn-only` for the Setups learn pool). See `references/notion-rest-read.md`.

## Core rules (always apply)
- **Stay within the catalog.** Every value written to a setup must obey the parameter's
  `Parameters` row: if its **`Discrete steps`** are filled, the value must be **one of them**;
  otherwise the value must be within the numeric **`Min..Max`**. Never invent a parameter a car
  doesn't have.
- **Every parameter the car has gets a value.** A complete setup specifies an **explicit value
  for every tunable parameter the car actually has** — there is no "use the default" / leave-it-
  blank option. A setup-row value column may be blank **only** when (a) the car does not have
  that parameter at all (the column is a union across the game's cars), or (b) it is the
  documented `FFB Multiplier` exception below. Never leave an applicable parameter blank because
  a default "would be fine."
- **Surface-resolved ranges.** A `Parameters` row may carry an optional **`Surface`** tag
  (`Tarmac`/`Gravel`/`Snow`); a few parameters expose a different range per surface. The legal
  range for a setup on surface **S** is the row tagged `S` **if one exists**; else if `S` is
  `Snow`, a `Gravel` row **if one exists** (snow inherits gravel's softer ranges — cars are
  onboarded with a gravel pass but no separate snow pass); else the blank (baseline) row. Resolve
  this before choosing/validating any value (see `references/notion-rest-read.md`). Most
  parameters have only the baseline row. **The user may set the build's surface explicitly**
  ("build a gravel setup", "use tarmac parameters") — this overrides the referenced stage's
  surface (or, with no stage, is simply the surface) for the **whole** build (range resolution,
  tyre choice, and surface-tagged guidelines) and becomes the setup row's `Surface`.
- **ACR tyre fallback + canonical names.** For ACR, the legal `Tyre Type` set is the car's
  stored `Discrete steps` list **when it specifies one**; only when that cell is blank or
  missing does the legal set fall back to the standard list: `Tarmac Soft, Tarmac Medium,
  Tarmac Hard, Tarmac Wet, Tarmac Winter, Tarmac Snow, Gravel Soft, Gravel Medium, Gravel
  Hard, Snow (Studs)`. Validate every tyre pick against this effective list. **Every tyre
  value written into a setup must be a fully-qualified name from that list** — never a
  bare/ambiguous value (`Snow` → `Tarmac Snow` or `Snow (Studs)`; `Gravel` →
  `Gravel Soft/Medium/Hard`; `Dry Tarmac` → `Tarmac Soft/Medium/Hard`). For non-ACR games,
  use the stored list as-is (no fallback).
- **Tyre pressure is always two values.** Every setup stores `Pressure Front` and
  `Pressure Rear` as two separate values — never a single combined tyre-pressure value.
- **Notion scope is `Car setups` only — never search broadly.** Navigate the hierarchy
  explicitly by name starting from the `Car setups` root; do not issue workspace-wide Notion
  searches to locate setup data, guidelines, or parameters. If a Notion API call returns results
  from outside `Car setups`, discard them entirely before processing. Out-of-scope content must
  never influence setup values, guideline layers, or parameter catalogs, even if it mentions car
  names or setup terms.
- **Skip `FFB Multiplier`.** It is a controller/display preference, not a car setup parameter —
  never capture it during onboarding and never include it in setups.
- **Skill version.** Determine once per run and record it on every `Setups` row you create
  (generated, tweaked, **and imported**). Read the bundled `VERSION` file at the skill root:
  - If it holds a concrete version (e.g. `v0.3.0`), that **is** your skill version.
  - If it holds `dev` (an unreleased source checkout): if you can run `git` in the skill's repo,
    use `git describe --tags --always --dirty` (e.g. `v0.2.0-3-gdbc15b1`, or a bare short hash if
    there are no tags); otherwise record `dev`.
- **Append-only.** Never modify or delete existing setups — only add rows. (Onboarding may
  update the parameter catalog.)
- **Refining is an in-chat loop — save only when asked.** Describing a handling problem or asking
  for a tweak is **not** a request to build or save a setup. Work the *problem → tweak → test →
  feedback* cycle conversationally: propose legal value changes in chat and iterate as the user
  reports back from driving — **write nothing to Notion**. Persist a single new `Setups` row (the
  session's final state) **only when the user explicitly asks to save** (`tweak-setup.md`). When the
  user signals they're happy with how the car feels, **remind them once** they can ask to save it —
  don't nag. (A fresh **build** is an explicit creation request and still writes its row per
  `build-setup.md`.)
- **The tool is the source of truth for validity** (Notion can't hard-enforce ranges) —
  validate every value before writing.
- **A setup's real values are its row, not its note.** A saved setup's actual values are its
  `Setups` **row value properties** — the single source of truth. The page-body summary/
  justification explains *why* values were chosen **at creation time** and can be **stale**: the
  user often edits the row's values directly in Notion afterward, leaving the prose out of date.
  Whenever you consume a past setup — learning from it, using one as a **reference/basis** for a
  new build, or comparing two — take each value from the **row**, never from the justification
  prose. You **may** still use the setup's stated **intent/goal** (the page-body summary) to
  inform a new build.
- **Setup names ≤ 15 characters.** The in-game name field caps at 15 characters, so every
  `Setups` row `Name` must be **≤15 chars**. Keep default/generated names within the limit. When a
  proposed or user-requested name is longer, **automatically compact it** to fit — drop spaces,
  abbreviate words, trim filler — keeping it recognizable (e.g. `Alsace tarmac dry fast` →
  `alsace dry fast`), and **state the name you used** in one line so the user can object. Only
  write a name longer than 15 chars if the user, after seeing the compacted version, **explicitly
  insists** on the longer one. **Never put the car's name in a generated setup name** — the car is
  always obvious from context (the `Car` property, the page it lives under), so it would only
  waste the 15-char budget; comply if the user explicitly asks for the car in the name, but never
  add it by default. **When the user doesn't specify a name**, build the default from, in priority
  order: a stage/location reference (abbreviated if long) → conditions (dry/wet/snow/ice) →
  driving style or desired experience (fast/fun/drift/traction) → an optional version tag —
  dropping or abbreviating the lower-priority pieces first to fit ≤15 chars.
- **Mobile-first output.** The user reads setups on a phone while in-game: each generated
  setup's Notion page leads with an **"Enter in-game" checklist** (values grouped by setup
  screen), with the justification in a **toggle** below. No wide tables in page bodies; short
  headings + bullets.
- **Drivetrain-aware.** Determine the car's drivetrain (FWD/RWD/AWD) and apply only guidance
  tagged `[All]` or that drivetrain (legend in `references/setup-tuning-principles.md`).
- **Layered guidelines — the user wins.** Reasoning precedence, later wins: base principles →
  global `Tuning guidelines` → matching surface section (that page's "Per surface" subsection,
  not a separate page) → per-car guidelines → the setup's own driving intent (most specific).
  Location/stage facts are objective inputs, not a guideline layer. More specific is the
  **default lean** — on a **material conflict between authored layers, ask the user** which to
  follow rather than silently picking one. Cite a user guideline when it drives a choice.
- **Notion by name.** Resolve the structure by its canonical names and create whatever is
  missing (per `references/notion-structure.md`); don't rely on stored IDs.
- **Reading rows.** To read a car's `Parameters` rows or a filtered slice of `Setups`, follow
  `references/notion-rest-read.md` — the connector can't list database rows reliably.
- **Assert column order on every `Setups` write — MANDATORY, never skip.** Any time you create a
  `Setups` linked view **or** append/update a `Setups` row, you **must**, in the same action, set
  the column order: run `scripts/query_notion_parameters.py … --show-order` and apply the result as
  the view `SHOW` on **every** affected projection (the main `Setups` table, the car's page view,
  and any stage/location view). A Setups write is **not finished** until this is done — skip it and
  columns render alphabetically. This applies on **every** run, including quick / low-effort ones;
  it is a required step, never an optional polish. How-to: `references/notion-structure.md` →
  *Applying the order*.

## Choosing a value (per parameter)
Each `Parameters` row is either constrained to an exact set or left as a free numeric range —
there is **no step grid and no interpolation**. For every parameter (using the row **resolved for
the setup's surface** — see *Surface-resolved ranges* above):

1. **`Discrete steps` filled** → choose **only** from that exact set (works for coarse numerics
   like spring stiffness *and* named options like gear set / caliper type). The checklist value
   is exact.
2. **No `Discrete steps`, numeric `Min..Max`** → choose any target within `Min..Max`; report it
   and tell the user to **dial to the nearest available position in-game** (the in-game
   increment is unknown, so the exact target may be a hair off — that's expected).
3. **No `Discrete steps` and `Min/Max = —`** (the car *has* this parameter, but it was never
   captured — no screenshot data) → **do not leave it blank** and do not treat it as a default:
   surface the gap, ask the user to enumerate the range (or re-onboard the car), then fill an
   explicit value once the range is known.

`Discrete steps` for **numeric** params is **optional and user-owned**: onboarding leaves it
blank and the user adds values in Notion when they want to constrain the parameter. For **`—`
named-selection** params onboarding seeds it with the option names the screenshots show (and the
standard ACR lists for `Tyre type`/brake pads); the user completes it (see
`references/notion-structure.md`).

## Glossary (ACR)
- **Adjuster ring** = ride height. **Gear set** picks a ratio family; **primary gear** = the
  final-drive pair.
- **LSD ramp (power/coast)**: lower angle = more lock. **Preload / plates** = base lock / number
  of friction plates.
- **ARB**: front stiffer → understeer; rear stiffer → oversteer.
- **Surfaces**: tarmac (stiffer, higher pressure), gravel & snow (softer, lower pressure).
