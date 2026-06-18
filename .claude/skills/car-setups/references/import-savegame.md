# Workflow: import existing setups from a save file

Import the setups the user already made in-game and append them to their Notion `Setups`
database as rows with `Source = imported`. Read `notion-structure.md` before writing.

**ACR-only.** The bundled parser reads ACR's UE5 GVAS save (`CarSetupsDataSaveSlot.sav`). Save-file
import is **not supported for other games** — don't attempt to parse a non-ACR save. For another
game, tell the user to onboard the car via screenshots (`onboard-car.md`) and build setups instead.

## Inputs
- An ACR save file, **attached in the chat** — `CarSetupsDataSaveSlot.sav` (on Windows it lives
  at `%LOCALAPPDATA%\acr\Saved\SaveGames\CarSetupsDataSaveSlot.sav`).
- **Car** (usually inferable from the save) and **game** (`ACR`).

## Procedure (hybrid: bundled parser, AI fallback)

1. **Run the bundled parser** on the attached file via code execution:
   `python scripts/parse_acr_save.py <file> --pretty` (human summary) or without `--pretty`
   for JSON. It returns `{ok, setup_count, recognized_fraction, notes, setups[]}`; each setup has
   `name, car, track, surface, game_version, drivetrain` (FWD/RWD/AWD, from the diff sections),
   `warnings`, and `params: [{key, label, value}]`
   where `key` is the raw game key (e.g. `Suspensions.Front.AdjusterRing`) with symmetric
   left/right already collapsed, `(Key:Value)` wrappers stripped, and decimals tidied. The parser
   is **schema-agnostic** — it captures *every* parameter, including ones it has no label for
   (those still come through with a humanized `label`).

2. **Branch on confidence.**
   - **`ok: true`** → continue to step 3 with the parsed setups.
   - **`ok: false`** (no setups, or `recognized_fraction` low — ACR may have changed its save
     format) → **fall back to AI extraction**: read the bytes yourself in code execution using
     the format clues below, reconstruct the same `setups[]` shape, and tell the user you used
     the fallback. Don't write anything you can't read confidently.

3. **Review with the user.** Show the parsed setups (names, car, key values) and any `warnings`,
   and get the user's **approval** before writing. The tool is not the source of truth here — the
   user is.

4. **Ensure the Notion structure exists** (per `notion-structure.md`). If this car was never
   onboarded (no `Parameters` catalog / no `Setups` columns for it), run the onboarding workflow
   first so the columns exist. Also set the car page's **`Drivetrain`** from the parser's
   `drivetrain` field (it's derived deterministically from the diff sections) if not already set.

5. **Map keys to the catalog, then write — append only.** Load the car's Notion `Parameters`
   catalog **via [notion-rest-read.md](notion-rest-read.md)** (the connector can't list rows
   reliably). It is the source of truth for column names: match each parsed `key`/`label` to that car's
   `Adjustment` (the raw keys are descriptive, e.g. `Suspensions.Front.AdjusterRing` →
   "Adjuster ring" in section "Suspensions — Front"). **Flag any key you can't confidently map**
   to the user rather than dropping it. **Validate each value against the catalog row resolved for
   that setup's surface** — map the parsed `surface` to the catalog's `Tarmac`/`Gravel`/`Snow`
   (asphalt → Tarmac; dirt/mud → Gravel; ice → Snow; anything else → baseline), then use the
   surface-specific row if the parameter has one; for `Snow`, fall back to a `Gravel` row before
   the baseline (see [notion-rest-read.md](notion-rest-read.md)). The value should fall within that row's
   `Min..Max`, or be a member of its `Discrete steps` when filled; **flag mismatches** rather than
   dropping them (a save value outside the catalog usually means the catalog is incomplete, not
   that the value is wrong). Then add one new
   `Setups` row per setup: `Name`, `Car`, `Location`/`Stage` (if a `track` maps to one in the
   `Locations` catalogue, else leave both blank — **never fabricate a stage facts page** from an
   import), `Surface`, `Game version`, `Date`, `Source = imported`, **`Learn from this` =
   unchecked** (imported setups carry raw numbers without driving-intent context — the user checks
   it after deciding a setup is worth learning from), plus the mapped value properties. Record values
   **as-is** (don't snap — they were already accepted in-game). **Never modify or delete existing
   rows.** After appending, **apply the column order** (`notion-structure.md` → *Applying the
   order*): set the `SHOW` on the main `Setups` table view and the car's linked view to the meta +
   value columns by each parameter's `Order` — an idempotent view update, not a rebuild.

6. **Report.** Setups imported, anything flagged outside the catalog, and whether the deterministic
   parser or the AI fallback was used. Remind the user that imported setups start **unrated** and
   unchecked — they can **rate each `1`–`5`** and tick `Learn from this` once they've vetted it.

## Save format clues (for the AI fallback)
- The file is an **Unreal Engine 5 GVAS** save (`/Script/dmengine.SaveGameSlot` ·
  `CarSetupsSaveGameData`). After the GVAS header it uses a custom body.
- Strings are **FString**: `int32 length` + that many bytes + a trailing `NUL` (length is
  negative for UTF-16). **Don't** read the file as text with NUL→space substitution — that
  corrupts length prefixes.
- Setups are stored as a sequence of `key → value` **string pairs**, e.g.
  `Suspensions.FrontLeft.AdjusterRing` → `0.087000`, `Differentials.Rear.LSDRamps` →
  `(LSDRampAngles:60_70)`. Keys are dotted identifiers; values are either numeric strings or
  `(Type:Value)` wrappers. Collapse symmetric `FrontLeft`/`FrontRight` & `RearLeft`/`RearRight`
  → Front/Rear (they should match). Per-setup metadata strings (name, version, car, track,
  surface) appear just before each block of pairs.

## Rules
- Append-only; never overwrite existing setups.
- Always get user approval of the parsed output before writing.
