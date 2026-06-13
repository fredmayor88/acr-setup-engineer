# Workflow: build a setup for a stage

Generate a setup for one car on one stage and append it as a **new row** in the user's Notion
`Setups` database, with a phone-readable "Enter in-game" checklist. Every value is constrained
to the car's catalog (legal by construction). Read `setup-tuning-principles.md` (reasoning base)
and `notion-structure.md` (structure + mobile conventions) before writing.

## Inputs
- **Car** (e.g. `Lancia Stratos HF`) and **game** (default `ACR`). The car is resolved **under its
  `{Game}` page**; if the same car name exists under more than one game, ask the user which game.
  Non-ACR games use the **same reasoning base** — no game-specific tuning is shipped.
- **Stage** — the stage page (its description + the driver's style). If it doesn't exist yet,
  ask the user for the stage description, or create it.
- **Setup name** (e.g. `alsace gpt1`).
- **Mode** — `learn` (default) or `independent`.
- **Surface override** (optional) — if the user names a surface ("build a gravel setup", "use
  tarmac settings/parameters", "treat this as snow"), it **overrides the stage page's surface for
  the whole build**: range resolution, tyre choice, surface-tagged guidelines, and the written
  row's `Surface`. Without it, the surface comes from the stage page (step 3).

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
   3. **Surface section** of those guidelines matching the stage's surface.
   4. **Per-car guidelines** — the car page's "Guidelines" section.
   Apply only base lines tagged `[All]` **or the car's drivetrain**. On conflict, the more
   specific / user-authored layer wins (base < global < surface < per-car < stage, next step).
   **Read only content within `Car setups / {Game}` — never follow links or results outside that
   scope, even if they mention car names or setup terms.**

3. **Load the stage context (most specific).** Fetch the stage page: surface, key
   corners/speeds, what the driver wants (rotation, stability, braking, bumps). It overrides the
   general guidelines where it speaks to the same thing. **Fix the build surface here:** if the
   user gave a **Surface override** (Inputs), it wins over the stage's stated surface — use it as
   the surface for guideline layer 3 (step 2.3), tyre choice (step 5), range resolution
   (steps 5–6), and the row's `Surface` (step 8); otherwise use the stage's surface.

4. **Handle prior setups by mode.**
   - `learn` (default): fetch existing `Setups` rows for this car **where `Learn from this` is
     checked** (the compound-filter query in [notion-rest-read.md](notion-rest-read.md); values +
     `Notes` + `Rating`); infer preferences, weighting by `Rating` (a **1–5 Select** — read the
     label as its integer, higher = better; treat a **blank** rating as unrated — neutral/no extra
     weight) and taking likes/dislikes from `Notes`. Bias toward them, adapt to this stage. If none
     are checked, proceed with **no prior-setup bias** and say so.
   - `independent`: do **not** read prior setups — reason from scratch to avoid anchoring.

5. **Choose values.** First pick the **tyre type** for the surface/conditions (biggest grip
   decision). Then, per parameter, reason from tyre + surface + stage + style + the merged
   guidelines (drivetrain-filtered), then make it legal — **using the range resolved for the
   build surface** (the surface-specific row if the parameter has one; for `Snow`, fall back to a
   `Gravel` row before the baseline; see [notion-rest-read.md](notion-rest-read.md)) — **no step
   grid, no interpolation**:
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
   a member of `Discrete steps`; continuous picks must be within `Min..Max`. Fix any violation
   before writing.

7. **Ensure the stage exists.** Per `notion-structure.md`, make sure the `{stage}` page (with its
   filtered `Setups[Car, Stage]` view) exists under the car's `setups`; create it from the stage
   description if missing. The linked view is **not** page markdown — after writing the stage
   description, create it with `notion-create-view` (`parent_page_id` = the `{stage}` page,
   `data_source_id` = the `Setups` data source, `type: "table"`,
   `configure: 'FILTER "Car" = "{Car}"; FILTER "Stage" = "{stage}"; SHOW <meta first, then value columns by Order>'`).
   Never write a `<linked-view />`-style placeholder into the page body (`notion-structure.md` →
   *Creating an inline linked view*).

8. **Write to Notion — append only** (via the user's Notion connection).
   - Create **one new row** in `Setups`: `Name`, `Car`, `Stage`, `Surface`, `Game version` (if
     known), `Date` (today), `Source = generated`, `Mode`, the chosen `Tyre type`, and each value
     property. Leave **`Learn from this` unchecked** (the user opts in after vetting). **Never
     modify or delete existing rows.**
   - **Apply the column order** (`notion-structure.md` → *Applying the order*): set the `SHOW` on
     the **main `Setups` table view** (meta columns + all value columns by `Order`) and on **this
     setup's stage/per-car linked view** (meta + this car's applicable value columns by `Order`,
     hiding blanks). Idempotent — this re-asserts the order from the current `Order` values, so the
     new setup's projection and the table read in game-menu order (and an alphabetized table or an
     edited `Order` self-heals). It's a view update, not a row/schema rebuild — the append above
     stays a single row. If a parameter has a blank `Order`, fall back to the canonical defaults
     (`notion-structure.md`) and optionally backfill it onto the `Parameters` row.
   - In the row's **page body**: the **per-parameter justification inside a toggle** — grouped by
     section and ordered by each parameter's **`Order`** (the in-game screen sequence: Gearbox →
     Suspensions → Dampers → Axles → Differentials → Wheels/Tyres → Brakes → Electronics &
     Aerodynamics, Front before Rear). Explain notable choices and **cite which guideline drove
     each** (especially a *user* guideline). No wide tables; short headings + bullets. **Do not**
     duplicate values into a separate checklist — the database row is the single source of truth.

9. **Report.** Summarise the setup (incl. tyre type), assumptions, which user guidelines were
   applied, and whether any checked prior setups were learned from. Link the new row; remind the
   user to **rate it `1`–`5`** and tick `Learn from this` if they like it after driving.

## Rules
- Legal by construction: pick from `Discrete steps` when set, else a target within `Min..Max`
  ("dial to nearest"); validate before writing.
- Apply only guidance tagged `[All]` or the car's drivetrain; user guidelines override the base.
- `learn` learns **only from `Learn from this`-checked** setups; new rows start unchecked.
- Page body: justification in a toggle only — no checklist (database row is the source of truth).
- Append-only; cite user guidelines; be explicit about trade-offs and guesses.
