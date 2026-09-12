# Notion structure — blueprint & maintenance

The authoritative description of how this product lays out data in the user's Notion, and how
the skills **create and maintain** it. There is **no separate bootstrap step**: the skills
create whatever is missing, on first use. Read this before any skill writes to Notion.

## Resolution rule — find by name, create if missing

Skills locate the structure **by its canonical names**, not by hardcoded IDs, so it's portable
across workspaces and self-healing:

1. Search for the root page **`ACR Setup Engineer`**; create it if absent.
2. Directly under the root, the **`Config`** page (holds the read-only Notion API token). **Create
   it if absent, seeded from [config-page-template.md](config-page-template.md)** (the integration
   setup instructions + an empty token line). **Never overwrite an existing `Config` page** — it
   may already hold the user's pasted token; leave its contents untouched.
3. Also under the root: the **`Parameters`** DB, the **`Setups`** DB, the **`Tuning guidelines`**
   page, the **`Parameter reference`** page, and the **`Locations`** catalogue page; create any
   that are missing (schemas below). Unlike the other pages, **`Parameter reference` is
   auto-maintained**: (re-)seed its body from `parameter-reference-template.md` on first create
   **and refresh it on skill updates** — it is not a user-editable layer (see its section below).
4. Per car: the **`{Car}`** page with its filtered view. Per location/stage referenced by a setup:
   the **`{Location}`** page and **`{Stage}`** page (under `Locations`) with their filtered views.

Never depend on stored page/database IDs — always re-resolve the structure **by name**. (You
may reuse an ID within a single run once you've found it, but a fresh run must still work.)

**Scope is `ACR Setup Engineer` only — never search broadly.** Once you've resolved the
`ACR Setup Engineer` root, navigate all deeper structure by name traversal (never issue a
workspace-wide Notion search to find setup data or guidelines). If a Notion API call returns
results from outside that root, discard them before processing. Anything outside it is out of
scope regardless of its title or content — never treat it as a guideline, prior setup, or
parameter source.

## Reading rows — use the REST query, not the connector
The Notion **connector cannot list a database's rows** (`notion-fetch` returns schema only;
`notion-search` is semantic, capped, and mixes cars). **Whenever a workflow needs a car's
`Parameters` rows or a filtered slice of `Setups`, follow
[notion-rest-read.md](notion-rest-read.md)** — it queries the data source over Notion's REST API
with an exact `Car` filter and pagination (reliable, complete, one call). If there's no token,
prompt the user through the one-time setup rather than substituting an unreliable connector read.
The one connector-readable copy of a catalog is the **`Catalog snapshot`** toggle on the car's
**`Catalog`** child page —
the sanctioned fallback when the REST path can't run at all (no network egress, e.g. Claude's Free
plan); see *Catalog snapshot* below and the fallback ladder in
[notion-rest-read.md](notion-rest-read.md). It covers `Parameters` catalogs only, never `Setups`
slices.

That read path uses a **read-only API token** the user sets up once (see *Give the skill read
access to Notion* in `README.md`). The token lives on a **`Config`** page directly under the
`ACR Setup Engineer` root; the skill `notion-fetch`es that page to read it. The `Config` page is
**auto-created** as part of the structure (create-if-missing, seeded from
[config-page-template.md](config-page-template.md)) carrying the integration-setup instructions and
an **empty token line** — so the page is normally present even before the user has pasted a token;
the user only has to follow the on-page steps and paste. Treat its contents as a secret: never echo
the token back, copy it into other pages, or include it in exports.

## Hierarchy

```
ACR Setup Engineer (root page)
├── Config (page)              holds the read-only Notion API token; auto-created with setup
│                               instructions, token blank until the user pastes it (see "Reading rows")
├── Parameters        (DB)     the catalog — one row per Car × Adjustment × Surface
├── Setups            (DB)     one row per setup
├── Tuning guidelines (page)   global user preferences (seeded from the template)
├── Parameter reference (page) parameter glossary — verbatim in-game descriptions of every
│                               tunable parameter; seeded AND refreshed from the template; read-only
├── Locations         (page)   catalogue parent — created on first stage/location reference
│   └── {Location} (page)      e.g. Monte Carlo — facts only, filtered Setups[Location] view
│       └── {Stage} (page)     e.g. Col de Turini — facts only (surface, length, key
│                               corners/speeds, character), filtered Setups[Stage] view
└── {Car} (page)               e.g. "Lancia Stratos HF" — an umbrella page, empty by design:
    │                           it holds nothing but the four child pages below
    ├── Guidelines (page)      YOURS. Tuning notes and preferences for this car. The skill
    │                           reads it and never writes to it (seeded empty, once)
    ├── Catalog (page)         THE SKILL'S. Identity facts, the three charts, the YAML
    │                           catalog snapshot. Overwritten wholesale on every refresh
    ├── Feedback (page)        THE SKILL'S. Dated record of what the driver reported after
    │                           drives. ADD-ONLY — entries are never edited or deleted
    └── Setups (page)          the filtered Setups[Car] view
```

**The `{Car}` children are split by ownership, and that split is the whole point.** `Guidelines`
is the user's and the skill never writes to it; `Catalog` is the skill's and is **replaced
wholesale, never merged** (no diffing, no asking — see *Catalog page* below). Keeping them on one
page is what used to force an expensive field-by-field comparison on every refresh just to avoid
clobbering something the user wrote. Separate pages make the cheap operation the safe one.

**Two DBs only** — car/location/stage pages are **filtered linked views**, never new
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
- **Value notation is literal — especially the compound-gear `*`.** Values are stored and shown
  exactly as the game spells them: slash pairs as `65//17`, ramp angles as `45/55`, and a
  two-stage primary drive as **`35//30*33//28`** — asterisk, no spaces. This is the **one
  canonical spelling**; never rewrite it as `x`, `×` or ` * `, and never drop the `*`.
  Because `*` is markdown emphasis, a value written unprotected into any markdown context (a
  page-body checklist, the `Catalog snapshot`, a report) loses its asterisks when two of them
  pair up — `35//30*33//28, 33//28*32//31` collapses to `35//3033//28, 33//2832//31`. **Wrap
  values in backticks** wherever they're written into page markdown, and **quote them in the
  snapshot YAML**, so the asterisk always survives the round trip (`SKILL.md` → *Compound gear
  values*). A value read back in the collapsed form is corrupted — repair it against
  `Discrete steps`, don't treat it as legal.
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
  `Conditions` (**Select**, optional), `Game version`, `Date` (**Date**, stores date *and* time),
  `Source` (`generated` | `screenshot` | `imported` | `default`), `Mode` (`learn` | `independent`),
  `Rating` (**Select**, options `1`–`5`, higher = better; **blank = unrated**), `Notes`,
  **`Learn from this`** (checkbox), `Model` (**Select**), `Skill version` (**Text**).
  Make `Car`, `Location`, `Stage`,
  and `Surface` **Select** (not plain text) so they render as **tags/pills** in the table — `Car`
  mirrors the `Parameters` DB's `Car` select, and `Surface` its `Tarmac`/`Gravel`/`Snow` options.
  **`Location` and `Stage` are both optional and independently blankable** — a setup may name
  neither (an arbitrary build with no place context, e.g. "drift setup, tarmac"), a `Location`
  only, or both. `Location`/`Stage` carry only the place reference, never style or goals.
  A setup's **driving intent is not a column** — it lives in the setup's own page-body summary (see
  *Mobile conventions* below).
  **`Conditions`** is a **Select** with the seeded options `Dry` / `Wet` / `Damp` / `Snow` / `Ice`
  (create-or-reuse, so other values are fine), describing the weather/road state the setup is for or
  was captured under. Give it the description *"Weather / road state (dry, wet, damp, snow, ice).
  Optional — leave blank if it doesn't matter or it's already obvious from the name."*
  **It is deliberately optional and often blank**, and a blank is never an error to fix:
  - the conditions are frequently already in the `Name` (`alsace wet`), which is fine — don't
    duplicate them into the column just for tidiness;
  - the user hand-edits rows and simply may not fill it in;
  - many builds genuinely don't care (a gravel setup that's fine dry or damp).

  Where it **does** matter is `Source = default` rows: the game's stock setup may differ by
  conditions, so a captured baseline records them whenever they're known (see *Default (stock)
  baseline rows*). Never **infer** a value to fill the column — leave it blank instead, and never
  treat a blank as "dry".
  **`Model`** is also a **Select** (renders as a tag) holding **just the model name + version**,
  e.g. `Opus 4.8` or `Sonnet 4.6`; give the column the description *"Which model+version built this
  setup (e.g. Opus 4.8). Blank for setups the skill didn't author."* **Blank for `screenshot`,
  `imported` and `default` rows** — only `generated` setups write it. The skill self-identifies with its known model name. No predefined options —
  create-or-reuse (Notion adds the option if absent).
  **`Skill version`** is plain **Text** (not Select — it's a free-form string, not a small fixed
  set) recording **which version of the acr-setup-engineer skill created this row**: the skill's
  `VERSION` file when released, or a `git describe` string for an unreleased source checkout (see
  `SKILL.md` → *Skill version*). Give the column the description *"Which version of the
  acr-setup-engineer skill created this row (e.g. v0.3.0, or a git-describe string for source builds)."*
  Unlike `Model`, it is written on **every** skill-created row — generated, tweaked, captured,
  **and imported** — since it identifies the tool/logic that produced the row, not the model that
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
  checked rows. Default **unchecked for every** `Source` value — the user checks it
  after reviewing and deciding a setup is worth learning from. **`Source = default` rows are never
  in the learn pool** even if checked (see below).

## Photo-captured setup rows (`Source = screenshot`)

A **`screenshot` row** records a setup the **user built themselves in-game**, transcribed from photos
of the car-setup screens (`capture-setup.md`). It is distinct from the other three sources:

| `Source` | Where the values came from |
|---|---|
| `generated` | the skill built them (`build-setup.md` / `tweak-setup.md`) |
| `screenshot` | the user built them in-game; read off setup-screen photos |
| `imported` | the user built them in-game; parsed from a `.sav` file (`import-savegame.md`) |
| `default` | the **game** produced them; the stock baseline read off setup-screen photos |

`screenshot` and `imported` are the same provenance (the user's own tuning) through different
transports, and the transport matters: a `.sav` parse is exact, whereas a photo reading can be
misread, so a `screenshot` row is the one place a stored value may carry a flagged reading. Keeping
them apart is what makes that traceable later.

- **Written like any other `Setups` row**, with `Source = screenshot`, `Name` ≤15 chars, `Date`,
  `Skill version`, **`Model` blank** (the values are the user's, not a model's), and **`Learn from
  this` unchecked** until the user opts in.
- **Eligible for the learn pool** once checked — unlike `default` rows, these are the user's taste.
- **Values are written as read** — never clamped, never dropped. A reading outside the catalog's
  resolved range is **flagged, not corrected** (`capture-setup.md` step 4).
- **Append-only.** A re-capture adds a new row; never edit an existing one.

## Default (stock) baseline rows (`Source = default`)

A **default baseline row** records the setup the *game itself* gives before anything is changed,
read off the user's setup-screen screenshots. It is the **numeric anchor** a build starts from
(`SKILL.md` → *Baseline first*; procedure in `build-setup.md` steps 4–6): the `Parameters` catalog
supplies legal *ranges* but nothing about where inside them ACR actually sits, and the captured
default supplies exactly that.

- **Written like any other `Setups` row**, with: `Source = default`, `Car`, `Stage`/`Location` (when
  the build named them), `Surface`, `Date`, `Game version` (when known), `Skill version`, `Name`
  ≤15 chars, **`Learn from this` unchecked**, and **`Model` blank** — the values are the game's, not
  a model's, exactly as for `imported` rows.
- **Excluded from the learn pool.** These are the game's values, not the user's taste; the
  `--learn-only` query filters them out (`notion-rest-read.md`). They are consumed only as the
  anchor.
- **Append-only.** A re-capture adds a **new** row; the most recent row whose context matches wins.
  Never edit an existing default row.

### Capture context — recorded, never inferred

**Whether ACR scopes its defaults per stage, per surface, per conditions, or not at all is unknown
and changes between releases.** A wet-tarmac default may well differ from dry, and `Surface`
(`Tarmac`/`Gravel`/`Snow`) is far too coarse to stand in for conditions. So the skill **never infers
the scoping**: it records the full context a capture was taken under and, when a stored default was
captured in a *different* context, shows the user the values and lets them confirm they apply here
rather than assuming (`build-setup.md` step 4).

The context is **stage, surface, conditions, game version, date**. Conditions go in the optional
**`Conditions`** column (above) — on a default row, fill it whenever the conditions are known, since
that's what a later build matches against. Leave it blank rather than guessing; a blank simply means
the match falls back to stage + surface and the user gets asked to confirm.

Because the column is optional and the rest of the context (game version, exact stage) isn't
columnar, also record the whole thing in prose:
- a **visible "Captured under" block** at the top of the row's page body (*not* inside a toggle), and
- a compact **one-line copy in `Notes`**, so it's readable in the table without opening the page.

That block is what `build-setup.md` step 4 shows the user when a stored default was captured in a
different context.

### Baseline assessment — the verdict on whether the default is usable

ACR sometimes gives out a default from the **wrong regime** for the context (a dry-tarmac setup for
a stage in snow conditions). Before a default is used as an anchor — and before the user is ever sent
out to drive it — `build-setup.md` **step 5b** judges it against the build's surface and conditions.

- **A default judged broken is still written and kept**, exactly like any other capture. It's a
  factual record of what the game gave; withholding it would only cost a re-screenshot later. It is
  simply **flagged**, so a later build reads the verdict instead of re-litigating it.
- The verdict lives in two places, mirroring the "Captured under" convention:
  - a **one-line dated verdict in `Notes`**, readable in the table without opening the page;
  - a visible dated **"Baseline assessment"** block in the page body (*not* inside a toggle), next to
    "Captured under": the verdict, what was flagged, and how it was handled — anchored with
    overrides, no anchor at all, or driven anyway at the user's request.
- **Written whenever the row is captured or written this run; on a previously stored row, only when
  the check fails.** A stored default that passes is left untouched — no churn on repeat builds.
- Dated and **appended**, the same way driving-feedback records are (below), so a row can carry
  assessments from several builds.

## Driving feedback records (collapsed + dated)

The output of a `driving-feedback-interview.md` session is stored so it survives the chat, without
burying the values the user actually came to read:

- **Setup row `Notes`** — a **one-line dated verdict** only, e.g.
  `2026-07-30 — liked it overall; understeer mid-corner, rear loose on hairpin exit.`
- **Setup row page body** — the full structured record (symptom family → corner phase → severity →
  the user's own words) inside a **collapsed toggle titled with the interview date**, e.g.
  *"Driving feedback — 2026-07-30"*. Repeat interviews on the same row **stack chronologically** as
  additional toggles; never overwrite an earlier one.
- **`{Car}` page** — anything that reads as a **lasting preference** ("I always want more entry
  rotation in this car") becomes a normal bullet in the page's **Guidelines** section, where it joins
  the per-car guideline layer. The **raw symptom log** goes in a separate collapsed **"Driving
  feedback log"** toggle, **dated, newest first** — that log is an objective record, **not** a
  guideline layer, the same way stage facts are objective inputs.

Every date comes from the deterministic Python one-liner under `Date` above, never from a guess at
the wall clock.

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
after every value column, in this order: `Car`, `Location`, `Stage`, `Surface`, `Conditions`,
`Date`, `Source`,
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

> **Stored values are setup-screen values.** Every value column holds the number **as the game's
> setup screen shows it**, never a normalised or sign-corrected one. This matters for `Toe Front` /
> `Toe Rear`: ACR's toe sign is **inverted** (positive = toe-**out**, negative = toe-**in**), and
> both `Parameters` ranges and `Setups` values keep that convention untouched — the interpretation
> happens in the reasoning and in the warning shown to the user (`SKILL.md` → *ACR's toe sign is
> inverted*).

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
- **per-car linked view** (on the car's `Setups` child page, filtered `Car = "{Car}"`) → `"{Car}" --show-order`;
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

The `{Car}` page — e.g. **`Lancia Stratos HF`** — is an **umbrella page with an empty body**. It
carries no facts, no charts and no views of its own; it exists to hold exactly four child pages:

| Child page | Owner | Written by the skill |
|---|---|---|
| **`Guidelines`** | **the user** | **Never** — created once, empty, then read-only forever |
| **`Catalog`** | the skill | **Replaced wholesale** on every refresh, no merge, no asking |
| **`Feedback`** | the skill | **Add-only** — new dated entries appended; nothing ever edited or removed |
| **`Setups`** | the skill | Holds the `Setups[Car=this]` filtered linked view |

**`Catalog` and `Feedback` are both skill-owned but behave oppositely, and confusing them loses
data.** `Catalog` is a *projection* of template data — regenerating it is free, so it's replaced
wholesale. `Feedback` is an *accumulated history* that exists nowhere else — so it is only ever
added to. Never rewrite `Feedback` as part of a refresh.

Resolve all four **by name** under the `{Car}` page and create whichever is missing, exactly as
everywhere else (*Resolution rule*). Nothing else belongs under `{Car}`.

**Every one of the four opens with a one-line maintenance note** — its first block, italic, so
anyone landing on the page knows immediately whether their edits will survive. Use these exact
lines; keep them to the single sentence they are:

| Page | First line on the page |
|---|---|
| `Guidelines` | *Yours. The skill reads this page and never writes to it.* |
| `Catalog` | *Maintained entirely by the skill — don't edit this page, every refresh replaces it.* |
| `Feedback` | *Add-only: the skill appends a dated entry after each drive and never edits or deletes one.* |
| `Setups` | *Kept up to date by the skill, but your own edits to these setups are never overwritten.* |

The `Parameters[Car=this]` filtered view is accessible via the Notion sidebar / linked DB; it is
**not** inlined anywhere in the car's pages, to keep them short.

### `Guidelines` page — the user's, never the skill's

Free-text car-specific tuning notes and preferences. This is the **per-car guidelines layer** in
`SKILL.md` → *Layered guidelines*, and the skill's relationship to it is simple:

- **Create it once**, at onboarding, with its maintenance line followed by a short seed stub
  inviting the user to write here (tone per `tuning-guidelines-template.md`).
- **After that, read it and never write to it.** Not on refresh, not to tidy it, not to add a
  heading, not to record what a build decided. If something the skill produced deserves to live
  here, *tell the user* and let them paste it.
- A refresh **never touches this page**, which is exactly why the `Catalog` page can be
  overwritten without asking anything.

### `Catalog` page — the skill's, overwritten wholesale

Everything static the skill knows about the car, regenerated from the bundled template and
**replaced in full** on every refresh. **No field-by-field comparison, no conflict resolution, no
questions** — the page is a projection of skill-side data, so making it match is a rewrite, not a
merge.

**First block on the page is its maintenance line** (above):

> *Maintained entirely by the skill — don't edit this page, every refresh replaces it.*

Then, in order:

1. **Car identity facts** — `Drivetrain`, `Engine layout`, `Weight bias`, `Weight`, `Max power`,
   `Max torque`, `Class`, `Gearbox`, `Steering lock`. Car facts that inform tuning reasoning —
   **not** tunable parameters; they never go in the `Parameters` DB. Populated during onboarding
   (`onboard-car.md` step 5) down the ladder **car information screenshot → bundled template →
   model knowledge → web lookup → ask the user (last resort)**; anything still unresolved is
   written as the literal **`couldn't determine`**. Because this page is skill-owned, a refresh
   **rewrites these from the current source** rather than protecting hand edits — a user who wants
   a fact to read differently puts it in `Guidelines`, which outranks it anyway.
2. **The engine and gearing charts** — up to three image blocks, in order: power/torque, gearing,
   final-drive, each only when the car's bundled template carries the matching URL. See *Engine
   and gearing charts* below.
3. **Gearing tool link** — *reserved*. A link to the interactive gearing web tool goes here once
   it exists. Until then, write nothing: no placeholder, no "coming soon" line.
4. **The `Catalog snapshot` toggle** — the car's full `Parameters` catalog as YAML, always the
   **last** block on the page (see *Catalog snapshot* below).

### `Feedback` page — the skill's, add-only

The car's running record of **what the driver actually reported after drives** — the output of
`driving-feedback-interview.md`. It exists because this history is the most personal thing the
skill has about a car and is reconstructable from nothing else.

- **The maintenance line stays first**, above every entry.
- **Add-only.** Each interview appends one **dated collapsed toggle** — `Driving feedback —
  {date}` — holding that session's record. **Never edit, reorder, merge or delete an existing
  entry**, and never rewrite the page. Newest at the **top**, so the recent ones are on screen
  when the page is opened on a phone.
- **A refresh must not touch this page.** It isn't regenerable; treat it like `Guidelines` in that
  respect, even though the skill is the one writing it.
- **It is an objective record, not a guideline layer.** Read it as *evidence* about how this
  driver describes this car; anything that should actually steer tuning decisions belongs in
  `Guidelines`, which the user owns and which outranks it (`SKILL.md` → *Layered guidelines*).
- Get every date from the deterministic Python one-liner in `Date` below, never from a guess at
  the wall clock.

### `Setups` page

Holds its maintenance line, then the **`Setups[Car=this]` filtered linked view** and nothing else
  (hide blank columns). The line is worth having here because the view is *live database rows*: the
  skill adds setups, but anything the user changes in a row stays changed.
Created with `notion-create-view` per *Creating an inline linked view*; the column order is set
from `--show-order` on every write, per *Applying the order*.

### Engine and gearing charts

Every bundled `car-templates/*.yaml` carries a **`power_torque_chart:`** URL (a PNG in the
project's public repo) plus an **`engine_curve:`** block holding the same data as numbers —
peak torque, peak power, and the raw `[rpm, Nm]` points. Most also carry a **`gearing_chart:`**
URL (speed against revs, every gear of every gear set) and, when the car's final drive is
adjustable, a **`final_drive_chart:`** URL (what each primary × differential-ratio combination
does to the whole ladder). All three PNGs are read straight out of the ACR game files, so they
describe **what the car actually makes and does in-game**, not a manufacturer brochure figure or
a guess.

**Putting them on the `Catalog` page.** Attach whichever of the three URLs the template carries,
**once**, when the identity facts are written — before the linked view exists, since
`notion-create-view` appends to the end of the page. Do all three (when present) in the same page
update, **in this order**: power/torque, then gearing, then final-drive.

For each URL:
1. **`notion-create-attachment`** with `source_url` = the template's URL and `filename` = the
   last path segment (e.g. `lancia-stratos-power-torque.png`, `lancia-stratos-gearing.png`,
   `lancia-stratos-final-drive.png`). Notion downloads a copy, so the page keeps working if the
   URL ever moves.
2. Put the returned **`markdown_source`** in the page update as an image block:
   `![Power and torque — {Car}](<markdown_source>)` / `![Gearing — {Car}](<markdown_source>)` /
   `![Final drive — {Car}](<markdown_source>)`.

If an attachment call fails or isn't available, **fall back to embedding that URL directly** —
e.g. `![Gearing — {Car}](<gearing_chart URL>)` — which renders the same, just hosted externally.
If the car has no bundled template, there are no charts at all; if it has one but a particular
field is missing (a car with no bundled template has none of the three; a car whose final drive
isn't adjustable simply has no `final_drive_chart:`), skip **only that block** rather than
inventing one, and **never** substitute a chart from a different car.

**The power/torque chart is not a fact source for `Max power` / `Max torque`.** Those nine
identity facts keep their own ladder (`onboard-car.md` step 5). Where they disagree with the
curve — which happens on forced-induction cars, whose quoted figures are usually real-world
specs — leave both standing and say so in the report; the curve is what the game simulates, the
fact line is what the car is advertised as. Reason about gearing, shift points and powerband from
**`engine_curve:`** and the gearing/final-drive charts, not from the `Max power` line.

**Charts on a refresh: no per-chart bookkeeping.** The `Catalog` page is rebuilt wholesale, so
the charts are simply re-emitted from whatever URLs the template carries right now. There is no
"is this chart already there?" check and no appending below an existing block — a car onboarded
before the gearing and final-drive charts existed picks them up because the whole page is
rewritten, not because anything went looking for what was missing.

**The car pages never hold stage sub-pages.** Stage and location facts live in the shared
catalogue below, not nested under any one car — a stage is referenced by `Stage` (and `Location`)
tags on `Setups` rows, never duplicated per car.

### Catalog snapshot

The **last block on every car's `Catalog` page** is a collapsed **toggle** titled **`Catalog snapshot`**,
holding the car's complete `Parameters` catalog as YAML. It exists so the catalog stays readable
when the REST read path can't run: the connector can fetch a page body in full even though it
can't list database rows, which is what keeps the skill working on accounts whose code sandbox
has no network egress (Claude's Free plan). Reading it: `notion-rest-read.md` → *The catalog
snapshot fallback*.

**This is the one deliberate exception to "never duplicate values into a page body"** (*Mobile
conventions* below). It is a cache, and it is treated like one: the `Parameters` **rows stay the
single source of truth**, the snapshot carries the metadata to be validated and dated, and every
catalog write refreshes it.

**Format.** Inside the toggle, first one banner line:

> Auto-maintained copy of this car's parameter catalog, used when the fast read path isn't
> available. Don't edit it (it gets overwritten) — edit the `Parameters` rows instead.

— then a fenced `yaml` code block:

```yaml
car: Lancia Stratos HF
written_at: 2026-09-05
skill_version: v0.13.0
row_count: 43
rows:
  - Adjustment: Adjuster Ring
    Section: Suspensions — Front
    Min: 20
    Max: 45
    Unit: mm
    Discrete steps: ""
    Order: 12
  - Adjustment: Spring Stiffness Front
    Section: Suspensions — Front
    Min: 42300
    Max: 73100
    Unit: N/m
    Discrete steps: "42300, 50000, 57700, 65400, 73100"
    Order: 14
  - Adjustment: Spring Stiffness Front
    Section: Suspensions — Front
    Surface: Gravel
    Min: 21000
    Max: 52000
    Unit: N/m
    Discrete steps: ""
    Order: 14
  - Adjustment: Primary Gear
    Section: Gearbox
    Min: "—"
    Max: "—"
    Unit: ""
    # Always quoted, and every `*` intact — see "Value notation is literal" above.
    Discrete steps: "35//30*33//28, 33//28*32//31, 33//31*31//30"
    Order: 1020
  # … one entry per Parameters row for this car
```

- `rows` holds **one entry per `Parameters` row** for this car — the baseline rows **and** every
  `Surface`-tagged row — with keys mirroring the REST read's output exactly
  (`notion-rest-read.md` → *Output*): `Surface` omitted on baseline rows, `Discrete steps` as
  `""` when blank, numeric fields omitted when null. A snapshot parses into the same in-memory
  catalog as the REST query, so every downstream rule (surface resolution, value legality)
  applies unchanged.
- `row_count` = the number of entries in `rows` — the read-side integrity check.
- `written_at` = the date of the write; `skill_version` per `SKILL.md` → *Skill version*.

**When to write it: every catalog write ends with it.** A run that creates or updates any of a
car's `Parameters` rows is **not finished** until the snapshot reflects the result. That means:
- `onboard-car.md` step 7 — first onboard or refresh, screenshot or template path;
- `onboard-car.md` step 8 — the gravel pass (the new `Surface = Gravel` rows go in too);
- `onboard-car.md` step 9 — when the user dictates `Discrete steps` in chat and the rows are
  updated in-run;
- `import-savegame.md` 5.2/5.3 — template auto-onboard.
Build it from the rows **you already hold in the run** — never read the catalog back just to
write the snapshot. (`refresh-catalog-snapshot.md` is the standalone version: it writes **only**
the snapshot, for cars onboarded before it existed — with a paste path that needs no egress.)

**Backfill — missing only, never a diff.** When a run (a) holds a **fresh, full REST read** of
the car's catalog, (b) has the fetched `Catalog` page in hand, (c) is **already writing to Notion**
for its own purposes, and (d) the page has **no** `Catalog snapshot` toggle — append one from the
rows in hand. That's a presence glance at a page already loaded, and at most one extra write in
a car's lifetime; it backfills cars onboarded before the snapshot existed. **Never compare an
existing snapshot against the rows** — staleness is not checked on reads: catalog writes refresh
it (above), and snapshot reads disclose `written_at`. Read-only workflows never gain a write from
this rule, and never add reads just to run it.

**Placement & refresh mechanics.** The toggle is the **last block of the `Catalog` page**, after
the maintenance line, the identity facts and the charts. The `Catalog` page holds no linked view, so it is
written as one ordered markdown replacement and the toggle simply comes last. A refresh rewrites
the whole page, so there is nothing to replace in place and no way to end up with two snapshots.
Like the `Parameter reference` page it holds no user content, so overwriting is safe; anything the
user typed inside it is overwritten by design — the page's maintenance line says so, and their real edits belong in
the `Parameters` rows (or in `Guidelines`).

## Locations & stages catalogue — shared, immutable facts

A **stage is reference data, not per-car content**: its road, surface, length, and corners don't
change depending on which car drives it. So locations and stages live **once**, centrally, under
the root page, and any number of `Setups` rows (any car) reference them by name via the `Location`
/ `Stage` select tags. **Stage/location pages hold objective facts only — never guidelines,
driving style, or per-build conditions** (those live on the setup itself; see `build-setup.md`
and *Mobile conventions* below).

```
Locations (page)            catalogue parent — created on first reference, under the root
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
  missing) under it, from the facts the user gives (or asks for) — see `build-setup.md` step 10.
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
- **car's `Setups` page** → `FILTER "Car" = "{Car}"; SHOW <output of `… "{Car}" --show-order`>` — `SHOW`
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
1. Write the page markdown first — the facts (`{Location}` / `{Stage}` page). On a car's **`Setups`**
   page there is nothing to write first: the view is the page's only content.
2. **Then** `notion-create-view` — the view lands right after that description.
3. **Then** append any trailing markdown. Never add a trailing section before the view, or the view
   ends up below it.

The multi-page car layout makes this much less fiddly than it used to be: the view has a page to
itself, and the `Catalog` page (maintenance line → facts → charts → snapshot toggle) holds no view at all, so
it can be written as one ordered markdown replacement.

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
A global **glossary**: the **verbatim in-game descriptions of every tunable parameter**
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
- **Create (page absent):** create the page under the root titled exactly `Parameter reference` and
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
     setup name, followed by 3–5 bullets covering location/stage/surface/conditions, **the driving
     intent for this build** (its only home — there's no `Setups` column for it; `Conditions` has an
     optional column, but the *intent* never does), tyre
     choice, the key guidelines applied (citing user guidelines by name), and what prior setups
     contributed (or "no prior setups used" if none). Mirrors what the chat report says, stored
     permanently for quick on-phone reference.
  2. **Per-parameter justification** — grouped by section (Gearbox → Suspensions → Dampers →
     Axles → Differentials → Wheels/Tyres → Brakes → Electronics & Aerodynamics, Front before
     Rear), inside a **toggle** so it's collapsible. Ordered by each parameter's **`Order`** (see
     *Setups column order* above) — the same sequence as the in-game setup screens. The same
     `Order` governs share snippets and exported templates, so every projection matches the table.
  **Never duplicate values into a page body checklist** — the database row is the single source
  of truth. A checklist would drift the moment the user edits a value in the table. (The `{Car}`
  page's `Catalog snapshot` toggle is the one deliberate exception — a validated, dated cache,
  refreshed on every catalog write; see *Catalog snapshot*.)
- **No wide tables inside page bodies** (they scroll horizontally on a phone); use short
  headings + bullet lists. Keep property names concise.
