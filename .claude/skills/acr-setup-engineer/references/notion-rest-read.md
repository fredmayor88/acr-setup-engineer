# Reading rows from a Notion database — the reliable way

**The canonical way to read a car's rows from an `ACR Setup Engineer` database** (the `Parameters`
catalog, or a filtered slice of `Setups`). Use this wherever a workflow says "fetch the car's
`Parameters` rows" or "fetch this car's `Setups` rows".

**Scope — which cars this doc's `Parameters` read is for.** `Parameters` holds the catalogs of
**screenshot cars** only. A **template car**'s catalog is the bundled YAML inside the skill: read
it with `python scripts/load_catalog.py car-templates/<slug>.yaml [--surface {Surface}]` — no
token, no network, no snapshot, on every plan — and never query `Parameters` for it. The script
prints rows in **exactly the *Output* shape below**, so everything downstream is identical, and
*Resolving the range for a surface* (below) is the same rule both sources obey — `load_catalog.py
--surface` applies it for you. The two kinds of car, and how to tell them apart from the car's
`Catalog source:` line, are defined in `notion-structure.md` → *Where a car's catalog lives*.
**`Setups` slices are read here for every car**, template or screenshot.

## Why this exists
The Notion **connector** (MCP tools `notion-search` + `notion-fetch`) **cannot reliably list a
database's rows**:
- `notion-fetch` on a database/data source returns its **schema only — no rows**.
- `notion-search` is **semantic, capped at 25, has no pagination, and mixes cars** — so for a
  shared table holding every car's parameters it silently drops rows or returns another car's.

So enumerating "all rows where `Car` = X" through the connector is not dependable. Instead, query
the database directly through Notion's REST API, which supports an exact filter and pagination.

## What you need
1. **The data source id.** Resolve the database by name (per `notion-structure.md`), then
   `notion-fetch` it once and read the `collection://<uuid>` from its `<data-source>` tag. The id
   is the `<uuid>` **with the `collection://` prefix stripped**.
2. **A read-only integration token** (`secret_…` / `ntn_…`). See "Give the skill read access to
   Notion" in `README.md` for the one-time setup. Obtain the token at read time:
   - **Primary:** `notion-fetch` the **`Config`** page under `ACR Setup Engineer` and read the token from
     it (it persists across chats). The page is auto-created with the structure, so it normally
     exists.
   - **Page exists but no token pasted yet** (just the seeded instructions): the one-time setup
     steps are right there on the page — point the user to them, or have them paste a token for
     this chat. Don't read rows without a token (see "No token" below).
   - **No `Config` page at all** (unusual): ask the user to paste the token for this chat, or walk
     them through the one-time setup (the README section / the `Config` page instructions).

## Do the reads in one pass (don't seed context one round-trip at a time)
For a template car, `load_catalog.py` goes in the **same code-execution block** as the `Setups`
REST queries — it is local, so it costs nothing extra and needs no token.

Resolve the structure **once**, then collapse the rest (`SKILL.md` → *Read efficiently*):
- Fire the independent reads **together in a single step (parallel tool calls)** — the
  `Parameters`/`Setups` DB `notion-fetch`es (for their `data_source_id`s), the car's `Catalog` and
  `Guidelines` pages, the
  `Tuning guidelines` page, and any `{Stage}`/`{Location}` page. `notion-fetch` is one entity per
  call, so issue them in parallel rather than sequentially.
- Run **all** the REST queries below (e.g. the car's `Parameters` **and** a `Setups` slice) in **one
  code-execution block**, not a separate block each.
- **Fetch each page once** (identity facts are on `Catalog`, the user's notes on `Guidelines`),
  reuse the
  `data_source_id`s within the run, and skip anything already loaded in the thread.

## The query — run the bundled script
Run this in **code execution** (the sandbox must allow outbound HTTPS to `api.notion.com` — when
it can't, walk the fallback ladder below):

```
# Parameters catalog for one SCREENSHOT car (a template car reads load_catalog.py instead):
python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>"

# Setups learn-pool slice (build-setup learn mode):
python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>" --learn-only

# Captured game-default (stock) baseline rows for a car (build-setup step 4 anchor):
python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>" --source default
```

- `<car_name>` must **exactly** match the `Car` select option (e.g. `Alpine A110 1.8 1973`).
- The script handles pagination automatically and exits 0 on success, 1 on HTTP/network error.
- `--learn-only` **excludes `Source = default` rows** automatically — a captured stock baseline holds
  the game's values, not the user's taste, so it is consumed only as the build anchor
  (`notion-structure.md` → *Default (stock) baseline rows*). The two slices are complementary: run
  both in the **same** code-execution block when a build needs the anchor and the learn pool.

**Output:** a JSON array — one object per row, property names as keys:
- `title` / `rich_text` properties → string (`""` when blank).
- `select` → string or omitted when null.
- `checkbox` → boolean. `number` → number or omitted when null.

For the **Parameters catalog** each object contains: `Adjustment`, `Section`, `Min`, `Max`,
`Unit`, `Discrete steps` (blank `""` means continuous or never captured), `Order`, `Car`, and an
optional `Surface` (`Tarmac` / `Gravel` / `Snow`; **omitted when blank** — that's the baseline
row). Build the in-memory catalog from these — then apply the normal value/legality rules.
**`scripts/load_catalog.py` prints the same objects, with the same keys and the same blank/omitted
conventions**, for a template car — which is why a workflow only has to change *where* it gets the
rows, never what it does with them.

## Resolving the range for a surface
A `Car × Adjustment` may have **more than one row**: a baseline row (`Surface` omitted) plus an
optional surface-specific row (e.g. `Surface = Gravel`) when its legal range differs on that
surface. Whenever you need a parameter's legal range for a setup on **surface S** (the stage's /
setup's `Surface`):

1. If a row for that `Adjustment` has `Surface == S`, use **that** row's `Min`/`Max`/`Discrete steps`.
2. **Else if `S == Snow` and a `Surface == Gravel` row exists, use the `Gravel` row** — snow
   inherits gravel's softer ranges. Snow never has rows of its own: a screenshot car's optional
   gravel pass, or a template's `Gravel` entries, are as far as the surface split goes.
3. Otherwise use the **baseline** row (no `Surface`).
4. If none exists, the parameter isn't available for that car — skip it.

So group the returned rows by `Adjustment`, then pick the surface-matching row if present (for
`Snow`, fall back to a `Gravel` row before the baseline), else the baseline. Most parameters have
only the baseline row and resolve to it on every surface.

## Offline mode — check the network once per chat
**Before the first REST query in a chat**, run `python scripts/check_egress.py` at the start of
that same code-execution block, and **let the block run the REST queries only when it printed
`egress: ok`** — the queries sit behind the probe in one block, so the block must gate them itself
(e.g. `python scripts/check_egress.py | grep -q "egress: ok" && python scripts/query_notion_parameters.py …`),
while token-free work in the block (`load_catalog.py`, `--show-order --from-template`) runs either
way. The probe prints `egress: ok` or `egress: none`, always exits 0, and takes 3 seconds at most. **Run it once per chat**: its answer holds for every later read and every
later workflow in the chat — don't re-run it per read.

- **`egress: ok`** → the normal path: token, REST query, and the ladder below if a query still
  fails.
- **`egress: none`** → **offline mode for the rest of the chat.** Run **no** REST query at all, and
  don't fetch `Config` for a token or ask for one — a token can't help without network. Each read
  goes straight to the rung it would have fallen back to anyway:
  - every **`Setups` slice** (the learn pool, a stored default, any other) → **empty**, as rung 2
    describes;
  - a **screenshot car's `Parameters`** → its `Catalog snapshot` (*The catalog snapshot fallback*
    below);
  - **column order** → the template part only (`notion-structure.md` → *Applying the order*),
    still pushed as `SHOW`.

  Nothing else changes: template catalogs (`load_catalog.py`), every connector read and write,
  and saving setups to Notion all work as usual.
- **Tell the user once per chat, in plain words** — the first time offline mode changes what a
  workflow does, never before each read, and never worded as an error:

  > *This chat can't reach Notion's API. That's normal on Claude's Free plan. It means I can't
  > read your saved setups, so the ones you ticked `Learn from this` won't shape this setup, and
  > I can't reuse a stored game default. Everything else works, and new setups still save to
  > Notion. (On Pro or Max you can turn this on: Settings → Capabilities → Network egress → All
  > domains, then start a new chat.)*

  Keep the `Learn from this` sentence whenever the workflow would have read the learn pool — it
  is the part the user loses without noticing. For a **screenshot car**, add that its parameter
  list comes from the `Catalog snapshot` and give the snapshot's `written_at`.

## When the REST query can't run — the fallback ladder
**Template cars never enter this ladder for their catalog** — it is on disk, so there is nothing
to fall back from (`load_catalog.py` needs no token and no egress). The ladder applies to a
screenshot car's `Parameters` read, and to a `Setups` slice for any car.

This REST query **is** the primary read path — **never** substitute the connector's row-listing
(`notion-search` / a database `notion-fetch`), which is unreliable (capped, semantic, mixes cars)
and produces silently wrong setups. When the query can't run, walk this ladder instead:

1. **No token available:** the `Config` page (auto-created with the structure) already carries the
   one-time setup steps — point the user there (or to "Give the skill read access to Notion" in
   `README.md`), or have them paste a token for this chat. Then read. (Never in offline mode —
   *Offline mode* above: there, don't mention a token at all.)
2. **Query errors / times out:** the usual cause is the code sandbox not being allowed outbound
   network to `api.notion.com` (egress is restricted by default — and on **Claude's Free plan it
   can't be widened at all**: the "All domains" egress setting doesn't exist there). Don't retry
   endlessly and don't guess values:
   - **`Parameters` catalog reads** (a screenshot car) fall back to that car's `Catalog` page
     **snapshot** — next section.
   - **`Setups` slice reads have no fallback** (setups accumulate; no snapshot can stay current).
     Proceed as if the slice came back **empty**, and say plainly which feature was skipped and
     why: a learn-pool read ⇒ the setup is built without the user's setup history; a
     stored-default read ⇒ no stored baseline is visible, so follow the normal no-baseline path
     (ask for fresh default screenshots). Anything captured **in the current chat** is unaffected
     — those values are already in context.
3. **Neither the query nor a valid snapshot is available:** surface the problem and stop the read
   — never assemble rows from search results, and never guess.

Tell the user which path a read took whenever it isn't the REST query (in offline mode, the one
message in *Offline mode* above covers it). On a plan **with** egress
control the fix is Settings → Capabilities → Network egress → **All domains**, then a **new chat**
(settings changes don't apply to an already-open conversation).

## The catalog snapshot fallback
Every car's **`Catalog`** page ends with an auto-maintained **`Catalog snapshot`** toggle — the
car's full catalog as YAML, refreshed by every workflow that writes the catalog
(`notion-structure.md` → *Catalog snapshot* has the format and refresh rules). **This is a read
path for screenshot cars only**: a template car's snapshot is a readable copy for the user, and
the skill reads that car's template file instead — always, egress or not. To read from it:

1. `notion-fetch` the car's `Catalog` page (you usually hold it already — `SKILL.md` → *Read
   efficiently*). **Check the response's `truncated` / `unknown_block_count` indicators first**:
   if the page came back incomplete, treat the snapshot as unavailable rather than parsing a
   partial block.
2. Parse the YAML inside the toggle and **validate before use**: `car` matches the requested car,
   and `row_count` equals the number of entries in `rows`. Any mismatch ⇒ treat as no snapshot
   (rung 3 above).
3. Each `rows` entry mirrors this doc's *Output* keys exactly (same names, same blank/omitted
   conventions), so build the in-memory catalog from them and apply the normal
   surface-resolution and value/legality rules unchanged.
4. **Say the read used the snapshot and give its `written_at`** — hand-edits to `Parameters` rows
   since that date aren't in it. When the output leaves the user's own Notion (e.g. a template
   export), confirm nothing was edited since — see `export-car-template.md` step 1.

**No snapshot on the page** (screenshot car onboarded by an older skill version): rung 3 above — and
offer the fix in the same breath: `refresh-catalog-snapshot.md` writes the snapshot and nothing
else, and works even without egress (the user pastes the car's `Parameters` table from Notion).
Re-onboarding also writes it, as does any setup-saving run on a plan with egress
(`notion-structure.md` → *Backfill*).

## Scope
Only ever query a data source **inside `ACR Setup Engineer`**. Never use this against a database resolved
from a workspace-wide search, and discard any row whose `Car` isn't the requested one.
