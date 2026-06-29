# Workflow: build a setup for a stage

Generate a setup for one car on one stage and append it as a **new row** in the user's Notion
`Setups` database, with a phone-readable "Enter in-game" checklist. Every value is constrained
to the car's catalog (legal by construction). Read `setup-tuning-principles.md` (reasoning base)
and `notion-structure.md` (structure + mobile conventions) before writing.

## Inputs
- **Car** (e.g. `Lancia Stratos HF`) and **game** (default `ACR`). The car is resolved **under its
  `{Game}` page**; if the same car name exists under more than one game, ask the user which game.
  Non-ACR games use the **same reasoning base** — no game-specific tuning is shipped. If the car
  **isn't onboarded yet**, step 0 onboards it first — automatically from a bundled template when one
  exists, otherwise by asking you to onboard via screenshots before the build proceeds.
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
- **Setup name** (e.g. `alsace dry fast`) — **≤15 chars**, the in-game limit; compact a longer
  proposed/requested name to fit (per `SKILL.md` core rules) and tell the user the name used.
- **Reference setup** (optional) — if the user says "build like setup X" or names a setup as a
  basis, load X's **row value properties** (per `notion-rest-read.md`) as a starting point, and
  X's page-body **intent** if stated. **Never** read X's per-parameter justification prose for
  values — the row is authoritative and the prose may be stale if the user has since edited the
  row by hand (per `SKILL.md` core rules).
  - **Cross-car reference — transfer feel, not raw numbers.** If X is for a **different car**
    (different weight bias / layout) or a **different surface** than this build, reproduce its
    **character/feel on this car** — don't copy its values. First read X for its **intent/character**
    (open & playful, rotation-friendly, planted, …); if that isn't clear (no stated intent and the
    values alone are ambiguous), **ask the user what feel they're after before translating** rather
    than guessing (as with intent above). Then treat **no value as automatically transferable** —
    re-derive each parameter for this car's identity facts (step 1) and the build surface, letting
    only car-independent *style* choices (e.g. preferred toe direction, an aid on/off) carry as-is.
    Pay special attention to the high-impact, easy-to-mis-copy params, judged against
    `setup-tuning-principles.md`:
    - **Diff** (*Differential (LSD)*) — power/coast lock, **preload**, **plates**, and for AWD the
      **centre-diff split / diff ratio**: match the lock/rotation *behaviour* X had, against this
      car's weight bias + the **surface regime**. E.g. a light car's open/low-preload diff becomes
      *more* lock + preload on a rear-heavy car on snow to keep the slide controllable.
    - **Suspension feel** (*Suspension*, *Dampers*) — ride height, springs, dampers (bump/rebound
      slow & fast), ARBs: raw rates and damper clicks **don't map 1:1 across different weights**
      (a rate gives a different ride frequency on a heavier/lighter car). Match the resulting feel
      (ride frequency / planted-vs-compliant, damping character), not the numbers.
    - **Tyre pressure**, **brake bias** (and brake hardware), **engine map** — adapt to this car's
      weight and the surface (on RWD low grip a softer map / longer gears tames snap).
    - **Tyre type and gearing are re-derived, not translated** — tyre type follows the **build
      surface** (step 5; never copy a different-surface reference's compound); gearing (gear set /
      primary gear) follows this car's engine/power band and its own ratio sets.
    **Flag** the adaptations in the report (step 9) and page body (step 8) — what changed from X and
    why. **Escape hatch:** if the user *explicitly* asks for X's **literal values** ("use X's exact
    diff", "copy X"), honor them verbatim **and warn** about any regime tension instead of
    translating. A **same-car** reference is unchanged — values and feel already transfer, so it's a
    straight starting point.
- **Mode** — `learn` (default) or `independent`.
- **Surface override** (optional) — if the user names a surface ("build a gravel setup", "use
  tarmac settings/parameters", "treat this as snow"), it **overrides the stage's stated surface for
  the whole build**: range resolution, tyre choice, surface-tagged guidelines, and the written
  row's `Surface`. Without it, the surface comes from the stage's facts (step 3); if there's no
  stage either, ask the user for the surface.

## Procedure

0. **Ensure the car is onboarded — auto-onboard from a bundled template if needed.** A build is
   *legal by construction* only against the car's `Parameters` catalog, so the catalog must exist
   before anything else. Determine whether the car is onboarded by fetching its `Parameters` rows
   (via [notion-rest-read.md](notion-rest-read.md)) — **this is the same fetch step 1 needs, so
   don't repeat it**. Then, exactly as in [import-savegame.md](import-savegame.md) §5.2:
   - **Catalog present (already onboarded)** → carry the rows into step 1 and continue.
   - **No catalog, but a bundled template matches this car** → **auto-onboard now**, before
     building. Match `car-templates/` by `car:` using the **same rule as `onboard-car.md` step 1**
     (case-insensitive; ignore punctuation, hyphens, apostrophes), then run **`onboard-car.md`'s
     bundled-template path**: write every template row into `Parameters` (with `Order` /
     `Discrete steps` / `Surface`) in **one `notion-create-pages` call**, add all the `Setups`
     value columns in **one `notion-update-data-source` call** (`SKILL.md` → *Batch Notion
     writes*), and set the car's `Drivetrain` + identity facts (`Engine layout` / `Weight bias` /
     `Weight`) from the template. **Skip** onboarding's interactive "Use this template? (Yes/No)"
     prompt **and** its optional gravel pass (the template already carries any `Surface` rows).
     **Don't add a separate Yes/No gate** — announce it in one line (*"{Car} isn't onboarded yet,
     but I have a bundled template — I'll onboard it from the template first, then build your
     setup."*) and **proceed within the build's natural flow**. The car now **has a catalog**;
     treat it as the onboarded case from here on.
   - **No catalog and no matching template** → a legal build is impossible without a catalog, and
     onboarding owns range capture, so **don't fabricate ranges**. Tell the user the car needs
     onboarding first, point them to `onboard-car.md` (screenshots), and offer to switch to that
     workflow. **Stop** the build here.

> **Load steps 1–3 as one batched read** (`SKILL.md` → *Read efficiently*): after resolving the
> structure, issue the independent reads together (parallel tool calls) and run the REST queries in
> one code-execution block — and fetch the `{Car}` page **once** for both its identity facts (step 1)
> and its Guidelines section (step 2), not twice. (When step 0 just auto-onboarded the car from a
> template, you already hold its catalog — don't re-fetch the `Parameters` rows.)

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
   - **`Min/Max = —` with no `Discrete steps`** → the car *has* this parameter but its range was
     never captured during onboarding. **Do not leave it blank** and do not treat it as a
     default: surface the gap to the user and ask them to enumerate the range (or re-onboard the
     car). Once the range is known, fill an explicit value like any other parameter.
   Never go outside `Min..Max` or off the `Discrete steps` set; never invent a parameter the car
   doesn't have.

6. **Validate.** Re-check every chosen value against the catalog **for the build surface**
   (surface-resolved range — `Snow` falls back to `Gravel`, then baseline): discrete picks must be
   a member of `Discrete steps`; continuous picks must be within `Min..Max`. For **ACR**
   `Tyre Type`, the chosen value must be a fully-qualified name from the car's stored list (or
   the standard fallback list if blank) — never a bare/ambiguous value. Confirm
   `Pressure Front` and `Pressure Rear` were both set as separate values. Fix any violation
   before writing. **Completeness:** confirm **every parameter the car has** (every applicable
   `Parameters` row for this car, except `FFB Multiplier`) received an explicit value — no
   applicable parameter is left blank. Any gap from an uncaptured range (step 5) must be
   resolved with the user before writing.

7. **Ensure the stage facts page exists in the catalogue (skip if no stage/location was given).**
   Per `notion-structure.md` → *Locations & stages catalogue*, resolve by name under
   `{Game} → Locations`: create the `{Location}` page if missing, then the `{Stage}` page under it
   if missing, seeded from the facts the user gave (surface, length, key corners/speeds,
   character) — **never** driving style or guidelines. **Reuse the existing page if the
   location/stage already exists** (any car) — never create a duplicate. Ensure its filtered
   `Setups[Stage=this]` view exists (and `Setups[Location=this]` on the location page if newly
   created). The linked view is **not** page markdown — create it with `notion-create-view`
   (`parent_page_id` = the `{Stage}` / `{Location}` page, `data_source_id` = the `Setups` data
   source, `type: "table"`, `configure: 'FILTER "Stage" = "{stage}"; SHOW <output of `… --all
   --show-order`>'` — get the `SHOW` list from the script per `notion-structure.md` → *Applying the
   order*; no `Car` filter, since the stage spans every car that's run it). Never
   write a `<linked-view />`-style placeholder into the page body (`notion-structure.md` →
   *Creating an inline linked view*).

8. **Write to Notion — append only** (via the user's Notion connection).
   - Create **one new row** in `Setups`: `Name`, `Car`, `Location` (if given), `Stage` (if given),
     `Surface`, `Game version` (if known), `Date` (current date/time — per `notion-structure.md`
     → `Date`: run the Python one-liner; don't guess the time), `Source = generated`, `Mode`, the
     chosen `Tyre type`, a value for **every** parameter the car has, **`Model`** (just your model
     name + version, e.g. `Opus 4.8`), and
     **`Skill version`** (per `SKILL.md` → *Skill version*).
     Leave **`Learn from this` unchecked** (the user opts in after vetting). **Never modify or
     delete existing rows.** There is no `Intent` column — driving intent is recorded only in the
     page body below.
   - **Apply the column order — MANDATORY, never skip (even on a quick / low-effort run).** The
     build is **not done** until you've done this (`notion-structure.md` → *Applying the order*),
     **after the row is written**. Get the `SHOW` list from the bundled script (don't build it by
     hand), then set `SHOW` (`notion-update-view`) on every projection:
     - **main `Setups` table view** → `… --all --show-order`;
     - **this car's linked view** (on the `{Car}` page) → `… "{Car}" --show-order` (lists only this
       car's value columns, hiding blanks);
     - **its `{Stage}` / `{Location}` linked view**, if a stage/location was referenced → `… --all
       --show-order` (no per-car filtering).
     Idempotent — re-asserting `SHOW` makes the new setup's projection and the table read in
     game-menu order (an alphabetized table or an edited `Order` self-heals). It's a view update,
     not a row/schema rebuild — the append above stays a single row. (The script handles the
     blank-`Order` fallback; you may still backfill a blank `Order` onto the `Parameters` row.)
   - First, write a **brief setup summary** directly in the page body (not inside a toggle, so
     it's always visible without expanding anything):
     - **H2 heading** with the setup name (e.g. `## alsace dry fast`).
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
     If a **cross-car reference** was used, note each parameter where this build departs from the
     reference and why (this car's weight bias / the surface regime).
     No wide tables; short headings + bullets. **Do not** duplicate values into a separate checklist —
     the database row is the single source of truth.

9. **Report.** Summarise the setup (incl. tyre type), assumptions, which user guidelines were
   applied, and whether any checked prior setups were learned from. If a **cross-car reference** was
   used, call out where the build diverged from it and why (one line). **Confirm in one line that
   you asserted the column order** (step 8) on the affected views — if you can't, you skipped a
   required step: go back and do it before finishing. Link the new row; remind the
   user to **rate it `1`–`5`** and tick `Learn from this` if they like it after driving. If the
   user comes back with how it drove and wants changes, switch to the refine loop
   (`tweak-setup.md`) and iterate **in chat** — don't rebuild from scratch.

## Rules
- **Onboard first (step 0).** If the car has no `Parameters` catalog: a matching bundled template ⇒
  auto-onboard from it (announce, no Yes/No gate) before building; no template ⇒ ask the user to
  onboard via screenshots (`onboard-car.md`) and don't build until the catalog exists.
- Legal by construction: pick from `Discrete steps` when set, else a target within `Min..Max`
  ("dial to nearest"); validate before writing.
- Apply only guidance tagged `[All]` or the car's drivetrain; user guidelines override the base.
- `learn` learns **only from `Learn from this`-checked** setups; new rows start unchecked.
- Page body: justification in a toggle only — no checklist (database row is the source of truth).
- Cross-car reference transfers **feel, not raw numbers**: treat no value as automatically
  transferable — re-derive every value for this car + surface (re-choose tyre type, re-derive
  gearing), translate the feel-shaping params (diff lock/preload/plates/centre-split,
  springs/dampers/ride height/ARBs, tyre pressure, brake bias, engine map) to match the reference's
  character, and flag the adaptations; copy literal values only when the user explicitly asks (then
  warn). Same-car reference = straight starting point.
- Append-only; cite user guidelines; be explicit about trade-offs and guesses.
