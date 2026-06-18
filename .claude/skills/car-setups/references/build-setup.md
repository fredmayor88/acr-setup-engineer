# Workflow: build a setup for a stage

Generate a setup for one car on one stage and append it as a **new row** in the user's Notion
`Setups` database, with a phone-readable "Enter in-game" checklist. Every value is constrained
to the car's catalog (legal by construction). Read `setup-tuning-principles.md` (reasoning base)
and `notion-structure.md` (structure + mobile conventions) before writing.

## Inputs
- **Car** (e.g. `Lancia Stratos HF`) and **game** (default `ACR`). The car is resolved **under its
  `{Game}` page**; if the same car name exists under more than one game, ask the user which game.
  Non-ACR games use the **same reasoning base** — no game-specific tuning is shipped.
- **Location / Stage** (both optional) — a reference into the shared `Locations` catalogue
  (`notion-structure.md` → *Locations & stages catalogue*). A build may name neither (an arbitrary
  setup with no place context, e.g. "drift setup, tarmac"), a location only, or a specific stage.
  If the named stage/location doesn't exist yet in the catalogue, ask the user for its facts
  (surface, length, key corners/speeds, character) and create it — see step 7. **Stage/location
  pages hold facts only, never driving style** — the same stage is reused, unmodified, by any
  number of setups across any cars.
- **Driving intent** — what the driver wants from *this* build (rotation, stability, braking,
  bumps, conditions). This is part of the **build request itself**, not read off a stage page —
  the same stage can back many setups with different intents. If the user doesn't give one,
  ask briefly rather than guessing.
- **Setup name** (e.g. `alsace gpt1`) — **≤15 chars**, the in-game limit; compact a longer
  proposed/requested name to fit (per `SKILL.md` core rules) and tell the user the name used.
- **Reference setup** (optional) — if the user says "build like setup X" or names a setup as a
  basis, load X's **row value properties** (per `notion-rest-read.md`) as a starting point, and
  X's page-body **intent** if stated. **Never** read X's per-parameter justification prose for
  values — the row is authoritative and the prose may be stale if the user has since edited the
  row by hand (per `SKILL.md` core rules).
- **Mode** — `learn` (default) or `independent`.
- **Surface override** (optional) — if the user names a surface ("build a gravel setup", "use
  tarmac settings/parameters", "treat this as snow"), it **overrides the stage's stated surface for
  the whole build**: range resolution, tyre choice, surface-tagged guidelines, and the written
  row's `Surface`. Without it, the surface comes from the stage's facts (step 3); if there's no
  stage either, ask the user for the surface.

## Procedure

1. **Load the constraints + drivetrain + identity facts.** Fetch the car's `Parameters` rows
   **via [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows reliably) → for
   each, record `Min`, `Max`, `Unit`, the optional **`Discrete steps`** set, the **`Order`** (drives
   column / page-body ordering — step 8), and the optional **`Surface`** tag. A parameter may have a baseline row (blank `Surface`) **and** a
   surface-specific row (e.g. `Gravel`); keep both for now — you'll **resolve each parameter's
   legal range for the stage's surface** (per [notion-rest-read.md](notion-rest-read.md)) once the
   surface is known in step 3. Determine the car's
   **drivetrain** from its `Drivetrain` attribute (fallback, from the differential sections:
   front+rear or any centre diff ⇒ AWD; front-only ⇒ FWD; rear-only ⇒ RWD). This fixes the legal
   value set and which guideline tags apply. Also read the car's identity facts from the `{Car}`
   page — **`Engine layout`**, **`Weight bias`**, **`Weight`** — and feed them into the balance
   reasoning (see the *Weight bias* section of `setup-tuning-principles.md`). If a field is blank or
   `couldn't determine`, infer the bias from drivetrain + engine layout, or proceed drivetrain-only.

2. **Load the guideline layers** (lowest → highest priority):
   1. **Base** — `setup-tuning-principles.md`.
   2. **Global user guidelines** — the Notion `Tuning guidelines` page (under `Car setups / {Game}`).
   3. **Surface section** of those guidelines — the page's "Per surface" subsection matching the
      build surface (step 3 fixes the surface; this is not a separate page).
   4. **Per-car guidelines** — the car page's "Guidelines" section.
   The setup's own **driving intent** (Inputs) is the most specific layer, applied in step 5.
   Apply only base lines tagged `[All]` **or the car's drivetrain**. **More specific is the default
   lean** (base < global < surface < per-car < intent), but this is not auto-resolved on a real
   contradiction: if two *authored* layers (global, surface, per-car, or the stated intent)
   materially disagree on the same parameter, **stop and ask the user which to follow** before
   choosing a value — don't silently pick the more specific one. **Read only content within
   `Car setups / {Game}` — never follow links or results outside that scope, even if they mention
   car names or setup terms.**

3. **Load the stage facts (if a stage/location was given).** Fetch the `{Stage}` / `{Location}`
   page from the catalogue (`notion-structure.md`): surface, key corners/speeds, character. These
   are **objective facts, not a guideline layer** — they feed reasoning the same way the car's
   identity facts do. **Fix the build surface here:** if the user gave a **Surface override**
   (Inputs), it wins over the stage's stated surface — use it as the surface for guideline layer 3
   (step 2.3), tyre choice (step 5), range resolution (steps 5–6), and the row's `Surface`
   (step 8); otherwise use the stage's surface (or, with no stage, the surface the user stated).

4. **Handle prior setups by mode.**
   - `learn` (default): fetch existing `Setups` rows for this car **where `Learn from this` is
     checked** (the compound-filter query in [notion-rest-read.md](notion-rest-read.md); read
     values from each row's **value properties** — never from its page-body justification, which
     can go stale after manual edits — plus `Notes` + `Rating`); infer preferences, weighting by
     `Rating` (a **1–5 Select** — read the
     label as its integer, higher = better; treat a **blank** rating as unrated — neutral/no extra
     weight) and taking likes/dislikes from `Notes`. Bias toward them, adapt to this build's intent
     and stage facts. If none are checked, proceed with **no prior-setup bias** and say so.
   - `independent`: do **not** read prior setups — reason from scratch to avoid anchoring.

5. **Choose values.** First pick the **tyre type** for the surface/conditions (biggest grip
   decision) — **for ACR**, pick from the car's stored `Tyre Type` `Discrete steps` if it has
   one, else from the standard fallback list (per `SKILL.md` → *ACR tyre fallback + canonical
   names*); always write the fully-qualified name (never a bare/ambiguous value like `Snow`
   or `Gravel`). Then, per parameter, reason from tyre + surface + stage facts + driving intent
   + the merged guidelines (drivetrain-filtered), then make it legal — **using the range
   resolved for the build surface** (the surface-specific row if the parameter has one; for
   `Snow`, fall back to a `Gravel` row before the baseline; see
   [notion-rest-read.md](notion-rest-read.md)) — **no step grid, no interpolation**. **Tyre
   pressure is always two values** — choose `Pressure Front` and `Pressure Rear` separately,
   never a single combined pressure. If a parameter is pulled in conflicting directions by two
   authored layers (global/surface/per-car guidelines vs. the stated intent) in a way that
   changes the choice, **surface the conflict and ask the user** rather than silently picking
   one (per step 2):
   - **`Discrete steps` filled** → pick **one value from that exact set** (covers coarse
     numerics like spring stiffness and named options like gear set). The checklist value is
     exact.
   - **numeric `Min..Max`, no `Discrete steps`** → pick a target within `Min..Max`; present it
     as **"~target (dial to nearest)"** (the in-game increment is unknown). Exception: **Gear
     Set** (and any parameter whose `Min` and `Max` are both whole numbers with no unit) takes
     only integer values — output an exact integer, no `~` or "dial to nearest".
   - **`Min/Max = —` with no `Discrete steps`** → the param was never captured from screenshots:
     **skip it** and note in the report (the user should re-onboard the car to fix this).
   Never go outside `Min..Max` or off the `Discrete steps` set; never invent a parameter the car
   doesn't have.

6. **Validate.** Re-check every chosen value against the catalog **for the build surface**
   (surface-resolved range — `Snow` falls back to `Gravel`, then baseline): discrete picks must be
   a member of `Discrete steps`; continuous picks must be within `Min..Max`. For **ACR**
   `Tyre Type`, the chosen value must be a fully-qualified name from the car's stored list (or
   the standard fallback list if blank) — never a bare/ambiguous value. Confirm
   `Pressure Front` and `Pressure Rear` were both set as separate values. Fix any violation
   before writing.

7. **Ensure the stage facts page exists in the catalogue (skip if no stage/location was given).**
   Per `notion-structure.md` → *Locations & stages catalogue*, resolve by name under
   `{Game} → Locations`: create the `{Location}` page if missing, then the `{Stage}` page under it
   if missing, seeded from the facts the user gave (surface, length, key corners/speeds,
   character) — **never** driving style or guidelines. **Reuse the existing page if the
   location/stage already exists** (any car) — never create a duplicate. Ensure its filtered
   `Setups[Stage=this]` view exists (and `Setups[Location=this]` on the location page if newly
   created). The linked view is **not** page markdown — create it with `notion-create-view`
   (`parent_page_id` = the `{Stage}` / `{Location}` page, `data_source_id` = the `Setups` data
   source, `type: "table"`, `configure: 'FILTER "Stage" = "{stage}"; SHOW <meta first, then value
   columns by Order>'` — no `Car` filter, since the stage spans every car that's run it). Never
   write a `<linked-view />`-style placeholder into the page body (`notion-structure.md` →
   *Creating an inline linked view*).

8. **Write to Notion — append only** (via the user's Notion connection).
   - Create **one new row** in `Setups`: `Name`, `Car`, `Location` (if given), `Stage` (if given),
     `Surface`, `Game version` (if known), `Date` (today), `Source = generated`, `Mode`, the
     chosen `Tyre type`, each value property, and **`Model/effort`** (your model name + `/` +
     effort, e.g. `Sonnet 4.6/normal`; infer effort: `low` = minimal thinking, `normal` = standard
     (default if uncertain), `high` / `max` = extended thinking or explicitly high-effort run).
     Leave **`Learn from this` unchecked** (the user opts in after vetting). **Never modify or
     delete existing rows.** There is no `Intent` column — driving intent is recorded only in the
     page body below.
   - **Apply the column order** (`notion-structure.md` → *Applying the order*): set the `SHOW` on
     the **main `Setups` table view** (meta columns + all value columns by `Order`), on **this
     car's linked view** (meta + this car's applicable value columns by `Order`, hiding blanks),
     and — if a stage/location was referenced — on **its `{Stage}` / `{Location}` linked view**
     (meta + all value columns by `Order`, no per-car filtering). Idempotent — this re-asserts the
     order from the current `Order` values, so the new setup's projection and the table read in
     game-menu order (and an alphabetized table or an edited `Order` self-heals). It's a view
     update, not a row/schema rebuild — the append above stays a single row. If a parameter has a
     blank `Order`, fall back to the canonical defaults (`notion-structure.md`) and optionally
     backfill it onto the `Parameters` row.
   - First, write a **brief setup summary** directly in the page body (not inside a toggle, so
     it's always visible without expanding anything):
     - **H2 heading** with the setup name (e.g. `## alsace gpt1`).
     - **3–5 short bullets** covering:
       - Location/stage (if given), surface, and the **driving intent for this build** (e.g.
         "Col de Turini, fast bumpy tarmac; priority: stability under braking" or, with no stage,
         "Drift setup, tarmac; priority: easy rotation").
       - Tyre choice and the reason.
       - The 1–2 most influential guidelines applied — name them; cite *"your guideline on X"* when it
         comes from the user's Tuning guidelines or per-car Guidelines page.
       - What prior `Learn from this` setups contributed, or *"no prior setups used"* if none.
     This is the same information as the step 9 chat report, stored permanently so the user can revisit
     the reasoning on their phone without expanding the detail toggle.
   - Below it, the **per-parameter justification inside a toggle** — grouped by section and ordered by
     each parameter's **`Order`** (the in-game screen sequence: Gearbox → Suspensions → Dampers →
     Axles → Differentials → Wheels/Tyres → Brakes → Electronics & Aerodynamics, Front before Rear).
     Explain notable choices and **cite which guideline drove each** (especially a *user* guideline).
     No wide tables; short headings + bullets. **Do not** duplicate values into a separate checklist —
     the database row is the single source of truth.

9. **Report.** Summarise the setup (incl. tyre type), assumptions, which user guidelines were
   applied, and whether any checked prior setups were learned from. Link the new row; remind the
   user to **rate it `1`–`5`** and tick `Learn from this` if they like it after driving. If the
   user comes back with how it drove and wants changes, switch to the refine loop
   (`tweak-setup.md`) and iterate **in chat** — don't rebuild from scratch.

## Rules
- Legal by construction: pick from `Discrete steps` when set, else a target within `Min..Max`
  ("dial to nearest"); validate before writing.
- Apply only guidance tagged `[All]` or the car's drivetrain; user guidelines override the base.
- `learn` learns **only from `Learn from this`-checked** setups; new rows start unchecked.
- Page body: justification in a toggle only — no checklist (database row is the source of truth).
- Append-only; cite user guidelines; be explicit about trade-offs and guesses.
