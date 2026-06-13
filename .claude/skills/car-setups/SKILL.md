---
name: car-setups
description: A complete system for the whole lifecycle of a personalized car setup for Assetto Corsa Rally (and other rally/racing games), saved to the user's Notion. Setups are tailored to the user's driving style and preferences and get more personal as they rate and learn from past setups. Use when the user wants to onboard a car (capture its tunable parameters from min/max setup-screen screenshots or a bundled template), generate or tweak a setup for a stage from its description and their driving style, review or share an existing setup from Notion, import existing setups from a save file, or export an onboarded car as a shareable community template. Reads and writes through the user's Notion connection and keeps every value within the car's legal ranges.
---

# car-setups

A **complete system for the whole lifecycle of a personalized car setup** for rally games (built
for **Assetto Corsa Rally**, ACR) — onboard, build, tweak, review, share, and import — storing
everything in the user's **Notion** via their Notion connection. Setups are **tailored to the
user's driving style and preferences** and get more personal as the user rates and learns from
past setups. The **game is chosen at onboarding** (ACR or another game) and data is filed under a
per-game page; other games are supported with the same workflows, except **save-file import is
ACR-only**. The bundled glossary and tuning principles are written for ACR but serve as the base
for **all** games — no game-specific knowledge is shipped.

A **community template library** lives in `car-templates/` — one YAML file per car with all
tunable parameters, Min/Max ranges, and Discrete steps pre-filled. When onboarding a car that
has a bundled template, the skill offers to auto-populate Notion from it (skipping screenshots).
Users can export their own onboarded car's parameters as a template to contribute back.

There are four workflows — read the matching file before acting:

| If the user wants to… | Follow |
|---|---|
| Onboard a car / capture its tunable parameters (from min & max screenshots) | `references/onboard-car.md` |
| Build a setup for a stage | `references/build-setup.md` |
| Tweak / refine an existing setup based on driving feedback | `references/tweak-setup.md` |
| Review an existing setup from Notion | `references/review-setup.md` |
| Share a setup as a plain-text snippet (copy-paste) | `references/share-setup.md` |
| Import existing setups from a save file | `references/import-savegame.md` |
| Export a car's parameters as a community template file | `references/export-car-template.md` |

Shared knowledge (read as needed):
- `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions, and
  the create-if-missing (resolve-by-name) rules.
- `references/notion-rest-read.md` — **the reliable way to read a car's `Parameters` rows (or a
  filtered slice of `Setups`)**; the connector can't list rows, so query the data source over
  REST. Follow this wherever a workflow says "fetch the car's rows".
- `references/setup-tuning-principles.md` — the tuning reasoning base (drivetrain-tagged).
- `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- `car-templates/` — bundled YAML parameter templates, one file per car (see
  `references/export-car-template.md` for the file format).

Bundled tools (stdlib Python, run via code execution):
- `scripts/parse_acr_save.py` — import workflow: parse ACR `.sav` files into JSON.
- `scripts/query_notion_parameters.py` — all read workflows: fetch a car's rows from a Notion
  data source via the REST API. Call as `python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>"` (add `--learn-only` for the Setups learn pool). See `references/notion-rest-read.md`.

## Core rules (always apply)
- **Stay within the catalog.** Every value written to a setup must obey the parameter's
  `Parameters` row: if its **`Discrete steps`** are filled, the value must be **one of them**;
  otherwise the value must be within the numeric **`Min..Max`**. Never invent a parameter a car
  doesn't have.
- **Notion scope is `Car setups` only — never search broadly.** Navigate the hierarchy
  explicitly by name starting from the `Car setups` root; do not issue workspace-wide Notion
  searches to locate setup data, guidelines, or parameters. If a Notion API call returns results
  from outside `Car setups`, discard them entirely before processing. Out-of-scope content must
  never influence setup values, guideline layers, or parameter catalogs, even if it mentions car
  names or setup terms.
- **Skip `FFB Multiplier`.** It is a controller/display preference, not a car setup parameter —
  never capture it during onboarding and never include it in setups.
- **Append-only.** Never modify or delete existing setups — only add rows. (Onboarding may
  update the parameter catalog.)
- **The tool is the source of truth for validity** (Notion can't hard-enforce ranges) —
  validate every value before writing.
- **Mobile-first output.** The user reads setups on a phone while in-game: each generated
  setup's Notion page leads with an **"Enter in-game" checklist** (values grouped by setup
  screen), with the justification in a **toggle** below. No wide tables in page bodies; short
  headings + bullets.
- **Drivetrain-aware.** Determine the car's drivetrain (FWD/RWD/AWD) and apply only guidance
  tagged `[All]` or that drivetrain (legend in `references/setup-tuning-principles.md`).
- **Layered guidelines — the user wins.** Reasoning precedence, later wins: base principles →
  global `Tuning guidelines` → matching surface section → per-car guidelines → the stage
  description. Cite a user guideline when it drives a choice.
- **Notion by name.** Resolve the structure by its canonical names and create whatever is
  missing (per `references/notion-structure.md`); don't rely on stored IDs.
- **Reading rows.** To read a car's `Parameters` rows or a filtered slice of `Setups`, follow
  `references/notion-rest-read.md` — the connector can't list database rows reliably.

## Choosing a value (per parameter)
Each `Parameters` row is either constrained to an exact set or left as a free numeric range —
there is **no step grid and no interpolation**. For every parameter:

1. **`Discrete steps` filled** → choose **only** from that exact set (works for coarse numerics
   like spring stiffness *and* named options like gear set / caliper type). The checklist value
   is exact.
2. **No `Discrete steps`, numeric `Min..Max`** → choose any target within `Min..Max`; report it
   and tell the user to **dial to the nearest available position in-game** (the in-game
   increment is unknown, so the exact target may be a hair off — that's expected).
3. **No `Discrete steps` and `Min/Max = —`** (param was never captured — no screenshot data) →
   **skip it** and tell the user to re-onboard the car so the values are captured.

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
