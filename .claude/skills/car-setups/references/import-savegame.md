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
`{ok, setup_count, recognized_fraction, game_versions, save_format, nul_count, handler_used,
notes, setups[]}`. Each setup has `name, car, track, surface, game_version, drivetrain`
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

Then, depending on whether the car has a `Parameters` catalog:

- **Onboarded car (catalog present).** Load the car's Notion `Parameters` catalog **via
  [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows reliably). It is the
  source of truth for column names: match each parsed `key`/`label` to that car's `Adjustment`
  (the raw keys are descriptive, e.g. `Suspensions.Front.AdjusterRing` → "Adjuster ring" in section
  "Suspensions — Front"). **Flag any key you can't confidently map** to the user rather than
  dropping it. **Validate each value against the catalog row resolved for that setup's surface** —
  map the parsed `surface` to the catalog's `Tarmac`/`Gravel`/`Snow` (asphalt → Tarmac; dirt/mud →
  Gravel; ice → Snow; anything else → baseline), then use the surface-specific row if the parameter
  has one; for `Snow`, fall back to a `Gravel` row before the baseline (see
  [notion-rest-read.md](notion-rest-read.md)). The value should fall within that row's `Min..Max`,
  or be a member of its `Discrete steps` when filled; **flag mismatches** rather than dropping them
  (a save value outside the catalog usually means the catalog is incomplete, not that the value is
  wrong). **`TyreType` values must be written fully-qualified** (e.g. `Tarmac Snow`,
  `Snow (Studs)`) — if the save or catalog holds an ambiguous legacy name (bare `Snow`, `Gravel`,
  `Dry Tarmac`), map it to its canonical ACR name before writing; if it can't be disambiguated
  confidently, flag it for the user instead of guessing.

- **Un-onboarded car (no catalog) — do not block.** Import anyway. Create the `Setups` **value
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
- `Name`, `Car`, `Surface`, `Game version`, `Date`, `Source = imported`;
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
rebuild.

### 6. Report (Notion path)
Which handler/version was used (or that the AI fallback was used), setups imported and which car
each landed under, anything flagged outside a catalog or un-mappable, and — for any un-onboarded
car — that its columns were created raw/unvalidated with the onboarding suggestion. Remind the user
that imported setups start **unrated** and **unchecked** — they can **rate each `1`–`5`** and tick
`Learn from this` once they've vetted it.

### 7. Chat-table output (no-Notion path)
For each selected **car**, print a short header line — `{Car}` and the distinct game version(s) —
then a **wide markdown table** comparing that car's selected setups:
- first column = **parameter label** (in the parser's emitted order; you may add `Section`
  sub-headers from the key prefix for readability),
- one column per selected setup, header = `{setup name} · {surface}`,
- cells = the parsed `value`.

Below the table, list any parser `warnings` (e.g. symmetric-corner mismatches) for that car. Remind
the user these are **raw in-game values** (not range-validated, no reasoning attached), and that
connecting Notion later lets them save, build, tweak, and review setups. Do **not** write anything
to Notion in this path.

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
- When Python parsing returns 0 setups, **always** fall back to AI extraction and tell the user.
