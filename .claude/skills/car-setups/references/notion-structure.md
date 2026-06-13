# Notion structure — blueprint & maintenance

The authoritative description of how this product lays out data in the user's Notion, and how
the skills **create and maintain** it. There is **no separate bootstrap step**: the skills
create whatever is missing, on first use. Read this before any skill writes to Notion.

## Resolution rule — find by name, create if missing

Skills locate the structure **by its canonical names**, not by hardcoded IDs, so it's portable
across workspaces and self-healing:

1. Search for the root page **`Car setups`**; create it if absent.
2. Under it, the game page (e.g. **`ACR`**); create if absent. Multiple `{Game}` pages may
   coexist — resolve a car under the game it was onboarded into, and ask the user if the same car
   name appears under more than one game.
3. Under the game: the **`Parameters`** DB, the **`Setups`** DB, and the **`Tuning guidelines`**
   page; create any that are missing (schemas below).
4. Per car/stage: the **`{Car}`** page and **`{stage}`** page with their filtered views.

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
access to Notion* in `README.md`). When present, the token lives on a **`Config`** page
directly under the `Car setups` root; the skill `notion-fetch`es that page to read it. The `Config`
page is **not** auto-created — only the user adds it. Treat its contents as a secret: never echo
the token back, copy it into other pages, or include it in exports.

## Hierarchy

```
Car setups (root page)
├── Config (page, optional)     holds the read-only Notion API token (see "Reading rows" below)
└── {Game}                      e.g. ACR
    ├── Parameters        (DB)  the catalog — one row per Car × Adjustment × Surface
    ├── Setups            (DB)  one row per setup
    ├── Tuning guidelines (page) global user preferences (seeded from the template)
    └── {Car} (page)            per car: identity facts (Drivetrain, Engine layout, Weight
        │                        bias, Weight), a "Guidelines" section, filtered views
        └── setups (section/page)
            └── {stage} (page)  stage description + driving style + filtered Setups view
```

Two DBs **per game** only — car/stage pages are **filtered linked views**, never new DBs.

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
- **Meta:** `Name` (title), `Car` (**Select**), `Stage` (**Select**),
  `Surface` (**Select**, options `Tarmac` / `Gravel` / `Snow`), `Game version`, `Date`,
  `Source` (`generated` | `imported`), `Mode` (`learn` | `independent`),
  `Rating` (**Select**, options `1`–`5`, higher = better; **blank = unrated**), `Notes`,
  **`Learn from this`** (checkbox). Make `Car`, `Stage`, and `Surface` **Select** (not plain text)
  so they render as **tags/pills** in the table — `Car` mirrors the `Parameters` DB's `Car` select,
  and `Surface` its `Tarmac`/`Gravel`/`Snow` options. When appending a setup row, **create-or-reuse**
  the matching option (Notion adds a new option if absent). Create `Rating` as a **Select** with five options `1` `2` `3`
  `4` `5` (in that order) — the picker then shows the user the valid values and prevents
  out-of-range entries — and give the column the description *"How good was this setup? 1 = poor …
  5 = great. Leave blank until you've driven it."* It is **user-entered** after driving — the skill
  never writes it, only reads it, mapping the chosen label to its integer (`"4"` → 4) for learn
  weighting / review. 
- **Values:** one property per tunable parameter (canonical `Adjustment` name), union across
  the game's cars; blank where a parameter doesn't apply. **Numeric** (Min/Max are numbers,
  whether continuous or discretely-stepped) → **Number**. **Named/string** (Min/Max are string
  labels, or `Discrete steps` contains named string options such as tyre compound) → **Select**,
  whose options are the union of every car's values for that Adjustment. Use `Text` as an
  acceptable alternative if the merged dropdown becomes noisy. Includes `Tyre type` and any
  car-specific params (transitions, centre/front diff, electronics, brake hardware) as they're
  discovered. Per-car legality is enforced by the **skill** against that car's `Parameters` row
  (range or `Discrete steps`) — Notion's column type is just storage. **Column display order**
  follows each parameter's `Order` (see *Setups column order* below), applied through the view's
  `SHOW` directive — never creation order.
- **`Learn from this`** gates the learning pool: `build-setup` `learn` mode learns only from
  checked rows. Default **unchecked for both** `generated` and `imported` — the user checks it
  after reviewing and deciding a setup is worth learning from.

## Setups column order — driven by the per-parameter `Order`

The display order of the `Setups` DB's **value columns** — and of every setup projection (the table
view, the per-car/per-stage linked views, the page-body justification toggle, the share snippet, and
exported templates) — is governed by each parameter's **`Order`** number in the `Parameters` catalog,
**not** by the order columns were created. Notion never reorders columns from row data, and SQL-DDL
schema insertion order does not reliably drive the rendered table — the lever is the view's **`SHOW`**
directive (see *Applying the order* below).

**Comparator.** Sort value columns by their parameter's **`Order` ascending**. A column whose
parameter has no `Order` falls back to `section_block + 990` (the end of its section), then by
`Adjustment` name. **Meta columns always come first**, before any value column, in this order:
`Name`, `Car`, `Stage`, `Surface`, `Date`, `Source`, `Mode`, `Rating`, `Learn from this`,
`Game version`, `Notes`.

**Ties are fine — never an error.** If two parameters share the same `Order` (e.g. after a manual
edit), show the tied columns in any order; don't flag, warn, or disambiguate. Order only has to be
right at the section / `Order` granularity.

### Canonical ACR default order (what onboarding assigns)
Numbering is **section-blocked** (`section×1000 + within×10`): the number encodes the section (so the
cross-car column union always groups correctly) and the ×10 gaps leave room to insert or renumber by
hand. Onboarding assigns these from the setup screens; the bundled templates carry them as `order:`.

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
  Pressure Front .................. 6020
  Camber Front .................... 6030
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
column order** — it is idempotent, so an alphabetized table or an edited `Order` self-heals on the
next run, with no migration:
1. Read `Order` per `Adjustment` from the `Parameters` catalog (workflows already read these rows via
   [notion-rest-read.md](notion-rest-read.md); for the **main** table's cross-car union, query the
   whole `Parameters` data source once to map every property name → `Order`).
2. Build the ordered property-name list (meta columns first, then value columns by the comparator).
3. Push it with the view **`SHOW`** directive (`notion-update-view`, or set it when creating a view
   via `notion-create-view`):
   - **main `Setups` table view** → `SHOW` all meta + all value columns in order;
   - **per-car / per-stage linked views** → `SHOW` meta + only that car's applicable value columns in
     order — this orders the columns **and** hides the blank ones in a single step.

## Car & stage pages

**`{Car}` page layout (top to bottom):**
1. **Car identity facts** on the page (stored the same way as each other, near the top):
   - **`Drivetrain`** (FWD/RWD/AWD).
   - **`Engine layout`** (descriptive placement, e.g. `mid-rear transverse V6 behind the driver`).
   - **`Weight bias`** (front/rear percentages, e.g. `~44% front / ~56% rear`).
   - **`Weight`** (approximate kerb weight, e.g. `~950 kg`).

   These are **car facts that inform tuning reasoning — not tunable parameters**; they never go in
   the `Parameters` DB. Any field the skill can't determine confidently is stored as the literal
   **`couldn't determine`** so the user knows it was attempted and can edit it by hand. Engine
   layout / weight bias / weight are populated during onboarding (see `onboard-car.md`); the user
   may overwrite any of them at any time.
2. **H2 "Setups"** heading — immediately followed by the `Setups[Car=this]` filtered linked
   view (hide blank columns). Stage sub-pages are nested here so they appear near the view.
3. **H2 "Guidelines"** heading — free-text car-specific preferences (seeded as a stub,
   tone per `tuning-guidelines-template.md`).

The `Parameters[Car=this]` filtered view is accessible via the Notion sidebar / linked DB;
it is **not** inlined on the car page body to keep the page short.

**Always create content in this order** when seeding or updating the `{Car}` page — the
Setups section must appear before Guidelines so it is the first thing visible on mobile.

- **`{stage}` page** — the stage description + driving style, plus a `Setups[Car, Stage]`
  filtered view. Nested under the car page's "Setups" section.

## `Tuning guidelines` page
Global user preferences, seeded from `tuning-guidelines-template.md`
(General style / Likes-Dislikes / Per surface). Part of the layered model in
[setup-tuning-principles.md](setup-tuning-principles.md): base (repo) → global → surface →
per-car → stage.

## Mobile conventions (pages are read on a phone, in-game)

Users often read these pages on a **phone while playing**, so:
- **Optimise for reading a single setup**, not side-by-side comparison (comparison stays a
  desktop task on the wide table view).
- Each generated setup's **page body contains only the per-parameter justification**, grouped
  by section, inside a **toggle** so it's collapsible. Order the sections and the parameters within
  them by each parameter's **`Order`** (see *Setups column order* above) — the same sequence as the
  in-game setup screens (Gearbox → Suspensions → Dampers → Axles → Differentials → Wheels/Tyres →
  Brakes → Electronics & Aerodynamics, Front before Rear). The same `Order` governs share snippets
  and exported templates, so every projection matches the table.
  **Never duplicate values into a page body checklist** — the database row is the single source
  of truth. A checklist would drift the moment the user edits a value in the table.
- **No wide tables inside page bodies** (they scroll horizontally on a phone); use short
  headings + bullet lists. Keep property names concise.
