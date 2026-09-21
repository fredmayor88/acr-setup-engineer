# Workflow: refresh the whole Notion structure (after a skill update)

**One command after an update:** bring everything the skill owns in the user's Notion in line with
the installed skill version — the skill's own root pages and **every onboarded car** — without
touching anything the user owns.

Read `notion-structure.md` (structure, ownership, the `How to use` / `Claude Free plan` pages) and
`onboard-car.md` → *Refreshing an already-onboarded car* before starting.

## Trigger phrases
"refresh my ACR Notion", "update my ACR Notion", "refresh everything", "refresh all my cars",
"I updated the skill". A request that names **one car** ("refresh the Lancia Stratos in my Notion")
is the per-car refresh in `onboard-car.md`, not this.

## What it never touches
The content of `Config`, `Tuning guidelines`, any car's `Guidelines`, the user's notes and the
skill's entries on any car's `Log`, and every `Setups` row. Same rules as the per-car refresh —
this workflow only runs it for every car.

## Procedure

1. **Resolve the structure by name** (`notion-structure.md` → *Resolution rule*) and create
   whatever is missing. The root fetch lists the `{Car}` pages — that list is the set of onboarded
   cars; no search, no extra reads. Run `scripts/check_egress.py` once if this chat hasn't yet
   (`notion-rest-read.md` → *Offline mode*); the legacy-rows migration in step 3 needs its answer.

2. **Rewrite the skill's root pages**, each as a whole-page replacement with the current version
   in its banner (`notion-structure.md` → *`How to use` and `Claude Free plan` pages*, and
   *`Parameter reference` page*):
   - `How to use` from `how-to-use-template.md`;
   - `Claude Free plan` from `free-plan-template.md`;
   - `Parameter reference` from `parameter-reference-template.md`.

3. **Refresh every car, one after another**, by running `onboard-car.md` → *Refreshing an
   already-onboarded car* for each `{Car}` page, exactly as a per-car refresh would — including
   the layout migration, the `Feedback` → `Log` rename, the catalog-rows migration that gives a
   screenshot car its `Parameters` page (**before** the `Catalog` rebuild, as that section has
   it), the `Catalog` rebuild and the screenshot-car rules (a switch to a template at least as new, the one question when the captured game version
   is `unknown`). Two differences, so one command doesn't turn into a long conversation:
   - **Don't wait on a car that can't be migrated.** Where the catalog-rows migration finds
     nothing to recover (`onboard-car.md` → *Migration — catalog rows to the `Parameters` page*,
     source 3), create the empty page as it says, note the car, and move on. List those cars in
     the report with *"onboard the {Car} from my screenshots"*.
   - **Ask the `unknown`-version question for all such cars at once**, before refreshing any of
     them: one message listing the cars, recommending yes for each (*"If you're not sure, say yes
     — the template is kept up to date with the game"*). Then refresh every car with the answers.
   - **Order the columns once at the end, not per car** for the shared views: each car's own
     `Setups` view gets its `SHOW` as part of its refresh; the main `Setups` table and the
     `{Location}` / `{Stage}` views get **one** call after the last car, carrying one
     `--from-template` per onboarded car (`notion-structure.md` → *Applying the order*).

4. **If the run gets long** — many cars, or a plan's usage limit — stop between two cars, never
   in the middle of one. Report which cars are done and say *"refresh my ACR Notion"* again to
   continue: every step is a full replacement or a create-if-missing, so running it twice changes
   nothing that's already up to date.

5. **Report.** One line for the root pages (with the version), then **one line per car** — what
   changed (brought up to date / switched to the bundled template / kept your screenshots /
   `Feedback` renamed to `Log` / migrated from the old layout). Then, only if any:
   - cars whose parameter list couldn't be recovered, with *"onboard the {Car} from my
     screenshots"* for each;
   - the legacy-rows line (`onboard-car.md` refresh step 5) once, naming the cars it applies to;
   - cars skipped because of an error, with what went wrong.
   Confirm in one line that the column order was asserted on the shared views.

## Rules
- **Same ownership rules as every refresh** — user pages and `Setups` rows are never written.
- **Per-car logic lives in `onboard-car.md` only.** This workflow loops it; it never re-states or
  changes how one car is refreshed.
- **Whole cars only** — a car is either fully refreshed or not started.
- Stay within `ACR Setup Engineer` scope, as always.
