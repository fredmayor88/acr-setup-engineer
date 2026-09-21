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
     *Canonical ACR default order*: the section's thousands, then the next free tens slot).
     **The legal values come from the user — never invent a range.** If `Min`, `Max`, `Unit` or
     the steps (or "no steps") are missing from what they said, ask for all of them in **one**
     question before going on: *"What are the lowest and highest values of {parameter} on the
     setup screen, its unit, and the exact steps if it only moves in steps?"* `Section` is the
     setup screen the parameter sits on — use the section names in `notion-structure.md` →
     *Canonical ACR default order*, and ask which one if it isn't obvious;
   - **remove a parameter** → drop its rows (baseline and surface).

4. **Validate** — every check is a one-liner; do all that apply:
   - numeric `Min` ≤ `Max`;
   - every step is inside `Min..Max` when both are numbers, and the steps are in ascending order;
   - `Discrete steps` values keep their exact spelling (`*` in gear values, `—` for none);
   - no two rows share `Adjustment` + `Surface`.
   A failed check → say which and ask for the corrected value. Don't write.

5. **Show before → after** for each changed row (`Adjustment`, surface if any, `Min`, `Max`,
   `Unit`, `Discrete steps`) and ask: *"Write this to the {Car}'s parameter list?"* Only on yes.

6. **Write the page.** These sub-steps in order; don't skip 6.5.

   1. **Build `rows.json`**: `{"header": …, "rows": <the edited list>}`. For the header, **copy
      every key `--to-template` accepts, unchanged**, from the top of the loaded file: `car`,
      `game`, `save_ids`, `drivetrain`, the identity facts (`engine_layout`, `weight_bias`,
      `weight`, `max_power`, `max_torque`, `class`, `gearbox`, `steering_lock`), `version`,
      `source`, and `forked_from` when the file already has one (a car forked by an earlier edit
      keeps it) — then apply the overrides below. Read those keys off the top of the file itself;
      the loader prints rows only. `gearing_tool`, `power_torque_chart` and `engine_curve` are
      **not** copied — they stay in the bundled file, and every workflow reads them from there
      (`notion-structure.md` → *Engine chart and gearing tool*).
      - **Template car (first edit — this forks it):** `source: "screenshots"`,
        `forked_from: "bundled template v{tv}"` where `{tv}` is the bundled file's `version:`.
      - **Screenshot car:** header unchanged, no overrides.

   2. **Run `python scripts/load_catalog.py --to-template rows.json`.** Write its output to
      `parameters/<slug>.yaml` as well (`catalog-read.md` → *Slug*, *Save the file*): that is the
      car's file for step 7 and for anything else this run reads.

   3. **Screenshot car** → replace the `yaml` block on the car's existing `Parameters` page with
      the output. Leave the maintenance line as it is. **Skip 6.4 and 6.5** — its `Catalog` page
      already says `your screenshots` — and go to step 7.

   4. **Template car — first find out whether the car already has a `Parameters` page.** Resolve
      `Parameters` under `{Car}` by name (`notion-structure.md` → *Resolution rule*): fetch the
      `{Car}` page and look at its child pages. It exists or it doesn't — that picks the case,
      and the two cases are the only ones:
      - **No `Parameters` page** → **create it** under `{Car}`, with the **forked** maintenance
        line (`notion-structure.md` → *Car page* table; today's date from the `Date` one-liner)
        and the script's output as its `yaml` block. Ask nothing — step 5's confirmation is the
        only question this case gets.
      - **A `Parameters` page exists** — it carries the *Not in use* line, because the car had
        its own captured list and a refresh switched it to a bundled template
        (`notion-structure.md` → *`Parameters` page*, item 2). **Fetch that page** — you need
        its blocks to replace them, its *Not in use* line for the date, and the `version:` in its
        `yaml` header for the game version. **That parked list is the user's own captured data
        and this replaces it, so ask first**: say in one line what is parked there (*"The {Car}'s
        `Parameters` page still holds your own captured list from game version {version}, not in
        use since {date}. Writing this change replaces it."* — drop either fact from the sentence
        if the page doesn't give it) and ask *"Replace it?"* **Only on yes.** On no, stop — nothing is written
        anywhere. On yes, **don't create a second page**: on that page, replace its `yaml` block
        with the output, replace its first line with the **forked** maintenance line, and
        **delete the *Not in use* line** — the list is in use again.

   5. **Any template car — page created or reused — then rewrite the `Catalog` page.** One
      replacement of the page body (it is disposable — `onboard-car.md` refresh step 3), with the
      source line
      `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
      **Without this the car still reads as a template car and the list you just wrote is never
      read again**, so it runs in **every** fork case, not just the one that created the page.
      **The power/torque chart and the gearing-tool link are written exactly as a refresh writes
      them — from the bundled file that matches this car, which is where they still live**
      (`notion-structure.md` → *Engine chart and gearing tool*). Forking does not lose them.

7. **A new `Adjustment`** → add its `Setups` value column (`onboard-car.md` step 7's
   *value-columns check*: Number for numeric, Select for `—`), then re-assert `SHOW`: on the
   car's own view with this car's new file, and on the shared views (the main `Setups` table and
   every `{Location}` / `{Stage}` view) with one `--from-template` per onboarded car
   (`notion-structure.md` → *Applying the order*). A removed parameter keeps its column (columns
   are never removed). No new column → nothing to reorder.

8. **Report, one line.** Screenshot car: *"Updated the {Car}'s parameter list: {what changed}."*
   Forked template car: *"Done. The {Car} now uses its own parameter list (copied from the
   bundled template, with this change). When a newer bundled template ships, a refresh will
   offer to switch back."* Forked onto a page that held a parked list (6.4's second case), add:
   *"It replaces the earlier list that was parked on the `Parameters` page."*

## Rules
- **Validate, show, confirm, then write.** Never write an unconfirmed change.
- **The page's block is replaced whole**, from the script's output — never patched by hand.
- **Forking a bundled car asks no question** — unless it would overwrite a parked list on an
  existing `Parameters` page (6.4), which is the user's own captured data and is asked about
  first. Otherwise the one-line report says what happened.
- **Never touch `Setups` rows** — a range change doesn't rewrite existing setups.
- Stay within `ACR Setup Engineer` scope.
