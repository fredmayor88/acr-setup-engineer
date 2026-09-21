# Workflow: change a car's parameter list (in chat)

Change a car's legal values — a range, its steps, a unit, add or remove a parameter, a
gravel-only range — by saying it in chat. The skill validates the change and rewrites the car's
**`Parameters` page** (`notion-structure.md` → *`Parameters` page*). This is the **only** way a
catalog changes; nobody edits YAML or rows by hand.

Read `catalog-read.md` and `notion-structure.md` → *`Parameters` page* before starting.

## Trigger phrases
"the {car}'s {parameter} goes from A to B", "{parameter} on the {car} now goes to X", "the last
step is Y", "set the steps for {parameter} to …", "add {parameter} to the {car}", "{parameter}
isn't adjustable on the {car}, remove it", "on gravel the {parameter} goes A to B" — any request
that changes what values a car's parameter may take. (A request to change a **setup's** value is
`tweak-setup.md`, not this.)

## Procedure

1. **Load the catalog** — `catalog-read.md` → *Load a car's catalog*. Keep the loader's JSON
   output; it is the list you'll edit. Note the car's kind from its `Catalog source:` line.
   **If the loader stops, this workflow stops**: say the exact line `catalog-read.md` gives for
   that case (unreadable page at its step 3, `no parameters found` at its step 5) and write
   nothing.

2. **Name the parameter exactly.** Match what the user said against the `Adjustment` names in
   the list. If it matches **more than one** (e.g. "ARB" → `Anti-roll Bar Front`, `Anti-roll Bar
   Rear`), ask: *"Front, rear, or both?"* If it matches **none** and the user isn't adding a new
   one, ask which of the closest two or three they mean. Never guess.

3. **Apply the change in memory** to the matching row(s) — the baseline row, or the row for the
   surface the user named (create that surface row from the baseline if it doesn't exist, when
   the user says "on gravel"):
   - a new min or max → set `Min` / `Max`;
   - "the last step is Y" → replace the last entry of `Discrete steps`; "steps are …" → replace
     the whole list; "add step Y" → insert it in numeric order;
   - a unit → `Unit`;
   - **add a parameter** → a new row with `Section`, `Adjustment`, `Min`, `Max`, `Unit`,
     `Discrete steps`, and an `Order` inside its section block (`notion-structure.md` →
     *Canonical ACR default order*: the section's thousands, then the next free tens slot);
   - **remove a parameter** → drop its rows (baseline and surface).

4. **Validate** — every check is a one-liner; do all that apply:
   - numeric `Min` ≤ `Max`;
   - every step is inside `Min..Max` when both are numbers, and the steps are in ascending order;
   - `Discrete steps` values keep their exact spelling (`*` in gear values, `—` for none);
   - no two rows share `Adjustment` + `Surface`.
   A failed check → say which and ask for the corrected value. Don't write.

5. **Show before → after** for each changed row (`Adjustment`, surface if any, `Min`, `Max`,
   `Unit`, `Discrete steps`) and ask: *"Write this to the {Car}'s parameter list?"* Only on yes.

6. **Write the page.**
   - Build `rows.json`: `{"header": …, "rows": <the edited list>}`. The header is the loaded
     file's header keys (`car`, `drivetrain`, the identity facts, `version`, `source`) — read them
     off the top of that file, above `parameters:`; the loader prints rows only — plus:
     - **Template car (first edit — this forks it):** `source: "screenshots"`,
       `forked_from: "bundled template v{tv}"` where `{tv}` is the bundled file's `version:`.
     - **Screenshot car:** header unchanged.
   - Run `python scripts/load_catalog.py --to-template rows.json`. Write its output to
     `parameters/<slug>.yaml` as well (`catalog-read.md` → *Slug*, *Save the file*): that is the
     car's file for step 7 and for anything else this run reads.
   - **Template car:** create the `Parameters` page under `{Car}` with the **forked** maintenance
     line (`notion-structure.md` → *Car page* table; today's date from the `Date` one-liner) and
     the output as its `yaml` block. Then rewrite the `Catalog` page (it is disposable — one
     replacement, `onboard-car.md` refresh step 3) with the source line
     `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
   - **Template car whose `Parameters` page already exists** — it carries the *Not in use* line,
     because the car had its own list and a refresh switched it to a bundled template
     (`notion-structure.md` → *`Parameters` page*, item 2). Fork the bundled file exactly as
     above, but **don't create the page**: replace its `yaml` block with the output, replace its
     first line with the **forked** maintenance line, and **delete the *Not in use* line** — the
     page's list is in use again.
   - **Screenshot car:** replace the page's `yaml` block with the output. Leave the maintenance
     line as it is.

7. **A new `Adjustment`** → add its `Setups` value column (`onboard-car.md` step 7's
   *value-columns check*: Number for numeric, Select for `—`), then re-assert `SHOW` on the
   car's view and the shared views with this car's new file
   (`notion-structure.md` → *Applying the order*). A removed parameter keeps its column (columns
   are never removed). No new column → nothing to reorder.

8. **Report, one line.** Screenshot car: *"Updated the {Car}'s parameter list: {what changed}."*
   Forked template car: *"Done. The {Car} now uses its own parameter list (copied from the
   bundled template, with this change). When a newer bundled template ships, a refresh will
   offer to switch back."*

## Rules
- **Validate, show, confirm, then write.** Never write an unconfirmed change.
- **The page's block is replaced whole**, from the script's output — never patched by hand.
- **Forking a bundled car asks no question**; the one-line report says what happened.
- **Never touch `Setups` rows** — a range change doesn't rewrite existing setups.
- Stay within `ACR Setup Engineer` scope.
