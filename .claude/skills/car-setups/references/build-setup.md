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

## Procedure

1. **Load the constraints + drivetrain + identity facts.** Fetch the car's `Parameters` rows
   **via [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows reliably) → for
   each, record `Min`, `Max`, `Unit`, and the optional **`Discrete steps`** set. Determine the car's
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
   general guidelines where it speaks to the same thing.

4. **Handle prior setups by mode.**
   - `learn` (default): fetch existing `Setups` rows for this car **where `Learn from this` is
     checked** (the compound-filter query in [notion-rest-read.md](notion-rest-read.md); values +
     `Notes` + `Rating`); infer preferences, weighting by `Rating` and
     taking likes/dislikes from `Notes`. Bias toward them, adapt to this stage. If none are
     checked, proceed with **no prior-setup bias** and say so.
   - `independent`: do **not** read prior setups — reason from scratch to avoid anchoring.

5. **Choose values.** First pick the **tyre type** for the surface/conditions (biggest grip
   decision). Then, per parameter, reason from tyre + surface + stage + style + the merged
   guidelines (drivetrain-filtered), then make it legal — **no step grid, no interpolation**:
   - **`Discrete steps` filled** → pick **one value from that exact set** (covers coarse
     numerics like spring stiffness and named options like gear set). The checklist value is
     exact.
   - **numeric `Min..Max`, no `Discrete steps`** → pick any target within `Min..Max`; in the
     checklist present it as **"~target (dial to nearest)"** (the in-game increment is unknown).
   - **`Min/Max = —` with no `Discrete steps`** → the param was never captured from screenshots:
     **skip it** and note in the report (the user should re-onboard the car to fix this).
   Never go outside `Min..Max` or off the `Discrete steps` set; never invent a parameter the car
   doesn't have.

6. **Validate.** Re-check every chosen value against the catalog: discrete picks must be a
   member of `Discrete steps`; continuous picks must be within `Min..Max`. Fix any violation
   before writing.

7. **Ensure the stage exists.** Per `notion-structure.md`, make sure the `{stage}` page (with its
   filtered `Setups[Car, Stage]` view) exists under the car's `setups`; create it from the stage
   description if missing.

8. **Write to Notion — append only** (via the user's Notion connection).
   - Create **one new row** in `Setups`: `Name`, `Car`, `Stage`, `Surface`, `Game version` (if
     known), `Date` (today), `Source = generated`, `Mode`, the chosen `Tyre type`, and each value
     property. Leave **`Learn from this` unchecked** (the user opts in after vetting). **Never
     modify or delete existing rows.**
   - In the row's **page body**: the **per-parameter justification inside a toggle** — group
     by section (Gearbox, Suspensions, Dampers, Differential, Wheels/Tyres, Brakes,
     Electronics…), explain notable choices, and **cite which guideline drove each** (especially
     a *user* guideline). No wide tables; short headings + bullets. **Do not** duplicate values
     into a separate checklist — the database row is the single source of truth.

9. **Report.** Summarise the setup (incl. tyre type), assumptions, which user guidelines were
   applied, and whether any checked prior setups were learned from. Link the new row; remind the
   user to tick `Learn from this` if they like it after driving.

## Rules
- Legal by construction: pick from `Discrete steps` when set, else a target within `Min..Max`
  ("dial to nearest"); validate before writing.
- Apply only guidance tagged `[All]` or the car's drivetrain; user guidelines override the base.
- `learn` learns **only from `Learn from this`-checked** setups; new rows start unchecked.
- Page body: justification in a toggle only — no checklist (database row is the source of truth).
- Append-only; cite user guidelines; be explicit about trade-offs and guesses.
