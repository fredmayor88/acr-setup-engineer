# Workflow: onboard a car (capture its tunable parameters)

Build (or refresh) the **catalog** of a car's tunable parameters in the user's Notion
`Parameters` database, from in-game Car Setup screenshots. The catalog is the authoritative set
of legal values every generated setup is constrained to. This workflow is also the product's
**first-run setup** — it creates the whole Notion structure if it doesn't exist yet.

Read `notion-structure.md` (structure + schemas + create-if-missing) before writing.

## Inputs
- **Car name** (e.g. `Lancia Stratos HF`).
- The car's **drivetrain** (FWD / RWD / AWD) — read it off the **car information screenshot**
  below, which states it outright (`RWD` / `FWD` / `AWD`, next to the drivetrain icon). Without
  that shot, derive it from which differential sections the car has:
  `Differentials.Front` + `Differentials.Rear` (or any `Differentials.Centre`) ⇒ **AWD**;
  front-only ⇒ **FWD**; rear-only ⇒ **RWD**. Confirm with the user if unclear.
- **Car information screenshot, attached in the chat:** the in-game **car info / HISTORY** screen —
  the one whose right-hand panel lists the car's name, year, class badges, `Engine`, `Max Power`,
  `Max Torque`, `Weight`, and the drivetrain / transmission / steering-lock icons, next to the
  history prose. **This is the primary source for the car's identity facts** (step 5) — one shot
  instead of a lookup. Ask for it alongside the min/max pass. It is **optional**: if the user
  doesn't have it, identity facts fall through the rest of the ladder in step 5. It is **not** a
  source of tunable parameters — nothing on it goes into `Parameters`.
- **Screenshots, attached in the chat:** two passes of the Car Setup screens —
  - a **min** set (every setting dialed to its minimum), and
  - a **max** set (every setting dialed to its maximum).
  Ask the user to attach both. One pair per setup screen/tab (Gearbox, Suspensions F/R,
  Dampers F/R, Axles, Differential(s), Wheels/Tyres F/R, Brakes, Electronics, …).
  - **This first pass must be taken on a TARMAC stage (e.g. Alsace).** Tarmac is the
    **baseline**: some parameters (chiefly on the Suspensions screen) expose a *different* range
    on gravel, and the whole catalog is anchored to the tarmac values. Capturing the baseline on
    gravel would mislabel the surface-specific ranges. The optional gravel pass comes later
    (step 8).

## Procedure

1. **Pick the source of the catalog.**

   **First: check for a bundled template.** Before asking for screenshots, look in
   `car-templates/` for a YAML file whose `car:` field matches the user-provided car name
   (case-insensitive; ignore punctuation differences like hyphens and apostrophes — e.g.
   "Lancia Stratos HF" matches `lancia-stratos-hf.yaml`).

   - **Match found:** Notify the user:
     > "Found a bundled parameter template for {Car}. It includes all parameters with
     > Min/Max ranges and Discrete steps pre-filled — no screenshots needed. Use it?
     > (Yes / No — I'd rather use my own screenshots)"

     - **User confirms (Yes):** Load every row from the template. Treat each entry as if it
       were an extracted row (same `Section`, `Adjustment`, `Min`, `Max`, `Unit`,
       `Discrete steps`, **`order`** fields — copy the template's `order:` straight into the
       row's `Order`). If an entry carries an optional **`surface`** field
       (`Tarmac`/`Gravel`/`Snow`), set that row's `Surface` accordingly and upsert on
       `Car` + `Adjustment` + `Surface`; entries without `surface` are baseline rows (blank
       `Surface`). A template that already includes surface-specific rows means **no gravel pass
       is needed** (skip step 8). Skip steps 2–4 (screenshot capture, extraction,
       confirmation table) and proceed to step 5 (identity facts) → step 6 (Notion structure)
       → step 7 (write to Notion) — writing `Discrete steps` values too, unlike the screenshot
       path. In the report (step 9), note which parameters still have a blank `Discrete steps`
       despite being a `—`-type param, and call them out for user enumeration as usual.
       The `drivetrain` field in the template sets the car's drivetrain. If the template carries
       the optional `engine_layout`, `weight_bias`, `weight`, `max_power`, `max_torque`, `class`,
       `gearbox`, or `steering_lock` fields, use them directly for the car identity facts in step 5
       — no lookup needed (see the determination step below). For any identity field the template
       **lacks**, still work step 5's ladder: an older template may predate several of these fields,
       and a car information screenshot (if the user has one) fills them in a single shot. An
       optional `save_ids` field (the exact in-save car string, used only by save-file import to
       match the car) needs no action here — it doesn't affect the screenshot/template catalog;
       carry it through untouched.
     - **User declines (No):** Fall through to the screenshot path below.

   - **No match:** Proceed to the screenshot path below (no announcement needed).

   Two source paths:
   - **Bundled template** (path above) — `Min`/`Max` **and** `Discrete steps` may already
     be filled. Writes all fields including `Discrete steps`.
   - **Screenshots** (the path below) — extract `Min`/`Max` from the two setup-screen
     passes. For `—` named-selection params, seed `Discrete steps` with the option names the
     screenshots show (plus the standard ACR lists for `Tyre Type`/brake pads); for numeric
     params `Discrete steps` is left blank (user-owned).

   **Pre-existing Notion content is NOT a source.** If the `{Car}` page or any other Notion
   page already contains notes, tables, or parameter values — ignore them entirely. Notion is
   a write destination; never read it to populate or replace extraction. Even if the existing
   content looks complete, proceed with the chosen source and upsert the extracted values.

2. **Read the attached screenshots** and pair each min shot with its max shot by the setup
   screen it shows. If a screen is missing, say so — don't guess its ranges. **Set the car
   information screenshot aside** — it has no min/max pair and contributes no `Parameters` rows;
   it feeds step 5 only.
   **Before the user uploads:** remind them (1) to take this pass on a **tarmac stage (e.g.
   Alsace)** — it's the baseline (see step 8 for the optional gravel pass); (2) to include
   screenshots of every setup tab, even tabs that show *"Not available for this car"* — those
   screenshots tell the skill which categories to skip cleanly; and (3) to add **one shot of the
   car information / HISTORY screen** so the identity facts come straight off the game instead of
   a lookup (step 5).

3. **Extract each Adjustment.** For every tunable row, capture `Section`, `Adjustment`
   (canonical name — reuse names already in the catalog), `Min` (from the min shot), `Max`
   (from the max shot), `Unit`. Mind sign conventions (e.g. negative camber). Record every range
   **exactly as the screen shows it** — in particular **don't "fix" toe**: ACR's toe sign is
   inverted (positive = toe-out; `SKILL.md` → *ACR's toe sign is inverted*), and the catalog stores
   screen values, so the min/max go in unconverted. **Never skip a
   row that appears on screen** — if a parameter shows `—` in both screenshots, still create
   the row with Min=`—`, Max=`—` and flag it for user enumeration; only omit a row if it is
   absent from the screenshots entirely.
   - **Also assign each parameter's `Order`** — its display position, from where it **actually
     appears top-to-bottom (Front side before Rear) on *this car's* setup screens** (or, when
     onboarding from a bundled template, the `order:` values already in that template). The
     screenshots/template are the source of truth for **sequence** — apply the **canonical ACR
     section-blocked numbering** in `notion-structure.md` (*Setups column order*) **to that observed
     order**, never the reverse. **Do not infer a parameter's position from how another
     already-onboarded car is ordered, or from the canonical list's default sequence** — some cars
     group corner sub-parameters differently (e.g. all bump settings before all rebound settings)
     and must be captured exactly as shown. For any car-specific parameter not in the canonical
     list, give it a number **inside its section's block** matching its screenshot position (exact
     slot needn't be perfect — the block keeps it grouped). A surface-tagged row shares its baseline
     row's `Order`.
   - **Always record the actual values shown in the screenshots**, including for discretely-stepped
     parameters: if the min screenshot shows `1` and the max shows `3` for gear set, record
     Min=1, Max=3.
     **Do not** ask for click counts and **do not** compute step sizes. What marks a parameter as
     enumerated is the `Discrete steps` column (user-owned) — not blank Min/Max.
   - **Use `—` for parameters that are named selections or paired/slash values.** For each,
     **seed `Discrete steps` with the option names the screenshots actually show** — typically
     the two endpoint values (the min shot's value and the max shot's value), comma-separated,
     in screenshot order, de-duplicated. **Observed values only — never invent option names the
     screenshots don't show.** The list is usually incomplete (only the endpoints are visible),
     so still flag the row for the user to add any middle options.
     - `Tyre type` — pre-fill `Discrete steps` with the standard ACR tyre list
       (see the tyre/pad exception below); use `—` for min/max as normal.
     - `Brake discs`, `Brake calipers` (front & rear) — seed with the observed disc/caliper
       names.
     - `Brake pads/shoe` (front & rear) — pre-fill `Discrete steps` with the
       standard pad list (see the tyre/pad exception below); use `—` for min/max as normal.
     - `Engine map`, `Throttle map`
     - `LSD power/coast ramp`, `Differential ratio`, and `Centre Ratio to Rear` — **always
       use `—`**, regardless of whether the screenshots show names (e.g. "Sport LSD") or paired
       numbers (e.g. `45/55`, `65//17`). These are discrete selections, not a continuous range;
       seed `Discrete steps` with the observed values so the user only completes the in-between
       options.
     **Flag every `—` row** in the confirmation table as *"needs user enumeration —
     review/complete"*; the seeded endpoints make it usable, but the user should verify and add
     any missing options. **(Exception: `Tyre Type` and `Brake pads/shoe` already have
     `Discrete steps` pre-filled with their standard lists — do not flag them.)**
   - **ABS map and TCS map are always numeric** (0–N integer levels). If their screenshots show
     numbers, capture min and max. If they show `—`, that most likely means this car has no
     ABS/TCS — omit them rather than recording `—`. Do not treat ABS/TCS as component
     selections.
   - **Plates number** and other discrete integer counts are **numeric** — treat them as a
     simple range. When the screenshots show numbers (e.g. min `2`, max `4`), record
     `Min`/`Max` directly (Min=2, Max=4) — **do not flag and do not ask.** Only when a count
     shows `—` in both screenshots is it flagged as uncertain and the user asked for the range
     rather than recording `—`.
   - For **numeric** parameters (those with a real `Min..Max`), leave **`Discrete steps`
     blank** — it is the user's to fill later (see step 9); onboarding never guesses a numeric
     step set. For **`—` named-selection** parameters, seed `Discrete steps` with the observed
     option names as described above (never fabricate names).
   - **Tyre/pad exception — `Tyre Type` and `Brake pads/shoe`**: pre-fill `Discrete steps` with
     the standard list — no screenshot or user action needed; these lists are the same for
     every car, so the rows are immediately usable and **not** flagged.
     - `Tyre Type`: `Tarmac Soft, Tarmac Medium, Tarmac Hard, Tarmac Wet, Tarmac Winter,
       Tarmac Snow, Gravel Soft, Gravel Medium, Gravel Hard, Snow (Studs)`.
     - `Brake pads/shoe` (front & rear): `SOFT, MEDIUM, HARD`.
   - **Tyre pressure is always per-axle.** Record `Pressure Front` and `Pressure Rear` as two
     separate rows (orders 6020 / 6050) — **never** a single combined `Tyre Pressure` row,
     even if the Wheels/Tyres screenshot layout looks like it shows one value. The screen
     exposes front and rear pressure separately (alongside camber/toe); look again if only one
     value was captured.
   - **Skip `FFB Multiplier`** — it is a display/controller preference, not a car setup parameter.
   - **Capture the easily-missed ones too**, when present: damper `Bump transition`
     / `Rebound transition`, `Centre differential` & `Front differential` (AWD), `Engine map`,
     `Throttle map`, `ABS`, `TCS`, and brake `master cylinder` / `disc` / `caliper` / `pad`
     (front & rear). (`Tyre type` and `Brake pads/shoe` are created automatically with their
     standard lists — no screenshot needed; skip them in the screenshot sweep.)
     These are **car-dependent** — older cars may simply lack them; that's fine. Capture whatever
     the screenshots actually show; never fabricate a parameter the car doesn't have.
   - **If a setup screen shows "Not available for this car"**, skip that entire category — do not
     create any rows for it. Note it in the confirmation table and final report as an
     informational item only (e.g. *"Dampers — not available for this car"*). This is normal;
     do not treat it as an error or ask the user to investigate.

4. **Confirm before writing.** Show the assembled table (`Section`, `Adjustment`, `Min`, `Max`,
   `Unit`) and **flag any uncertain reads**. Proceed on the OK.

5. **Determine the car's identity facts.** These describe **the car itself**, not what can be tuned
   on it; they inform tuning balance (see `setup-tuning-principles.md`). They are **car facts, not
   tunable parameters** — every one of them is stored on the `{Car}` page (step 7), never in
   `Parameters`. The full set:

   | Field | Example |
   |---|---|
   | `Drivetrain` | `RWD` |
   | `Engine layout` | `front longitudinal inline-4 (1290 cc DOHC), driving the rear wheels` |
   | `Weight bias` | `~56% front / ~44% rear` |
   | `Weight` | `760 kg` |
   | `Max power` | `163 hp at 8400 rpm` |
   | `Max torque` | `148 Nm at 6500 rpm` |
   | `Class` | `Group 2/4 · H3` |
   | `Gearbox` | `Manual 5-speed` |
   | `Steering lock` | `1332°` |

   **Resolve each field independently, stopping at the first confident source** — a single car
   normally draws from several rungs at once (weight off the screenshot, weight bias off the web):

   1. **Car information screenshot** — the primary source when the user attached one. Read it
      directly; no lookup, no confirmation needed for what it states outright. See *What the info
      screen does and doesn't give* below.
   2. **Bundled template** — when onboarding from a template carrying `engine_layout`,
      `weight_bias`, `weight`, `max_power`, `max_torque`, `class`, `gearbox`, or `steering_lock`,
      use those values directly. If a template value **materially disagrees** with the info
      screenshot, **prefer the screenshot** (it is what this build of the game actually models) and
      note the discrepancy in the report.
   3. **Model knowledge** — for a well-known car, state the facts directly (e.g. *"Lancia Stratos —
      mid-rear transverse V6 behind the driver, ~44% front / ~56% rear, ~950 kg"*).
   4. **Web lookup** — if web search/fetch is available in this session, look up whatever is still
      missing: the **engine layout** (descriptive placement — where the engine sits and how it's
      oriented), the **weight bias** (front/rear percentages, derived from the approximate
      front/rear weight distribution), the **approximate kerb weight**, peak **power**/**torque**,
      the competition **class**, **gearbox** and **steering lock**. If web access is **not**
      available in this session, skip this rung silently.
      This is a factual *car* lookup — **distinct** from the "Notion scope only / never search
      broadly" rule, which governs *setup-data* search, not real-world research. The lookup never
      produces a setup value.
   5. **Ask the user — last resort only.** Only for fields still unresolved after rungs 1–4. Ask
      **once**, in a single batched question listing just the gaps (*"Two things I couldn't pin
      down for the {Car}: its weight bias and steering lock. Know either? Fine to skip."*) — never
      one question per field, and never for a field the screenshot already answered.

   **What the info screen does and doesn't give:**
   - **Stated outright** — `Drivetrain`, `Weight`, `Max power`, `Max torque`, `Class` (the badges,
     e.g. `GROUP 2/4` + `H3`), `Gearbox` (from the transmission icon, e.g. `Manual 5` ⇒
     `Manual 5-speed`), `Steering lock` (the degrees figure, e.g. `1332°`). Record these
     **exactly as shown**, units included.
   - **Partial** — `Engine layout`. The panel gives only the cylinder configuration (e.g.
     `Inline 4`); **placement and orientation** (front/mid/rear, longitudinal/transverse) are not
     in the panel. Read the **history prose** on the same screenshot first — it frequently states
     displacement, layout and construction — then fall through to rungs 3–4 to complete it. Combine
     into one descriptive string rather than storing the bare cylinder count.
   - **Never shown** — `Weight bias`. It always falls through to rungs 2–5.

   - **Confirm with the user** before storing: show each value with its **source and confidence**,
     and let them correct it. Values read straight off the screenshot can be shown as settled
     (source: *info screen*); flag inferred or web-sourced ones as such.
   - For any field still unresolved after the whole ladder — including a field the user was asked
     about and didn't know — record the literal **`couldn't determine`** so the user can fill it
     in by hand later.
   - **Never block onboarding** over a missing identity fact — record what you have (or
     `couldn't determine`) and continue.

6. **Ensure the Notion structure exists (create-if-missing).** Per `notion-structure.md`,
   resolve **by name** and create whatever is missing: the `ACR Setup Engineer` root → the `Config`
   page (seed from `config-page-template.md` if missing — token blank; **never overwrite an
   existing one**) → the `Parameters` and `Setups` DBs → the global `Tuning guidelines` page
   (seed it from `tuning-guidelines-template.md`) → the global `Parameter reference` page (seed its
   body from `parameter-reference-template.md`; **this page is auto-maintained — if it already
   exists, refresh its body by replacing it, don't append**, unlike the never-overwrite
   `Config`/`Tuning guidelines` pages — see the *`Parameter reference` page* create/refresh steps in
   `notion-structure.md`). Then ensure the `{Car}` page exists with its filtered
   `Parameters` / `Setups` views.

7. **Write to Notion** (via the user's Notion connection):
   - Upsert one row per `Car × Adjustment` into the `Parameters` DB (match on `Car` +
     `Adjustment` + `Surface`; update if present, else create — never duplicate). **Batch the
     writes** (`SKILL.md` → *Batch Notion writes*): write **all** the car's rows in a **single
     `notion-create-pages` call** (a car has well under 100 params) — on a first onboard that's
     every row; on a refresh, batch the creates in one call and issue updates only for rows whose
     values changed. These tarmac
     baseline rows leave **`Surface` blank** (the gravel pass in step 8 may add `Gravel`-tagged
     rows later). Set `Min`/`Max`/`Unit` **and `Order`** (step 3; a surface-tagged row mirrors its
     baseline row's `Order`). For `—` named-selection params, write the observed
     option names into `Discrete steps` (observed values only); for numeric params leave
     `Discrete steps` blank. **ACR exception:** set `Tyre Type` `Discrete steps` to the standard
     ACR tyre list and `Brake pads/shoe` (front & rear) to `SOFT, MEDIUM, HARD`.
     **Backfill:** if refreshing a car whose existing rows have a blank `Order`, fill it from the
     canonical defaults (`notion-structure.md`) — no re-screenshotting needed.
   - Ensure the `Setups` DB has a matching **value property** per Adjustment: **Number** for a
     numeric parameter (has a numeric `Min..Max`), **Select** for an enumerated one
     (`Min/Max = —`). **Add them in one call** (`SKILL.md` → *Batch Notion writes*): include every
     value column in the `CREATE TABLE` when the `Setups` DB is first created, or combine **all**
     the new columns into a **single `notion-update-data-source`** call (semicolon-separated
     `ADD COLUMN`s) — never one column per call. Don't remove or rename existing properties. The
     meta columns `Car`, `Location`, `Stage`, `Surface`, and `Conditions` are **Select** (so they
     render as tags), per `notion-structure.md`. Then **apply the column order — MANDATORY, never skip (even on a
     quick / low-effort run)** (`notion-structure.md` → *Applying the order*): get the main table's
     `SHOW` list from the bundled script (`… --all --show-order`) and set the main `Setups` table
     view's `SHOW` to it.
     Creation order does **not** drive the rendered table — the view's `SHOW` directive does.
   - **Record the car's identity facts** on the `{Car}` page — **all nine resolved in step 5**:
     `Drivetrain`, `Engine layout`, `Weight bias`, `Weight`, `Max power`, `Max torque`, `Class`,
     `Gearbox`, `Steering lock` (write the literal `couldn't determine` for any the ladder didn't
     resolve). Write them **together in one page update**, not field by field. They live on the
     page next to each other — never as `Parameters` rows. On a **refresh** of an
     already-onboarded car, fill in fields that are blank or hold `couldn't determine`, and update
     any the info screenshot now answers outright; **don't overwrite a value the user has edited
     by hand** unless the screenshot contradicts it, in which case show both and let them choose.
   - **Seed the `{Car}` page body in this order** (create sections that are missing; never
     overwrite existing content). The linked view is **not** page markdown — create it with
     `notion-create-view`, never as a `<linked-view />`-style placeholder (`notion-structure.md` →
     *Creating an inline linked view*). Because that tool appends the view to the **end** of the
     page, do these in sequence:
     1. **H2 "Setups"** heading (markdown). This section must come first so it's the first thing
        visible on mobile.
     2. The `Setups[Car=this]` filtered linked view — `notion-create-view` with
        `parent_page_id` = the `{Car}` page, `data_source_id` = the `Setups` data source
        (`notion-fetch` it for the id), `type: "table"`, and
        `configure: 'FILTER "Car" = "{Car}"; SHOW <output of `… "{Car}" --show-order`>'` (get the
        `SHOW` list from the bundled script, per `notion-structure.md` → *Applying the order*).
        `SHOW` orders the columns **and** hides blank ones in one step. It lands directly under the
        heading from step 1.
     3. **H2 "Guidelines"** heading + a short stub inviting car-specific tuning preferences
        (tone per `tuning-guidelines-template.md`) — appended **after** the view.

8. **Check for surface-specific ranges (optional gravel pass).**

   The catalog written above is the **tarmac baseline**. On many cars, some **Suspensions**
   settings (most commonly **spring stiffness**, sometimes ride height / ARB) expose a *different*
   min/max on **gravel**. Tell the user and offer a quick check:
   > "That's your tarmac baseline. On a lot of cars, some suspension settings have a different
   > range on gravel. Quick check: load a **gravel stage (e.g. Wales)**, open the **Suspensions**
   > screen, and compare the **spring stiffness** min/max to what I just captured
   > ({tarmac spring-stiffness range}). Same, or different?"

   No separate **snow** pass is needed: snow setups inherit the `Gravel` rows via the resolution
   rule (`Snow` → `Gravel` → baseline; see `notion-rest-read.md`).

   - **Same (or the user would rather not bother):** nothing to do — the baseline covers every
     surface. Continue to the report.
   - **It differs:** ask for a **second full min/max pass taken on a gravel stage** (both a min
     set and a max set — a *full* pass is safest so any other surface-dependent screen is caught,
     not just Suspensions). Then:
     1. **Extract** the gravel pass exactly as in steps 2–3 (reuse the same `Section` /
        `Adjustment` names so rows line up).
     2. **Auto-diff** against the tarmac baseline: for each `Adjustment`, compare the gravel
        `Min`/`Max` (and, for `—` named-selection params, the observed discrete endpoints) to the
        baseline row.
     3. **Show the diff and confirm:** present a short list of only the parameters whose gravel
        range differs (baseline → gravel). Proceed on the OK.
     4. **Write a `Surface = Gravel` row only for each differing parameter** — upsert on `Car` +
        `Adjustment` + `Surface = Gravel`, carrying the gravel `Min`/`Max`/`Unit`/`Discrete steps`
        (and the **same `Order`** as the baseline row).
        **Never touch the baseline rows**, and **never** create a gravel row for a parameter whose
        range is unchanged (it stays a single blank-`Surface` row). If the `Parameters` DB has no
        `Surface` property yet, add it first (per `notion-structure.md` create-if-missing).

9. **Report.** Rows added/updated, and the car's identity facts as written to the `{Car}` page —
   all nine (`Drivetrain` / `Engine layout` / `Weight bias` / `Weight` / `Max power` /
   `Max torque` / `Class` / `Gearbox` / `Steering lock`), **each with the rung it came from**
   (info screen / template / model knowledge / web / you), so the user can see what was read off
   the game and what was inferred. Call out any stored as `couldn't determine` for the user to fill
   in, and any template-vs-screenshot discrepancy. Then: any **surface-specific `Gravel` rows**
   created (list which parameters differ from the tarmac baseline), and anything flagged uncertain.
   **If no car information screenshot was attached**, mention once that one shot of the in-game car
   info screen would have settled most of these — useful next time, not worth redoing now.
   **Tell the user about `Discrete steps`:** any parameter can be pinned to an exact set of
   values by filling its `Discrete steps` cell in Notion (e.g. spring stiffness
   `42300, 50000, 57700, 65400, 73100`, or gear set `1, 2, 3`).
   **Parameters needing user action — call these out explicitly in three groups:**
   - *Component-name selections* (brake discs/calipers, engine/throttle map,
     differential ratio/LSD ramp when shown as names): `Min/Max = —`, **pre-seeded with the
     option names observed in the screenshots** (usually just the two endpoints). The row is
     usable from those endpoints, but **ask the user to review and add any missing in-between
     options** in `Discrete steps` (e.g. seeded `Sport, Rally` → user adds `Race`).
     (**ACR `Tyre Type` and `Brake pads/shoe` are excluded from this group — they are pre-filled
     with their standard ACR lists and immediately usable.**)
   - *Flagged numeric parameters* (any numeric parameter that showed `—` in screenshots — e.g.
     plates number only when it was blank): the user must supply the numeric range so the row
     can be updated. A numeric count that showed real numbers (e.g. plates number `2`–`4`) is
     **not** flagged — it's recorded as a normal range.
   - *Coarse numeric parameters recommended for discretization*: have a valid numeric
     `Min..Max` but in practice only expose a small number of discrete click positions in-game,
     making a free-range target meaningless. **Always flag these when present:**
     `Spring Stiffness Front`, `Spring Stiffness Rear`, `Anti-roll Bar Stiffness Front`,
     `Anti-roll Bar Stiffness Rear`. (Damper channels are intentionally excluded — their value
     density is high enough that free-range targets remain useful.) These work as a free range
     until the user fills `Discrete steps` with the exact click values (e.g.
     `42300, 50000, 57700, 65400, 73100`), but setup values will be poorly-targeted without it.
     Non-blocking — they can be used immediately — but strongly recommended.

## Rules
- **Identity facts are never `Parameters` rows**, and the car information screenshot is never a
  source of tunable ranges. It answers step 5 only; the min/max setup-screen passes remain the
  sole source of the catalog.
- **Asking the user is the last resort for identity facts.** Work the ladder — info screenshot →
  template → model knowledge → web lookup — and only then ask, once, batched, for whatever is
  still missing. Never open onboarding by asking the user to type facts the game or the web can
  supply.
- Prefer canonical `Adjustment` names so `Setups` columns stay consistent across cars. If a car
  uses different wording for a familiar parameter, accept it and record it as shown — never
  reject or flag a parameter for non-standard naming. New parameter names are simply added to
  the table.
- This workflow only defines *legal ranges* — never write a value into a setup here.
- Never ask for click counts or interpolate. For **numeric** params `Discrete steps` is
  **optional and user-owned** — onboarding leaves it blank. For **`—` named-selection** params
  onboarding seeds it with the option names the screenshots show (observed values only, never
  fabricated) plus the standard ACR lists for `Tyre Type`/brake pads; the user completes it.
- **Never use existing Notion content as parameter input.** The `{Car}` page is a write
  destination. Any tables or notes already on it are the user's own work — do not read,
  compare, or defer to them during extraction. Screenshots (or a bundled profile) are the only
  valid sources.
