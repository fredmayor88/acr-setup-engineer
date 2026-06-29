# Reading rows from a Notion database — the reliable way

**The canonical way to read a car's rows from a `Car setups` database** (the `Parameters`
catalog, or a filtered slice of `Setups`). Use this wherever a workflow says "fetch the car's
`Parameters` rows" or "fetch this car's `Setups` rows".

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
   - **Primary:** `notion-fetch` the **`Config`** page under `Car setups` and read the token from
     it (it persists across chats).
   - If there is no `Config` page, ask the user to paste the token for this chat. If they don't
     have one yet, **walk them through the one-time setup** (point to the README section) — don't
     try to read rows without it (see "No token" below).

## Do the reads in one pass (don't seed context one round-trip at a time)
Resolve the structure **once**, then collapse the rest (`SKILL.md` → *Read efficiently*):
- Fire the independent reads **together in a single step (parallel tool calls)** — the
  `Parameters`/`Setups` DB `notion-fetch`es (for their `data_source_id`s), the `{Car}` page, the
  `Tuning guidelines` page, and any `{Stage}`/`{Location}` page. `notion-fetch` is one entity per
  call, so issue them in parallel rather than sequentially.
- Run **all** the REST queries below (e.g. the car's `Parameters` **and** a `Setups` slice) in **one
  code-execution block**, not a separate block each.
- **Fetch each page once** (the `{Car}` page has both identity facts and Guidelines), reuse the
  `data_source_id`s within the run, and skip anything already loaded in the thread.

## The query — run the bundled script
Run this in **code execution** (the sandbox must allow outbound HTTPS to `api.notion.com`):

```
# Parameters catalog for one car:
python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>"

# Setups learn-pool slice (build-setup learn mode):
python scripts/query_notion_parameters.py <data_source_id> <token> "<car_name>" --learn-only
```

- `<car_name>` must **exactly** match the `Car` select option (e.g. `Alpine A110 1.8 1973`).
- The script handles pagination automatically and exits 0 on success, 1 on HTTP/network error.

**Output:** a JSON array — one object per row, property names as keys:
- `title` / `rich_text` properties → string (`""` when blank).
- `select` → string or omitted when null.
- `checkbox` → boolean. `number` → number or omitted when null.

For the **Parameters catalog** each object contains: `Adjustment`, `Section`, `Min`, `Max`,
`Unit`, `Discrete steps` (blank `""` means continuous or never captured), `Car`, and an optional
`Surface` (`Tarmac` / `Gravel` / `Snow`; **omitted when blank** — that's the baseline row).
Build the in-memory catalog from these — then apply the normal value/legality rules.

## Resolving the range for a surface
A `Car × Adjustment` may have **more than one row**: a baseline row (`Surface` omitted) plus an
optional surface-specific row (e.g. `Surface = Gravel`) when its legal range differs on that
surface. Whenever you need a parameter's legal range for a setup on **surface S** (the stage's /
setup's `Surface`):

1. If a row for that `Adjustment` has `Surface == S`, use **that** row's `Min`/`Max`/`Discrete steps`.
2. **Else if `S == Snow` and a `Surface == Gravel` row exists, use the `Gravel` row** — snow
   inherits gravel's softer ranges (cars are onboarded with a gravel pass but no separate snow
   pass).
3. Otherwise use the **baseline** row (no `Surface`).
4. If none exists, the parameter isn't available for that car — skip it.

So group the returned rows by `Adjustment`, then pick the surface-matching row if present (for
`Snow`, fall back to a `Gravel` row before the baseline), else the baseline. Most parameters have
only the baseline row and resolve to it on every surface.

## No token (or the query fails)
This REST query **is** the read path — don't substitute the connector's row-listing, which is
unreliable (capped, semantic, mixes cars) and produces silently wrong setups.
- **No token available:** stop and walk the user through the one-time setup ("Give the skill read
  access to Notion" in `README.md`), or have them paste a token for this chat. Then read.
- **Query errors / times out:** the most common cause is the code sandbox not being allowed
  outbound network to `api.notion.com` (egress is restricted by default). Tell the user reads need
  outbound access enabled (or a pasted token) — surface the problem; don't fall back to a degraded
  read and don't guess values.

## Scope
Only ever query a data source **inside `Car setups`**. Never use this against a database resolved
from a workspace-wide search, and discard any row whose `Car` isn't the requested one.
