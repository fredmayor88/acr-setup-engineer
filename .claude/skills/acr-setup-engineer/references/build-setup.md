# Workflow: build a setup for a stage

Generate a setup for one car on one stage and append it as a **new row** in the user's Notion
`Setups` database, with a phone-readable "Enter in-game" checklist. Every value is constrained
to the car's catalog (legal by construction). Read `setup-tuning-principles.md` (reasoning base)
and `notion-structure.md` (structure + mobile conventions) before writing.

**Baseline first.** A build is anchored on the **game's own default setup** wherever possible: if a
captured default exists for this context, the build starts from its values and moves only what the
driver's feedback justifies; if none exists, the default path is to *recommend the user drive the
default first*, capture it, and interview them (steps 4–6) rather than generating from scratch. The
catalog gives legal *ranges* but no sense of where inside them the game itself sits — the captured
default supplies exactly that, so every later change is a targeted fix instead of a guess. This is a
strong recommendation, **not a gate**: if the user would rather just have a setup now, build one.

## Inputs
- **Car** (e.g. `Lancia Stratos HF`), resolved under the `ACR Setup Engineer` root. If the car
  **isn't onboarded yet**, step 0 onboards it first — automatically from a bundled template when one
  exists, otherwise by asking you to onboard via screenshots before the build proceeds.
- **Location / Stage** (both optional) — a reference into the shared `Locations` catalogue
  (`notion-structure.md` → *Locations & stages catalogue*). A build may name neither (an arbitrary
  setup with no place context, e.g. "drift setup, tarmac"), a location only, or a specific stage.
  If the named stage/location doesn't exist yet in the catalogue, ask the user for its facts
  (surface, length, key corners/speeds, character) and create it — see step 10. **Stage/location
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
      surface** (step 8; never copy a different-surface reference's compound); gearing (gear set /
      primary gear) follows this car's engine/power band and its own ratio sets.
    **Flag** the adaptations in the report (step 12) and page body (step 11) — what changed from X and
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

> **Load steps 1–4 as one batched read** (`SKILL.md` → *Read efficiently*): after resolving the
> structure, issue the independent reads together (parallel tool calls) and run the REST queries in
> one code-execution block — and fetch the `{Car}` page **once** for both its identity facts (step 1)
> and its Guidelines section (step 2), not twice. The `Setups` slices step 4 (default baseline) and
> step 7 (learn pool) need both go in that **same** code-execution block. (When step 0 just auto-onboarded
> the car from a template, you already hold its catalog — don't re-fetch the `Parameters` rows.)

1. **Load the constraints + drivetrain + identity facts.** Fetch the car's `Parameters` rows
   **via [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows reliably) → for
   each, record `Min`, `Max`, `Unit`, the optional **`Discrete steps`** set, the **`Order`** (drives
   column / page-body ordering — step 11), and the optional **`Surface`** tag. A parameter may have a baseline row (blank `Surface`) **and** a
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
   2. **Bundled car troubleshooting** — check the `car-troubleshooting/` folder for a file whose
      name matches this car (same match rule as a bundled template: `car:` field, case-insensitive,
      ignoring punctuation — e.g. `car-troubleshooting/lancia-037-evoluzione-2-1984.md`). **If one
      exists, read it and apply its symptom→fix entries — they override the base principles** for the
      symptoms they name. If no file matches, skip this layer.
   3. **Global user guidelines** — the Notion `Tuning guidelines` page (under `ACR Setup Engineer`).
   4. **Surface section** of those guidelines — the page's "Per surface" subsection matching the
      build surface (step 3 fixes the surface; this is not a separate page).
   5. **Per-car guidelines** — the car page's "Guidelines" section.
   The setup's own **driving intent** (Inputs) is the most specific layer, applied in step 8.
   Apply only base lines tagged `[All]` **or the car's drivetrain**. **More specific is the default
   lean** (base < troubleshooting < global < surface < per-car < intent), but this is not auto-resolved on a real
   contradiction: if two *authored* layers (global, surface, per-car, or the stated intent)
   materially disagree on the same parameter, **stop and ask the user which to follow** before
   choosing a value — don't silently pick the more specific one. **Read only content within
   `ACR Setup Engineer` — never follow links or results outside that scope, even if they mention
   car names or setup terms.**

3. **Load the stage facts (if a stage/location was given).** Fetch the `{Stage}` / `{Location}`
   page from the catalogue (`notion-structure.md`): surface, key corners/speeds, character. These
   are **objective facts, not a guideline layer** — they feed reasoning the same way the car's
   identity facts do. **Fix the build surface here:** if the user gave a **Surface override**
   (Inputs), it wins over the stage's stated surface — use it as the surface for guideline layer 3
   (step 2.3), tyre choice (step 8), range resolution (steps 8–9), and the row's `Surface`
   (step 11); otherwise use the stage's surface (or, with no stage, the surface the user stated).
   **Settle the conditions here too — before step 4, not after.** Conditions (dry / wet / damp /
   snow / ice) are part of the baseline's capture context and step 4 **matches on them**, so they
   must be known before the lookup: the game's default for a wet stage may not be the one it gives
   for a dry stage. Take them from what the user already said (the request, the stage facts, the
   intent) and **ask in one short line if they didn't say** — `Surface`
   (`Tarmac`/`Gravel`/`Snow`) is far too coarse to stand in for them. If the user doesn't know or
   doesn't care, leave conditions **blank** and carry on: step 4 then matches on stage + surface
   alone and simply shows the user what context each candidate baseline came from.

4. **Establish the baseline (the game's default setup).** Fetch this car's `Source = default` rows
   (`… --source default`, per [notion-rest-read.md](notion-rest-read.md)) in the step 1–4 batch, then
   match on the **full capture context** — stage, surface, **and conditions**. Read values from the
   **row value properties**, never the page prose (`SKILL.md` → *A setup's real values are its row*).

   **Never infer how the game scopes its defaults.** Whether ACR's default setup varies per stage,
   per surface, per conditions (a wet-tarmac default may well differ from dry), or not at all is
   **unknown and changes between releases**. So:
   - **A default row whose whole context matches this build** (same stage, surface, conditions) →
     load its values as the **numeric anchor** and continue to step 7.
   - **A default row for this car in any differing context** (another stage, another surface, or the
     same surface in different conditions) → don't demand a fresh screenshot pass, and **don't assume
     it transfers**. Show the user the stored values *and the context they were captured under*, and
     ask them to glance at the in-game setup screen here: *"Do these match what the game gives you on
     this stage, in these conditions?"* **Confirmed** → write a `default` row for this context from
     those values (step 5's write, no screenshots needed) and continue. **Different** → fall through
     to the capture path below.
   - **No default row for this car at all** → the recommend-first path:
     1. In one short message, recommend running the stage on the **in-game default setup** first, and
        say why: it's the game's own baseline, it's often already decent, and it turns everything
        after it into a targeted fix rather than a guess.
     2. Deliver the **pre-drive briefing** from
        [driving-feedback-interview.md](driving-feedback-interview.md) — the corner-phase vocabulary
        plus a short "what to pay attention to" list tailored to this stage's facts (step 3), and the
        gearing prompts. A driver can't report on things they didn't know to notice, so this comes
        **before** the drive, not after.
     3. Ask for **setup-screen screenshots of the default** so it can be captured (step 5).
     4. **Stop here** — don't build yet. **But this is a recommendation, not a gate:** if the user
        says to build anyway, or would rather not drive the default, go straight on to step 7 and
        build normally, noting in the report (step 12) and page body (step 11) that no baseline
        anchor was used.

5. **Capture the default (when the screenshots arrive).** Use the **conditions settled in step 3** —
   don't ask again here; if they were left blank there because the user didn't know, ask once now,
   since this row is the one that will be matched against later.

   Read the values off the screenshots: the **same setup screens** as
   [onboard-car.md](onboard-car.md) → *Inputs*, but recording the **currently displayed value**
   instead of a min/max pair. Reuse onboarding's canonical `Adjustment` names, section grouping, and
   `Order`. Validate each against the car's catalog for the build surface — if a shown value falls
   **outside** a captured range, **flag it rather than clamping it**: that means the `Parameters`
   range is wrong or stale and the car needs re-onboarding.

   Then write **one** `Setups` row: `Source = default`, `Car`, `Stage`/`Location` (when the build
   names them), `Surface`, **`Conditions`** (from step 3 — fill it whenever they're known, since
   this is what a later build matches on; leave **blank** rather than guessing), `Date`,
   `Game version` (if known), `Skill version`, `Learn from this`
   **unchecked**, `Model` **blank** (the values are the game's, not a model's), `Name` ≤15 chars.
   Also record the **capture context** — stage, surface, **conditions**, game version, date — in a
   visible **"Captured under"** block at the top of the page body (*not* in a toggle) plus a compact
   one-line copy in `Notes`; that block is what the reuse check in step 4 shows the user, and it
   carries the parts of the context (game version, exact stage) that aren't columns. Then **assert the
   column order** exactly as step 11 requires — it's a `Setups` write like any other. Append-only: a
   re-capture adds a **new** row and the most recent matching context wins. Full conventions:
   `notion-structure.md` → *Default (stock) baseline rows*.

6. **Interview the driver.** When the user reports back from the default drive, run
   [driving-feedback-interview.md](driving-feedback-interview.md): the opening triage, then the
   symptom families and the gearing sub-interview, in small batches and plain language. Persist the
   result as that file's *Recording the outcome* section describes — a one-line dated verdict in the
   baseline row's `Notes`, the full record in a dated collapsed **"Driving feedback"** toggle in its
   page body, and any **lasting** preference (not a one-off stage symptom) as a bullet in the
   `{Car}` page's Guidelines section, with the raw log in that page's collapsed **"Driving feedback
   log"** toggle. The symptom list is the most specific input to step 8, alongside the driving intent.

7. **Handle prior setups by mode.**
   - `learn` (default): fetch existing `Setups` rows for this car **where `Learn from this` is
     checked** (the compound-filter query in [notion-rest-read.md](notion-rest-read.md); read
     values from each row's **value properties** — never from its page-body justification, which
     can go stale after manual edits — plus `Notes` + `Rating`); infer preferences, weighting by
     `Rating` (a **1–5 Select** — read the
     label as its integer, higher = better; treat a **blank** rating as unrated — neutral/no extra
     weight) and taking likes/dislikes from `Notes`. Bias toward them, adapt to this build's intent
     and stage facts. If none are checked, proceed with **no prior-setup bias** and say so.
     **`Source = default` rows are never part of the learn pool** — they are the game's values, not
     the user's taste, and they are consumed as the step 4 anchor instead. The `--learn-only` query
     excludes them.
   - `independent`: do **not** read prior setups — reason from scratch to avoid anchoring. (The
     step 4 baseline anchor still applies: `independent` means no *preference* anchoring from past
     setups, not discarding the game's own reference values.)

8. **Choose values.** First pick the **tyre type** for the surface/conditions (biggest grip
   decision) — **for ACR**, pick from the car's stored `Tyre Type` `Discrete steps` if it has
   one, else from the standard fallback list (per `SKILL.md` → *ACR tyre fallback + canonical
   names*); always write the fully-qualified name (never a bare/ambiguous value like `Snow`
   or `Gravel`). Then, per parameter, reason from tyre + surface + stage facts + driving intent
   + the merged guidelines (drivetrain-filtered), then make it legal — **using the range
   resolved for the build surface** (the surface-specific row if the parameter has one; for
   `Snow`, fall back to a `Gravel` row before the baseline; see
   [notion-rest-read.md](notion-rest-read.md)) — **no step grid, no interpolation**.

   - **Anchor on the baseline when one exists (step 4).** Start from the **default's values** and
     move a parameter **only** when the interview symptoms (step 6) or the driving intent justify it.
     Every departure is reasoned and reported as `default → new`. A parameter with nothing pointing
     at it **keeps the default's value** — that's the whole point of the anchor, and it does not
     weaken `SKILL.md` → *Every parameter the car has gets a value*, because the default row is a
     fully captured explicit row, not a blank. Work the changes in **fix-order ladder** order (tyre
     type → differential → ride height/springs → ARBs → dampers → alignment → brake bias; gearing in
     parallel), fixing the major problem before the fine tuning — see
     [driving-feedback-interview.md](driving-feedback-interview.md) → *Fix-order ladder*. **What the
     driver actually reported outranks the ladder.**
   - **Tyre type is always re-derived**, even with a baseline — it follows the build surface, never
     the default's compound.
   - **Tyre pressure is always two values** — choose `Pressure Front` and `Pressure Rear` separately,
     never a single combined pressure, each per the *Tyre pressure* section of
     [setup-tuning-principles.md](setup-tuning-principles.md). **With a baseline, hold the default's
     pressures** and move them only on a reported pressure symptom — ACR's pressure model isn't
     physically sensible, so the game's own numbers beat the skill's reasoning. Without a baseline,
     fall back to that file's **ACR pressure rule** (start in the upper half of the legal range).

   If a parameter is pulled in conflicting directions by two
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
   - **Brake hardware (`Brake Discs` / `Brake Calipers`, front & rear — when the car has them):**
     choose these on their **braking merit**, not left at stock. Caliper piston area drives brake
     force (a 4-piston vs 2-piston caliper is a real tuning lever) and disc size drives brake torque
     / cooling / modulation for the surface — pick both for the surface grip and driving intent (see
     `setup-tuning-principles.md` *Discs* / *Calipers*). Choose the **caliper first** (bigger
     effect), then the disc size. Pick each from its own `Discrete steps` set as usual — the exact
     disc+caliper pair may not be co-selectable in-game, which the step 12 caveat handles.

9. **Validate.** Re-check every chosen value against the catalog **for the build surface**
   (surface-resolved range — `Snow` falls back to `Gravel`, then baseline): discrete picks must be
   a member of `Discrete steps`; continuous picks must be within `Min..Max`. For **ACR**
   `Tyre Type`, the chosen value must be a fully-qualified name from the car's stored list (or
   the standard fallback list if blank) — never a bare/ambiguous value. Confirm
   `Pressure Front` and `Pressure Rear` were both set as separate values. For brakes, validate each
   of `Brake Discs` and `Brake Calipers` is a member of **its own** `Discrete steps` — **do not**
   enforce disc+caliper *pair* compatibility (the catalog doesn't encode it; the step 12 caveat
   covers a pair that isn't co-selectable in-game). Fix any violation
   before writing. **Completeness:** confirm **every parameter the car has** (every applicable
   `Parameters` row for this car, except `FFB Multiplier`) received an explicit value — no
   applicable parameter is left blank. Any gap from an uncaptured range (step 8) must be
   resolved with the user before writing.

10. **Ensure the stage facts page exists in the catalogue (skip if no stage/location was given).**
   Per `notion-structure.md` → *Locations & stages catalogue*, resolve by name under
   `ACR Setup Engineer → Locations`: create the `{Location}` page if missing, then the `{Stage}`
   page under it if missing, seeded from the facts the user gave (surface, length, key corners/speeds,
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

11. **Write to Notion — append only** (via the user's Notion connection).
   - Create **one new row** in `Setups`: `Name`, `Car`, `Location` (if given), `Stage` (if given),
     `Surface`, `Conditions` (if known from step 3 — **optional, leave blank rather than guessing**;
     no need to fill it when the name already says it), `Game version` (if known), `Date` (current date/time — per `notion-structure.md`
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
       - Whether the build was **anchored on a captured default** (name the baseline row) or built
         from scratch with **no baseline anchor**, and the headline symptoms from the interview that
         drove the changes.
     This is the same information as the step 12 chat report, stored permanently so the user can revisit
     the reasoning on their phone without expanding the detail toggle.
   - When a baseline anchor was used (step 4), add a toggle **"Changes from the stock baseline"** —
     one line per parameter that moved: `default value → new value` + a one-line reason, in
     fix-order ladder order. Parameters left at the default are **not** listed; say how many were
     held. (Same shape as `tweak-setup.md`'s "Changes from {source}" toggle.)
   - Below it, the **per-parameter justification inside a toggle** — grouped by section and ordered by
     each parameter's **`Order`** (the in-game screen sequence: Gearbox → Suspensions → Dampers →
     Axles → Differentials → Wheels/Tyres → Brakes → Electronics & Aerodynamics, Front before Rear).
     Explain notable choices and **cite which guideline drove each** (especially a *user* guideline).
     If a **cross-car reference** was used, note each parameter where this build departs from the
     reference and why (this car's weight bias / the surface regime).
     No wide tables; short headings + bullets. **Do not** duplicate values into a separate checklist —
     the database row is the single source of truth.

12. **Report.** Summarise the setup (incl. tyre type), assumptions, which user guidelines were
   applied, and whether any checked prior setups were learned from. State whether the build was
   **anchored on a captured default** — if so, how many parameters moved off it and how many were
   held; if not, say plainly that **no baseline anchor was used** and that driving the game's default
   first would make the next iteration sharper. If a **cross-car reference** was
   used, call out where the build diverged from it and why (one line). **Confirm in one line that
   you asserted the column order** (step 11) on the affected views — if you can't, you skipped a
   required step: go back and do it before finishing. Link the new row; remind the
   user to **rate it `1`–`5`** and tick `Learn from this` if they like it after driving.
   **Also ask for tyre-pressure feedback**: one line inviting the user to say, after driving,
   whether the pressures felt too low, too high, or right — the in-game pressure model is still
   being calibrated, and their answer should be recorded (in the setup's `Notes` and, if it's a
   general preference, their `Tuning guidelines` page) so future builds improve. If the
   user comes back with how it drove and wants changes, switch to the refine loop
   (`tweak-setup.md`) and iterate **in chat** — don't rebuild from scratch; if what they say is
   vague ("it felt off"), run [driving-feedback-interview.md](driving-feedback-interview.md) first.
   - **Brake disc/caliper availability caveat.** If the setup includes **both** a `Brake Discs`
     and a `Brake Calipers` selection (front and/or rear), add this one-line note to the chat
     report: *"Note: the in-game **calipers available depend on the selected brake disc**, so this
     exact disc+caliper combination may not be selectable. If so, keep the recommended calipers and
     pick the closest available disc size — the caliper carries the bigger braking effect."* Omit it
     when the car has no brake disc/caliper params.

## Rules
- **Onboard first (step 0).** If the car has no `Parameters` catalog: a matching bundled template ⇒
  auto-onboard from it (announce, no Yes/No gate) before building; no template ⇒ ask the user to
  onboard via screenshots (`onboard-car.md`) and don't build until the catalog exists.
- **Baseline first, but never a gate (steps 4–6).** With a captured default for this context, anchor
  on it and move only what the driver's feedback justifies. Without one, recommend driving the game's
  default, brief the user *before* they drive, and offer to capture it — then build anyway the moment
  they ask.
- **Never infer how the game scopes its defaults** (per stage / surface / conditions / car). Reuse
  across any differing context is **user-confirmed**, never assumed.
- **Hold the default's tyre pressures** unless a symptom points at them; ACR's pressure model isn't
  physically sensible, so the game's numbers beat the skill's reasoning.
- **Fix major before fine** — work the ladder (tyre → diff → height/springs → ARBs → dampers →
  alignment → brake bias), and let what the driver actually reported override it.
- Legal by construction: pick from `Discrete steps` when set, else a target within `Min..Max`
  ("dial to nearest"); validate before writing.
- Apply only guidance tagged `[All]` or the car's drivetrain; user guidelines override the base.
- `learn` learns **only from `Learn from this`-checked** setups, and **never from `Source = default`
  rows**; new rows start unchecked.
- Page body: justification in a toggle only — no checklist (database row is the source of truth).
- Cross-car reference transfers **feel, not raw numbers**: treat no value as automatically
  transferable — re-derive every value for this car + surface (re-choose tyre type, re-derive
  gearing), translate the feel-shaping params (diff lock/preload/plates/centre-split,
  springs/dampers/ride height/ARBs, tyre pressure, brake bias, engine map) to match the reference's
  character, and flag the adaptations; copy literal values only when the user explicitly asks (then
  warn). Same-car reference = straight starting point.
- Append-only; cite user guidelines; be explicit about trade-offs and guesses.
