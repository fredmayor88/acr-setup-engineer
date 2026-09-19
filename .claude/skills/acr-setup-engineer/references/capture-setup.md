# Workflow: capture a setup from setup-screen photos

Store a setup the **user built themselves in-game** into Notion, read off photos of the car-setup
screens. This is the "I finished tinkering, here are the screens, save it as *XYZ*" flow.

The screens are the **authoritative record of what the setup is** — this workflow does not judge,
improve, sanity-check or re-derive the values. It transcribes them, normalizes them to the catalog's
vocabulary, and writes one row. It is deliberately the **cheapest and quietest** workflow in the
skill: no guideline layers, no tuning principles, no driving interview, no reasoning prose.

**Do not** run `build-setup.md`'s baseline machinery here. In particular the wrong-regime check
(`build-setup.md` step 5b) exists for setups **the game** produced; the user built this one on
purpose and it never gets second-guessed.

Read `notion-structure.md` (schemas + create-if-missing) before writing.

## Inputs
- **Car name** — as onboarded (e.g. `Lancia Stratos HF`).
- **Setup name** — what to save it as, **≤15 chars** (`SKILL.md` → *Setup names*). Compact a longer
  one automatically and say what you used.
- **Photos of the car-setup screens, attached in the chat** — the same screens as
  [onboard-car.md](onboard-car.md) → *Inputs*, but showing the **currently displayed value** rather
  than a min/max pass. One shot per screen/tab (Gearbox, Suspensions F/R, Dampers F/R, Axles,
  Differential(s), Wheels/Tyres F/R, Brakes, Electronics …).
- **Optional context** — stage / location, surface, conditions. Ask **once, in one line**, only if
  the user gave none, and accept "doesn't matter" — `Location`, `Stage` and `Conditions` are all
  legitimately blank (`notion-structure.md`). Surface: take the user's word, else infer from the
  stage, else from the tyre compound in the photos.

## Procedure

1. **Read once, in parallel.** Resolve the `ACR Setup Engineer` structure, then issue the remaining
   reads **together in a single step** (`SKILL.md` → *Read efficiently*): the `Setups` data source,
   the car's `Catalog` page, and the car's catalog, in **one** code-execution block.
   **Load the car's catalog:** a **template car** → `python scripts/load_catalog.py
   car-templates/<slug>.yaml --surface {Surface}` (no token, no network) — **leave `--surface`
   off when the surface isn't known yet** (the *Inputs* allow "doesn't matter"), which gives every
   row, baseline and surface-tagged, to resolve later; a **screenshot car** →
   its `Parameters` rows via [notion-rest-read.md](notion-rest-read.md) (fetch the `Parameters`
   data source too, for that). Decide which from the `Catalog` page's `Catalog source:` line
   (`notion-structure.md` → *Where a car's catalog lives*). Do **not** load
   `setup-tuning-principles.md`, the `Tuning guidelines` page, the car's guidelines, the
   `car-troubleshooting/` file, or the learn pool — none of them are used here.

   **Car not onboarded yet?** Same rule as a build: a matching file in `car-templates/`
   auto-onboards it first (no screenshots, no separate step); otherwise stop and ask the user to
   onboard it (`onboard-car.md`) — without a catalog there are no value columns to write into.

2. **Transcribe the screens.** For each parameter shown, record the displayed value against the
   catalog's canonical `Adjustment` name, section grouping and `Order` (reuse onboarding's names —
   never invent one). **Flag any label you can't confidently map** rather than dropping it.
   A captured value that falls outside a **template car's** range is trigger (b) of
   `onboard-car.md` → *When the template may be stale*: say the one line, then flag and write the
   value as read exactly as step 4 already requires.

3. **Normalize to the catalog** (this part is not optional — it's what makes the row usable by
   later builds, tweaks and reviews):
   - **`Discrete steps` filled** → store the matching step when the reading is **unambiguously**
     that step (exact after tidying decimals, or within float-noise tolerance). Ambiguous ⇒ leave
     the reading as-is and flag it.
   - **Continuous `Min..Max`** → keep the value exactly as read.
   - **`Tyre type`** → always a **fully-qualified** name (`Tarmac Snow`, `Snow (Studs)`, …); map a
     bare `Snow` / `Gravel` / `Dry Tarmac` to its canonical ACR name, or flag it rather than guess
     (`SKILL.md` → *Tyre fallback + canonical names*).
   - Resolve each parameter's row for the setup's **surface** first (`SKILL.md` → *Surface-resolved
     ranges*).

4. **Range-check — silently, as misread detection.** Compare each value against its resolved row.
   This is **not** validating the setup: the game screen is authoritative about the setup. It is
   validating **the reading of a photo**, which is the one genuinely unreliable step here — a
   dropped decimal point, an 8 read as a 3, a value taken off the wrong row.

   - **Everything in range (the normal case) → say nothing.** No per-parameter table, no
     "✓ within range" lines, no validation report. Silence is the pass condition.
   - **Out of range → never clamp, never drop.** Write the value as read and flag it in **one
     line**, naming the two possible causes: *"Rear ARB reads 9, catalog says 1–8 — either I
     misread the photo or the catalog is stale. Written as read."* If the user wants to fix a
     stale catalog, give them the exact request: a **screenshot car** is re-onboarded with
     *"onboard the {Car} from my screenshots"*; for a **template car** the same phrase —
     *"re-onboard the {Car} from my screenshots"* — switches it to a catalog they own
     (`onboard-car.md` → *Trigger phrases*). A bare "re-onboard" is a template refresh and would
     take the same template again.

   Values are **never rejected** and the user is **never blocked**. This check costs one comparison
   per value against data already in context; it earns its keep because a misread number is silent
   forever once it's a row — it just quietly poisons the next build that reads it.

5. **Fill every parameter the car has.** A setup row leaves no applicable parameter blank
   (`SKILL.md` → *Core rules*). If the photos don't cover every screen, list the missing parameters
   in one message and ask for the remaining shot(s) — don't invent values and don't leave holes.

6. **Write one `Setups` row — append only.** First, **if this car is a template car whose
   `Catalog` page carried no `Catalog source:` line** (step 1), its `Setups` columns were created
   by an older skill version and the current template may name columns the DB doesn't have: run
   the check in `notion-structure.md` → *Legacy template car — check the `Setups` columns before
   the first write* — add the missing columns in one call, never rename or remove anything, and
   say the one line it gives. You already hold both sides of the comparison, so this adds no
   read. Then write the row: `Name` (≤15 chars), `Car`, `Location` / `Stage` (if
   given), `Surface`, `Conditions` (only when known — **blank rather than guessed**), `Date`
   (the Python one-liner, never a guessed clock time), `Game version` (if known), `Skill version`,
   **`Source = screenshot`**, `Mode` (default `learn`), a value for every parameter the car has,
   **`Model` blank** (the values are the user's, not a model's), **`Learn from this` unchecked**
   (the user opts in after rating it).

   Page body — **short**. There is no reasoning to record, so don't manufacture any:
   - one line: *"Captured from setup-screen photos on {date}"*, plus the stage/surface/conditions
     context when given;
   - the **toe warning** whenever the car has toe parameters, verbatim as in `build-setup.md` step
     11 — it's read while re-entering values in-game;
   - nothing else. No justification toggle, no changes-from-baseline toggle, no value checklist (the
     row is the source of truth).

7. **Assert the column order — MANDATORY** (`SKILL.md` → *Assert column order*;
   `notion-structure.md` → *Applying the order*, which says which form to run). Run
   `scripts/query_notion_parameters.py … --show-order` and apply the `SHOW` to the car's linked
   view (case 1, `--show-order --from-template car-templates/<slug>.yaml`, for a template car;
   case 2, `<params_ds> <token> "{Car}" --show-order`, for a screenshot car), and to the main
   `Setups` view and any stage/location view (case 3: one call, a `--from-template` per onboarded
   template car plus `<params_ds> <token> --all` only if a screenshot car exists). The capture is **not done** until this
   is applied, on quick runs too.

8. **Report — one line, plus exceptions.** *"Saved **{name}** for the {Car} ({n} parameters,
   {stage/surface/conditions})."* Then, only if there were any: the flagged readings, unmapped
   labels, or ambiguous tyre names. Add the toe-sign warning line whenever toe values were captured.
   Nothing else — no summary of the setup, no opinion on it, no suggested improvements unless the
   user asks.

## What this workflow deliberately does not do
- Judge whether the setup is any good (that's `review-setup.md`, on request).
- Run the wrong-regime / broken-default check (`build-setup.md` step 5b) — that's for the game's
  defaults, not the user's own work.
- Load guideline layers or the tuning principles.
- Change any value for any reason.
