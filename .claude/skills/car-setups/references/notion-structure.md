# Notion structure — blueprint & maintenance

The authoritative description of how this product lays out data in the user's Notion, and how
the skills **create and maintain** it. There is **no separate bootstrap step**: the skills
create whatever is missing, on first use. Read this before any skill writes to Notion.

## Resolution rule — find by name, create if missing

Skills locate the structure **by its canonical names**, not by hardcoded IDs, so it's portable
across workspaces and self-healing:

1. Search for the root page **`Car setups`**; create it if absent.
2. Directly under the root, the **`Config`** page (holds the read-only Notion API token). **Create
   it if absent, seeded from [config-page-template.md](config-page-template.md)** (the integration
   setup instructions + an empty token line). **Never overwrite an existing `Config` page** — it
   may already hold the user's pasted token; leave its contents untouched.
3. Under the root, the game page (e.g. **`ACR`**); create if absent. Multiple `{Game}` pages may
   coexist — resolve a car under the game it was onboarded into, and ask the user if the same car
   name appears under more than one game.
4. Under the game: the **`Parameters`** DB, the **`Setups`** DB, the **`Tuning guidelines`**
   page, the **`Parameter reference`** page, and the **`Locations`** catalogue page; create any
   that are missing (schemas below). Unlike the other pages, **`Parameter reference` is
   auto-maintained**: (re-)seed its body from `parameter-reference-template.md` on first create
   **and refresh it on skill updates** — it is not a user-editable layer (see its section below).
5. Per car: the **`{Car}`** page with its filtered view. Per location/stage referenced by a setup:
   the **`{Location}`** page and **`{Stage}`** page (under `Locations`) with their filtered views.

Never depend on stored page/database IDs — always re-resolve the structure **by name**. (You
may reuse an ID within a single run once you've found it, but a fresh run must still work.)

**Scope is `Car setups` only — never search broadly.** Once you've resolved the `Car setups`
root, navigate all deeper structure by name traversal (never issue a workspace-wide Notion search
to find setup data or guidelines). If a Notion API call returns results from outside `Car setups`,
discard them before processing. Anything outside that root is out of scope regardless of its
title or content — never treat it as a guideline, prior setup, or parameter source.

## Reading rows — use the REST query, not the connector
The Notion **connector cannot list a database's rows** (`notion-fetch` returns schema only;
`notion-search` is semantic, capped, and mixes cars). **Whenever a workflow needs a car's
`Parameters` rows or a filtered slice of `Setups`, follow
[notion-rest-read.md](notion-rest-read.md)** — it queries the data source over Notion's REST API
with an exact `Car` filter and pagination (reliable, complete, one call). If there's no token,
prompt the user through the one-time setup rather than substituting an unreliable connector read.

That read path uses a **read-only API token** the user sets up once (see *Give the skill read
access to Notion* in `README.md`). The token lives on a **`Config`** page directly under the
`Car setups` root; the skill `notion-fetch`es that page to read it. The `Config` page is
**auto-created** as part of the structure (create-if-missing, seeded from
[config-page-template.md](config-page-template.md)) carrying the integration-setup instructions and
an **empty token line** — so the page is normally present even before the user has pasted a token;
the user only has to follow the on-page steps and paste. Treat its contents as a secret: never echo
the token back, copy it into other pages, or include it in exports.

## Hierarchy

```
Car setups (root page)
├── Config (page)               holds the read-only Notion API token; auto-created with setup
│                                instructions, token blank until the user pastes it (see "Reading rows")
└── {Game}                      e.g. ACR
    ├── Parameters        (DB)  the catalog — one row per Car × Adjustment × Surface
    ├── Setups            (DB)  one row per setup
    ├── Tuning guidelines (page) global user preferences (seeded from the template)
    ├── Parameter reference (page) game parameter glossary — verbatim in-game descriptions of every
    │                            tunable parameter; seeded AND refreshed from the template; read-only
    ├── Locations         (page) catalogue parent — created on first stage/location reference
    │   └── {Location} (page)   e.g. Monte Carlo — facts only, filtered Setups[Location] view
    │       └── {Stage} (page)  e.g. Col de Turini — facts only (surface, length, key
    │                            corners/speeds, character), filtered Setups[Stage] view
    └── {Car} (page)            per car: identity facts (Drivetrain, Engine layout, Weight
                                 bias, Weight, Max power, Max torque), a "Guidelines" section,
                                 filtered Setups[Car] view
```

Two DBs **per game** only — car/location/stage pages are **filtered linked views**, never new
DBs. A stage is **immutable, shared reference data** — it is created once under `Locations` and
referenced by any number of setups (any car, any number of times), never duplicated per car.

**Batch every write (`SKILL.md` → *Batch Notion writes*).** Create a DB with its **full column set
in one `notion-create-database` `CREATE TABLE`**; when adding columns to an existing DB, combine
**all** `ADD COLUMN`s into **one** `notion-update-data-source` call. Create many rows (a car's whole
`Parameters` catalog, all imported setup rows) in **one** `notion-create-pages` call (≤100 rows;
batch in 100s only if more). Never add columns or rows one call at a time — it's slow and
token-heavy.

## `Parameters` DB — one row per `Car × Adjustment` (× `Surface` when ranges differ)
`Car`, `Section`, `Adjustment` (title), `Min`, `Max`, `Unit`, **`Discrete steps`**, **`Order`**,
and an optional **`Surface`**. The authoritative legal-value catalog. Parameter availability is
**per car** — absent parameters simply have no row.

- **`Surface`** (Select, **optional**) — options `Tarmac`, `Gravel`, `Snow`. **Blank = the
  default/baseline** range, captured from the required **tarmac** onboarding pass; it applies to
  **any** surface that has no surface-specific override row. Most parameters keep a single
  blank-`Surface` row. A few parameters (chiefly on the **Suspensions** screen — e.g. spring
  stiffness) expose a **different range on gravel**; for those, a second row tagged
  `Surface = Gravel` (or `Snow`) holds the surface-specific `Min`/`Max`/`Discrete steps`. The
  blank-`Surface` row and a `Gravel` row for the same `Car × Adjustment` coexist legitimately.
  - **Row key (upsert):** `Car` + `Adjustment` + `Surface` — match on all three; update if
    present, else create. A blank `Surface` is itself a distinct key value (the baseline row).
  - **Resolution rule** (how `build-setup`/`tweak`/`review`/`import` pick a parameter's legal
    range for a setup on surface **S**): use the row whose `Surface = S` **if one exists**;
    **else if `S = Snow`, fall back to a `Gravel` row** (snow inherits gravel's softer ranges —
    onboarding does a gravel pass but no separate snow pass); else fall back to the
    **blank-`Surface`** row. If none exists, the parameter isn't available for that car. (Same
    rule documented for readers in [notion-rest-read.md](notion-rest-read.md).)
  - **Backward compatible:** existing catalogs are entirely blank-`Surface`, so every parameter
    resolves to its single row on every surface — unchanged behavior, no migration.
- **`Min` / `Max`** — the extremes read from the min/max setup screenshots. Always capture the
  actual values shown, including for discretely-stepped parameters (e.g. gear set Min=1, Max=3).
  Use `—` only for **named-selection params** — either component/compound names with no numeric
  ordering (`Tyre type`, `Brake calipers`, `Brake discs`, `Brake pads`, `Engine map`,
  `Throttle map`) **or paired/slash values that cannot be meaningfully ordered as a single
  number** (`LSD Power/Coast Ramp` values like `45/55`; `Differential Ratio` and `Centre Ratio
  to Rear` values like `65//17`). Also use `—` for non-adjustable rows.
- **`Discrete steps`** — free text, comma-separated. For **numeric** params it is **optional
  and user-owned**: onboarding leaves it **blank** and the user fills it in Notion whenever they
  want to pin the parameter to an exact set of values (e.g. spring stiffness
  `42300, 50000, 57700, 65400, 73100`). For **`—` named-selection** params onboarding **seeds
  it with the option names observed in the screenshots** (observed values only — typically the
  two endpoints) so the user only completes the in-between options; for **ACR** it pre-fills the
  standard lists for `Tyre type` (full tyre list) and `Brake pads` (`SOFT, MEDIUM, HARD`),
  which are immediately usable. **When present it is the authoritative legal set** for that
  car's parameter; when blank the parameter is treated as continuous over `Min..Max`.
- **`Order`** (Number) — the parameter's **display position**, driving the order of every `Setups`
  column and every setup projection. Seeded at onboarding from the order the parameter appears on
  the in-game setup screens (canonical ACR defaults + numbering in **Setups column order** below);
  the bundled templates carry it as `order:`. **User-owned:** the user may renumber it in Notion to
  rearrange columns, and the change shows on the next onboard/build. It is **per `Adjustment`** — a
  surface-specific row carries the **same `Order`** as its baseline row (both collapse to one
  `Setups` column).
- A row read as **"no adjustment"** in-game is recorded as not adjustable (don't fabricate a
  range). There is no `Steps` / `Step size` / `Type` column — the presence of `Discrete steps`
  (vs. a numeric `Min..Max`) is what tells `build-setup` how to choose a value.
- **Create-if-missing:** include the `Surface` select **and the `Order` number** when first creating
  the `Parameters` DB. When writing to a **pre-existing** DB that lacks a property, add it first
  (`Surface` select before a surface-tagged row; `ADD COLUMN "Order" NUMBER` before writing `Order`),
  then write the row. Never tag the baseline rows — leave their `Surface` blank.

## `Setups` DB — one row per setup
- **Meta:** `Name` (title), `Car` (**Select**), `Location` (**Select**, optional), `Stage`
  (**Select**, optional), `Surface` (**Select**, options `Tarmac` / `Gravel` / `Snow`),
  `Game version`, `Date` (**Date**, stores date *and* time), `Source` (`generated` | `imported`),
  `Mode` (`learn` | `independent`),
  `Rating` (**Select**, options `1`–`5`, higher = better; **blank = unrated**), `Notes`,
  **`Learn from this`** (checkbox), `Model` (**Select**), `Skill version` (**Text**).
  Make `Car`, `Location`, `Stage`,
  and `Surface` **Select** (not plain text) so they render as **tags/pills** in the table — `Car`
  mirrors the `Parameters` DB's `Car` select, and `Surface` its `Tarmac`/`Gravel`/`Snow` options.
  **`Location` and `Stage` are both optional and independently blankable** — a setup may name
  neither (an arbitrary build with no place context, e.g. "drift setup, tarmac"), a `Location`
  only, or both. A setup's **driving intent / conditions are not a column** — they live in the
  setup's own page-body summary (see *Mobile conventions* below); `Location`/`Stage` carry only
  the place reference, never style or goals.
  **`Model`** is also a **Select** (renders as a tag) holding **just the model name + version**,
  e.g. `Opus 4.8` or `Sonnet 4.6`; give the column the description *"Which model+version built this
  setup (e.g. Opus 4.8). Blank for imported setups."* **Blank for imported rows** — only `generated`
  setups write it. The skill self-identifies with its known model name. No predefined options —
  create-or-reuse (Notion adds the option if absent).
  **`Skill version`** is plain **Text** (not Select — it's a free-form string, not a small fixed
  set) recording **which version of the car-setups skill created this row**: the skill's
  `VERSION` file when released, or a `git describe` string for an unreleased source checkout (see
  `SKILL.md` → *Skill version*). Give the column the description *"Which version of the
  car-setups skill created this row (e.g. v0.3.0, or a git-describe string for source builds)."*
  Unlike `Model`, it is written on **every** skill-created row — generated, tweaked, **and
  imported** — since it identifies the tool/logic that produced the row, not the model that
  authored values. When
  appending a setup row, **create-or-reuse** all Select options (Notion adds a new option if
  absent). Create `Rating` as a **Select** with five options `1` `2` `3`
  `4` `5` (in that order) — the picker then shows the user the valid values and prevents
  out-of-range entries — and give the column the description *"How good was this setup? 1 = poor …
  5 = great. Leave blank until you've driven it."* It is **user-entered** after driving — the skill
  never writes it, only reads it, mapping the chosen label to its integer (`"4"` → 4) for learn
  weighting / review.
  **`Date`** is a **Date** property that stores **date *and* time** (Notion renders the time
  whenever the stored value carries one — no special column type needed). Write it on **every**
  skill-created row — generated, tweaked, **and imported** — as the current local date/time, and
  get that value **deterministically by running Python**, never by typing the model's guess at the
  wall-clock time:
  `python -c "import datetime; print(datetime.datetime.now().astimezone().isoformat(timespec='minutes'))"`
  (prints e.g. `2026-06-29T14:32+02:00`; write that string into `Date`). Give the column the
  description *"When this row was created (local date + time), set deterministically by the skill."*
- **Values:** one property per tunable parameter (canonical `Adjustment` name), union across
  the game's cars; blank where a parameter doesn't apply **to this car** (or for the documented
  `FFB Multiplier` exception) — never as a "default" for a parameter the car has; a setup must
  give every applicable parameter an explicit value (`SKILL.md` → *Core rules*). **Numeric** (Min/Max are numbers,
  whether continuous or discretely-stepped) → **Number**. **Named/string** (Min/Max are string
  labels, or `Discrete steps` contains named string options such as tyre compound) → **Select**,
  whose options are the union of every car's values for that Adjustment. Use `Text` as an
  acceptable alternative if the merged dropdown becomes noisy. Includes `Tyre type` and any
  car-specific params (transitions, centre/front diff, electronics, brake hardware) as they're
  discovered. Per-car legality is enforced by the **skill** against that car's `Parameters` row
  (range or `Discrete steps`) — Notion's column type is just storage. **Column display order**
  puts the value columns (by each parameter's `Order`) right after `Name`, with the rest of the
  meta columns last (see *Setups column order* below), applied through the view's `SHOW`
  directive — never creation order.
- **`Learn from this`** gates the learning pool: `build-setup` `learn` mode learns only from
  checked rows. Default **unchecked for both** `generated` and `imported` — the user checks it
  after reviewing and deciding a setup is worth learning from.

## Setups column order — driven by the per-parameter `Order`

The display order of the `Setups` DB's **value columns** — and of every setup projection (the table
view, the per-car / per-location / per-stage linked views, the page-body justification toggle, the
share snippet, and exported templates) — is governed by each parameter's **`Order`** number in the `Parameters` catalog,
**not** by the order columns were created. Notion never reorders columns from row data, and SQL-DDL
schema insertion order does not reliably drive the rendered table — the lever is the view's **`SHOW`**
directive (see *Applying the order* below).

**Comparator.** `Name` (the title column) is always first — Notion forces the title column
leftmost regardless of `SHOW` order. Next come the **value columns**, sorted by their parameter's
**`Order` ascending**. A column whose parameter has no `Order` falls back to `section_block + 990`
(the end of its section), then by `Adjustment` name. **The rest of the meta columns come last**,
after every value column, in this order: `Car`, `Location`, `Stage`, `Surface`, `Date`, `Source`,
`Mode`, `Rating`, `Learn from this`, `Game version`, `Notes`, `Model`, `Skill version`. This
puts the setup's tunable values first for fast on-phone reading, with bookkeeping metadata trailing.

**Ties are fine — never an error.** If two parameters share the same `Order` (e.g. after a manual
edit), show the tied columns in any order; don't flag, warn, or disambiguate. Order only has to be
right at the section / `Order` granularity.

### Canonical ACR default order (what onboarding assigns)
Numbering is **section-blocked** (`section×1000 + within×10`): the number encodes the section (so the
cross-car column union always groups correctly) and the ×10 gaps leave room to insert or renumber by
hand. Onboarding assigns these from the setup screens; the bundled templates carry them as `order:`.

**This is the common per-corner sequence, not a guarantee for every car.** The list below (e.g.
Dampers: Slow Bump, Slow Rebound, Fast Bump, Fast Rebound) reflects how most cars lay out their
setup screens, but **the in-game screen order for the car being onboarded is always authoritative**
— some cars group their corner sub-parameters differently (e.g. all bump settings before all
rebound settings). Never carry over another car's layout, or this default list's sequence, when it
conflicts with what the current car's screenshots (or its bundled template) actually show; apply
this numbering scheme **to the observed order**, not the other way around.

```
Gearbox (1000)
  Gear Set ........................ 1010
Suspensions (2000)                (per corner: Adjuster Ring, then Spring Stiffness)
  Adjuster Ring Front ............. 2010
  Spring Stiffness Front .......... 2020
  Adjuster Ring Rear .............. 2030
  Spring Stiffness Rear ........... 2040
Dampers (3000)                    (per corner: Slow Bump, Slow Rebound, Fast Bump, Fast Rebound)
  Slow Bump Front ................. 3010
  Slow Rebound Front .............. 3020
  Fast Bump Front ................. 3030
  Fast Rebound Front .............. 3040
  Slow Bump Rear .................. 3050
  Slow Rebound Rear ............... 3060
  Fast Bump Rear .................. 3070
  Fast Rebound Rear ............... 3080
Axles (4000)
  Anti-roll Bar Stiffness Front ... 4010
  Anti-roll Bar Stiffness Rear .... 4020
Differentials (5000)              (per corner: LSD Power/Coast Ramp, LSD Preload, Plates Number)
  LSD Power/Coast Ramp Front ...... 5010
  LSD Preload Front ............... 5020
  Plates Number Front ............. 5030
  LSD Power/Coast Ramp Rear ....... 5040
  LSD Preload Rear ................ 5050
  Plates Number Rear .............. 5060
Wheels/Tyres (6000)               (per corner: Pressure, Camber, Toe; FFB Multiplier skipped)
  Tyre Type ....................... 6010   (tyre-compound choice — leads the section)
  Pressure Front .................. 6020   (front/rear pressure are always two Number columns —
  Camber Front .................... 6030    never a single combined "Tyre Pressure" column)
  Toe Front ....................... 6040
  Pressure Rear ................... 6050
  Camber Rear ..................... 6060
  Toe Rear ........................ 6070
Brakes (7000)                     (front hardware → central brake-system box → rear hardware)
  Brake Discs Front ............... 7010
  Brake Calipers Front ............ 7020
  Brake Pads Front ................ 7030
  Front Bias ...................... 7040
  Front Cylinder .................. 7050
  Rear Cylinder ................... 7060
  Handbrake Force ................. 7070
  Brake Discs Rear ................ 7080
  Brake Calipers Rear ............. 7090
  Brake Pads Rear ................. 7100
Electronics & Aerodynamics (8000) (Additional Lights toggle not captured — omitted)
  ABS Map ......................... 8010
  TCS Map ......................... 8020
```

**Car-specific extras** not in this list (AWD centre/front diffs, damper bump/rebound *transitions*,
engine/throttle map, master-cylinder variants, adjustable aero, …) get a number **inside the right
section block**, from their screenshot position (e.g. a centre diff between the front & rear diff
groups → ~5032; a bump transition in Dampers → ~3045). The exact within-section slot need not be
perfect — the section block keeps them grouped (this is the accepted fallback for cars whose
parameter set differs from the list).

### Applying the order (the `SHOW` operation)
Whenever a workflow creates/updates the `Setups` schema **or appends a setup row**, **(re)assert the
column order**. It is idempotent, so an alphabetized table or an edited `Order` self-heals on the
next run, with no migration.

**A new linked view shows its columns alphabetically until you assert `SHOW`.** So you must always
push `SHOW`, both when first creating a view and on every later write — and push it **after** the
value columns exist (i.e. after the schema/rows are written), or it can't order columns that
aren't there yet.

**Get the `SHOW` list from the bundled script — don't assemble it by hand.** Run, against the
**`Parameters`** data source (using the read token from `notion-rest-read.md`):

```
# per-car view (lists only that car's value columns, then the meta columns):
python scripts/query_notion_parameters.py <params_data_source_id> <token> "{Car}" --show-order
# main table / per-location / per-stage views (union of all value columns):
python scripts/query_notion_parameters.py <params_data_source_id> <token> --all --show-order
```

**Token-free path — when the car's catalog was just created from a bundled template this run** (e.g.
an import auto-onboard, `import-savegame.md` step 5): you already hold every `Order` locally, so there
is **no reason to read it back from Notion**. Get the same list from the template file(s) — **no
token, no `Config` page, no network**:

```
# per-car view — the just-onboarded car's template:
python scripts/query_notion_parameters.py --show-order --from-template car-templates/<car>.yaml
# main table — the union, one --from-template per imported car:
python scripts/query_notion_parameters.py --show-order --from-template <c1>.yaml --from-template <c2>.yaml …
```

This still goes **through the script** (the same `Order`-driven comparator below) — it is **not**
hand-assembly, so the "don't assemble it by hand" rule holds. Use the **token** form above only for
cars whose catalog you read back from Notion (already onboarded before this run). Either form prints
the exact, ready-to-paste property list: `"Name"`, then value columns by `Order`, then the fixed meta
columns (`Car` … `Model`, `Skill version`). Use it verbatim as the `SHOW` value:

- **main `Setups` table view** → `--all --show-order`; `SHOW <script output>`;
- **per-car linked view** (on the `{Car}` page, filtered `Car = "{Car}"`) → `"{Car}" --show-order`;
  `SHOW <script output>` — this orders the columns **and** hides the blank ones in one step (the
  script lists only that car's value columns);
- **per-location / per-stage linked views** (on `{Location}` / `{Stage}` pages, filtered by
  `Location` / `Stage` only — **not** `Car`, since many cars can share a place) → `--all
  --show-order`; `SHOW <script output>`.

Push it with the view **`SHOW`** directive — `notion-update-view` for an existing view, or the
`configure` string when first creating the view (*Creating an inline linked view* below). Because
this is re-asserted on every append, projections created before a meta column existed (e.g.
`Model`, `Skill version`) **self-heal** on the next build/tweak/review.

(Background — what the script encodes: `Name` first, value columns by `Order` ascending — a
parameter with no `Order` sorts last by name — then the fixed meta order from *Setups column order*
above. You don't compute this yourself; the script does.)

This step re-asserts `SHOW` on a view that **already exists**. Creating the linked-view *block* in
the first place is a separate operation — see *Creating an inline linked view* below
(`notion-create-view` with `parent_page_id`); never express a linked view as page markdown.

## Car page

**`{Car}` page layout (top to bottom):**
1. **Car identity facts** on the page (stored the same way as each other, near the top):
   - **`Drivetrain`** (FWD/RWD/AWD).
   - **`Engine layout`** (descriptive placement, e.g. `mid-rear transverse V6 behind the driver`).
   - **`Weight bias`** (front/rear percentages, e.g. `~44% front / ~56% rear`).
   - **`Weight`** (approximate kerb weight, e.g. `~950 kg`).
   - **`Max power`** (peak power with rpm, e.g. `250 hp at 7700 rpm`).
   - **`Max torque`** (peak torque with rpm, e.g. `260 Nm at 6000 rpm`).

   These are **car facts that inform tuning reasoning — not tunable parameters**; they never go in
   the `Parameters` DB. Any field the skill can't determine confidently is stored as the literal
   **`couldn't determine`** so the user knows it was attempted and can edit it by hand. Engine
   layout / weight bias / weight / max power / max torque are populated during onboarding (see
   `onboard-car.md`); the user may overwrite any of them at any time. **Max power / max torque may be
   left blank** — unlike the others they aren't web-looked-up on the screenshot path (the user is
   only asked for them optionally), so a blank field is normal rather than `couldn't determine`.
2. **H2 "Setups"** heading — immediately followed by the `Setups[Car=this]` filtered linked
   view (hide blank columns).
3. **H2 "Guidelines"** heading — free-text car-specific preferences (seeded as a stub,
   tone per `tuning-guidelines-template.md`).

The `Parameters[Car=this]` filtered view is accessible via the Notion sidebar / linked DB;
it is **not** inlined on the car page body to keep the page short.

**Always create content in this order** when seeding or updating the `{Car}` page — the
Setups section must appear before Guidelines so it is the first thing visible on mobile.

**The car page never holds stage sub-pages.** Stage and location facts live in the shared
catalogue below, not nested under any one car — a stage is referenced by `Stage` (and `Location`)
tags on `Setups` rows, never duplicated per car.

## Locations & stages catalogue — shared, immutable facts

A **stage is reference data, not per-car content**: its road, surface, length, and corners don't
change depending on which car drives it. So locations and stages live **once**, centrally, under
the game page, and any number of `Setups` rows (any car) reference them by name via the `Location`
/ `Stage` select tags. **Stage/location pages hold objective facts only — never guidelines,
driving style, or per-build conditions** (those live on the setup itself; see `build-setup.md`
and *Mobile conventions* below).

```
Locations (page)            catalogue parent — created on first reference, under {Game}
└── {Location} (page)       e.g. Monte Carlo — region/character facts
    └── {Stage} (page)      e.g. Col de Turini — surface, length, key corners/speeds, character
```

- **`{Location}` page** — free-text facts about the place (region, typical conditions/character),
  plus a `Setups[Location=this]` filtered linked view (no `Car` filter — shows every car's setups
  at this location).
- **`{Stage}` page** — free-text facts about the specific stage: **surface** (Tarmac/Gravel/Snow),
  approximate length, key corners/speeds, and general character (fast/flowing, tight/technical,
  rough/smooth). Plus a `Setups[Stage=this]` filtered linked view (no `Car` filter).
- **Create-if-missing, resolve by name:** when a setup names a location/stage that doesn't exist
  yet, create the `{Location}` page (if missing) under `Locations`, then the `{Stage}` page (if
  missing) under it, from the facts the user gives (or asks for) — see `build-setup.md` step 7.
  When the same stage is referenced again (any car), reuse the existing page — **never create a
  second stage page for the same name.**
- **A setup may reference a `Location` and/or `Stage`, or neither** — both are optional, blankable
  tags. An arbitrary build with no place context (e.g. "drift setup for the Stratos, tarmac") is
  valid and leaves both blank.

### Creating an inline linked view
A "filtered linked view" is a Notion **linked database view**, created with the
**`notion-create-view`** tool — **not** page markdown. **There is no Markdown syntax for a linked
view; never write a placeholder (e.g. `<linked-view />`, `[linked view]`, or a heading promising a
table) into a page's `content`** — it is stored as literal text and no table appears.

**Mechanism.** `notion-fetch` the `Setups` DB to get its **`data_source_id`** (from the
`<data-source>` tag in the response). Get the **`SHOW` list from the script** (*Applying the order*
above — `--show-order`, with `--all` for location/stage). Then call `notion-create-view` with
`parent_page_id` = the target page, `data_source_id` = the `Setups` data source, `type: "table"`, a
`name` (e.g. `"Setups"`), and a `configure` DSL string (see `notion://docs/view-dsl-spec`) carrying
the filter and the script's `SHOW` list:
- **`{Car}` page** → `FILTER "Car" = "{Car}"; SHOW <output of `… "{Car}" --show-order`>` — `SHOW`
  both orders the columns and hides the ones it omits (blank per-car columns).
- **`{Location}` page** → `FILTER "Location" = "{location}"; SHOW <output of `… --all --show-order`>`
  — no `Car` filter, since many cars may share a location.
- **`{Stage}` page** → `FILTER "Stage" = "{stage}"; SHOW <output of `… --all --show-order`>` — no
  `Car` filter, same reasoning.
Because the value columns must already exist for `SHOW` to order them, if you create the view before
writing the setup's value columns, **re-assert `SHOW`** (*Applying the order*) right after the
columns/rows are written.

**Positioning matters.** `notion-create-view(parent_page_id=…)` **appends the linked-view block to
the end of the page**, so sequence the operations:
1. Write the page markdown first — identity facts + the **H2 "Setups"** heading (`{Car}` page), or
   the facts (`{Location}` / `{Stage}` page).
2. **Then** `notion-create-view` — the view lands right after that heading/description.
3. **Then** append any trailing markdown (e.g. the `{Car}` page's **H2 "Guidelines"** stub).
   Never add the trailing section before the view, or the view ends up below it.

**Idempotent.** Before creating, `notion-fetch` the page; if a linked view of the `Setups` data
source already exists there, re-assert it with `notion-update-view` (see *Applying the order*)
instead of appending a duplicate.

## `Tuning guidelines` page
Global user preferences, seeded from `tuning-guidelines-template.md`
(General style / Likes-Dislikes / Per surface). The page's **"Per surface" section** *is* the
**surface** layer of the model below — there is no separate per-surface store. Part of the
layered model in [setup-tuning-principles.md](setup-tuning-principles.md): base (repo) → global →
surface → per-car → **the setup's own driving intent** (most specific). Location/stage facts are
**not** a guideline layer — they're objective inputs (surface, corners) read from the catalogue
above. More-specific is the default lean; a **material conflict between authored layers (global,
surface, per-car, intent) is surfaced to the user to resolve, not auto-picked.**

## `Parameter reference` page
A global, per-game **glossary**: the **verbatim in-game descriptions of every tunable parameter**
(what each setting does, grouped by setup screen — Gearbox → Suspension → Dampers → Axles → Wheels →
Brakes → Differentials → Electronics & Aerodynamics), so the user can read them on a phone without
opening the game. Seeded from [parameter-reference-template.md](parameter-reference-template.md).

**Unlike `Config` and `Tuning guidelines`, this page is auto-maintained and is NOT a
create-if-missing-then-never-touch page and NOT a user-editable guideline layer.** (Re-)seed it from
the template on first create **and refresh its body on skill updates** so the game text stays
current. The seeded body opens with a **read-only banner** telling the user not to add notes here
(they'd be overwritten) — personal tuning preferences belong on `Tuning guidelines` instead. It is
purely reference and plays no part in the layered tuning model above.

**How to create / refresh (do this exactly):** copy **everything below the `---` line** in
`parameter-reference-template.md` (the banner + all parameter sections) as the page body.
- **Create (page absent):** create the page under `{Game}` titled exactly `Parameter reference` and
  write that content as its body.
- **Refresh (page already exists):** **replace** the body — first **delete every existing block on
  the page**, then write the current template content fresh. **Do not append** (appending
  duplicates the whole glossary). If you can't cleanly clear the blocks, it's safe to skip the
  refresh and leave the existing page as-is rather than append.
- This is a **whole-page overwrite**, so the "never overwrite" caution that applies to `Config` and
  `Tuning guidelines` **does not apply here** — the page holds only shipped game text, never user
  input, so there's nothing of the user's to lose.

## Mobile conventions (pages are read on a phone, in-game)

Users often read these pages on a **phone while playing**, so:
- **Optimise for reading a single setup**, not side-by-side comparison (comparison stays a
  desktop task on the wide table view).
- Each generated setup's **page body** has two sections, in this order:
  1. **Brief setup summary** — always visible (not inside a toggle): an **H2 heading** with the
     setup name, followed by 3–5 bullets covering location/stage/surface, **the driving
     intent/conditions for this build** (its only home — there's no `Setups` column for it), tyre
     choice, the key guidelines applied (citing user guidelines by name), and what prior setups
     contributed (or "no prior setups used" if none). Mirrors what the chat report says, stored
     permanently for quick on-phone reference.
  2. **Per-parameter justification** — grouped by section (Gearbox → Suspensions → Dampers →
     Axles → Differentials → Wheels/Tyres → Brakes → Electronics & Aerodynamics, Front before
     Rear), inside a **toggle** so it's collapsible. Ordered by each parameter's **`Order`** (see
     *Setups column order* above) — the same sequence as the in-game setup screens. The same
     `Order` governs share snippets and exported templates, so every projection matches the table.
  **Never duplicate values into a page body checklist** — the database row is the single source
  of truth. A checklist would drift the moment the user edits a value in the table.
- **No wide tables inside page bodies** (they scroll horizontally on a phone); use short
  headings + bullet lists. Keep property names concise.
