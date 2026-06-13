# Workflow: onboard a car (capture its tunable parameters)

Build (or refresh) the **catalog** of a car's tunable parameters in the user's Notion
`Parameters` database, from in-game Car Setup screenshots. The catalog is the authoritative set
of legal values every generated setup is constrained to. This workflow is also the product's
**first-run setup** — it creates the whole Notion structure if it doesn't exist yet.

Read `notion-structure.md` (structure + schemas + create-if-missing) before writing.

## Inputs
- **Car name** (e.g. `Lancia Stratos HF`); the **game** — **ask the user which game this car is
  for** (Assetto Corsa Rally, or another game), defaulting to `ACR` if they don't say. The answer
  is the `{Game}` page name in step 6 (create-if-missing handles a brand-new game page). For a
  **non-ACR game** this same screenshot workflow applies — extract whatever the screenshots show.
- The car's **drivetrain** (FWD / RWD / AWD) — derive it from which differential sections the car
  has:
  `Differentials.Front` + `Differentials.Rear` (or any `Differentials.Centre`) ⇒ **AWD**;
  front-only ⇒ **FWD**; rear-only ⇒ **RWD**. Confirm with the user if unclear.
- **Screenshots, attached in the chat:** two passes of the Car Setup screens —
  - a **min** set (every setting dialed to its minimum), and
  - a **max** set (every setting dialed to its maximum).
  Ask the user to attach both. One pair per setup screen/tab (Gearbox, Suspensions F/R,
  Dampers F/R, Axles, Differential(s), Wheels/Tyres F/R, Brakes, Electronics, …).
  - **For ACR, this first pass must be taken on a TARMAC stage (e.g. Alsace).** Tarmac is the
    **baseline**: some parameters (chiefly on the Suspensions screen) expose a *different* range
    on gravel, and the whole catalog is anchored to the tarmac values. Capturing the baseline on
    gravel would mislabel the surface-specific ranges. The optional gravel pass comes later
    (step 8). (For a non-ACR game without this surface behaviour, any one stage is fine.)

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
       `Discrete steps` fields). If an entry carries an optional **`surface`** field
       (`Tarmac`/`Gravel`/`Snow`), set that row's `Surface` accordingly and upsert on
       `Car` + `Adjustment` + `Surface`; entries without `surface` are baseline rows (blank
       `Surface`). A template that already includes surface-specific rows means **no gravel pass
       is needed** (skip step 8). Skip steps 2–4 (screenshot capture, extraction,
       confirmation table) and proceed to step 5 (identity facts) → step 6 (Notion structure)
       → step 7 (write to Notion) — writing `Discrete steps` values too, unlike the screenshot
       path. In the report (step 9), note which parameters still have a blank `Discrete steps`
       despite being a `—`-type param, and call them out for user enumeration as usual.
       The `drivetrain` field in the template sets the car's drivetrain. If the template carries
       the optional `engine_layout`, `weight_bias`, or `weight` fields, use them directly for the
       car identity facts in step 5 — no lookup needed (see the determination step below).
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
   screen it shows. If a screen is missing, say so — don't guess its ranges.
   **Before the user uploads:** remind them (1) to take this pass on a **tarmac stage (e.g.
   Alsace)** — it's the baseline (see step 8 for the optional gravel pass); and (2) to include
   screenshots of every setup tab, even tabs that show *"Not available for this car"* — those
   screenshots tell the skill which categories to skip cleanly.

3. **Extract each Adjustment.** For every tunable row, capture `Section`, `Adjustment`
   (canonical name — reuse names already in the catalog), `Min` (from the min shot), `Max`
   (from the max shot), `Unit`. Mind sign conventions (e.g. negative camber). **Never skip a
   row that appears on screen** — if a parameter shows `—` in both screenshots, still create
   the row with Min=`—`, Max=`—` and flag it for user enumeration; only omit a row if it is
   absent from the screenshots entirely.
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
     - `Tyre type` — for **ACR**, pre-fill `Discrete steps` with the standard ACR tyre list
       (see the ACR exception below); use `—` for min/max as normal.
       For non-ACR games, seed with the observed values as usual.
     - `Brake discs`, `Brake calipers` (front & rear) — seed with the observed disc/caliper
       names.
     - `Brake pads/shoe` (front & rear) — for **ACR**, pre-fill `Discrete steps` with the
       standard pad list (see the ACR exception below); use `—` for min/max as normal. For
       non-ACR games, seed with the observed values as usual.
     - `Engine map`, `Throttle map`
     - `LSD power/coast ramp`, `Differential ratio`, and `Centre Ratio to Rear` — **always
       use `—`**, regardless of whether the screenshots show names (e.g. "Sport LSD") or paired
       numbers (e.g. `45/55`, `65//17`). These are discrete selections, not a continuous range;
       seed `Discrete steps` with the observed values so the user only completes the in-between
       options.
     **Flag every `—` row** in the confirmation table as *"needs user enumeration —
     review/complete"*; the seeded endpoints make it usable, but the user should verify and add
     any missing options. **(ACR exception: `Tyre Type` and `Brake pads/shoe` already have
     `Discrete steps` pre-filled with their standard ACR lists — do not flag them.)**
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
   - **ACR exception — `Tyre Type` and `Brake pads/shoe`**: pre-fill `Discrete steps` with the
     standard ACR list — no screenshot or user action needed; these lists are the same for
     every ACR car, so the rows are immediately usable and **not** flagged.
     - `Tyre Type`: `Tarmac Soft, Tarmac Medium, Tarmac Hard, Tarmac Wet, Tarmac Winter,
       Tarmac Snow, Gravel Soft, Gravel Medium, Gravel Hard, Snow (Studs)`.
     - `Brake pads/shoe` (front & rear): `SOFT, MEDIUM, HARD`.
   - **Skip `FFB Multiplier`** — it is a display/controller preference, not a car setup parameter.
   - **Capture the easily-missed ones too**, when present: damper `Bump transition`
     / `Rebound transition`, `Centre differential` & `Front differential` (AWD), `Engine map`,
     `Throttle map`, `ABS`, `TCS`, and brake `master cylinder` / `disc` / `caliper` / `pad`
     (front & rear). (**ACR only**: `Tyre type` and `Brake pads/shoe` are created automatically
     with their standard ACR lists — no screenshot needed; skip them in the screenshot sweep.)
     These are **car-dependent** — older cars may simply lack them; that's fine.
     For a **non-ACR game** this list is only a *hint*: that game may expose different settings or
     none of these. Capture whatever the screenshots actually show; never fabricate an ACR
     parameter the game doesn't have.
   - **If a setup screen shows "Not available for this car"**, skip that entire category — do not
     create any rows for it. Note it in the confirmation table and final report as an
     informational item only (e.g. *"Dampers — not available for this car"*). This is normal;
     do not treat it as an error or ask the user to investigate.

4. **Confirm before writing.** Show the assembled table (`Section`, `Adjustment`, `Min`, `Max`,
   `Unit`) and **flag any uncertain reads**. Proceed on the OK.

5. **Determine the car's identity facts (engine layout, weight bias, weight).** These are
   **real-world facts about the physical car** — the game does not expose them — and they inform
   tuning balance (see `setup-tuning-principles.md`). They are **car facts, not tunable
   parameters**, and are stored on the `{Car}` page (next to `Drivetrain`), never in `Parameters`.
   Resolve each in this order, stopping at the first confident source:
   1. **Template** — if onboarding from a bundled template that carries `engine_layout`,
      `weight_bias`, or `weight`, use those values directly; no lookup.
   2. **Model knowledge** — for a well-known car, state the facts directly (e.g. *"Lancia Stratos —
      mid-rear transverse V6 behind the driver, ~44% front / ~56% rear, ~950 kg"*).
   3. **Web lookup (optional)** — if web search/fetch is available in this session and the car is
      unfamiliar, look up the **engine layout** (descriptive placement — where the engine sits
      and how it's oriented, e.g. *"mid-rear transverse V6 behind the driver"*), the **weight
      bias** (front/rear percentages, e.g. *"~44% front / ~56% rear"*, derived from the
      approximate front/rear weight distribution), and the **approximate kerb weight**. If web access is **not** available, skip silently.
   - This is a factual *car* lookup — it is **distinct** from the "Notion scope only / never search
     broadly" rule, which governs *setup-data* search, not real-world research. The lookup never
     produces a setup value.
   - **Confirm with the user** before storing: show each value with its **source and confidence**,
     and let them correct it. For any value not found confidently, record the literal
     **`couldn't determine`** so the user can fill it in by hand later.
   - **Never block onboarding** over a missing identity fact — record what you have (or
     `couldn't determine`) and continue.

6. **Ensure the Notion structure exists (create-if-missing).** Per `notion-structure.md`,
   resolve **by name** and create whatever is missing: the `Car setups` root → `{Game}` page →
   the `Parameters` and `Setups` DBs → the global `Tuning guidelines` page (seed it from
   `tuning-guidelines-template.md`). Then ensure the `{Car}` page exists with its filtered
   `Parameters` / `Setups` views.

7. **Write to Notion** (via the user's Notion connection):
   - Upsert one row per `Car × Adjustment` into the `Parameters` DB (match on `Car` +
     `Adjustment` + `Surface`; update if present, else create — never duplicate). These tarmac
     baseline rows leave **`Surface` blank** (the gravel pass in step 8 may add `Gravel`-tagged
     rows later). Set `Min`/`Max`/`Unit`. For `—` named-selection params, write the observed
     option names into `Discrete steps` (observed values only); for numeric params leave
     `Discrete steps` blank. **ACR exception:** set `Tyre Type` `Discrete steps` to the standard
     ACR tyre list and `Brake pads/shoe` (front & rear) to `SOFT, MEDIUM, HARD`.
   - Ensure the `Setups` DB has a matching **value property** per Adjustment: **Number** for a
     numeric parameter (has a numeric `Min..Max`), **Select** for an enumerated one
     (`Min/Max = —`). Don't remove or rename existing properties.
   - **Record the car's identity facts** on the `{Car}` page: `Drivetrain`, and the
     `Engine layout` / `Weight bias` / `Weight` resolved in step 5 (write `couldn't determine`
     for any that weren't found). These live on the page next to each other — never as
     `Parameters` rows.
   - **Seed the `{Car}` page body in this order** (create sections that are missing; never
     overwrite existing content):
     1. **H2 "Setups"** heading + the `Setups[Car=this]` filtered linked view (hide blank
        columns). This must come first so it's the first thing visible on mobile.
     2. **H2 "Guidelines"** heading + a short stub inviting car-specific tuning preferences
        (tone per `tuning-guidelines-template.md`).

8. **Check for surface-specific ranges (optional gravel pass).** **ACR only** — skip for games
   without surface-dependent ranges.

   The catalog written above is the **tarmac baseline**. On many cars, some **Suspensions**
   settings (most commonly **spring stiffness**, sometimes ride height / ARB) expose a *different*
   min/max on **gravel**. Tell the user and offer a quick check:
   > "That's your tarmac baseline. On a lot of cars, some suspension settings have a different
   > range on gravel. Quick check: load a **gravel stage (e.g. Wales)**, open the **Suspensions**
   > screen, and compare the **spring stiffness** min/max to what I just captured
   > ({tarmac spring-stiffness range}). Same, or different?"

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
        `Adjustment` + `Surface = Gravel`, carrying the gravel `Min`/`Max`/`Unit`/`Discrete steps`.
        **Never touch the baseline rows**, and **never** create a gravel row for a parameter whose
        range is unchanged (it stays a single blank-`Surface` row). If the `Parameters` DB has no
        `Surface` property yet, add it first (per `notion-structure.md` create-if-missing).

9. **Report.** Rows added/updated, the recorded drivetrain, the car's identity facts
   (`Engine layout` / `Weight bias` / `Weight`, noting any stored as `couldn't determine` for the
   user to fill in), any **surface-specific `Gravel` rows** created (list which parameters differ
   from the tarmac baseline), and anything flagged uncertain.
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

   **Invite them to share the car (screenshot onboarding only).** If this car was onboarded from
   screenshots — i.e. it was **not** already in the bundled library (step 1) — close the report
   with a short, no-pressure nudge to contribute it back, so future drivers can skip the
   screenshot work:
   > "By the way — you just built this car's whole catalog from screenshots, and it's not in the
   > shared library yet. If you'd like, I can package it up and hand you a one-click link to
   > share it, so the next person who drives the {Car} can onboard it instantly. Just say
   > *'export the {Car}'* whenever you're up for it — totally optional."

   Do **not** add this nudge when the car was onboarded from a bundled template (it's already in
   the library). Keep it to a sentence or two; don't repeat it or push.

## Rules
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
