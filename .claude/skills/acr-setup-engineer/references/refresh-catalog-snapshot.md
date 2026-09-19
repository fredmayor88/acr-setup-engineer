# Workflow: refresh the catalog snapshot

Create or refresh the **`Catalog snapshot`** toggle on a car's **`Catalog`** page (`notion-structure.md` →
*Catalog snapshot*) **without touching anything else** — no `Parameters` rows, no `Setups` rows,
no identity facts, no views. Made for cars onboarded before the snapshot existed and for repairing
a snapshot that fails validation. It matters most for a **screenshot car**, whose snapshot is the
read path when the sandbox has no network egress (Claude's Free plan); a **template car** is read
from its bundled file either way, so its snapshot is a readable copy for the user.

Read `notion-structure.md` → *Catalog snapshot* (format + placement) before writing.

## Trigger phrases
"refresh the catalog snapshot", "add / create the catalog snapshot for {car}", "fix the
snapshot", "make {car} readable on Free" — and arriving from `notion-rest-read.md`'s *No snapshot
on the page* case.

**Not this workflow: a bare "refresh {car}".** *"Refresh the Lancia Stratos in my Notion"*,
*"update the {car}"*, *"re-onboard {car}"* name the **car**, not the snapshot — the user wants
everything static about it brought up to date (identity facts, the catalog source line, the
power/torque chart and the gearing-tool link, the catalog itself **and** the snapshot). That's `onboard-car.md`'s
refresh path; go there. This workflow is the **narrow** one, chosen only when the user names the
*snapshot* itself or when a read path sent you here. Writing only the snapshot for a request that
said "refresh the car" silently leaves the chart, the link and identity facts stale — the exact
failure this note exists to prevent.

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
