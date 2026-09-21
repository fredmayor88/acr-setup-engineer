# Workflow: refresh the catalog snapshot

Create or refresh the **`Catalog snapshot`** toggle on a car's **`Catalog`** page (`notion-structure.md` →
*Catalog snapshot*) **without touching anything else** — no `Parameters` rows, no `Setups` rows,
no identity facts, no views. Made for cars onboarded before the snapshot existed and for repairing
a snapshot that fails validation. It matters most for a **screenshot car**, whose snapshot is the
read path when the sandbox has no network egress (Claude's Free plan); a **template car** is read
from its bundled file either way, so its snapshot is a readable copy for the user.

Read `notion-structure.md` → *Catalog snapshot* (format + placement) before writing.

## When this runs — never as a user command
There is **no user-facing snapshot command.** Every request about a car's snapshot — *"refresh
the catalog snapshot for {car}"*, *"make {car} readable on Free"*, *"fix the snapshot"* — is a
**car refresh** (`onboard-car.md` → *Refreshing an already-onboarded car*), which also brings the
chart, the gearing link and the identity facts up to date and may switch a screenshot car to a
newer bundled template. Writing only the snapshot for such a request would leave all that stale.

This procedure is called from exactly two places:
- **`onboard-car.md` refresh, step 4** — a screenshot car that keeps its screenshots.
- **`notion-rest-read.md` → *No snapshot on the page*** — a read that found no valid snapshot.

## Inputs
- **Car name** — must already be onboarded (it has a `{Car}` page with a `Catalog` child). If it
  isn't,
  say so and point to `onboard-car.md` — onboarding writes the snapshot itself, and its step 9
  can take `Discrete steps` in chat so a fresh screenshot onboard needs no refresh at all.

## Procedure

1. **Resolve the structure by name** (`notion-structure.md`) and fetch the car's **`Catalog`**
   page (under the `{Car}` umbrella page). If the car is still on the old one-page layout, this
   workflow is the wrong one — a structural migration is a refresh (`onboard-car.md`).

2. **Get the car's rows — start from the car's kind** (its `Catalog source:` line;
   `notion-structure.md` → *Where a car's catalog lives*):

   **Template car → the template, full stop.** Build the rows from
   `python scripts/load_catalog.py car-templates/<slug>.yaml --snapshot` and write them. No REST
   read, no token, no paste, no questions: the template **is** this car's catalog, so nothing
   else could be more correct. Note its `version:` in the report (step 4). (A car with **no**
   `Catalog source:` line but a matching template is a template car — rule 3 of *Where a car's
   catalog lives*.)

   **Screenshot car → first source that works, in this order:**

   1. **The REST read** (`notion-rest-read.md`) — the normal path whenever the sandbox has
      egress. Complete and exact; use it if it runs.
   2. **The paste path — works everywhere, including Free.** Ask the user to open the
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

4. **Report.** Row count, `written_at`, and which source the rows came from (template — with its
   `version:` — or REST, or pasted). For a **template car**, one line that this snapshot is a
   readable copy of the bundled template and that the skill reads that file directly anyway, on
   every plan. For a **screenshot car** read from a paste, one line that a later run with egress
   reads the live table again as normal — the snapshot only serves the runs that can't.

## Rules
- **This workflow writes exactly one thing: the snapshot toggle.** It never creates, updates, or
  deletes `Parameters` rows, `Setups` rows, linked views, or identity facts — so existing setups
  and hand-edits are untouchable by construction.
- Row count and `car` in the YAML header must match what was gathered — the snapshot's own
  validation rules (`notion-rest-read.md` → *The catalog snapshot fallback*) apply to what you
  write here.
- Stay within `ACR Setup Engineer` scope, as always.
