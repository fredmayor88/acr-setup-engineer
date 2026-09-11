# car-catalog — setup ranges out of the ACR game files

Maintainer tooling. Rebuilds the `parameters:` block of every bundled template in
[`.claude/skills/acr-setup-engineer/car-templates/`](../../.claude/skills/acr-setup-engineer/car-templates)
straight from Assetto Corsa Rally's pak files, so a game update is a re-run instead of a
fresh round of setup-screen screenshots.

**Nothing here ships inside the skill.** It needs a local game install, so it can't run on
claude.ai. The skill consumes only the committed templates.

## Running it

```bash
python extract_car_catalog.py --dry-run          # report only, writes nothing
python extract_car_catalog.py                    # rewrite every template
python extract_car_catalog.py --car lancia-stratos
```

`--paks` overrides the game path if ACR isn't at the default Steam location. Re-running is
idempotent: a second pass reports zero changes. It shares `iostore.py` and `ooz_unpack.mjs`
with [`../torque-curves`](../torque-curves), so run `npm install` in that folder once first.

Run it after any game update, then read the diff — the report lists every range that moved.
Add new cars to `CAR_MAP` (template slug → presets asset) as they're onboarded.

## Where the data comes from

Each car has `acr/Content/Data/CarSetups/DA_<Car>Presets.uasset`. Inside it:

- a `TMap<FName, UCarSettingOverride*>` keyed by setting id (`Dampers.FrontLeft.SlowBump`),
  whose values are `FPackageIndex` references — **value − 1 is the export index**, so each
  range is its own export with a known offset and size in the export map. That makes the
  join exact rather than a byte-scan heuristic.
- one `CarSetupVariantsSurface` object per surface. A variant may *narrow* a range for that
  surface — gravel springs are much softer than tarmac ones — and those become extra
  template rows carrying `surface: "Gravel"`.

Three things make it awkward, and all three are handled:

- **Oodle compression**, as in `torque-curves`; the same `ooz_unpack.mjs` does the decode.
- **UE 5.5 package headers.** `FZenPackageSummary` gained `CellImportMapOffset` /
  `CellExportMapOffset`, so the name map starts 8 bytes later than a stock UE5 parser
  expects. `zen.py` accounts for it; get this wrong and the name map is garbage.
- **Unversioned properties.** `unversioned.py` decodes the `FUnversionedHeader` fragments
  (`SkipNum = v & 0x7f`, `bHasAnyZeroes = v & 0x80`, `bIsLast = v & 0x100`,
  `ValueNum = v >> 9`) plus the zero-mask. For a range object the schema is
  `[0] Min, [1] Max, [2] Step`, and each object ends with a 4-byte trailer.

**A property that equals its default is simply not written.** So a missing `Min` means zero,
not missing data — that's how an anti-roll bar legitimately reads `0..7500`. The exception is
when *neither* bound is stored: no car has a genuine `0..0` range, so the extractor treats
that as "inherit" and keeps whatever the previous template had. See *What it doesn't touch*.

**Sanity check.** Left and right corners must agree — the extractor raises if they ever don't,
because that would mean the export-map join had slipped and averaging it would hide the bug.
The other check is the DataTable-backed lists: gear sets, primary gears, differential ratios
and LSD ramps are resolved from `DT_*Lists` and came out matching the previous
screenshot-derived templates exactly, which is what makes the rest of the numbers believable.

### Discrete steps

`discrete_steps` is emitted only when the grid has at most `MAX_DISCRETE` (64) entries.
Ride height, LSD preload and handbrake force step so finely that listing every value is noise;
`min`/`max` says it better. Anti-roll bars, dampers, springs and pressures still get a list.

## What it doesn't touch

These stay as the previous template had them, and the run prints which ones were carried over:

- **Tyre Type, brake discs / calipers / pads, master cylinders.** These are DB part records
  whose *display* strings the UI synthesises from part specs — the files hold
  `APLockheed_CP4448-81_267x28_Baffled_5x108_APLockheedDisc00` where the setup screen shows
  `267/156X28 B TYPE1`. Emitting the raw ids would be worse than useless for matching what's
  on screen, so the human-readable lists are kept.
- **Proportioning preload, front cylinder, rear cylinder.** The per-car asset stores no bound
  for these; the displayed range is derived from the fitted master cylinder.
- **Identity facts** (`weight`, `class`, `max_power`, …). `DT_Cars` holds them and they parse,
  but wiring that up is a separate job. `max_power` / `max_torque` are real-world specs anyway,
  not game output — compare them against the `engine_curve:` peaks, not against each other.
- **`Front Bias` (0.25–0.75), `Proportioning Ratio` (0–1), `ABS Map` / `TCS Map` (1–3).**
  Definition-level constants: every car's asset overrides only the *step*, so the bounds live
  in the shared setting definition. They're pinned in `mapping.py`'s `DEFINITION_RANGES`.
