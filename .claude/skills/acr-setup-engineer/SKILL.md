---
name: acr-setup-engineer
description: A complete system for the whole lifecycle of a personalized car setup for Assetto Corsa Rally (ACR), saved to the user's Notion. Setups are tailored to the user's driving style and get more personal as they rate and learn from past ones. Use when the user wants to onboard a car (capturing its tunable parameters from min/max setup-screen screenshots or a bundled template, plus the in-game car info screen), generate or tweak a setup for a stage from its description and their driving style (optionally based on an existing setup, including one from another car), review or share an existing setup from Notion, store a setup they built themselves in-game from photos of the setup screens, import existing setups from a save file, export an onboarded car as a shareable community template, or ask questions about setups and tuning (why a setup uses a value, what a parameter does, how to think about ARBs or diffs). Reads and writes through the user's Notion connection, keeping values within the car's legal ranges.
---

# ACR Setup Engineer

A **complete system for the whole lifecycle of a personalized car setup** for **Assetto Corsa
Rally** (ACR) — onboard, build, tweak, review, share, import, and explain — storing everything in
the user's **Notion** via their Notion connection. Setups are **tailored to the user's driving
style and preferences** and get more personal as the user rates and learns from past setups.

A **community template library** lives in `car-templates/` — one YAML file per car with all
tunable parameters, Min/Max ranges, and Discrete steps pre-filled. When onboarding a car that
has a bundled template, the skill offers to auto-populate Notion from it (skipping screenshots).
When the user asks to **build** (or **import**) a setup for a car that isn't onboarded yet, a
matching template **auto-onboards it first** — no screenshots, no separate step. Users can export
their own onboarded car's parameters as a template to contribute back — and after a **screenshot**
onboarding (a car with no bundled template) the skill **offers this unprompted**, since that user is
the only one who can supply that car's catalog (`references/onboard-car.md` step 10).

Pick the matching workflow and read its file before acting:

| If the user wants to… | Follow |
|---|---|
| Onboard a car / capture its tunable parameters (from min & max screenshots, plus the car info screen for its identity facts) | `references/onboard-car.md` |
| **Refresh an already-onboarded car** — *"refresh the {car} in my Notion"*, *"update {car}"*, *"re-onboard {car}"*: a car onboarded **from screenshots** switches to a bundled template that is at least as new as its captured game version (asking once, recommending yes, when that version is `unknown`) — that adds a ***Not in use*** line to the car's **`Parameters`** page and leaves its list sitting there, unused, so it can be switched back to. Rebuilds the car's **`Catalog`** page wholesale (identity facts, the **catalog source line**, the power/torque chart and the gearing-tool link) and **never regenerates a `Parameters` page** — for a template car there is nothing to write in Notion at all, its catalog lives in the skill. It also migrates a car still on the old one-page layout, including renaming a legacy **`Feedback`** page to **`Log`** in place, and migrating a screenshot car's old catalog table into its `Parameters` page once. Never touches the content of the user's `Guidelines` page, the content of the car's `Log` page, or `Setups` rows | `references/onboard-car.md` (refresh path) |
| **Change a car's parameter list** — *"the {car}'s {parameter} goes from A to B"*, *"set the steps for {parameter} to …"*, *"add / remove {parameter} on the {car}"*: validates the change and rewrites the car's `Parameters` page; a bundled car is copied into its own page on the first edit, without asking | `references/edit-catalog.md` |
| **Re-onboard a car from screenshots** — *"onboard the {car} from my screenshots"*, *"re-onboard the {car} from screenshots"*: **not** a refresh. Captures the car's ranges from the user's own min/max setup screens even if it is on a bundled template today, writes them to its `Parameters` page and flips the catalog source line to `your screenshots`. A bare *"re-onboard {car}"* is the refresh row above | `references/onboard-car.md` (screenshot path) |
| **Refresh everything after a skill update** — *"refresh my ACR Notion"*, *"update my ACR Notion"*, *"refresh all my cars"*, *"I updated the skill"*: rewrites the skill's root pages (`How to use`, `Claude Free plan`, `Parameter reference`) and runs the per-car refresh for every onboarded car. Never touches the user's pages, their `Log` notes or `Setups` rows | `references/refresh-notion.md` |
| Build a setup for a stage | `references/build-setup.md` |
| Tweak / refine a setup, or describe a handling problem to work through (problem → tweak → test loop) | `references/tweak-setup.md` |
| Work out **what's actually wrong** with how the car feels — guided questions after a drive, when the user can't put it into words (then continue into `tweak-setup.md` / `build-setup.md` with the diagnosis) | `references/driving-feedback-interview.md` |
| Review an existing setup from Notion — a rally mechanic's verdict on whether it suits the stage and the driver, with the few changes they'd make before the start | `references/review-setup.md` |
| Ask a question / explain a setup or a tuning concept (read-only) | `references/ask-setups.md` |
| Share a setup as a plain-text snippet (copy-paste) | `references/share-setup.md` |
| **Save/store a setup the user built themselves in-game**, from photos of the setup screens — *"store this as {name} for the {car}"*, *"save these screens as a setup"* (photos show **current values**, and a name to save it under is given or asked for) | `references/capture-setup.md` |
| Import existing setups from a save file | `references/import-savegame.md` |
| Export a car's parameters as a community template file | `references/export-car-template.md` |

Shared knowledge (read as needed):
- `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions, the
  create-if-missing (resolve-by-name) rules, and the shared `Locations`/`Stages` facts catalogue
  (a stage is created once, centrally, and referenced — never duplicated — by any setup).
- `references/catalog-read.md` — **the one way to load a car's catalog**, whichever kind of car
  it is: the bundled `car-templates/<slug>.yaml`, or the `yaml` block on the car's `Parameters`
  page saved to `parameters/<slug>.yaml`, both read with `scripts/load_catalog.py`. No token, no
  network, on every plan. Every workflow that needs a car's legal values goes through it; nothing
  else reads a catalog.
- `references/notion-rest-read.md` — **the reliable way to read any car's filtered slice of
  `Setups`**; the connector can't list database rows, so query the data source over REST. Follow
  this wherever a workflow says "fetch the car's `Setups` rows". **A catalog is never read here.**
  It also carries **offline mode** and the **fallback ladder** for when the sandbox can't reach
  `api.notion.com` (no network egress — e.g. Claude's Free plan): `Setups` slices degrade to
  empty, stated plainly, while catalogs are unaffected because they never needed the network.
- `references/setup-tuning-principles.md` — the tuning reasoning base (drivetrain-tagged).
- `references/driving-feedback-interview.md` — the shared **symptom → cause** question bank: how to
  interview a beginner about how the car felt (plain language, terms defined inline, "not sure" always
  allowed), the **pre-drive briefing** given before the default run, the gearing sub-interview, and
  the **fix-order ladder** that decides what to change first. Read it from `build-setup.md` (before
  and after the default drive) and from `tweak-setup.md` whenever feedback is vague.
- `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- `references/parameter-reference-template.md` — seed for the auto-maintained, read-only
  `Parameter reference` Notion page (verbatim in-game descriptions of every tuning parameter; also
  the single source of that game text — `setup-tuning-principles.md` links here).
- `references/config-page-template.md` — seed for the auto-created `Config` page (integration
  setup instructions + a blank token line for the read-only Notion token).
- `car-templates/` — bundled YAML parameter templates, one file per car (see
  `references/export-car-template.md` for the file format). **For a car that has one, this file
  *is* the parameter catalog** — read it with `scripts/load_catalog.py`, never from Notion
  (`references/notion-structure.md` → *Where a car's catalog lives*). Each also carries the car's
  **engine curve read out of the ACR game files** — a `power_torque_chart:` URL attached to the
  car's `Catalog` page, an `engine_curve:` block (peak torque, peak power, and the raw `[rpm, Nm]`
  points) to reason about gearing and shift points from, and a `gearing_tool:` link to the car's
  page in the ACR Car Lab (interactive speed-per-gear charts for every gear set, final drive and
  rev limit). See `references/notion-structure.md` → *Engine chart and gearing tool*.
- `car-troubleshooting/` — bundled per-car **symptom→fix** knowledge, one markdown file per car
  (e.g. `car-troubleshooting/lancia-037-evoluzione-2-1984.md`), matched to the car the same way as a
  template (matched on the `car:` name by `references/onboard-car.md` step 1 →
  *Matching a car name*). Whenever a
  workflow loads its guideline layers, **check this folder and, if a file matches the car, read it**;
  it is a **guideline layer that overrides the base principles** for the symptoms it names (see the
  *Layered guidelines* core rule).
- `VERSION` — the skill's own version (or `dev` for a source checkout); see *Skill version* below.

Bundled tools (stdlib Python, run via code execution):
- `scripts/parse_acr_save.py` — import workflow: parse ACR `.sav` files into JSON. **Version-aware**:
  reports the save-format fingerprint (`save_format`), the per-setup game version(s)
  (`game_versions`), and which handler ran (`handler_used` — a small registry dispatches by format;
  `parse_structural` for v0.4-style saves, `parse_nul_tolerant` for saves delivered without NUL
  terminators). `ok: false` ⇒ caller falls back to AI extraction.
- `scripts/load_catalog.py` — **every** read workflow, **both kinds of car**: read a car's
  catalog out of its template file — no token, no network (`references/catalog-read.md`). Call as
  `python scripts/load_catalog.py <file> [--surface Tarmac|Gravel|Snow]`, where `<file>` is
  `car-templates/<slug>.yaml` for a template car or the saved `parameters/<slug>.yaml` for a
  screenshot car; it prints the rows every downstream rule consumes. Also `--check values.json`
  (validate values against the catalog — it **exits 3 with a JSON report when it finds anything
  illegal, which is the expected outcome, not a failed script**), `--to-template rows.json`
  (takes `{"header": {…}, "rows": […]}` and prints the body of a car's `Parameters` page —
  onboarding, `references/edit-catalog.md`, migration; **never hand-format that YAML**) and
  `--pretty`. Without `--surface`, `--check` uses each parameter's baseline row.
- `scripts/check_egress.py` — once per chat, before the first REST query: prints `egress: ok` or
  `egress: none`. On `none` the chat runs in **offline mode** — no REST query, no token request,
  one plain line to the user (`references/notion-rest-read.md` → *Offline mode*).
- `scripts/query_notion_parameters.py` — `Setups` slices over REST, and
  `--show-order --from-template <file> …` for every view; it never reads a catalog. Call as
  `python scripts/query_notion_parameters.py <setups_data_source_id> <token> "<car_name>"` (add
  `--learn-only` for the `Setups` learn pool) — see `references/notion-rest-read.md`. For column
  order, pass one `--from-template` per car the view spans and no token at all
  (`references/notion-structure.md` → *Applying the order* is the only place that says which
  files a view needs).

## Core rules (always apply)
- **Stay within the catalog.** Every value written to a setup must obey the parameter's catalog
  row: if its **`Discrete steps`** are filled, the value must be **one of them**; otherwise the
  value must be within the numeric **`Min..Max`**. Never invent a parameter a car doesn't have.
  **Where the catalog comes from depends on the car** (`references/notion-structure.md` →
  *Where a car's catalog lives*): for a **template car** it is the bundled `car-templates/*.yaml`
  file; for a **screenshot car** it is the `yaml` block on its `Parameters` page. Both are loaded
  by the same path — `references/catalog-read.md` — and the rows come out in the same shape, so
  these legality rules are identical whichever the source.
- **Every parameter the car has gets a value.** A complete setup specifies an **explicit value
  for every tunable parameter the car actually has** — there is no "use the default" / leave-it-
  blank option. A setup-row value column may be blank **only** when (a) the car does not have
  that parameter at all (the column is a union across the game's cars), or (b) it is the
  documented `FFB Multiplier` exception below. Never leave an applicable parameter blank because
  a default "would be fine." (This is about *blank cells*, and does not conflict with the
  baseline-first rule below: a **captured** default row holds explicit values for every parameter,
  so anchoring a build on it never produces a blank.)
- **Baseline first — anchor on the game's own default setup.** The catalog gives legal *ranges* but
  no sense of where inside them the game itself sits, so a from-scratch build is anchored on nothing.
  For any new setup: if a **captured default** (`Source = default`) exists for this car in this
  context, start from **its values** and move only what the driver's reported symptoms and the build's
  intent justify — parameters nothing points at keep the default's value. If none exists, the default
  path is to ask for **setup-screen screenshots of the in-game default first**, capture it, and
  **check it (below) before recommending a drive** — then brief the user on what to notice
  *before* they drive (`references/driving-feedback-interview.md` → *Pre-drive briefing*). This is a
  **strong recommendation, never a gate** — if the user would rather just have a setup now, build one
  and say no baseline anchor was used.
  **Never infer how the game scopes its defaults** — per stage, per surface, per conditions (a
  wet-tarmac default may differ from dry), or not at all is **unknown and changes between releases**.
  Match on the full capture context, and when a stored default was captured in a *different* context,
  show it to the user and let them confirm it applies rather than assuming. Full procedure:
  `references/build-setup.md` steps 4–6; storage conventions: `references/notion-structure.md` →
  *Default (stock) baseline rows*.
- **Check the default before anyone drives it — ACR's defaults are sometimes broken.** The game
  occasionally hands out a setup from the wrong regime entirely (the recurring case: a dry-tarmac
  setup for the same stage in **snow** conditions). So whenever a default's values are in hand and
  about to become the anchor — fresh capture, exact-context match, or confirmed reuse — judge them
  against the build's surface and conditions **before** sending the user out to drive it. The bar is
  **wrong-regime or self-contradictory, never merely suboptimal** (suboptimal is what the
  anchor-plus-interview flow is *for*), and the check is **silent when it passes**. Wrong in a few
  parameters ⇒ **keep the anchor and override just those**, naming them to the user. Wrong across the
  board ⇒ **tell the user the game's default looks broken**, don't recommend driving it, and build a
  proper setup with no anchor. A user who wants to drive it anyway gets to. The broken default is
  still **stored and flagged** as a `Source = default` row, never withheld. Full procedure:
  `references/build-setup.md` step 5b.
- **Fix major issues before fine tuning.** When several things could be changed, work the
  **fix-order ladder**: tyre type → differential (preload → ramp angles → plates) → suspension (ride
  height → springs) → ARBs → dampers → alignment (camber, toe) → brake bias (and brake hardware when
  braking itself is the complaint). Gearing is a **parallel track**; **tyre pressure sits outside the
  ladder** and is held at the captured default unless a symptom points at it (ACR's pressure model
  isn't physically sensible). **What the driver actually reports always outranks this order.** See
  `references/driving-feedback-interview.md` → *Fix-order ladder*.
- **Surface-resolved ranges.** A catalog row may carry an optional **`Surface`** tag
  (`Tarmac`/`Gravel`/`Snow`); a few parameters expose a different range per surface. The legal
  range for a setup on surface **S** is the row tagged `S` **if one exists**; else if `S` is
  `Snow`, a `Gravel` row **if one exists** (snow inherits gravel's softer ranges — nothing is
  ever captured for snow on its own); else the blank (baseline) row. Resolve
  this before choosing/validating any value (see `references/notion-rest-read.md`; for a template
  car, `scripts/load_catalog.py --surface {S}` applies the same rule and reports which row it
  used). Most
  parameters have only the baseline row. **The user may set the build's surface explicitly**
  ("build a gravel setup", "use tarmac parameters") — this overrides the referenced stage's
  surface (or, with no stage, is simply the surface) for the **whole** build (range resolution,
  tyre choice, and surface-tagged guidelines) and becomes the setup row's `Surface`.
- **Tyre fallback + canonical names.** The legal `Tyre Type` set is the car's
  stored `Discrete steps` list **when it specifies one**; only when that cell is blank or
  missing does the legal set fall back to the standard list: `Tarmac Soft, Tarmac Medium,
  Tarmac Hard, Tarmac Wet, Tarmac Winter, Tarmac Snow, Gravel Soft, Gravel Medium, Gravel
  Hard, Snow (Studs)`. Validate every tyre pick against this effective list. **Every tyre
  value written into a setup must be a fully-qualified name from that list** — never a
  bare/ambiguous value (`Snow` → `Tarmac Snow` or `Snow (Studs)`; `Gravel` →
  `Gravel Soft/Medium/Hard`; `Dry Tarmac` → `Tarmac Soft/Medium/Hard`).
- **Tyre pressure is always two values.** Every setup stores `Pressure Front` and
  `Pressure Rear` as two separate values — never a single combined tyre-pressure value.
- **Every parameter value you show the user is written in backticks — in chat replies too.**
  `29//27*31//35`, `Tarmac Soft`, `57500`, `45/55`. This is the form of a value in a chat
  message, a confirmation, a change table, the in-game checklist, a share snippet and any Notion
  page body; a value repeated back to the user ("I wrote `35//30*33//28, 33//28*32//31`") is no
  exception. Chat is markdown, and without the backticks two `*` in one message pair up and
  vanish, so the user sees `35//3033//28`. A gear value is **always shown with its asterisk** —
  never in the form without it, even when that is how a stored value reads.
- **A gear value with a `*` in it is an ordinary value — use it, show it, never comment on it.** A
  car with a two-stage primary drive spells it `35//30*33//28` (two gear pairs, multiplied). That
  is the game's own spelling. **Accept it exactly as given** — from a setup screen, a save file, a
  template, a Notion row or the user — and treat it like any other option name: match it, store
  it, compare it, recommend it. **Never tell the user anything about this notation**: not that it
  looks unusual, not that an asterisk is special in markdown, not that a stored list "lost" its
  asterisks, not that you restored one. It is not a finding, and it never belongs in a report.
  - **`A//B*C//D` (asterisk, no spaces) is the only spelling.** Never write `x`, `×` or ` * `,
    never drop the `*`, never "tidy" a value you are copying.
  - **Writing to Notion — three cases, because `*` is markdown emphasis** and two of them in one
    string pair up and disappear (`35//30*33//28, 33//28*32//31` is stored as
    `35//3033//28, 33//2832//31`):
    1. **Page body** (checklist, justification, `Log` entry) → backticks, as above. On the
       `Parameters` page the values sit inside a fenced `yaml` block and are quoted.
    2. **A text property** — `Discrete steps`, `Notes`, a row's `Name`, a page `title`: these are
       inline markdown too. Write every `*` as **`\*`** (`35//30\*33//28, 33//28\*32//31`); the
       backslash is not stored, the asterisk is.
    3. **A Select or Number property** (a `Setups` value column such as `Primary Gear`) → the
       plain value, `35//30*33//28`, no backslash and no backticks.
  - **Reading — a value without its asterisks is the same value.** Rows written by older versions
    can hold `35//3033//28`. When you compare a gear value with a `Discrete steps` list, **compare
    with every `*` removed from both sides**; on a match, use the spelling that has the asterisk
    (the one from the screen, the save, the template or the user). Do this silently. Only when a
    value matches **no** entry, or **several**, ask the user which option they mean — one short
    question that lists the options, nothing about notation. `scripts/load_catalog.py --check`
    does the same match for a template car.
- **ACR's toe sign is inverted (game bug) — reason in directions, write the screen number.** In
  ACR's setup screen a toe value does the **opposite** of what its sign suggests: a **positive**
  toe value points the wheels **outwards** (toe-**out**), a **negative** one points them
  **inwards** (toe-**in**). Every toe number the skill stores, reads, or shows is the value **as it
  appears in the setup screen** — never a "corrected" physical value — so nothing is ever converted
  on read or write; only the *reasoning* maps:
  - want **toe-out** (front turn-in bite, rear rotation) → choose a **positive** value;
  - want **toe-in** (front straight-line stability, rear exit stability) → choose a **negative** value;
  - reading an existing / captured / imported value → **positive = toe-out, negative = toe-in**.
  The rally default (**front toe-out + rear toe-in**) is therefore **front positive, rear
  negative**. **Whenever you give the user toe values** — build report, tweak change table, review,
  share snippet, import preview — add a one-line warning that ACR's toe sign is inverted, saying
  which direction the given numbers actually produce and that they must be entered **exactly as
  given** (don't flip them). Authoritative statement:
  `references/parameter-reference-template.md` → *Toe*.
- **Notion scope is `ACR Setup Engineer` only — never search broadly.** Navigate the hierarchy
  explicitly by name starting from the `ACR Setup Engineer` root; do not issue workspace-wide Notion
  searches to locate setup data, guidelines, or parameters. If a Notion API call returns results
  from outside `ACR Setup Engineer`, discard them entirely before processing. Out-of-scope content must
  never influence setup values, guideline layers, or parameter catalogs, even if it mentions car
  names or setup terms.
- **Skip `FFB Multiplier`.** It is a controller/display preference, not a car setup parameter —
  never capture it during onboarding and never include it in setups.
- **Skill version.** Determine once per run and record it on every `Setups` row you create
  (generated, tweaked, captured, **and imported**). Read the bundled `VERSION` file at the skill root:
  - If it holds a concrete version (e.g. `v0.3.0`), that **is** your skill version.
  - If it holds `dev` (an unreleased source checkout): if you can run `git` in the skill's repo,
    use `git describe --tags --always --dirty` (e.g. `v0.2.0-3-gdbc15b1`, or a bare short hash if
    there are no tags); otherwise record `dev`.
- **Append-only.** Never modify or delete existing setups — only add rows. (Onboarding may
  update the parameter catalog.)
- **A car's pages are split by ownership — respect it exactly.** Each `{Car}` umbrella page holds
  five children — four for a template car (`notion-structure.md` → *Car page*):
  - **`Guidelines` is the user's.** Create it once, empty, at onboarding; after that **read it and
    never write to it** — not to append, tidy, reformat, or record what a build decided. If
    something belongs there, tell the user and let them paste it.
  - **`Catalog` is the skill's, and disposable.** It is **replaced wholesale** on every refresh —
    no diffing, no merging, no asking, no preserving edits. It carries a banner saying so. This is
    only safe *because* the user's writing lives on a different page, so never move user content
    onto it. It also carries the **catalog source line**, which says whether this car's legal
    values come from a bundled template or from the user's screenshots — and therefore where
    every workflow reads them from.
  - **`Log` is shared, and precious.** The car's running log: the user's own notes about the car,
    written anywhere on the page, plus the skill's dated record of what the driver reported after
    drives. **Add-only for the skill:** append one new dated entry directly below the maintenance
    line, so the newest is at the top; **never edit, reorder, merge or delete any existing block —
    the user's or an earlier entry of its own** — and **never rewrite it on a refresh**.
    **`build`, `tweak` and `review` read the whole page** — a **separate fetch**, batched with
    `Guidelines` (`build-setup.md` step 2, `tweak-setup.md` step 3, `review-setup.md` step 3) — as
    context about this driver and car. It
    is evidence, **not a guideline layer**, so `Guidelines` still outranks it, and a user note
    that is really a standing tuning rule gets *offered* for `Guidelines` in chat, never moved
    there. `ask` doesn't read it. Unlike `Catalog` none of it can be
    regenerated. It was called `Feedback` before; a legacy page of that name is **renamed in
    place** (`notion-structure.md` → *Resolving the page (`Log`, and the legacy `Feedback`
    name)*).
  - **`Parameters` is the skill's, and the only copy** (screenshot cars only). Written by
    onboarding and `edit-catalog.md`; a refresh never regenerates it. Users change it by saying
    the change in chat.
  - **`Setups`** holds the car's filtered linked view and nothing else.
- **Refining is an in-chat loop — save only when asked.** Describing a handling problem or asking
  for a tweak is **not** a request to build or save a setup. Work the *problem → tweak → test →
  feedback* cycle conversationally: propose legal value changes in chat and iterate as the user
  reports back from driving — **write nothing to Notion**, with **one named exception**: every
  round of feedback writes one dated entry on the car's **`Log`** page as it ends — a
  driving-feedback interview's record when one ran (on every path,
  `driving-feedback-interview.md` → *Recording the outcome*), otherwise the user's own words and
  the changes proposed (`tweak-setup.md` step 5). That
  entry is add-only history of what the driver said, not a setup write. It is the **only** write
  the exception allows — never a `Setups` row, a `Notes` verdict, a row toggle or anything on
  `Guidelines`, and never anything at any other point in the loop. Persist a single new `Setups` row (the
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
  bundled car troubleshooting (the matching file in `car-troubleshooting/`, if one exists —
  overrides the base for the symptoms it names) → global `Tuning guidelines` → matching surface
  section (that page's
  "Per surface" subsection, not a separate page) → per-car guidelines (the car's **`Guidelines`**
  child page) → the setup's own driving intent (most specific).
  **The per-car layer is its own page and its own fetch** — `Guidelines` sits beside `Catalog`
  under `{Car}`, so fetching identity facts does **not** pick it up. Any workflow that chooses or
  judges setup values (`build`, `tweak`, `review`, `ask`) must read it explicitly, batched with its
  other reads. Missing it fails silently: the setup just quietly ignores everything the user
  wrote about the car.
  **The car's `Log` page is *not* one of these layers.** `build` and `tweak` fetch it in the same
  batch and read it as **context/evidence** about this driver and car — never as a layer that can
  outrank `Guidelines` (`notion-structure.md` → *`Log` page*).
  Location/stage facts are objective inputs, not a guideline layer. More specific is the
  **default lean** — on a **material conflict between authored layers, ask the user** which to
  follow rather than silently picking one. Cite a user guideline when it drives a choice.
- **Notion by name.** Resolve the structure by its canonical names and create whatever is
  missing (per `references/notion-structure.md`); don't rely on stored IDs.
- **Keep the skill's own root pages current — once per chat.** The first time a workflow resolves
  the structure, fetch `How to use` in the same batch; if it's missing or its banner shows another
  skill version, rewrite `How to use`, `Claude Free plan` and `Parameter reference` and tell the
  user once to say *"refresh my ACR Notion"* for their car pages
  (`references/notion-structure.md` → *Keeping them current — the version check*). Never refresh
  car pages from this check.
- **Reading a catalog.** Every car's catalog is a template file — bundled, or the `yaml` block
  on the car's `Parameters` page — loaded by `references/catalog-read.md`: no token, no network,
  on every plan. **Reading `Setups` rows** (learn pool, stored default) is the REST query in
  `references/notion-rest-read.md`; check the network once per chat first
  (`scripts/check_egress.py`) and on `egress: none` run no REST query for the rest of the chat
  (that doc's *Offline mode*). Never substitute connector row-listing, never guess.
- **Read efficiently — collapse round-trips.** Seeding context is slow when reads are done one at a
  time. After resolving the structure once, the remaining reads are **independent**: issue them
  **together in a single step (parallel tool calls)** — e.g. the `Setups` DB fetch for its
  `data_source_id`, the car's `Catalog` / `Guidelines` / `Log` pages (`Log` in `build`, `tweak` and `review` only), the
  `Tuning guidelines` page, and any `{Stage}`/`{Location}` page — rather than one-by-one. Run
  **all** REST queries (`scripts/query_notion_parameters.py`) in **one code-execution block**.
  A screenshot car's `Parameters` page is fetched in that same batch (`catalog-read.md`) — run
  `scripts/load_catalog.py` in the same code-execution block as the `Setups` slices. **Fetch each page once**
  (identity facts on `Catalog`, the user's notes on `Guidelines`, the driving history and the
  user's car notes on `Log`), **reuse
  resolved IDs / `data_source_id`s** within the run, and **don't read anything already in the
  thread**.
- **Batch Notion writes — never loop one row / one column per call** (it's slow and token-heavy).
  Create many database rows in a **single `notion-create-pages` call** (its `pages[]` takes up to
  100; split into 100-row batches only if there are more). Create or extend a DB's columns in one
  call too: a single `notion-create-database` `CREATE TABLE` for a new DB, or a single
  `notion-update-data-source` with **all** `ADD COLUMN`s combined (semicolon-separated). So any car's
  `Setups` value columns and all imported setup rows each go in **one** call, not dozens. (A car's
  catalog is never rows: it is one `yaml` block on its `Parameters` page, written in one update.)
- **Assert column order on every `Setups` write — MANDATORY, never skip.** Any time you create a
  `Setups` linked view **or** append/update a `Setups` row, you **must**, in the same action, set
  the column order: run `scripts/query_notion_parameters.py … --show-order` and apply the result as
  the view `SHOW` on **every** affected projection (the main `Setups` table, the car's page view,
  and any stage/location view). **One form, every view:** one `--from-template` per car the view
  spans — `references/notion-structure.md` → *Applying the order* — no token. Never merge two
  `SHOW` lists by hand. A Setups write is **not finished** until this is done — skip it and
  columns render alphabetically. This applies on **every** run, including quick / low-effort ones;
  it is a required step, never an optional polish. How-to: `references/notion-structure.md` →
  *Applying the order*.

## Choosing a value (per parameter)
Each catalog row — from the car's template file, bundled or on its `Parameters` page — is either
constrained to an exact set or left as a free numeric range —
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

On a **screenshot car**, `Discrete steps` for **numeric** params is **optional**: onboarding
leaves it blank, and the user constrains the parameter later by **saying so in chat**
(`references/edit-catalog.md`) — nobody edits the list by hand. For **`—` named-selection** params
onboarding seeds it with the option names the screenshots show (and the standard ACR lists for
`Tyre type`/brake pads); the user completes it the same way. On a **template car** the steps come
from the game files and are whatever the template says — editing them in chat copies the car onto
its own `Parameters` page (`references/edit-catalog.md`).

## Glossary (ACR)
- **Default / stock baseline** = the setup the *game itself* gives you before you change anything.
  Captured from setup-screen screenshots and stored as a `Setups` row with `Source = default`; it is
  the numeric anchor a build starts from (*Baseline first*, above).
- **Corner phases** — **entry** (turning in, usually still braking), **mid** (off the brakes, steady
  through the middle), **exit** (back on the throttle). Weight moves forward under braking, so the
  front governs entry; it moves back on power, so the rear governs exit. Every balance symptom
  resolves to a phase.
- **Adjuster ring** = ride height. **Gear set** picks a ratio family; **primary gear** = the
  final-drive pair.
- **LSD ramp (power/coast)**: lower angle = more lock. **Preload / plates** = base lock / number
  of friction plates.
- **ARB**: front stiffer → understeer; rear stiffer → oversteer.
- **Toe sign (ACR bug)**: positive setup-screen value = toe-**out**; negative = toe-**in** (see the
  core rule above).
- **Surfaces**: tarmac (stiffer, higher pressure), gravel & snow (softer, lower pressure).
