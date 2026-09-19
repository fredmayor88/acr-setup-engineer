# Workflow: onboard a car (capture its tunable parameters)

Set up (or refresh) a car so setups can be built for it. The **catalog** — the authoritative set
of legal values every generated setup is constrained to — comes from one of two sources, and this
workflow is where a car gets assigned one (`notion-structure.md` → *Where a car's catalog lives*):

- **A bundled template** (`car-templates/<slug>.yaml`) makes it a **template car**. The template
  *is* the catalog; it stays in the skill and **no `Parameters` rows are written**. Notion gets
  the `Setups` value columns, the car's four pages, and a readable `Catalog snapshot`.
- **The user's min/max Car Setup screenshots** make it a **screenshot car**. Its catalog is
  written into the Notion `Parameters` DB, one row per parameter, as it always was.

This workflow is also the product's **first-run setup** — it creates the whole Notion structure if
it doesn't exist yet.

Read `notion-structure.md` (structure + schemas + create-if-missing) before writing.

## Trigger phrases
**Onboarding:** "onboard my car", "onboard the {car}", "capture the {car}'s parameters", "add the
{car} to Notion".

**Refreshing an already-onboarded car:** "refresh the {car} in my Notion", "update the {car}",
"re-onboard the {car}", "bring the {car} up to date". A refresh request that names the **car**
lands here — **not** in `refresh-catalog-snapshot.md`, which is only for a request that names the
**snapshot** itself.

**Re-onboarding an already-onboarded car from screenshots:** "onboard the {car} from my
screenshots", "re-onboard the {car} from screenshots", "onboard the {car} from screenshots
instead". **A request that names screenshots is not a refresh**: it takes the **screenshot path**
below, whatever the car is today, and its catalog source line becomes `your screenshots`. A bare
"re-onboard the {car}" or "refresh the {car}", with no mention of screenshots, stays a template
refresh.

## Refreshing an already-onboarded car

A refresh brings **everything the skill owns** back in line with the bundled template. It is
deliberately cheap: the car's `Catalog` page is **regenerated and replaced wholesale**, with **no
field-by-field comparison and no questions**, because nothing the user wrote lives on it.

0. **Decide what was asked, and which kind of car this is.** Two checks, in this order:

   - **Did the user ask for screenshots? Then this is not a refresh.** If the request names
     screenshots — *"onboard the {car} from my screenshots"*, *"re-onboard the {car} from
     screenshots"* — leave this section and run the **screenshot path** in *Procedure* from step
     1, even though the car is already onboarded. The car becomes (or stays) a **screenshot
     car**: its catalog goes into the `Parameters` DB and its catalog source line becomes `your
     screenshots`. Say in one line what that changes — *"From now on the {Car}'s legal values
     come from your own `Parameters` rows, not from the bundled template."* A bare *"re-onboard
     the {car}"* or *"refresh the {car}"* with no mention of screenshots is a normal refresh:
     carry on below.
   - **Which kind of car is it?** Fetch its `Catalog` page and read the `Catalog source:` line
     (`notion-structure.md` → *Where a car's catalog lives*). A car onboarded by an older skill
     version has **no such line**: it is a **template car** when a `car-templates/` file matches
     its name, and a **screenshot car** otherwise. Everything below branches on this.
1. **Migrate the page structure if it's still the old one-page layout** — see *Migration* below.
   Do this first; everything after assumes the four-page structure.
2. **Rename a legacy `Feedback` page to `Log`** — the car's log page used to carry the old name,
   and a refresh renames it in place so nothing is lost. **The mechanics live in one place only:
   `notion-structure.md` → *Resolving the page (`Log`, and the legacy `Feedback` name)*.** Follow
   it exactly. Two user-facing outcomes: if the page was renamed, **tell the user in one line that
   `Feedback` is now called `Log`**; if **both** `Log` and `Feedback` exist, leave both alone, say
   so, and ask what they want done with the old one.
3. **Rebuild the `Catalog` page in full — a template car.** Maintenance line, identity facts, the
   **catalog source line**, the power/torque chart and the gearing-tool link, the
   `Catalog snapshot` toggle (built from the template with
   `python scripts/load_catalog.py car-templates/<slug>.yaml --snapshot`) — as **one replacement**
   of the page body. Don't read the old values to compare them; don't ask about anything; don't
   preserve edits. The page's own maintenance line says this will happen.
   **For a screenshot car there is no template to rebuild the catalog from**, so the catalog side
   of this step does not apply — go to step 4's screenshot-car bullet. One exception: a screenshot
   car that step 1 has just **migrated** off the old one-page layout has no `Catalog` page yet, so
   *Migration* step 5 builds it — identity facts, the catalog source line (`your screenshots`) and
   a snapshot from that car's `Parameters` rows. Migration builds the page once; a refresh of an
   already-migrated screenshot car leaves it alone.
4. **Write no `Parameters` rows.** A template car's catalog lives in the skill, so the `Catalog`
   page rebuild in step 3 **is** the refresh of its catalog — plus the `Setups` value columns
   check (*Procedure* step 7) and the `SHOW` re-assert in step 6 below. There is nothing to
   upsert.
   - **Legacy rows from an older skill version.** Earlier versions did write `Parameters` rows for
     bundled cars. They are never read and never deleted. **Say so once, in one line, whenever
     this car's `Catalog` page had no `Catalog source:` line** (step 0) — that missing line is
     exactly what says an older version onboarded it, so nothing has to be read to find out:
     *"This car still has `Parameters` rows from an older version of the skill. They aren't read
     any more — edits you make there, like a range or a `Discrete steps` cell, no longer have any
     effect. Delete them if you want a tidy table."* **Never query `Parameters` to check whether
     the rows are there**; the line is about what is no longer used either way. A car whose page
     already carried a source line gets no such line — it was onboarded by a version that never
     wrote those rows.
   - **Refreshing a screenshot car** (its `Catalog source:` line says `your screenshots`) — there
     is no template to refresh it from, so this whole path has nothing to do. If **no**
     `car-templates/` file matches the car, say so in one line — *"The {Car} was onboarded from
     your screenshots, so there's no template to refresh it from. Your `Parameters` rows are its
     catalog and they're untouched."* — and stop, apart from steps 1, 2 and 5 (the layout
     migration, the `Feedback` → `Log` rename, and creating a missing `Guidelines`/`Log`), which
     are about the car's pages rather than its catalog and still apply.
     If a template **does** now match the car, offer the switch in one line: refreshing from it
     makes this a template car, so its legal values come from the bundled file from then on — and
     say what happens to their rows: **nothing**, they stay in Notion, simply unread. **Only on
     the user's yes**, in which case run steps 3–6 as a template car. On a no, leave the car
     exactly as it is.
5. **Leave the content of `Guidelines` and `Log` completely alone.** Never read-modify-write,
   append to, or reformat either. Create whichever is missing (`Guidelines` with its seed stub,
   `Log` with its maintenance line and nothing else); otherwise don't touch their content. `Log`
   is **shared** — the user writes their own notes on it and the skill only ever appends a dated
   entry — and it holds history that can't be regenerated, so a refresh never rewrites it. The
   one exception is step 2's rename of a legacy `Feedback` page, which changes the page's
   **title** and, at most, adds the maintenance line.
6. **Re-assert the `Setups` view's column order** on the car's `Setups` page (`SKILL.md` →
   *Assert column order*).

**What a refresh never touches:** the content of the `Guidelines` page, the content of the `Log`
page, and `Setups` rows (append-only, as always).

**For a template car a refresh needs no screenshots and asks nothing at all** — the
template on disk is the source for the catalog, the facts, the power/torque chart and the
gearing-tool link, so **skip the "Use it?" prompt in *Procedure* step 1** and run straight
through. Report what it rebuilt in a line or two; if the car
was already current, say so rather than inventing work.

### Migration — old one-page car → four-page structure

Cars onboarded before the multi-page layout have a single `{Car}` page holding identity facts,
charts, an H2 `Setups` section with the linked view, an H2 `Guidelines` section, possibly a
"Driving feedback log" toggle, and the `Catalog snapshot` toggle. A refresh migrates it in place. **The user's writing is the only thing
that can't be regenerated, so it is the only thing handled carefully:**

1. **Fetch the old `{Car}` page** and extract the body of its **`Guidelines`** section verbatim —
   everything under that H2, exactly as written.
2. **Create the four child pages** under `{Car}`: `Guidelines`, `Catalog`, `Log`, `Setups`.
3. **Move the user's text into the new `Guidelines` page**, verbatim. If the old section held
   nothing but the seeded stub (or is empty), seed the new page with the stub instead. **Never
   summarize, reformat, or "improve" it in transit** — copy it.
4. **Move any existing driving-feedback record onto `Log`**, verbatim — older car pages kept
   a collapsed **"Driving feedback log"** toggle. Carry its dated entries across unchanged; like
   `Guidelines` text, this is history that can't be regenerated. If there is none, leave the new
   page with nothing but its maintenance line.
5. **Build `Catalog` and `Setups` from scratch** from whichever source the car's catalog comes
   from — the bundled template, or its `Parameters` rows for a screenshot car. Nothing is carried
   over from the old page: identity facts, the catalog source line, the power/torque chart, the
   gearing-tool link and the snapshot are
   all regenerated, and the linked view is recreated on the `Setups` page. **This is the one place
   a screenshot car's `Catalog` page is built during a refresh** (the old layout had none); the
   refresh's own step 3 doesn't apply to it. If the car's rows can't be read (no egress, no
   token), still create the page with its maintenance line, identity facts and source line, and
   say the snapshot needs a later `refresh-catalog-snapshot.md` run.
6. **Clear the old `{Car}` page body** so the umbrella page is empty and only the four children
   remain. **Don't delete the `{Car}` page itself** — it keeps its identity, its URL, and any
   links the user has to it.
7. **Say what happened** in the report: that the car moved to the four-page layout, and explicitly
   what was carried across — their `Guidelines` text and any old driving-feedback entries, which
   now live on `Log` (or that there was none of either).

**If anything about the migration is ambiguous — two `Guidelines`-looking sections, an unfamiliar
page layout, content that doesn't fit any of the three buckets — stop and ask** rather than
guessing. Regenerating the skill's own data is free; losing the user's notes is not.

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

  **Not this workflow:** photos showing a single set of **current values** (no min/max pass), with a
  name to save them under, are a *setup* to store, not a catalog — go to
  [capture-setup.md](capture-setup.md).
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
   `car-templates/` for a YAML file whose `car:` field matches the user-provided car name, by
   the rule below.

   **Matching a car name — the skill's single name-matching rule.** Every other file points
   here rather than restating it: a bundled template, a `car-troubleshooting/` file, a `{Car}`
   page name, a save file's car string, and the script's own template matching all use it.

   - **Normalise both names** the same way: lowercase them, turn every punctuation character
     (hyphen, apostrophe, dot, underscore, …) into a space, and collapse runs of spaces into
     one. Letters keep their accents. So `Lancia-Stratos HF` and `lancia stratos hf` normalise
     alike, and the file `lancia-stratos.yaml` normalises to `lancia stratos`.
   - **A given name matches a template when every token of the given name appears in the
     template's normalised `car:`.** The template's `car:` may carry extra tokens the user
     didn't type — a year, a trim — so *"Lancia Stratos"* and *"lancia stratos hf"* both match
     `car: "Lancia Stratos HF 1976"` in `lancia-stratos.yaml`.
   - **Exactly one template must qualify.** If two or more do (e.g. *"Peugeot"* against the
     206, the 208 and the 306), **ask the user which car they mean** — never pick one. If none
     does, there is no bundled template for this car.

   Matching a Notion `Car` value to a template's `car:` inside the tooling is the stricter
   case of the same rule: **exact equality of the two normalised names**, which is what
   `scripts/query_notion_parameters.py` applies when it drops a template car's legacy rows
   (`notion-structure.md` → *Applying the order*).

   - **Match found:** Notify the user:
     > "Found a bundled parameter template for {Car}. It includes all parameters with
     > Min/Max ranges and Discrete steps pre-filled — no screenshots needed. Use it?
     > (Yes / No — I'd rather use my own screenshots)"

     **On a refresh of an already-onboarded car, don't ask** — take the template and say so
     (*Refreshing an already-onboarded car*, above).

     **Unless the user asked for screenshots.** A request that names them — *"onboard the {car}
     from my screenshots"*, *"re-onboard the {car} from screenshots"* — skips this prompt in the
     other direction: **don't offer the template, go straight to the screenshot path below**,
     even for a car that is a template car today. Its catalog goes into the `Parameters` DB, its
     catalog source line is rewritten to `your screenshots` in step 7, and it stays a screenshot
     car until the user asks to refresh it from the template. Any `Setups` columns the template
     created stay as they are — onboarding never removes a column.

     - **User confirms (Yes):** Load every row from the template with
       `python scripts/load_catalog.py car-templates/<slug>.yaml`. Each entry becomes a catalog
       row in the usual shape (`Section`, `Adjustment`, `Min`, `Max`, `Unit`, `Discrete steps`,
       `Order` from the template's `order:`), and an entry carrying the optional **`surface`**
       field (`Tarmac`/`Gravel`/`Snow`) is that surface's row while entries without one are
       baseline rows.

       **This car is now a template car, and its catalog stays in the skill: no `Parameters` rows
       are written for it, on a first onboard or a refresh** (`notion-structure.md` → *Where a
       car's catalog lives*). The rows you loaded here are used **in this run** — to create the
       `Setups` value columns, to order them, and to build the `Catalog snapshot` — and are read
       from the file again on every later run with `scripts/load_catalog.py`.

       **No gravel pass for a template car — ever.** Skip step 8 outright: the templates come from
       the game files, which carry whatever surface-specific ranges the car has, so there is
       nothing for the user to check.

       Skip steps 2–4 (screenshot capture, extraction, confirmation table) and proceed to step 5
       (identity facts) → step 6 (Notion structure) → step 7 (write to Notion).
       Its `Discrete steps` come from the game files and are complete as shipped — don't ask the
       user to enumerate anything, and don't offer to edit them (there is no row to edit).
       The `drivetrain` field in the template sets the car's drivetrain. If the template carries
       the optional `engine_layout`, `weight_bias`, `weight`, `max_power`, `max_torque`, `class`,
       `gearbox`, or `steering_lock` fields, use them directly for the car identity facts in step 5
       — no lookup needed (see the determination step below). For any identity field the template
       **lacks**, still work step 5's ladder: an older template may predate several of these fields,
       and a car information screenshot (if the user has one) fills them in a single shot.
       If the template carries `power_torque_chart:` / `engine_curve:` / `gearing_tool:`
       (extracted from the game files, so no ladder applies), the chart and the gearing-tool link
       go on the car's `Catalog` page in step 7 and the curve is available to every later gearing
       decision. An
       optional `save_ids` field (the exact in-save car string, used only by save-file import to
       match the car) needs no action here — it doesn't affect the screenshot/template catalog;
       carry it through untouched.
     - **User declines (No):** Fall through to the screenshot path below. **The car then becomes
       a screenshot car** — its catalog goes into the `Parameters` DB as usual and its catalog
       source line says `your screenshots`. It stays a screenshot car until the user asks to
       refresh it from the template (*Refreshing an already-onboarded car*, above).

   - **No match:** Proceed to the screenshot path below (no announcement needed).

   Two source paths:
   - **Bundled template** (path above) — `Min`/`Max` **and** `Discrete steps` are already filled.
     The file stays the catalog; **nothing goes into the `Parameters` DB**.
   - **Screenshots** (the path below) — extract `Min`/`Max` from the two setup-screen
     passes, and write one `Parameters` row per parameter. For `—` named-selection params, seed `Discrete steps` with the option names the
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
   **Ask for the game version here too, once:** *"Which game version are you on? It goes on the
   car's `Catalog` page so a later reader knows how old these ranges are — 'don't know' is
   fine."* Write the answer (or the literal `unknown`) into the catalog source line in step 7
   (`notion-structure.md` → *Car page*). Ask it only on this screenshot path; a template carries
   its own version.

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
   tunable parameters** — every one of them is stored on the car's `Catalog` page (step 7),
   never in
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
   `notion-structure.md`). Then ensure the `{Car}` page exists with its four child pages, the
   filtered `Setups` view living on its `Setups` page. **A screenshot car's `Parameters` view is
   not inlined anywhere** — it is reached through the Notion sidebar / linked DB
   (`notion-structure.md` → *Car page*).

7. **Write to Notion** (via the user's Notion connection):
   - **Screenshot path only — upsert the `Parameters` rows.** A template car writes **no rows
     here**: its catalog is the file on disk (`notion-structure.md` → *Where a car's catalog
     lives*), so skip this whole bullet and start at the `Setups` value properties below. On the
     screenshot path:
     Upsert one row per `Car × Adjustment` into the `Parameters` DB (match on `Car` +
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
     quick / low-effort run)** (`notion-structure.md` → *Applying the order*, case 3): get the
     main table's `SHOW` list from **one** call and set the main `Setups` table view's `SHOW` to
     it — one `--from-template car-templates/<slug>.yaml` per **onboarded template car**, plus
     `<params_data_source_id> <token> --all` in the **same** call only when at least one
     screenshot car exists:
     `python scripts/query_notion_parameters.py --show-order --from-template <c1>.yaml --from-template <c2>.yaml …`.
     The main table spans every car, so leaving a template car out of that call hides its value
     columns.
     Creation order does **not** drive the rendered table — the view's `SHOW` directive does.
   - **Build the car's four pages** (`notion-structure.md` → *Car page*). The `{Car}` page itself
     is an **umbrella with an empty body** — everything below hangs off it as a child page. **Each
     of the four opens with its one-line maintenance note**, verbatim from the table in
     `notion-structure.md` → *Car page*. On a
     refresh of a car still on the old one-page layout, migrate it first
     (*Refreshing an already-onboarded car* → *Migration*, above).

     1. **`Guidelines`** — create it if missing, with its maintenance line and a short stub
        inviting car-specific tuning preferences (tone per `tuning-guidelines-template.md`). **If it already exists, do
        nothing at all to it.** The skill never writes here again.
     2. **`Catalog`** — write the whole page body in **one update**, in this order:
        1. its **maintenance line** (exact wording in `notion-structure.md` → *Car page*);
        2. the **nine identity facts** resolved in step 5 — `Drivetrain`, `Engine layout`,
           `Weight bias`, `Weight`, `Max power`, `Max torque`, `Class`, `Gearbox`,
           `Steering lock`, writing the literal `couldn't determine` for any the ladder didn't
           resolve. Never as `Parameters` rows;
        3. the **catalog source line**, in the exact format for this car's kind
           (`notion-structure.md` → *Car page*, item 2): for a template car
           `**Catalog source:** bundled template — game version {template version}, from {game
           files | a community export}`; for a screenshot car
           `**Catalog source:** your screenshots — game version {the version the user gave in
           step 2, or `unknown`}`. Every later run reads this line to decide where the car's
           catalog comes from, so it is not optional;
        4. **the power/torque chart, then the gearing-tool link** — the chart (when the template
           carries `power_torque_chart:`) via `notion-create-attachment` on its `source_url` then
           an image block; the link (when the template carries `gearing_tool:`) as the plain
           paragraph line `Gearing tool: <link>` (`notion-structure.md` → *Engine chart and
           gearing tool*, which carries the fallback and the exact link wording). A field the
           template doesn't have is simply absent: skip that block, never invent one or borrow
           another car's;
        5. the **`Catalog snapshot` toggle** last — the car's full catalog as YAML
           (`notion-structure.md` → *Catalog snapshot*). Build it from what this run already
           holds — no read-back: on the template path run
           `python scripts/load_catalog.py car-templates/<slug>.yaml --snapshot` and paste its
           output; on the screenshot path build it from the rows just written. For a screenshot
           car it is what keeps reads working with no network egress (Claude's Free plan); for a
           template car it is a readable copy for the user, since the skill reads the file on
           disk. Either way the write isn't finished without it.

        **On a refresh this page is replaced wholesale** — one write, no reading the old body, no
        comparing, no asking. That is the entire point of the split.
     3. **`Log`** — create it with its maintenance line if missing, and **otherwise leave its
        content alone**. Resolve it per `notion-structure.md` → *Resolving the page (`Log`, and
        the legacy `Feedback` name)*: a car onboarded by an older version has this page under the
        name `Feedback`, and it is **renamed in place**, never recreated. The page is **shared** —
        the user writes their own notes anywhere on it, and driving interviews add dated entries
        at the top later (`driving-feedback-interview.md` → *Recording the outcome*). It is
        **add-only** for the skill and a refresh never rewrites it.
     4. **`Setups`** — its maintenance line, then the `Setups[Car=this]` filtered linked view. Create it
        with `notion-create-view` (never a `<linked-view />`-style placeholder): `parent_page_id`
        = the `Setups` child page, `data_source_id` = the `Setups` data source (`notion-fetch` it
        for the id), `type: "table"`, and
        `configure: 'FILTER "Car" = "{Car}"; SHOW <the script's SHOW list for this car>'` (get it
        from the bundled script, per `notion-structure.md` → *Applying the order*: case 1,
        `python scripts/query_notion_parameters.py --show-order --from-template car-templates/<slug>.yaml`,
        for a template car — no token; case 2,
        `python scripts/query_notion_parameters.py <params_data_source_id> <token> "{Car}" --show-order`,
        for a screenshot car).
        `SHOW` orders the columns **and** hides blank ones in one step. If the view already
        exists, re-assert it with `notion-update-view` rather than appending a duplicate.

8. **Check for surface-specific ranges (optional gravel pass) — screenshot path only.**

   **Never run this for a template car.** All the templates come from the game files, which
   already carry each car's surface-specific ranges, so there is nothing to compare and nothing
   to ask. Skip straight to step 9.

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
     5. **Refresh the `Catalog snapshot`** on the car's `Catalog` page so the new `Gravel` rows
        are in it
        (`notion-structure.md` → *Catalog snapshot*) — the catalog write isn't finished until the
        snapshot matches the rows.

9. **Report.** What the run wrote, and the car's identity facts as written to the car's
   `Catalog` page —
   all nine (`Drivetrain` / `Engine layout` / `Weight bias` / `Weight` / `Max power` /
   `Max torque` / `Class` / `Gearbox` / `Steering lock`), **each with the rung it came from**
   (info screen / template / model knowledge / web / you), so the user can see what was read off
   the game and what was inferred. Call out any stored as `couldn't determine` for the user to fill
   in, and any template-vs-screenshot discrepancy. Say whether the **power/torque chart** went on
   the page (skipped only when the template has none — e.g. the Peugeot 206 WRC) and that the
   **gearing-tool link** was added, and if the power/torque curve's peaks disagree with the
   `Max power` / `Max torque` facts, show both figures and explain which is which
   (`notion-structure.md` → *Engine chart and gearing tool*). Then: any **surface-specific `Gravel` rows**
   created (list which parameters differ from the tarmac baseline), and anything flagged uncertain.
   **If no car information screenshot was attached**, mention once that one shot of the in-game car
   info screen would have settled most of these — useful next time, not worth redoing now.
   **For a template car, report it as a template onboard:** *"Catalog: bundled template, game
   version {version} ({game files | a community export}) — it lives in the skill, so nothing was
   written to your `Parameters` table for this car."* Then the `Setups` value columns added. Say
   the `Parameters` part plainly: a user who opens that table and finds no rows for the car should
   already know why. **Everything below this line — the `Discrete steps` offer and the three
   groups of parameters needing user action — is screenshot path only.** A template car's steps
   come from the game files; there is no Notion row to fill in and nothing to enumerate, so don't
   offer it and don't flag anything for enumeration.

   **Tell the user about `Discrete steps`, and offer to take them now.** Any parameter can be
   pinned to an exact set of values (e.g. spring stiffness
   `42300, 50000, 57700, 65400, 73100`, or gear set `1, 2, 3`). Two ways, and **offer the first
   one** when the report flags any parameter below:
   - **Give them here, in chat** — *"Read them off the in-game screen and paste them and I'll
     write them in."* You still hold every row you just created, so update those rows directly
     (one batched `notion-update-page` pass over the affected rows) **and rewrite the `Catalog
     snapshot` from the updated rows** in the same breath. No row lookup, no re-onboarding, and
     the car leaves this run complete. This is the **only** moment the values can be written
     without a row query, so it is the recommended route on **any** plan and the *only*
     self-service one where the sandbox has no network egress (Claude's Free plan — see
     `notion-rest-read.md`).
   - **Fill the cells in Notion later** — always available, and the right call if they need to
     go look at the game first. **On a plan without egress, tell them the follow-up**: those
     edits live only in the rows, so the snapshot keeps serving the old values until they say
     *"refresh the catalog snapshot for this car"* (`refresh-catalog-snapshot.md`). On a plan
     with egress nothing is needed — reads go to the live rows.
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

10. **Offer to contribute the catalog as a community template — screenshot path only.**

    This car had **no bundled template** (that's why there were screenshots), so the catalog the
    user just built exists nowhere but their Notion. They're the only person who can give it to the
    next driver of this car — but they'd have to know the export workflow exists to ask for it, so
    **offer it here** rather than waiting.

    **Only offer when all of these hold:**
    - The catalog came from **screenshots**, not a bundled template. (A template-onboarded car has
      nothing new to contribute — it came from `car-templates/` already.)
    - **No** `car-templates/` file matched this car in step 1. If one matched and the user
      *declined* it in favour of their own screenshots, don't offer — a template already exists;
      instead mention in one line that their capture may be worth contributing if the bundled one
      looks out of date for their game version, and leave it there.
    - The write in step 7 **succeeded**.

    **Mind the gaps first.** A template whose `discrete_steps` are empty is unusable to whoever
    imports it, and step 9 has just listed exactly those gaps (`—` rows still needing enumeration,
    flagged numerics). So:
    - **Gaps outstanding** → don't push an export now. Close the report with one line: once those
      cells are filled in Notion, they can say *"contribute my car"* and it'll be turned into a
      shareable template. Don't repeat it or ask again.
    - **No gaps** → make the offer directly.

    **Don't restate the invitation here** — the wording, the GitHub hand-off and the
    filename-prefilled link are authored in `export-car-template.md` → *Offer to share it with the
    community*. On a yes, run `export-car-template.md` from the top — its **Game version** input is
    the version this run just wrote into the catalog source line, so don't ask for it again. **You already hold every row from this run: don't re-fetch
    the car's `Parameters` from Notion** (`SKILL.md` → *Read efficiently*); pick that workflow up at
    its completeness check with the rows in hand — **unless the user has edited Notion since the
    step 7 write** (typically filling the `Discrete steps` this report asked for). Those edits live
    only in Notion, so in that case re-read the car's rows first (`export-car-template.md` step 1 and
    its *Exception*) — an export missing the user's `Discrete steps` is useless to whoever imports it.

    **Never pressure, and never gate anything on it.** A "no" (or no answer) ends the topic —
    onboarding is already complete either way.

## When the template may be stale

A bundled template is a snapshot of the game files at the version in its `version:` field. The
game moves; the template follows on the next skill release. **This never stops a run** — read
this section from `build-setup.md`, `capture-setup.md`, `import-savegame.md` and
`tweak-setup.md` whenever either trigger fires.

**Triggers** (either one is enough):

- **(a) A newer game version.** The run learns the user's game version — a save file's
  `game_versions`, the user saying it, a car info screenshot showing it — and its **major.minor**
  (the first two dotted parts, e.g. `0.7.1.123` → `0.7`) is **newer** than the template's
  `version:`.
- **(b) A value outside the template.** A value the user captured, imported or dictated for a
  template car is outside the template's `Min..Max`, or is not one of its `Discrete steps`.

**Response — one line, then carry on:**

> "The bundled {Car} template is from game version {v}; your game is {v2} — so the template may be
> out of date. I'll continue with it."

or, for trigger (b):

> "The bundled {Car} template is from game version {v} and this value is outside its range — so
> the template may be out of date. I'll continue with it."

Then **continue best-effort, with every normal rule intact**:

- validation still uses the template — it is the only catalog this car has;
- a **captured or imported value outside the range is written as read and flagged**, never clamped
  and never dropped (`capture-setup.md` step 4; `import-savegame.md` 5.4);
- a **build still snaps to the template's** steps and ranges.

**Offer the way out once, at the end of the run**, never in the middle and never twice: the user
can re-onboard the car from their own min/max screenshots, which turns it into a screenshot car
whose catalog they own. **Give them the exact words**, because a bare "re-onboard" is a template
refresh and would take the same template again:

> "If you'd rather own this car's ranges yourself, say **"re-onboard the {Car} from my
> screenshots"** and I'll capture them from your min/max setup screens instead."

That request takes the screenshot path (*Trigger phrases* → *Re-onboarding an already-onboarded
car from screenshots*). It is an offer, never a requirement — a "no" or no answer ends it and the
run's result stands.

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
- Never ask for click counts or interpolate. **On the screenshot path**, for **numeric** params
  `Discrete steps` is **optional and user-owned** — onboarding never fabricates or infers it, and
  the write in step 7 leaves it blank. (On the template path the steps come from the game files
  and there is no Notion row at all, so none of this applies.) Step 9 may *offer* to record values the user reads off the game and dictates
  in chat; that's the user filling their own cell through a convenient channel, not the skill
  deriving one, and a "no thanks" leaves the cell blank as before. For **`—` named-selection**
  params onboarding seeds it with the option names the screenshots show (observed values only,
  never fabricated) plus the standard ACR lists for `Tyre Type`/brake pads; the user completes
  it.
- **Never use existing Notion content as parameter input.** The `{Car}` page is a write
  destination. Any tables or notes already on it are the user's own work — do not read,
  compare, or defer to them during extraction. Screenshots (or a bundled profile) are the only
  valid sources.
