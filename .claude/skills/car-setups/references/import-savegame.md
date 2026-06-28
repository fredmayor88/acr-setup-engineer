# Workflow: import existing setups from a save file

Recover the setups the user already made in-game from their save file. Import is a **standalone
recovery feature**: it works **with or without a Notion connection**, and **whether or not the car
is onboarded**. When Notion is available the setups are appended to the `Setups` database (rows
with `Source = imported`); when it isn't, they're printed as a copy-pasteable table in chat.

**ACR-only.** The bundled parser reads ACR's UE5 GVAS save (`CarSetupsDataSaveSlot.sav`). Save-file
import is **not supported for other games** — don't attempt to parse a non-ACR save. For another
game, tell the user to onboard the car via screenshots (`onboard-car.md`) and build setups instead.

## Inputs
- An ACR save file, **attached in the chat** — `CarSetupsDataSaveSlot.sav` (on Windows it lives
  at `%LOCALAPPDATA%\acr\Saved\SaveGames\CarSetupsDataSaveSlot.sav`).
- **Car(s)** (usually inferable from the save) and **game** (`ACR`).
- A Notion connection is **optional** (see step 4).

## Procedure

### 1. Run the bundled parser
Run on the attached file via code execution: `python scripts/parse_acr_save.py <file> --pretty`
(human summary) or without `--pretty` for JSON. It returns
`{ok, setup_count, game_versions, save_format, nul_count, handler_used, notes, setups[]}`. Each
setup has `name, car, track, surface, game_version, drivetrain`
(FWD/RWD/AWD, from the diff sections), `warnings`, and `params: [{key, label, value}]` where `key`
is the raw game key (e.g. `Suspensions.Front.AdjusterRing`) with symmetric left/right already
collapsed, `(Key:Value)` wrappers stripped, and decimals tidied. The parser is **schema-agnostic** —
it captures *every* parameter, including ones it has no label for (those still come through with a
humanized `label`).

The parser is **version-aware**: it fingerprints the save format (`save_format`: GVAS engine /
custom versions), reads the per-setup game version(s) (`game_versions`), and dispatches to a
handler from a small registry (`handler_used`). Today there are two deterministic handlers —
`parse_structural` (strict reads; v0.4 and any same-format build) and `parse_nul_tolerant` (for
saves delivered without NUL terminators, seen on v0.2/v0.3 samples).

### 2. Branch on the result, and tell the user what happened
- **`ok: true`, `handler_used = parse_structural`** → continue to step 3.
- **`ok: true`, `handler_used = parse_nul_tolerant`** → continue, but **tell the user the save
  arrived without NUL terminators and was recovered** with the tolerant reader. Parameter values
  and multi-word names are recovered intact; however older saves don't always store a **surface**
  per setup, so a setup's `surface` may come back blank — ask the user to supply it in the approval
  step (it affects range resolution for onboarded cars). If they can re-export a clean save the
  strict path is tidier, but recovery is fine.
- **`ok: true` but a `game_versions` entry is outside the tested set** (the parser adds a
  `not in the tested set` note — e.g. a future `0.5.*`) → continue, but **flag that the version
  isn't explicitly validated** and ask the user to sanity-check the values before writing.
- **`ok: false`** (every Python handler found no setups / very few — the body format genuinely
  differs, e.g. a future build that re-serializes) → **fall back to AI extraction**. This is a hard
  rule: import never dead-ends just because Python parsing returned nothing. **Notify the user
  explicitly**: say the deterministic parser couldn't read the file (mention `handler_used` tried,
  the detected `save_format`/`game_versions`), that you're now reading the bytes directly yourself,
  and — when done — that this was an AI-assisted read to sanity-check. Read the bytes in code
  execution using the **Save format clues** below, reconstruct the same `setups[]` shape, and
  suggest the user share the save so a version-specific handler can be added to
  `scripts/parse_acr_save.py`. **Don't write anything you can't read confidently.**

### 3. Pick which setups to import
If the parsed setups span **more than one car, or more than one setup**, list them grouped by car
(name · track · surface · game version) and **ask the user whether to import all of them, only
specific cars, or only specific setups.** Carry only the selected subset through the rest of the
workflow. (A single setup → skip the prompt.) Show any `warnings` so the user can weigh them.

Then, for the selected subset, **show the full parsed values for approval** using the
**copy-pasteable convention** below — this is the user's confirmation before anything is written to
Notion (Rules: always get approval before writing), and it doubles as the final output for the
no-Notion path (step 7).

### Presenting setups in chat (copy-pasteable)
Whenever you print a setup's **parameter values** — for the approval step above, or as the
no-Notion output in step 7 — put them in a **fenced code block, one per car**. Never present
values as a rendered (pipe-syntax) markdown table outside a code block — those don't
select/copy cleanly. Inside each car's block:
- a header line: `{Car} — {distinct game version(s)}`;
- an aligned **monospace table**: first column = parameter label (parser's emitted order; you may
  add `[Section]` sub-headers from the key prefix for readability, per `share-setup.md`), then one
  column per selected setup of that car (column header = setup name, plus `· {surface}` when
  known); pad every column so values line up.

List any parser `warnings` for that car **below** the block (outside the fences), not inside it.

### 4. Notion available, or chat-only?
Try to resolve the **`Car setups`** root via the Notion connector (per `notion-structure.md`).
- **Connector available** → continue to step 5 (write to Notion).
- **No Notion connection** (connector not configured / calls fail) → present a **choice**:
  1. **Set up Notion now** — walk the user through connecting Notion (claude.ai → Settings →
     Connectors → add Notion; see `README.md` setup steps) so their setups are saved and they get
     the full build/tweak/review experience. Once connected, continue to step 5; the structure is
     created on first write (`notion-structure.md` create-if-missing).
  2. **Just show them in chat** — skip Notion entirely and go to the **chat-table output**
     (step 7). Mention they can re-run the import later once Notion is set up.

### 5. Write to Notion — onboarding is optional
Read `notion-structure.md` before writing. Per selected car:

**Ensure the structure exists** (per `notion-structure.md`): the `Car setups` root → `{Game}` page
→ the `Parameters`/`Setups` DBs → the `{Car}` page. Set the car page's **`Drivetrain`** from the
parser's `drivetrain` field (derived deterministically from the diff sections) if not already set.

**Ensure the `{Car}` page has its Setups view** (this is what makes imported rows show up on the
car page — without it the rows exist only in the main `Setups` table). Seed the page body the
**same way onboarding does** (`onboard-car.md` step 7, sub-steps 1–3): H2 "Setups" heading → the
`Setups[Car=this]` filtered linked view → H2 "Guidelines" stub. The linked view is **not** page
markdown — create it with `notion-create-view` per `notion-structure.md` → *Creating an inline
linked view*, which is **idempotent**: `notion-fetch` the page first; if a `Setups` linked view
already exists, re-assert it (don't append a duplicate); if it's missing, create it. This applies
to **every** car you import into — onboarded or not (an un-onboarded car still gets a car page
with a Setups view; only its Guidelines stub / identity facts are sparse).

Then, depending on whether the car has a `Parameters` catalog:

- **No catalog yet, but a bundled template matches this car → onboard it first.** Before treating
  the car as un-onboarded, look in `car-templates/` for a file whose `car:` matches the parsed car
  name — **same match rule as `onboard-car.md` step 1** (case-insensitive; ignore punctuation,
  hyphens, apostrophes). If one matches, **auto-onboard the car from that template** by running
  `onboard-car.md`'s bundled-template path: load every template row into the `Parameters` catalog
  (with `Order` / `Discrete steps` / `Surface`), set the car's `Drivetrain` and identity facts
  (`Engine layout` / `Weight bias` / `Weight`) from the template, and seed the `{Car}` page body
  (the H2 "Setups" → linked view → H2 "Guidelines" sequence above). **Don't** show onboarding's
  interactive "Use this template? (Yes/No)" prompt — instead fold it into this import's existing
  approval (step 3): tell the user *"{Car} isn't onboarded yet but a bundled template exists — I'll
  onboard it from the template and import these N setups,"* and proceed on the same OK. If the
  parser's `drivetrain` disagrees with the template's, **prefer the template** (it's the curated
  catalog) and note the discrepancy. **Skip onboarding's optional gravel pass** (`onboard-car.md`
  step 8) — an import has no screenshots to compare, so use the template's rows as-is (templates
  that ship `Surface` rows already cover gravel). After onboarding, the car **has a catalog** —
  proceed as the onboarded-car case below.

- **Onboarded car (catalog present).** Load the car's Notion `Parameters` catalog **via
  [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows reliably). It is the
  source of truth for column names: match each parsed `key`/`label` to that car's `Adjustment`
  (the raw keys are descriptive, e.g. `Suspensions.Front.AdjusterRing` → "Adjuster ring" in section
  "Suspensions — Front"). **Flag any key you can't confidently map** to the user rather than
  dropping it. **Do not range-enforce the values** — a save is usually from an **older game
  version**, so a value outside the current catalog is expected and legitimate, not an error.
  Resolve the surface row only to pick the right column: map the parsed `surface` to the catalog's
  `Tarmac`/`Gravel`/`Snow` (asphalt → Tarmac; dirt/mud → Gravel; ice → Snow; anything else →
  baseline), then use the surface-specific row if the parameter has one; for `Snow`, fall back to a
  `Gravel` row before the baseline (see [notion-rest-read.md](notion-rest-read.md)). **Write every
  value exactly as the save had it — never clamp it to the range or drop it.** When a value falls
  outside its resolved row's `Min..Max` (or isn't in its `Discrete steps` when filled), don't flag
  it one-by-one; instead **collect them all into one short, non-blocking note** for the report
  (step 6), framed as a likely version difference — e.g. *"2 values are outside the current catalog
  range, written as-is (likely an older game version): Spring Stiffness Front 41000 (catalog
  42300–73100); Rear ARB 9 (catalog 1–8)."* (This is informational, not something the user must
  fix.) **`TyreType` values must be written fully-qualified** (e.g. `Tarmac Snow`,
  `Snow (Studs)`) — if the save or catalog holds an ambiguous legacy name (bare `Snow`, `Gravel`,
  `Dry Tarmac`), map it to its canonical ACR name before writing; if it can't be disambiguated
  confidently, flag it for the user instead of guessing.

- **Un-onboarded car — no catalog *and* no matching template — do not block.** (Only reach this
  case after the template check above found nothing.) Import anyway. Create the `Setups` **value
  columns directly from the parsed keys** — use each param's humanized `label` as the column name,
  typed **Number** when the value is numeric and **Select** otherwise. Write the values **as-is,
  unvalidated** (there's no catalog to range-check against). In the report (step 6) state plainly
  that columns were created from the save and **ranges were not validated**, and **suggest
  onboarding** the car (screenshots or a bundled template, `onboard-car.md`) so values get
  validated and the full build/tweak/review experience is unlocked. Don't fabricate ranges or a
  `Parameters` catalog here — onboarding owns that.

**In both cases**, parsed names come from the in-game field and are already **≤15 chars**; if one
somehow exceeds it, compact it before writing (per `SKILL.md` core rules). Then add one new
`Setups` row per setup:
- `Name`, `Car`, `Surface`, `Game version`, `Date`, `Source = imported`. Write `Car` as the
  **exact same `Car` Select value** the car page's linked view filters on (`FILTER "Car" =
  "{Car}"`), via create-or-reuse — a casing or spacing mismatch would make the rows vanish from the
  per-car view even though they're in the table;
- `Location`/`Stage` if a `track` maps to one in the `Locations` catalogue, else leave both blank —
  **never fabricate a stage facts page** from an import;
- **`Skill version`** (per `SKILL.md` → *Skill version* — written for imported rows too, since it
  identifies the import logic that produced the row, unlike `Model/effort` which stays blank here);
- **`Learn from this` = unchecked** (imported setups carry raw numbers without driving-intent
  context — the user checks it after deciding a setup is worth learning from);
- plus the mapped (onboarded) or raw (un-onboarded) value properties.

Record values **as-is** (don't snap — they were already accepted in-game). **Never modify or delete
existing rows.** After appending, **apply the column order** (`notion-structure.md` → *Applying the
order*): set the `SHOW` on the main `Setups` table view and the car's linked view to `Name`, then
value columns (by each parameter's `Order` when the catalog has it; otherwise in the parser's
emitted order for raw columns), then the remaining meta columns — an idempotent view update, not a
rebuild. This step **re-asserts `SHOW` on views that already exist**, so the car's linked Setups
view must have been created earlier in this step (see *Ensure the `{Car}` page has its Setups
view* above) — applying the order does **not** create a missing view.

### 6. Report (Notion path)
Cover, in order:
- which handler/version was used (or that the AI fallback was used);
- the setups imported and which car each landed under;
- for any car you **auto-onboarded from a bundled template**, say so (the catalog/columns came
  from the template, not screenshots);
- any **un-mappable keys** you couldn't confidently match to a column (these are still flagged for
  the user);
- **out-of-range values as a single informational note** — *"written as-is, likely an older game
  version"* (see the onboarded-car branch in step 5). This is **not** a warning and **not**
  something the user must fix;
- for an **un-onboarded car with no template** (raw-columns path), that its columns were created
  raw/unvalidated, with the suggestion to onboard it (screenshots or a template) for the full
  build/tweak/review experience.

Remind the user that imported setups start **unrated** and **unchecked** — they can **rate each
`1`–`5`** and tick `Learn from this` once they've vetted it.

### 7. Chat-table output (no-Notion path)
Present the selected setups using the **copy-pasteable convention** above (one fenced code block
per car). Remind the user these are **raw in-game values** (not range-validated, no reasoning
attached), and that connecting Notion later lets them save, build, tweak, and review setups. Do
**not** write anything to Notion in this path.

## Save format clues (for the AI fallback)
- The file is an **Unreal Engine 5 GVAS** save (`/Script/dmengine.SaveGameSlot` ·
  `CarSetupsSaveGameData`). After the GVAS header it uses a custom body.
- Strings are **FString**: `int32 length` + that many bytes + a trailing `NUL` (length is
  negative for UTF-16). **Don't** read the file as text with NUL→space substitution — that
  corrupts length prefixes. (If a file *arrives* already NUL-stripped — `nul_count == 0`, every
  `0x00` is `0x20` — the deterministic `parse_nul_tolerant` handler already covers it; you only
  reach this AI fallback when **both** handlers fail.)
- Setups are stored as a sequence of `key → value` **string pairs**, e.g.
  `Suspensions.FrontLeft.AdjusterRing` → `0.087000`, `Differentials.Rear.LSDRamps` →
  `(LSDRampAngles:60_70)`. Keys are dotted identifiers; values are either numeric strings or
  `(Type:Value)` wrappers. Collapse symmetric `FrontLeft`/`FrontRight` & `RearLeft`/`RearRight`
  → Front/Rear (they should match). Per-setup metadata strings (name, version, car, track,
  surface) appear just before each block of pairs.

## Rules
- Append-only; never overwrite existing setups.
- Always get user approval of the parsed output before writing.
- Import works **without Notion** (chat table) and **without onboarding** (raw columns) — never
  block recovery on either.
- **Every car imported into Notion gets a `{Car}` page with a `Setups` linked view** — without it
  the rows don't show on the car page (create-if-missing, re-assert-if-present; step 5).
- **If the car isn't onboarded but a bundled template matches it, auto-onboard from the template
  first** (step 5), then import onto that catalog.
- **Never range-enforce imported values** — write them exactly as the save had them; report
  out-of-range values as a single informational note (likely an older game version), never an error.
- When Python parsing returns 0 setups, **always** fall back to AI extraction and tell the user.
