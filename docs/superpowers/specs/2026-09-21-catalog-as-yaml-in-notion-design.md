# Every car's catalog is a template file — bundled, or stored in Notion

**Status:** approved 2026-09-21 · **Date:** 2026-09-21

## Summary

Today a car's catalog (the legal values of its tunable parameters) lives in one of two places:
a bundled `car-templates/*.yaml` file inside the skill, or rows in the `Parameters` database in
the user's Notion. The rows can only be read over the Notion REST API, which needs a token and
network access the code sandbox doesn't have on Claude's Free plan. Everything built around that
gap (the `Catalog snapshot` fallback, the paste route, the REST `Parameters` query, the mixed
column-ordering call) exists only because the rows can't be read any other way.

This design removes the second place. **A car onboarded from screenshots stores its catalog as a
template file too, in the same YAML format as a bundled one, on a page in the user's Notion.**
The Notion connector can fetch a page in full on every plan, and `load_catalog.py` already reads
that format. So there is one catalog format, one reader, one edit path (in chat), and no
`Parameters` database. The REST token is then only ever needed for the `Setups` history.

## Goals

- One catalog format for every car: the bundled template format.
- One read path: `load_catalog.py` on a file — bundled, or fetched from Notion and saved in the
  sandbox. Works identically on Free and on paid plans.
- Catalog edits happen in chat, validated, on every plan. No paste route, no hand-editing rows.
- Export a screenshot car = hand over the file that is already in Notion.
- Column ordering for every view comes from template files only.
- No `Parameters` database is created for new users. Existing ones are left alone and never read
  after migration.

## Non-goals

- Reading `Setups` rows without REST (the `Learn from this` gap on Free). Separate design.
- Deleting anything from the user's Notion. The legacy `Parameters` DB stays where it is.
- Changing the template format itself, beyond adding optional header keys.

## Data model

### Car kinds

| Kind | Catalog lives in | `Catalog source:` line |
|---|---|---|
| **Template car** | `car-templates/<slug>.yaml` inside the skill | `bundled template — game version {v}, from {source}` |
| **Screenshot car** | the car's **`Parameters` page** in Notion | `your screenshots — game version {v}` |

Nothing else changes about the kinds: a screenshot car is still one the user captured (or one
they edited away from a bundled template — see *Editing*), and the source line still decides the
kind. A refresh still switches a screenshot car to a template at least as new (already shipped).

### The car's `Parameters` page (screenshot cars only)

A fifth child page under `{Car}`, next to `Guidelines`, `Catalog`, `Log` and `Setups`. A template
car has no such page.

```
{Car}
├── Guidelines    yours
├── Catalog       the skill's, replaced wholesale on refresh
├── Log           shared, add-only
├── Parameters    the skill's, edited in chat — NEVER regenerated, this is the only copy
└── Setups        the filtered view
```

Body, in order:

1. Maintenance line (italic, first block):
   *Your car's parameter list, kept by the skill. To change a range, say it in chat
   ("the front ARB goes 1 to 6 in steps of 1") — don't edit this page by hand. It survives
   refreshes.*
2. One fenced `yaml` code block: **a complete template file** for the car, exactly what
   `car-templates/<slug>.yaml` would contain if it were bundled — header fields (`car`, `game`,
   `drivetrain`, identity facts, `version`, `source: "screenshots"`, no `gearing_tool` or
   `engine_curve` unless known), then `parameters:` with one entry per row, `surface:` on
   surface-specific entries.

Optional header keys the skill adds so the file is self-describing and checkable:

```yaml
written_at: "2026-09-21"
skill_version: "v0.20.0"
parameter_count: 43
```

`load_catalog.py` ignores header keys it doesn't know, so these are safe today; it gains a check
that `parameter_count`, when present, equals the number of `parameters:` entries (a truncated
fetch fails that check instead of silently producing a short catalog).

**Ownership:** the skill writes it, the user changes it through chat. A refresh **never
regenerates it** — there is nothing to regenerate it from. The connector fetch of this page is
the read path; a `truncated` / `unknown_block_count` flag on the fetch means "unreadable", never
"use what came back".

**Naming.** `Parameters` (decided). The root-level legacy `Parameters` database keeps its name; the
new page is a child of the car, so the two never resolve to each other. The page is the **complete
list**, read *instead of* the bundled file — not an override merged onto it.

### What goes away

- `Catalog snapshot` toggle on `Catalog` pages. A template car's `Catalog` page loses it (the
  bundled file is the copy; `Catalog` keeps the identity facts, source line, chart and link). A
  screenshot car's catalog is on its own page.
- The `Parameters` DB: never created, never read. `notion-structure.md`'s schema section for it
  becomes a *Legacy* note.
- `refresh-catalog-snapshot.md` and the paste route.
- The REST `Parameters` query and the `--all` / `<params_ds> <token> "{Car}"` forms of
  `query_notion_parameters.py` for ordering. The script keeps its `Setups` reads and
  `--show-order --from-template`.

## Read path (every workflow that loads a catalog)

1. Decide the kind from the `Catalog source:` line, as today.
2. **Template car:** `python scripts/load_catalog.py car-templates/<slug>.yaml [--surface S]`.
3. **Screenshot car:** fetch the car's `Parameters` page (batched with `Catalog`, `Guidelines`,
   `Log` — one round trip, as `SKILL.md` → *Read efficiently* already requires), check the fetch
   isn't truncated, write the YAML block to `parameters/<slug>.yaml` in the sandbox, then the same
   `load_catalog.py` call. The model never parses the YAML itself.
4. If the page is missing or unreadable: stop the read and say so — *"the {Car}'s `Parameters`
   page is missing/unreadable; say 'refresh the {Car} in my Notion' to rebuild it, or 'onboard
   the {Car} from my screenshots'"*. Never fall back to connector row-listing (unchanged rule).

`notion-rest-read.md` shrinks to the `Setups` reads and offline mode. Its *fallback ladder* loses
the catalog rungs; *The catalog snapshot fallback* section is deleted.

## Writes

### Onboarding from screenshots (`onboard-car.md`, screenshot path)

Steps 2–5 (read the screenshots, extract, confirm, identity facts) are unchanged. Step 7 changes:

- **Write the `Parameters` page** with the maintenance line and the template YAML built from the
  rows in hand (`load_catalog.py` gains `--to-template rows.json` to emit it, so the model never
  hand-formats YAML). Create-or-replace: a re-onboard from screenshots replaces the block.
- **Write no `Parameters` DB rows**, and don't create the DB.
- `Setups` value columns and the `SHOW` order: as today, from the rows in hand.
- Step 8 (gravel pass) and step 9 (`Discrete steps` given in chat) update the same block —
  rebuild the YAML from the updated rows and replace the block. No "fill the cells in Notion
  later" option any more; the offer is "tell me here whenever you have them".

### Editing a catalog in chat (new: `edit-catalog.md`)

Trigger: *"the {car}'s {parameter} goes from A to B"*, *"set the steps for {parameter} to …"*,
*"add {parameter} to the {car}"*, *"{parameter} isn't adjustable on the {car}, remove it"*, and
any request that changes a car's legal values.

1. Load the catalog (read path above).
2. Apply the change in memory: min/max, `Discrete steps`, unit, `Order` (a new parameter gets an
   order inside its section block per *Canonical ACR default order*), surface-specific entry,
   removal. Validate: numeric min ≤ max, steps inside min..max when both exist, gear notation
   rules (`SKILL.md` → *Value notation is literal*), no duplicate `Adjustment × Surface`.
3. Show the affected entries before/after and get an explicit OK.
4. **Template car → fork, no question, one line.** Write a `Parameters` page for the car from
   the bundled template plus the change. Its maintenance line carries the moment and the reason:
   *"Started {date} as a copy of the bundled template (game version {tv}), with your edits. The
   skill keeps this list; say changes in chat."* The YAML header gets
   `forked_from: "bundled template v{tv}"`. Rewrite `Catalog` with the source line
   `your screenshots — started from bundled template v{tv} on {date}`. Say in one line that the
   car now uses its own list and that a refresh will offer the bundled one again only when a
   newer template ships.
5. **Screenshot car → replace the block**, bump `written_at`, `parameter_count`.
6. A new `Adjustment` → add the `Setups` value column (existing *value-columns check*), then
   reassert `SHOW` on the car's view and the shared views.
7. Report in one line what changed.

### Refresh (`onboard-car.md` refresh path, and `refresh-notion.md`)

- Template car: as today, minus the snapshot toggle.
- Screenshot car: **`Parameters` page is left untouched**, except migration (below). The
  version-based switch to a template (already shipped) keeps working; on a switch the page is
  **left in place, unread**, with one line added at the top of its body:
  *"Not in use since {date}: a newer bundled template (game version {v}) appeared, so this car
  uses that now. Say 'onboard the {Car} from my screenshots' to use this list again."* — the only time the skill writes to this page outside
  an edit. (Keeping it means the user's captured list is never lost.)

### Migration — a screenshot car from before this change

Runs inside the refresh, once, when a screenshot car has **no `Parameters` page**:

1. **Source, first that works:**
   a. its `Catalog snapshot` toggle (old format) — convert rows → template YAML;
   b. its rows in the legacy `Parameters` DB over REST, when the chat has network and a token;
   c. neither → create the page with the maintenance line and an empty `parameters:` list, and
      tell the user the car needs *"onboard the {Car} from my screenshots"* before it can be
      used. A read of an empty catalog fails loudly (step 4 of the read path).
2. Write the page. Rebuild `Catalog` without the snapshot toggle.
3. Report: *"moved the {Car}'s parameter list to its own page"*; once per run, the legacy line:
   *"Your `Parameters` table isn't read any more by any car. You can delete it."*

A template car's refresh just drops the snapshot toggle from `Catalog`. Nothing else to migrate.

### Import from a save file (`import-savegame.md`)

Unchanged in substance: a template car auto-onboards from the bundled file; a car with no
template still needs onboarding first. The step that wrote the snapshot goes.

## Column ordering (`notion-structure.md` → *Applying the order*)

Three cases collapse into one: **every car is a template file.** For the shared views
(main `Setups` table, `{Location}`, `{Stage}`):

```
python scripts/query_notion_parameters.py --show-order \
    --from-template car-templates/<c1>.yaml --from-template parameters/<c2>.yaml …
```

A screenshot car's file is the one saved to the sandbox during the read (or from the rows in hand
during onboarding). No token, no network, no `--all`. The "which cars to pass" rule stays: the
root fetch lists the cars; a screenshot car's page is fetched only when its file isn't already in
the sandbox this run. When a screenshot car's page can't be fetched (offline and truncated,
say), pass the cars you have and say that car's columns keep their position — the existing
"never drop the SHOW" rule.

## Export (`export-car-template.md`)

For a screenshot car the file already exists: fetch the `Parameters` page, save the block, run
the existing validation, and hand it over exactly as today (the GitHub form flow). Step 1's REST
read and the staleness question go. `source:` in the exported file is normalised to
`"community"`; `written_at` / `skill_version` / `parameter_count` are stripped.

## Free plan

The `Claude Free plan` page and `notion-rest-read.md` → *Offline mode* lose the screenshot-car
bullets: catalogs behave the same on every plan. What Free can't do is only the `Setups` history.
The offline message's wording is unchanged (it never mentioned catalogs).

## Scripts

`load_catalog.py`:
- `--to-template rows.json` — rows in the REST/`Output` shape (what onboarding assembles) →
  a complete template YAML on stdout, header fields from a `header` object in the same JSON.
  Used by onboarding, editing and migration (a) so YAML is never hand-formatted.
- `parameter_count` header check on load (mismatch → exit 1 with a clear message).
- `--snapshot` is removed.

`query_notion_parameters.py`: the `Parameters` query paths and `--all` are removed; `Setups`
reads and `--show-order --from-template` stay. Tests for the removed paths go with them.

New tests: `--to-template` round-trips through `load_catalog.py` to identical rows; the
`parameter_count` check fails on a truncated file; a fork of a bundled car produces a file that
loads to the same rows plus the edit.

## Documentation

- `notion-structure.md`: *Where a car's catalog lives* (rewritten), *Car page* (five children),
  a new *`Parameters` page* section, *Applying the order* (one case), *Catalog snapshot*
  (deleted), *`Parameters` DB* (legacy note).
- `notion-rest-read.md`: `Setups` reads and offline mode only.
- `onboard-car.md`, `export-car-template.md`, `import-savegame.md`, every workflow's "load the
  catalog" step: the read path above.
- New `edit-catalog.md`; `refresh-catalog-snapshot.md` deleted; `SKILL.md` routing table
  (+ edit, − snapshot), tools list, *Reading rows* rule.
- `How to use` template: an *Edit a car's parameter list* line (the coverage test enforces it).
- README: *What it creates in Notion*, *Pinning a setting to exact values* (becomes "say it in
  chat"), the Free section, *How it reads and writes Notion*.
- `CLAUDE.md`: the scripts list and the new page.

## Rollout

One release. Existing users: the first refresh (single car, or *"refresh my ACR Notion"*)
migrates each screenshot car; until then a screenshot car without a `Parameters` page is
migrated on the spot by whichever workflow first reads it (the migration is one page write from
data already in hand, so it is allowed from a read workflow — the one exception to "read-only
workflows never gain a write", stated explicitly).

## Decisions from review (2026-09-21)

1. Page name: `Parameters`.
2. On a switch to a bundled template: keep the page, add the "not in use since" line with the
   reason (a newer template appeared).
3. Editing a template car forks without asking; one line says so, with the timestamp.
4. **Every workflow must be followable by a less capable model** (Sonnet): short numbered steps,
   one decision per step, exact wording to say, and scripts for everything deterministic
   (parsing, YAML, validation). Recorded as a project rule in `CLAUDE.md`.
