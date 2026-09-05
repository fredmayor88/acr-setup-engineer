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

## Inputs
- **Car name** — must already be onboarded (its `Parameters` rows exist in Notion). If it isn't,
  say so and point to `onboard-car.md` — onboarding writes the snapshot itself.

## Procedure

1. **Resolve the structure by name** (`notion-structure.md`) and fetch the `{Car}` page.

2. **Get the car's rows — first source that works, in this order:**

   1. **The REST read** (`notion-rest-read.md`) — the normal path whenever the sandbox has
      egress. Complete and exact; use it if it runs.
   2. **The bundled template — only if the catalog is an untouched template onboard.** When the
      car was onboarded from a `car-templates/` file, ask one question: *"Have you hand-edited
      any `Parameters` cell for this car since onboarding (filling `Discrete steps`, fixing a
      range)?"* **Untouched** → build the rows from the template file (same field mapping as
      `onboard-car.md` step 1). **Edited, unsure, or the skill has been upgraded since the
      onboard** (the bundled template may be newer than what was written back then) → fall
      through to the paste path: the snapshot must mirror **the rows in Notion**, not the
      current template.
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

4. **Report.** Row count, `written_at`, and which source the rows came from (REST / template /
   pasted). If the rows came from the paste path or the template, add one line that a later run
   with egress will read the live table again as normal — the snapshot only serves the runs that
   can't.

## Rules
- **This workflow writes exactly one thing: the snapshot toggle.** It never creates, updates, or
  deletes `Parameters` rows, `Setups` rows, linked views, or identity facts — so existing setups
  and hand-edits are untouchable by construction.
- Row count and `car` in the YAML header must match what was gathered — the snapshot's own
  validation rules (`notion-rest-read.md` → *The catalog snapshot fallback*) apply to what you
  write here.
- Stay within `ACR Setup Engineer` scope, as always.
