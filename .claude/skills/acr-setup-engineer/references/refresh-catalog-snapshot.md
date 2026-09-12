# Workflow: refresh the catalog snapshot

Create or refresh the **`Catalog snapshot`** toggle on a `{Car}` page (`notion-structure.md` →
*Catalog snapshot*) **without touching anything else** — no `Parameters` rows, no `Setups` rows,
no identity facts, no views. Made for cars onboarded before the snapshot existed (so they become
readable without network egress — e.g. on Claude's Free plan), and for repairing a snapshot that
fails validation.

Read `notion-structure.md` → *Catalog snapshot* (format + placement) before writing.

## Trigger phrases
"refresh the catalog snapshot", "add / create the catalog snapshot for {car}", "fix the
snapshot", "make {car} readable on Free" — and arriving from `notion-rest-read.md`'s *No snapshot
on the page* case.

**Not this workflow: a bare "refresh {car}".** *"Refresh the Lancia Stratos in my Notion"*,
*"update the {car}"*, *"re-onboard {car}"* name the **car**, not the snapshot — the user wants
everything static about it brought up to date (identity facts, the engine/gearing charts, the
`Parameters` catalog **and** the snapshot). That's `onboard-car.md`'s refresh path; go there. This
workflow is the **narrow** one, chosen only when the user names the *snapshot* itself or when a
read path sent you here. Writing only the snapshot for a request that said "refresh the car"
silently leaves the charts and identity facts stale — the exact failure this note exists to
prevent.

## Inputs
- **Car name** — must already be onboarded (its `Parameters` rows exist in Notion). If it isn't,
  say so and point to `onboard-car.md` — onboarding writes the snapshot itself, and its step 9
  can take `Discrete steps` in chat so a fresh screenshot onboard needs no refresh at all.

## Procedure

1. **Resolve the structure by name** (`notion-structure.md`) and fetch the `{Car}` page.

2. **Get the car's rows — first source that works, in this order:**

   1. **The REST read** (`notion-rest-read.md`) — the normal path whenever the sandbox has
      egress. Complete and exact; use it if it runs.
   2. **The bundled template — automatic whenever one matches the car.** Look in
      `car-templates/` for a matching file (same match rule as `onboard-car.md` step 1) and, if
      one is there, **build the rows from it and write the snapshot — no questions first.** It's
      on disk, it needs no network, and it is the curated catalog for that car. Don't ask the
      user to paste anything they already shipped with the skill.
      Then **say so in the report** (step 4) and add one line: the snapshot holds the bundled
      template's ranges, so if they've hand-filled `Discrete steps` or corrected a range in
      Notion, those aren't in it — say the word and it gets rebuilt from a paste instead. That's
      a cheap, reversible disclosure, and it beats interrogating every user about edits most of
      them never made.
      Note the template's `version:` in the report too: a template newer than the user's onboard
      carries **corrected** ranges for the current game version, which is a fix, not a
      regression — the `Parameters` rows in Notion are left untouched either way.
   3. **The paste path — works everywhere, including Free.** Ask the user to open the
      `Parameters` view filtered to this car in Notion (desktop is easiest), select the table,
      and paste it into the chat. Parse the pasted rows into the catalog fields (`Adjustment`,
      `Section`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`, `Surface`), then **echo the
      parsed table and row count back and get an explicit OK before writing** — the user is the
      completeness check on this path. A pasted table is *user input*, so `onboard-car.md`'s
      "pre-existing Notion content is not a source" ban doesn't apply — but nothing becomes the
      snapshot unconfirmed.

   **Never** build the rows from connector row-listing (`notion-search` / a database
   `notion-fetch`) — the same ban as everywhere (`notion-rest-read.md`).

3. **Write the toggle** per `notion-structure.md` → *Catalog snapshot*: replace the existing
   toggle's contents if the page has one, else append it at the very end of the page.

4. **Report.** Row count, `written_at`, and which source the rows came from (REST / template —
   with its `version:` / pasted). For the template path, add the hand-edit line from rung 2. For
   any non-REST source, one line that a later run with egress reads the live table again as
   normal — the snapshot only serves the runs that can't.

## Rules
- **This workflow writes exactly one thing: the snapshot toggle.** It never creates, updates, or
  deletes `Parameters` rows, `Setups` rows, linked views, or identity facts — so existing setups
  and hand-edits are untouchable by construction.
- Row count and `car` in the YAML header must match what was gathered — the snapshot's own
  validation rules (`notion-rest-read.md` → *The catalog snapshot fallback*) apply to what you
  write here.
- Stay within `ACR Setup Engineer` scope, as always.
