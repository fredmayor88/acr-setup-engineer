# Reading `Setups` rows from Notion — the REST query

**The one way to read a filtered slice of the `Setups` database** (the learn pool, a stored game
default, a named setup's row when a workflow needs the row's values). Use it wherever a workflow
says "fetch this car's `Setups` rows".

**Catalogs are not read here.** A car's legal values come from a template file — bundled, or the
`yaml` block on the car's `Parameters` page — loaded by `catalog-read.md`. That path needs no
token and no network, on every plan.

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
   - **No `Config` page at all** (unusual): ask the user to paste a token for this chat, or walk
     them through the one-time setup (the README section / the `Config` page instructions).

## Do the reads in one pass (don't seed context one round-trip at a time)
For a template car, `load_catalog.py` goes in the **same code-execution block** as the `Setups`
REST queries — it is local, so it costs nothing extra and needs no token.

Resolve the structure **once**, then collapse the rest (`SKILL.md` → *Read efficiently*):
- Fire the independent reads **together in a single step (parallel tool calls)** — the
  `Setups` DB `notion-fetch` (for its `setups_data_source_id`), the car's `Catalog` and
  `Guidelines` pages, the
  `Tuning guidelines` page, and any `{Stage}`/`{Location}` page. `notion-fetch` is one entity per
  call, so issue them in parallel rather than sequentially.
- Run **all** the REST queries below (e.g. the learn-pool slice **and** the stored-default slice)
  in **one code-execution block**, not a separate block each.
- **Fetch each page once** (identity facts are on `Catalog`, the user's notes on `Guidelines`),
  reuse the
  `setups_data_source_id` within the run, and skip anything already loaded in the thread.

## The query — run the bundled script
Run this in **code execution** (the sandbox must allow outbound HTTPS to `api.notion.com` — when
it can't, walk the fallback ladder below):

```
# Setups learn-pool slice (build-setup learn mode):
python scripts/query_notion_parameters.py <setups_data_source_id> <token> "<car_name>" --learn-only

# Captured game-default (stock) baseline rows for a car (build-setup step 4 anchor):
python scripts/query_notion_parameters.py <setups_data_source_id> <token> "<car_name>" --source default

# Plain (unfiltered) Setups slice for the car — every row, learn pool and defaults alike:
python scripts/query_notion_parameters.py <setups_data_source_id> <token> "<car_name>"
```

- `<car_name>` must **exactly** match the `Car` select option (e.g. `Alpine A110 1.8 1973`).
- The script handles pagination automatically and exits 0 on success, 1 on HTTP/network error.
- `--learn-only` **excludes `Source = default` rows** automatically — a captured stock baseline holds
  the game's values, not the user's taste, so it is consumed only as the build anchor
  (`notion-structure.md` → *Default (stock) baseline rows*). The two slices are complementary: run
  both in the **same** code-execution block when a build needs the anchor and the learn pool.
- The **plain slice** (no `--source`/`--learn-only` filter) is what *The `learn:` override on paid
  plans* below adds `learn: yes` rows from. Run it in the **same** code-execution block as the
  other two whenever the build reads its learn pool — the override step needs it. It is one more
  REST query, but a small one, and it reuses the token and data source id already in hand from the
  other calls in the same block.

**Output:** a JSON array — one object per row, property names as keys:
- `title` / `rich_text` properties → string (`""` when blank).
- `select` → string or omitted when null.
- `checkbox` → boolean. `number` → number or omitted when null.

**`Setups` rows** (what the queries above return): one object per setup, keyed by the meta
columns — `Name`, `Car`, `Location`, `Stage`, `Surface`, `Conditions`, `Date`, `Source`, `Mode`,
`Rating`, `Learn from this`, `Game version`, `Notes`, `Model`, `Skill version` (the exact list is
`notion-structure.md` → *`Setups` DB*) — plus **one key per tunable parameter, named after the
parameter** (e.g. `"Spring Stiffness Front": 50000`). Blank cells follow the property-type rules
above.

**Catalog rows** (not returned by this query): a car's catalog rows — loaded by
`catalog-read.md`, never by this query — contain: `Adjustment`, `Section`, `Min`, `Max`, `Unit`,
`Discrete steps` (blank `""` means continuous or never captured), `Order`, `Car`, and an optional
`Surface` (`Tarmac` / `Gravel` / `Snow`; **omitted when blank** — that's the baseline row). This
is also the shape `load_catalog.py` prints, so every downstream rule reads one shape, whichever
file the catalog came from.

## The `learn:` override on paid plans

The user may mark a line in the car's `Setup index` by hand with ` - learn: yes` or
` - learn: no` (`notion-structure.md` → *`Setups` page*). It means the same thing on every plan,
so a build that read its learn pool over REST honours it too — one extra page fetch, once per
build, right after the REST queries:

1. Fetch the car's `Setups` page (it's fetched anyway for the column order), save it to
   `setups/<slug>.md`, run `python scripts/setups_list.py --overrides setups/<slug>.md` → JSON
   `{"yes": [names], "no": [names], "malformed": n}`.
2. **Drop** from the learn pool every row whose `Name` is in `no`.
3. **Add** every row whose `Name` is in `yes` and isn't in the pool yet — its row is in the **plain
   slice** run above (`## The query — run the bundled script`, the third command, no
   `--source`/`--learn-only` filter), already fetched in the same code-execution block, so no extra
   REST call is needed.
4. Both lists empty → nothing to do, say nothing.

## Resolving the range for a surface
Applied for you by `load_catalog.py --surface`; documented here because `catalog-read.md` points
to it.

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
  - every **`Setups` slice** (the learn pool, a stored default) → **read from the car's `Setup
    index` instead**, per [setups-list-read.md](setups-list-read.md): the list of links on the
    car's `Setups` page, a capped set of page fetches through the connector. Never empty by
    default, never a search;
  - a **named setup** (review, tweak, ask, share) → `setups-list-read.md` → *Finding one setup by
    name*;
  - **column order** → unchanged — it never needed the network (`notion-structure.md` → *Applying
    the order*), still pushed as `SHOW`.

  Nothing else changes: template catalogs (`load_catalog.py`), every connector read and write,
  and saving setups to Notion all work as usual.
- **Tell the user once per chat, in plain words** — the exact text is in `setups-list-read.md` →
  *Telling the user*. Say it the first time offline mode changes what a workflow does, never
  before each read, never as an error. Never claim the skill has no access to what's saved: it
  reads it fine, for the setups the skill saved from this version on.

## When the REST query can't run — the fallback ladder
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
   - **`Setups` slice reads have no fallback** (setups accumulate; no snapshot can stay current).
     Proceed as if the slice came back **empty**, and say plainly which feature was skipped and
     why: a learn-pool read ⇒ the setup is built without the user's setup history; a
     stored-default read ⇒ no stored baseline is visible, so follow the normal no-baseline path
     (ask for fresh default screenshots). Anything captured **in the current chat** is unaffected
     — those values are already in context. This rung is for a plan **with** egress whose query
     failed; it never applies in offline mode, which reads the index instead.
3. **The query can't run and the workflow needs the rows:** say which feature was skipped and go
   on without them (rung 2). Never assemble rows from search results, and never guess.

Tell the user which path a read took whenever it isn't the REST query (in offline mode, the one
message in *Offline mode* above covers it). On a plan **with** egress
control the fix is Settings → Capabilities → Network egress → **All domains**, then a **new chat**
(settings changes don't apply to an already-open conversation).

## Scope
Only ever query a data source **inside `ACR Setup Engineer`**. Never use this against a database resolved
from a workspace-wide search, and discard any row whose `Car` isn't the requested one.
