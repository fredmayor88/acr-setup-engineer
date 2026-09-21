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
3. Also under the root: the **`Setups`** DB, the **`Tuning guidelines`** page, the
   **`Parameter reference`** page, and the **`Locations`** catalogue page; create any that are
   missing (schemas below). There is **no `Parameters` database** any more: a screenshot car's
   catalog is the `Parameters` **page** under the car (*`Parameters` page* below). A `Parameters`
   DB an older skill version created is left alone and never read (*Legacy `Parameters` DB*
   below). Unlike the other pages, **`Parameter reference` is
   auto-maintained**: (re-)seed its body from `parameter-reference-template.md` on first create
   **and refresh it on skill updates** — it is not a user-editable layer (see its section below).
   The same holds for the two documentation pages, **`How to use`** and **`Claude Free plan`**
   (*`How to use` and `Claude Free plan` pages* below).
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

## Where a car's catalog lives — template cars and screenshot cars

A car's **catalog** is the set of legal values for its tunable parameters. It comes from one of
two places, and every workflow that reads or validates values has to know which. **This is the
definition the rest of the skill refers to.**

- **Template car** — a car that has a bundled `car-templates/*.yaml` (matched on the file's
  `car:` field, by the rule in `onboard-car.md` step 1 → *Matching a car name*).
  **The template file is its catalog.** Onboarding a template car writes no catalog to Notion,
  and its values change only when the skill ships a new template.
- **Screenshot car** — a car whose catalog is **the `yaml` block on its `Parameters` page** in
  Notion: captured from the user's min/max setup-screen screenshots, or copied from a bundled
  template and then edited in chat (`edit-catalog.md`). The block is a complete template file in
  the same format as a bundled one.

Both are read by **one script on one file** — `catalog-read.md` — so every rule about the rows is
the same either way: surface resolution, `Discrete steps` vs numeric `Min..Max`, `Order`, legality.

**How to tell which kind a car is — the `Catalog source:` line.** It sits on the car's `Catalog`
page (see *Car page* below). Every workflow that chooses or judges setup values already fetches
that page for the car's identity facts, so for those the decision costs no extra read; a workflow
that only needs the catalog's shape — `share-setup.md` — fetches the page for this line alone,
batched with its other reads:

1. The line says **`your screenshots …`** → **screenshot car**.
2. The line says **`bundled template …`** → **template car**.
3. **No line at all** — the car was onboarded by an older skill version → **template car** when a
   `car-templates/` file matches its name, else **screenshot car**.

A user who **declines** the bundled template at onboarding and uploads screenshots gets a car
whose line says `your screenshots`: it is a screenshot car until a refresh finds a template at
least as new as the game version on that line, and then it switches to the template on its own
(`onboard-car.md` → *Refreshing an already-onboarded car*, step 4).

**A legacy `Parameters` DB** — created by skill versions before every catalog became a file —
is **never read and never deleted**. A refresh migrates each screenshot car's rows into its
`Parameters` page once (`onboard-car.md` → *Migration — catalog rows to the `Parameters`
page*) and then says, once, that the table can be deleted.

### Legacy template car — check the `Setups` columns before the first write

A template car whose `Catalog` page has **no `Catalog source:` line** (rule 3 above) is a
**legacy template car**: it was onboarded by an older skill version, so its `Setups` **value
columns were created from the template that version shipped**. Adjustment names have changed
since — a renamed parameter leaves the old column behind and the new name has no column at all —
so the current template can name a column the user's `Setups` DB does not have, and a setup
write, which gives **every** parameter a value, would write into a property that isn't there.

**So before the first `Setups` write of a run** for such a car — `build-setup.md` step 11's row
write, `tweak-setup.md` step 7's save, `capture-setup.md` step 6's row write, or
`import-savegame.md` 5.5 on an **already-onboarded** car — run the **`Setups` value-columns
check** exactly as `onboard-car.md` step 7 describes it (the *"Ensure the `Setups` DB has a
matching value property per Adjustment"* bullet), against the **current** template, and add every
missing column in **one `notion-update-data-source` call**.

- **It costs no extra read.** The car's `Catalog` page is already fetched (that is where the
  source line is read) and the `Setups` data source is already fetched for its `data_source_id`,
  which carries its property list. The check compares the template's Adjustments against those
  properties — nothing else is fetched.
- **Add only, never migrate.** Never rename, remove or rewrite an existing column or any value in
  it. A parameter the template has since **renamed keeps its old column, with all its old values,
  untouched**; the new name gets a new column, and new setups write that one. The old column
  simply stays blank on new rows.
- **Tell the user once, in one plain line**, once the columns have been added — e.g. *"The {Car} was onboarded by
  an older version of the skill, so I added {n} missing columns to your `Setups` table. Say
  'refresh the {car} in my Notion' when you want the car's pages brought up to date as well."*
  Say nothing when no column was missing.
- **This is not a refresh.** A refresh replaces the `Catalog` page and renames a legacy
  `Feedback` page, which the user did not ask for by asking for a setup. Only the columns are
  touched here.
- Once the user does refresh the car, its `Catalog` page carries a source line, so it is no
  longer a legacy template car and this check no longer applies.

## Reading rows — use the REST query, not the connector
This is about **rows in a Notion database**, which now means one thing only: a filtered slice of
`Setups` (for **every** car, template or screenshot). **Catalogs are not rows** — a car's catalog
is a file, read through [catalog-read.md](catalog-read.md) (*Where a car's catalog lives*, above).

The Notion **connector cannot list a database's rows** (`notion-fetch` returns schema only;
`notion-search` is semantic, capped, and mixes cars). **Whenever a workflow needs a filtered slice
of `Setups`, follow [notion-rest-read.md](notion-rest-read.md)** — it queries the data source over
Notion's REST API with an exact `Car` filter and pagination (reliable, complete, one call). If
there's no token, prompt the user through the one-time setup rather than substituting an
unreliable connector read.

A screenshot car's catalog is read from its `Parameters` page through the connector —
`catalog-read.md`. The REST token is only ever needed for `Setups` reads.

That read path uses a **read-only API token** the user sets up once (see *Give the skill read
access to Notion* in `README.md`). The token lives on a **`Config`** page directly under the
`ACR Setup Engineer` root; the skill `notion-fetch`es that page to read it. The `Config` page is
**auto-created** as part of the structure (create-if-missing, seeded from
[config-page-template.md](config-page-template.md)) carrying the integration-setup instructions and
an **empty token line** — so the page is normally present even before the user has pasted a token;
the user only has to follow the on-page steps and paste. In **offline mode** (no network,
`notion-rest-read.md` → *Offline mode*) the skill doesn't read the token or ask for one. Treat its contents as a secret: never echo
the token back, copy it into other pages, or include it in exports.

## Hierarchy

```
ACR Setup Engineer (root page)
├── How to use (page)          what to ask for, the command to run after an update, who owns
│                               which page; skill-owned, rewritten on every skill update
├── Claude Free plan (page)    what works and what doesn't on Claude's Free plan; skill-owned,
│                               rewritten on every skill update
├── Config (page)              holds the read-only Notion API token; auto-created with setup
│                               instructions, token blank until the user pastes it (see "Reading rows")
├── Setups            (DB)     one row per setup
├── Tuning guidelines (page)   global user preferences (seeded from the template)
├── Parameter reference (page) parameter glossary — verbatim in-game descriptions of every
│                               tunable parameter; seeded AND refreshed from the template; read-only
├── Locations         (page)   catalogue parent — created on first stage/location reference
│   └── {Location} (page)      e.g. Monte Carlo — facts only, filtered Setups[Location] view
│       └── {Stage} (page)     e.g. Col de Turini — facts only (surface, length, key
│                               corners/speeds, character), filtered Setups[Stage] view
└── {Car} (page)               e.g. "Lancia Stratos HF" — an umbrella page, empty by design:
    │                           it holds nothing but the child pages below
    ├── Guidelines (page)      YOURS. Tuning notes and preferences for this car. The skill
    │                           reads it and never writes to it (seeded empty, once)
    ├── Catalog (page)         THE SKILL'S. Identity facts, the catalog source line, the
    │                           power/torque chart and the gearing-tool link. Overwritten
    │                           wholesale on every refresh
    ├── Log (page)             SHARED — yours and the skill's. Your own notes about the car,
    │                           plus the skill's dated record of what the driver reported
    │                           after drives. You write and edit yours freely; THE SKILL
    │                           ONLY ADDS — it never edits or deletes anything here
    ├── Parameters (page)      SCREENSHOT CARS ONLY. The car's complete parameter list as a
    │                           template-format YAML block. THE SKILL'S — edited only through
    │                           chat (edit-catalog.md); never regenerated, it is the only copy
    └── Setups (page)          the filtered Setups[Car] view
```

**The `{Car}` children are split by ownership, and that split is the whole point.** `Guidelines`
is the user's and the skill never writes to it; `Catalog` is the skill's and is **replaced
wholesale, never merged** (no diffing, no asking — see *Catalog page* below). Keeping them on one
page is what used to force an expensive field-by-field comparison on every refresh just to avoid
clobbering something the user wrote. Separate pages make the cheap operation the safe one.

**One DB only** — the `Setups` DB; car/location/stage pages are **filtered linked views**, never
new DBs. A stage is **immutable, shared reference data** — it is created once under `Locations` and
referenced by any number of setups (any car, any number of times), never duplicated per car.

**Batch every write (`SKILL.md` → *Batch Notion writes*).** Create a DB with its **full column set
in one `notion-create-database` `CREATE TABLE`**; when adding columns to an existing DB, combine
**all** `ADD COLUMN`s into **one** `notion-update-data-source` call. Create many rows (all
imported setup rows) in **one** `notion-create-pages` call (≤100 rows; batch in 100s only if
more). Never add columns or rows one call at a time — it's slow and token-heavy.

## Legacy `Parameters` DB

Skill versions before every catalog became a file kept a screenshot car's catalog as rows in a
`Parameters` database under the root (`Car`, `Section`, `Adjustment`, `Min`, `Max`, `Unit`,
`Discrete steps`, `Order`, optional `Surface`). **The skill no longer creates, reads or writes
it.** It stays in the user's Notion until they delete it. The one thing the skill still does
with it: a refresh of a screenshot car that has no `Parameters` page yet may read that car's
rows over REST, once, to build the page (`onboard-car.md` → *Migration — catalog rows to the
`Parameters` page*).

## `Setups` DB — one row per setup
- **Meta:** `Name` (title), `Car` (**Select**), `Location` (**Select**, optional), `Stage`
  (**Select**, optional), `Surface` (**Select**, options `Tarmac` / `Gravel` / `Snow`),
  `Conditions` (**Select**, optional), `Game version`, `Date` (**Date**, stores date *and* time),
  `Source` (`generated` | `screenshot` | `imported` | `default`), `Mode` (`learn` | `independent`),
  `Rating` (**Select**, options `1`–`5`, higher = better; **blank = unrated**), `Notes`,
  **`Learn from this`** (checkbox), `Model` (**Select**), `Skill version` (**Text**).
  Make `Car`, `Location`, `Stage`,
  and `Surface` **Select** (not plain text) so they render as **tags/pills** in the table;
  `Surface` carries the `Tarmac` / `Gravel` / `Snow` options a catalog uses.
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
  discovered. Per-car legality is enforced by the **skill** against that car's catalog row
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
(`SKILL.md` → *Baseline first*; procedure in `build-setup.md` steps 4–6): the catalog
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
- **The car's `Log` page** — the car-level record: one dated collapsed toggle per interview,
  added at the top. A tweak round that ran no interview adds its own entry the same way (the
  user's words and the changes proposed — `tweak-setup.md` step 5). The rules for that page, including what happens to a **lasting preference**
  the interview spots (it is noted in the `Log` entry and **offered** to the user for their
  `Guidelines` page — the skill never writes `Guidelines` itself), live in one place: *`Log`
  page* below, with the interview's own side in `driving-feedback-interview.md` → *Recording the
  outcome*. **Nothing is ever written to `Guidelines` or onto the `{Car}` umbrella page**, which
  stays empty by design (*Car page*).

Every date comes from the deterministic Python one-liner under `Date` above, never from a guess at
the wall clock.

## Setups column order — driven by the per-parameter `Order`

The display order of the `Setups` DB's **value columns** — and of every setup projection (the table
view, the per-car / per-location / per-stage linked views, the page-body justification toggle, the
share snippet, and exported templates) — is governed by each parameter's **`Order`** number in the car's catalog,
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
> both catalog ranges and `Setups` values keep that convention untouched — the interpretation
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

**Get the `SHOW` list from the bundled script — don't assemble it by hand, and never merge two
of its outputs by hand** (they are finished lists with no `Order` left to interleave by). **This
section is the only place that says which form to run**; every workflow points here.

**One form, every view.** Every car's catalog is a template file — bundled, or the screenshot
car's `parameters/<slug>.yaml` saved to the sandbox by `catalog-read.md`. Pass one
`--from-template` per car the view spans:

```
python scripts/query_notion_parameters.py --show-order --from-template <file1> --from-template <file2> …
```

- **Per-car view** (the car's `Setups` page) → that car's file only.
- **Main `Setups` table, `{Location}` and `{Stage}` views** → every onboarded car's file.

No token, no sandbox network — the script runs on files; on every plan.

**Which files to pass, without extra reads.** The onboarded cars are the `{Car}` pages under the
root — the root fetch you already did lists them. For each: a name matching a bundled template →
`car-templates/<slug>.yaml`, **unless** its `Catalog` page was read this run and says
`your screenshots`; otherwise it is a screenshot car → fetch its `Parameters` page (batch these
fetches) and save each per `catalog-read.md` → *Save the file*. A screenshot car whose page can't
be read is left out: say in one line that its columns keep their current position until its page
is readable. **Never drop the `SHOW`** for that reason, and never assemble a list by hand.

The script prints the exact, ready-to-use property list: `"Name"`, then
value columns by `Order`, then the fixed meta columns (`Car` … `Model`, `Skill version`). Use it
verbatim as the `SHOW` value:

- **main `Setups` table view** → `SHOW <script output>`;
- **per-car linked view** (on the car's `Setups` child page, filtered `Car = "{Car}"`) →
  `SHOW <script output>` — this orders the columns **and** hides the blank ones in one step
  (the script lists only that car's value columns);
- **per-location / per-stage linked views** (on `{Location}` / `{Stage}` pages, filtered by
  `Location` / `Stage` only — **not** `Car`, since many cars can share a place) →
  `SHOW <script output>`.

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
carries no facts, no charts and no views of its own; it exists to hold five child pages (four for
a template car — it has no `Parameters` page):

| Child page | Owner | Written by the skill |
|---|---|---|
| **`Guidelines`** | **the user** | **Never** — created once, empty, then read-only forever |
| **`Catalog`** | the skill | **Replaced wholesale** on every refresh, no merge, no asking |
| **`Log`** | **shared — the user *and* the skill** | **Add-only** — the skill appends a new dated entry at the top and never edits, reorders or removes anything already on the page (the user edits their own notes freely) |
| **`Parameters`** | the skill's | written by onboarding and `edit-catalog.md`; **never** by a refresh (except the *Not in use* line and the one-time migration that creates the page — `onboard-car.md` → *Migration — catalog rows to the `Parameters` page*); the only copy |
| **`Setups`** | the skill | Holds the `Setups[Car=this]` filtered linked view |

**`Catalog` and `Log` both carry skill writing, but they behave oppositely, and confusing them
loses data.** `Catalog` is a *projection* of template data — regenerating it is free, so it's
replaced wholesale. `Log` is an *accumulated history* that exists nowhere else, and part of it was
written by the user — so the skill only ever adds to it. Never rewrite `Log` as part of a refresh.

Resolve them all **by name** under the `{Car}` page and create whichever is missing, exactly as
everywhere else (*Resolution rule*). The one extra step is `Log`, which older versions of the
skill called `Feedback`: before creating it, check for a page under the old name and **rename it
in place** — see *Resolving the page (`Log`, and the legacy `Feedback` name)* below. Nothing else
belongs under `{Car}`.

**Every one of them opens with a one-line maintenance note** — its first block, italic, so
anyone landing on the page knows immediately whether their edits will survive. Use these exact
lines; keep them as short as they are and don't add to them:

| Page | First line on the page |
|---|---|
| `Guidelines` | *Yours. The skill reads this page and never writes to it.* |
| `Catalog` | *Maintained entirely by the skill — don't edit this page, every refresh replaces it.* |
| `Log` | *Your notes on this car go anywhere on this page. When you tell Claude how a drive felt, the skill adds a dated entry at the top. Building a setup adds nothing here. The skill never edits or removes anything on this page.* |
| `Parameters` | screenshot car: *Your car's parameter list, kept by the skill. To change a range, say it in chat ("the front ARB goes 1 to 6 in steps of 1") — don't edit this page by hand. It survives refreshes.* — forked car: *Started {YYYY-MM-DD} as a copy of the bundled template (game version {tv}), with your edits. The skill keeps this list; say changes in chat.* |
| `Setups` | *Kept up to date by the skill, but your own edits to these setups are never overwritten.* |

The date comes from the deterministic one-liner under *Date* (never a guess).

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
- **Reading it is a separate fetch.** It used to be a section of the car page, so it arrived free
  with the identity facts; now it doesn't. Every workflow that chooses or judges setup values must
  fetch it in its own right (`SKILL.md` → *Layered guidelines*).

### `Catalog` page — the skill's, overwritten wholesale

Everything static the skill knows about the car, regenerated from what the skill holds (the
bundled template for a template car; the identity facts and source line for a screenshot car) and
**replaced in full** on every refresh. **No field-by-field comparison, no conflict resolution, no
questions** — the page is a projection of skill-side data, so making it match is a rewrite, not a
merge.

**First block on the page is its maintenance line** (above):

> *Maintained entirely by the skill — don't edit this page, every refresh replaces it.*

Then, in order:

1. **Car identity facts** — `Drivetrain`, `Engine layout`, `Weight bias`, `Weight`, `Max power`,
   `Max torque`, `Class`, `Gearbox`, `Steering lock`. Car facts that inform tuning reasoning —
   **not** tunable parameters; they are never part of the car's catalog. Populated during onboarding
   (`onboard-car.md` step 5) down the ladder **car information screenshot → bundled template →
   model knowledge → web lookup → ask the user (last resort)**; anything still unresolved is
   written as the literal **`couldn't determine`**. **That ladder runs at onboarding only.**
   Because this page is skill-owned, a refresh **rewrites these from the car's own file** rather
   than protecting hand edits — from the **bundled file's header** for a template car, and from
   the **header of the `Parameters` page yaml** for a screenshot or forked car (`onboard-car.md`
   → *Refreshing an already-onboarded car*, step 3); a key that is missing or empty there is
   written as `couldn't determine`, never looked up again. A user who wants a fact to read
   differently puts it in `Guidelines`, which outranks it anyway.
2. **The catalog source line** — one paragraph line of its own, directly under the identity
   facts and above the chart. It says where this car's legal values come from, and **every read
   workflow decides from it whether the car is a template car or a screenshot car** (*Where a
   car's catalog lives*, above). Three exact formats, nothing else:
   - **Template car:** `**Catalog source:** bundled template — game version {version}, from {source}`
     — `{version}` is the template's `version:` field, and `{source}` is **`game files`** when the
     template says `source: game-files` and **`a community export`** when it says
     `source: community` (a template with no `source:` field counts as `community`). Example:
     `**Catalog source:** bundled template — game version 0.6, from game files`.
   - **Screenshot car:** `**Catalog source:** your screenshots — game version {version}` — the
     game version the user gave when they uploaded the screenshots (`onboard-car.md` step 2), or
     the literal `unknown` if they didn't know. Example:
     `**Catalog source:** your screenshots — game version unknown`.
   - **Forked car** (a bundled template the user edited in chat):
     `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
     It is a screenshot car for every rule.

   Write it on every `Catalog` page the skill builds or rebuilds. A car whose page predates it
   gets one on its next refresh; until then, rule 3 of *Where a car's catalog lives* decides.
3. **The power/torque chart** — one image block, only when a bundled template matches the car
   (even if the car's catalog is its own `Parameters` page) and carries a `power_torque_chart:`
   URL. See *Engine chart and gearing tool* below, which is the one place that says which file
   the chart, the link and the curve are read from.
4. **Gearing tool link** — one plain paragraph line, right after the chart (or right after the
   catalog source line when there is no chart), reading `Gearing tool: <gearing_tool URL>`, the URL
   written as a markdown link whose text is `Gearing — {Car} (ACR Car Lab)` and whose target is
   the matching bundled template's `gearing_tool` value — e.g.
   `Gearing tool: [Gearing — Lancia Stratos (ACR Car Lab)](https://fredmayor88.github.io/acr-car-lab/lancia-stratos/gears/)` —
   so it renders as a clickable link on a phone. Say in one sentence what the tool is: interactive
   speed-per-gear charts for every gear set, final drive and rev limit of this car, read from the
   game files. Emit it only when a bundled template matches the car (even if the car's catalog is
   its own `Parameters` page) and has `gearing_tool:`; a car with no matching bundled template
   gets no link — never build the URL from the car name.

### `Log` page — shared; the skill only adds

The car's running log. **Two kinds of writing live here side by side:**

- **The user's own notes** — anything they want to record about this car: observations, reminders,
  things to try, what a stage felt like. They may write **anywhere on the page, in any format**.
- **The skill's dated record of what the driver reported after drives** — the output of
  `driving-feedback-interview.md`, and of every `tweak-setup.md` feedback round that needed no
  interview. This history is the most personal thing the skill has about a
  car and is reconstructable from nothing else.

Rules:

- **The maintenance line stays first**, above everything else on the page.
- **Add-only — for the skill. The user edits their own notes freely.** Each interview, and each
  tweak feedback round that ran none, appends one **dated collapsed toggle** —
  `Driving feedback — {date}` — holding that record. Put it
  **directly below the maintenance line**, so the newest entry is at the **top** and the recent
  ones are on screen when the page is opened on a phone. **The skill never edits, reorders, merges
  or deletes any existing block on this page — the user's or its own — and never rewrites the
  page.** Adding one block is the only write the skill ever makes here.
- **The user's blocks are not the skill's to tidy.** Don't reformat them, don't move them under a
  heading, don't merge two notes, don't "fix" a date. If something looks wrong, say so in chat.
- **A refresh must not touch this page's content.** It isn't regenerable; treat it like
  `Guidelines` in that respect, even though the skill also writes here. A refresh may **rename**
  a legacy `Feedback` page to `Log` and add the maintenance line — see *Resolving the page
  (`Log`, and the legacy `Feedback` name)* below — and nothing else.
- **It is evidence, not a guideline layer.** **`build-setup.md` (step 2), `tweak-setup.md`
  (step 3) and `review-setup.md` (step 3) fetch this page**, batched with `Guidelines`, and read
  the **whole page** — the skill's entries *and* the user's notes — as context about how this
  driver describes this car. (A read never renames a legacy `Feedback` page; that happens on a
  write or a refresh. `ask-setups.md` doesn't read it at all; `review-setup.md` reads it but
  never writes to it.) It never outranks
  `Guidelines`: anything that should actually steer tuning decisions belongs there, which the user
  owns and which wins (`SKILL.md` → *Layered guidelines*). When a user note on `Log` reads like a
  **standing rule for this car** rather than a one-off observation, **offer it for `Guidelines`**
  in chat, written exactly as they'd paste it — the same way the interview already offers lasting
  preferences (`driving-feedback-interview.md` → *Recording the outcome*). Offer once; never move
  or copy it there yourself, and never delete it from `Log`.
- Get every date from the deterministic Python one-liner in `Date` below, never from a guess at
  the wall clock.

#### Resolving the page (`Log`, and the legacy `Feedback` name)

This page was called **`Feedback`** in earlier versions of the skill. **Every workflow that writes
to it resolves it like this**, so a user who hasn't refreshed the car yet still gets their entries
in the right place and nothing is split across two pages. **A workflow that only *reads* the page
resolves it the same way but renames nothing and creates nothing** — it reads whichever page it
found and says so; if neither `Log` nor `Feedback` exists, it skips the page silently (step 3's
"create `Log`" applies to writes and refreshes only). The rename happens on a write or a refresh.

1. Look for a child page named **`Log`** under `{Car}`. If it exists, **use it** — even if a
   `Feedback` page also exists. In that case do **not** merge, move or delete anything: tell the
   user that both pages exist and ask what they want done with the old one.
2. No `Log`, but a **`Feedback`** page exists → **rename that page's title to `Log` in place**,
   then use it. Same page, same id, so all its content and any links to it are preserved. **Never
   create a new page and copy entries across.**
   - The rename is a **page property update**, not a body edit:
     `notion-update-page` with `command: "update_properties"` and `properties: {"title": "Log"}`
     on that page's id. (`title` is the only property a page outside a database has.) Body edits
     use a different command on the same tool (`insert_content` / `update_content`), so a body
     write will **not** rename anything.
   - The REST path in `notion-rest-read.md` is **read-only** (the `Config` token is a read-only
     integration token), so there is no REST fallback for the rename — it goes through the Notion
     connector. If the connector call is unavailable, **change nothing** and tell the user the
     page still has its old name.
   - **Verify after the call:** `notion-fetch` the page and confirm its title now reads `Log`
     before writing anything into it. If it doesn't, stop and say so rather than creating a
     second page.
   - Then fix the maintenance line, touching as little as possible: if the **first block is
     exactly the old `Feedback` maintenance line** (*Add-only: the skill appends a dated entry
     after each drive and never edits or deletes one.*), replace **that block only** with the new
     `Log` line. If the first block is **anything else**, **insert** the new maintenance line
     above it and edit nothing.
   - Tell the user in one line that the `Feedback` page is now called `Log`.
3. Neither exists → **create `Log`** with its maintenance line as its first block.

### `Parameters` page — screenshot cars only; the skill's; edited through chat

The car's complete catalog, as a **template-format YAML file** in one fenced ```` ```yaml ````
block. Read by `catalog-read.md`; written by `onboard-car.md` (screenshot path), by
`edit-catalog.md`, and by the one-time migration in a refresh. A template car has no such page.

**Body, in this order — nothing else on the page:**

1. The maintenance line (*Car page* table above — the screenshot or the forked wording).
2. **Only when the car has switched to a bundled template:** the *Not in use* line, italic:
   *Not in use since {YYYY-MM-DD}: a newer bundled template (game version {v}) appeared, so this
   car uses that now. Say 'onboard the {Car} from my screenshots' to use this list again.*
   The date comes from the deterministic one-liner under *Date* (never a guess).
3. One ```` ```yaml ```` block: the file printed by
   `python scripts/load_catalog.py --to-template rows.json` — every header key `--to-template`
   accepts (`car`, `game`, `save_ids` when known, `drivetrain`, the eight other identity facts
   `engine_layout`, `weight_bias`, `weight`, `max_power`, `max_torque`, `class`, `gearbox`,
   `steering_lock`, then `version`, `source: "screenshots"`, `forked_from` for a forked car),
   then the three bookkeeping keys the script adds (`written_at`, `skill_version`,
   `parameter_count`), then `parameters:`. **Never `gearing_tool`, `power_torque_chart` or
   `engine_curve`** — those stay in the bundled file and are read from there (*Engine chart and
   gearing tool* below). **The nine identity facts in this header are what a refresh rebuilds
   this car's `Catalog` page from** (`onboard-car.md` → *Refreshing an already-onboarded car*,
   step 3). **Never write this block by hand**: build `rows.json` from the rows in hand and use
   the script's output verbatim.

**Rules:**
- **The only copy.** A refresh never regenerates it — there is nothing to regenerate it from.
  The only writes a refresh makes here are the *Not in use* line (item 2), inserted when the car
  switches to a bundled template, and the one-time migration that creates the page
  (`onboard-car.md` → *Migration — catalog rows to the `Parameters` page*). The block stays.
- **Replace, never append.** An edit or a re-onboard replaces the block (delete it, write the new
  one), so there is exactly one block on the page.
- **A `parameter_count` mismatch on read means a truncated fetch, never a bad file** — the read
  path stops and says so (`catalog-read.md` step 5).
- **Never delete the page.** If the user asks for the car to be removed, tell them what to
  delete in Notion; the skill deletes nothing.

### `Setups` page

Holds its maintenance line, then the **`Setups[Car=this]` filtered linked view** and nothing else
  (hide blank columns). The line is worth having here because the view is *live database rows*: the
  skill adds setups, but anything the user changes in a row stays changed.
Created with `notion-create-view` per *Creating an inline linked view*; the column order is set
from `--show-order` on every write, per *Applying the order*.

### Engine chart and gearing tool

**Where these three come from — one rule, for every car.** `gearing_tool:`,
`power_torque_chart:` and the `engine_curve:` block describe the car's engine and gearing data,
not its tunable ranges, and a user's edit never changes them. They live **only in bundled
`car-templates/*.yaml` files** and are **never stored on a `Parameters` page** —
`scripts/load_catalog.py --to-template` does not emit them. So every workflow that needs the
chart, the gearing-tool link or the curve reads it from **the bundled file whose `car:` matches
the car by name** (`onboard-car.md` step 1 → *Matching a car name*), **whatever the car's
`Catalog source:` line says** — template car, screenshot car and forked car alike. A car with no
matching bundled file has no chart, no link and no curve: skip them, never invent one and never
borrow another car's.

Every bundled `car-templates/*.yaml` carries an **`engine_curve:`** block holding peak torque,
peak power, and the raw `[rpm, Nm]` points, read straight out of the ACR game files, so it
describes **what the car actually makes in-game**, not a manufacturer brochure figure or a guess.
Most also carry a **`power_torque_chart:`** URL — a PNG of that same curve, in the project's
public repo. All 18 bundled templates carry a **`gearing_tool:`** URL — a link to that car's page
in the **ACR Car Lab**, the live interactive web tool (speed-per-gear for every gear set, final
drive and rev limit, computed from the same game files).

**Putting them on the `Catalog` page.** Attach the chart (when the matching bundled template
carries `power_torque_chart:`) and write the gearing-tool link line, **once**, when the
identity facts are written — before the linked view exists, since `notion-create-view`
appends to the end of the page. Do both (when present) in the same page update, **in this
order**: the chart, then the link line.

For the chart:
1. **`notion-create-attachment`** with `source_url` = the matching bundled template's
   `power_torque_chart:` URL and `filename` = the last path segment
   (e.g. `lancia-stratos-power-torque.png`). Notion downloads a copy, so the page keeps working
   if the URL ever moves.
2. Put the returned **`markdown_source`** in the page update as an image block:
   `![Power and torque — {Car}](<markdown_source>)`.

If the attachment call fails or isn't available, **fall back to embedding the URL directly** —
`![Power and torque — {Car}](<power_torque_chart URL>)` — which renders the same, just hosted
externally. If no bundled template matches the car, there is no chart and no link at all; if one
matches but has no `power_torque_chart:` (e.g. the Peugeot 206 WRC, which the game ships no engine
curve for), skip **only the chart block** rather than inventing one, and **never** substitute a
chart from a different car.

For the link line, write the plain paragraph described in *`Catalog` page* item 4 above — no
attachment call, it's a markdown link, not an image.

**The power/torque chart is not a fact source for `Max power` / `Max torque`.** Those nine
identity facts keep their own ladder (`onboard-car.md` step 5). Where they disagree with the
curve — which happens on forced-induction cars, whose quoted figures are usually real-world
specs — leave both standing and say so in the report; the curve is what the game simulates, the
fact line is what the car is advertised as. Reason about gearing, shift points and powerband from
**`engine_curve:`**, not from the `Max power` line, and point the user at the gearing-tool link
for speed-per-gear questions.

**Charts on a refresh: no per-chart bookkeeping.** The `Catalog` page is rebuilt wholesale, so
the chart and the link line are simply re-emitted from whatever the matching bundled template
carries right now.
There is no "is this chart already there?" check and no appending below an existing block — a car
onboarded before the gearing tool existed picks it up because the whole page is rewritten, not
because anything went looking for what was missing.

**The car pages never hold stage sub-pages.** Stage and location facts live in the shared
catalogue below, not nested under any one car — a stage is referenced by `Stage` (and `Location`)
tags on `Setups` rows, never duplicated per car.

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
above — the car's own file for its own view, every car's file for a location/stage view). Then call
`notion-create-view` with
`parent_page_id` = the target page, `data_source_id` = the `Setups` data source, `type: "table"`, a
`name` (e.g. `"Setups"`), and a `configure` DSL string (see `notion://docs/view-dsl-spec`) carrying
the filter and the script's `SHOW` list:
- **car's `Setups` page** → `FILTER "Car" = "{Car}"; SHOW <script output>` — `SHOW`
  both orders the columns and hides the ones it omits (blank per-car columns).
- **`{Location}` page** → `FILTER "Location" = "{location}"; SHOW <script output>`
  — no `Car` filter, since many cars may share a location.
- **`{Stage}` page** → `FILTER "Stage" = "{stage}"; SHOW <script output>` — no
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
itself, and the `Catalog` page (maintenance line → facts → source line → chart → gearing-tool
link) holds no view at all, so it can be written as one ordered markdown replacement.

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
current — "on skill updates" means the version check in *`How to use` and `Claude Free plan`
pages* above, and *"refresh my ACR Notion"*. The seeded body opens with a **read-only banner** telling the user not to add notes here
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

## `How to use` and `Claude Free plan` pages

Two short documentation pages directly under the root, for the user to read on a phone:

- **`How to use`** — seeded from [how-to-use-template.md](how-to-use-template.md): one line per
  thing the user can ask for, with a prompt to copy; the command to run after updating the skill
  (*"refresh my ACR Notion"*); and which page is whose.
- **`Claude Free plan`** — seeded from [free-plan-template.md](free-plan-template.md): what works
  and what doesn't without network access to Notion's API. The offline-mode message points here
  (`notion-rest-read.md` → *Offline mode*).

Both are **skill-owned and auto-maintained, exactly like `Parameter reference`**: never a user
layer, and a whole-page replacement is always safe because nothing of the user's lives on them.
**Create / refresh** the same way — copy everything below the template's `---` line, replace
`{version}` with the skill version (`SKILL.md` → *Skill version*), and on a refresh delete every
existing block first and write the body fresh (never append).

### Keeping them current — the version check

The banner on `How to use` carries the skill version that wrote it. **Once per chat, the first
time a workflow resolves the structure, fetch `How to use` in that same batch of reads** and
compare its banner version with the running skill's version:

- **Same version** → nothing to do.
- **Page missing, or a different version** → rewrite **`How to use`, `Claude Free plan` and
  `Parameter reference`** now (create any that is missing), before the workflow's own writes, and
  tell the user once, in one line: *"Your Notion was set up by an older version of the skill ({old
  version}). I've updated `How to use`; say "refresh my ACR Notion" to bring your car pages up to
  date too."* (Say *"set up by an older version"* only when there was a page to compare; a missing
  page just gets created, silently.)
- **Never refresh car pages from this check** — that is many writes, and the user decides when
  (`refresh-notion.md`).

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
  of truth. A checklist would drift the moment the user edits a value in the table. (A screenshot
  car's `Parameters` page is not an exception: the YAML block there **is** the catalog, not a copy
  of it.)
- **No wide tables inside page bodies** (they scroll horizontally on a phone); use short
  headings + bullet lists. Keep property names concise.
