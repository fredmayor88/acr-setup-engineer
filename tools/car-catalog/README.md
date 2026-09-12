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

- **Brake discs and calipers.** These are DB part records whose *display* strings the UI
  synthesises — the files hold `APLockheed_CP4448-81_267x28_Baffled_5x108_APLockheedDisc00`
  where the setup screen shows `267/156X28 B TYPE1`. `DT_DiscsLists` / `DT_CalipersLists` do
  give the per-car, per-axle part ids (keyed `<DT_Wheels prefix>_<Surface>_<Axle>`), and the id
  yields the outer diameter, the thickness and the `P`/`B`/`D` letter (`Planar`/`Baffled`/…) —
  but **the middle number and the `TYPE<n>` index are not in the game data**. Searched and ruled
  out: the `DT_Discs` row bytes, the per-disc `DA_*` DataAsset (524 bytes: asset paths plus one
  description string, `AlfaRomeo 250mm Type1 250x22 4x108` — no `140`), and the part id itself.
  Some disc assets happen to embed it (`Alcon DIV2216X 355-249/32 …` → `355/249X32`) but most
  don't, so it's most likely read off the disc mesh or computed UI-side. Re-check only with new
  evidence. Calipers are the same story: `2x48` comes from the id, `TYPE<n>` doesn't.
- **`Proportioning Preload`.** The per-car asset stores no bound; the displayed range is derived
  from the fitted master cylinder by a formula that hasn't been worked out. Affects few cars.
- **`Engine Map` / `Throttle Map`.** Present as bound-less settings on a couple of cars. Only one
  bundled template has them at all (the Xsara: `0, 1` and `1, 2`), and those two disagree on
  whether the list starts at 0 or 1 — one car is not enough evidence to pin a definition-level
  constant, so they still need a screenshot.
- **`Front Bias` (0.25–0.75), `Proportioning Ratio` (0–1), `ABS Map` / `TCS Map` (1–3).**
  Definition-level constants: every car's asset overrides only the *step*, so the bounds live
  in the shared setting definition. They're pinned in `mapping.py`'s `DEFINITION_RANGES`.
- **`weight`, `weight_bias`, `max_power`, `max_torque`, `steering_lock`, and the precise
  `engine_layout` prose** (orientation, displacement, valve gear). Not FName-tagged fields in
  `DT_Cars` — see *Car identity facts* below for what *is* — and `max_power`/`max_torque` are
  real-world specs anyway, not game output; compare them against the `engine_curve:` peaks,
  not against each other. One look at the game's car-info screen (plus a spec sheet for the
  power/torque numbers) fills these in.

## Part lists that *are* recovered from the game files

A brand-new car gets these filled automatically (the run prints
`+ filled from the game files: …`), so they never need a screenshot. An existing template's own
wording still wins on a refresh, which is why adding this changed nothing in the 14
screenshot-onboarded templates:

- **`Tyre Type`, `Brake Pads Front` / `Brake Pads Rear` — game-wide constants, not per-car.**
  All 14 screenshot-onboarded templates carry byte-identical lists: the canonical 10 tyre
  compounds and `SOFT, MEDIUM, HARD`. Pinned in `mapping.py`'s `CONSTANT_STEPS`; the tyre list
  must stay identical to the one the skill validates against in `SKILL.md`.
- **`Front Cylinder` / `Rear Cylinder` — `DT_MasterCylindersLists`**, keyed by the car's
  `DT_Wheels` prefix (`LanciaRally037Evoluzione2`, `AudiQuattroGr.4`, …), one bore list per car
  serving both axles. Verified against every bundled template that has these rows — 037, i20,
  306, Xsara, Fabia, Impreza, 131 — all exact matches. A car absent from that table has no
  cylinder parameter at all (the Peugeot 208 Rally4), which lines up with what its presets asset
  exposes. The combined `Master Cylinder` row some cars use instead (front/rear pairs, e.g. the
  Alfa's `20.64_20.64, 22.23_22.23`) lives in `DT_MasterCylindersSets` and is **not** wired up —
  no queued car needed it.

The table naming is a consistent pattern worth knowing: `DT_<Thing>Lists` holds the per-car or
per-part *option lists* and parses with the plain `datatable.rows()` reader, while `DT_<Thing>`
holds the part records themselves and needs struct-level parsing. That's the same mechanism
`build_rows()` already uses for gear sets and diff ramps, which is why wiring a new one up is
usually a `WANTED_TABLES` entry plus a lookup.

## Car identity facts

`car_identity.py` reads `DT_Cars` (`acr/Content/Data/Database/Main/CarSelection/DT_Cars.uasset`)
for the identity-header fields that *do* come out clean as plain `FName` values: `drivetrain`
(from `WheelDrives`), `class` (from `CarsClasses`), `gearbox` (from `GearsTypes`), plus
manufacturer and enough engine metadata (`EngineTypes`/`EnginePositions`/`Inductions`) for a
starting `engine_layout` draft. It does **not** give you weight, power/torque, steering lock, or
engine orientation/displacement — those aren't stored as named fields in this table (they're
either real-world specs or raw numeric properties whose per-row schema layout hasn't been
reverse-engineered).

```bash
python car_identity.py                       # every car DT_Cars has a row for
python car_identity.py --car AudiQuattroGr4   # one row, by its DT_Cars row key
```

**Why a new extractor instead of reusing `tagged_rows()`:** `DT_Cars` rows interleave the tags
above with a lot of unrelated untagged names (asset paths, localization keys, livery lists), and
`tagged_rows()`'s "any untagged name becomes the new current row" heuristic — fine for the
uniform `DT_Wheels` rows it was written for — silently attributes a tag to the wrong row when one
of those untagged names sits between the real row key and its tags (this bit `Peugeot206WRC`
during validation). `datatable.struct_rows()` instead anchors each row's boundary on the first
occurrence of a designated anchor tag (`Manufacturers`, which the game always writes immediately
after the row's own key with nothing between them) and only reads tags from within that row's
own slice. **Validated against all 14 bundled templates**: drivetrain, class and gearbox came
back matching the hand-written value for every one, which is what makes trusting it for new cars
possible — see `class_label()`/`gearbox_label()` in `car_identity.py` for the exact string
mappings that reproduce each template's existing spelling (`A8_Evo2` → `Group A · A8 EV02`,
`Sequential6_7_Lever` → `Sequential 6-speed`, …).

`DT_Cars`'s row key usually equals the `Vehicles/` folder name (`AudiQuattroGr4`,
`VWPoloGTIR5`, …) but not always — `Peugeot206WRC`'s row is keyed `Peugeot206`,
`LanciaFulviaCoupeHF`'s is `LanciaFulviaHF`, `LanciaDeltaHFIntegraleEvo`'s is
`LanciaDeltaIntegraleEvo`, `Peugeot306IIMaxi`'s is `Peugeot306IIMaxiKitCar`. `car_identity.py`'s
`SLUGS` dict carries the known row-key → template-slug mapping; add a new car there when you
onboard it (a wrong-guessed key just falls through as "not a DT_Cars row" — the error names the
actual key list).

## Onboarding a brand-new car (no bundled template yet)

Confirmed working (Audi Quattro Gr4, VW Polo GTI R5, Peugeot 208 Rally4, Peugeot 206 WRC were
bootstrapped this way):

1. **Add the car everywhere it needs a map entry** — four separate per-tool maps, each keyed for
   that tool's own job (not yet unified, and the duplication is intentional per the existing
   pattern rather than a shared table to invent):
   - `extract_car_catalog.py`'s `CAR_MAP`: slug → `DA_<Car>Presets` asset basename
     (`acr/Content/Data/CarSetups/`).
   - `car_identity.py`'s `SLUGS`: `DT_Cars` row key → slug (see above for why the key can
     differ from the folder name).
   - `../torque-curves/extract_torque_curves.py`'s `CAR_MAP`: `Vehicles/` folder name →
     (slug, display name) — for the engine curve chart. A car whose game files don't have an
     `FC_*_Torque.uasset` yet (Peugeot 206 WRC, currently) still gets an entry; it's a no-op
     until the game ships that asset.
   - `../gearing-charts/make_gearing_chart.py`'s `CARS`: slug → (gear-set asset prefix, `DT_Wheels`
     row prefix, car data asset — the first and third are almost always identical; look up the
     `DT_Wheels` prefix by grepping that table's row names for the car, since it can differ
     arbitrarily from the folder name, e.g. `AudiQuattroGr4` → `AudiQuattroGr.4`, literal dot).
2. **Run `python extract_car_catalog.py --car <slug>`** (drop `--car` for a full pass; add
   `--dry-run` to preview). With no existing `<slug>.yaml`, it now bootstraps one from scratch
   instead of erroring: the full `parameters:` block from the game files (identical machinery to
   a refresh), plus a header pre-filled from `car_identity.py` (`drivetrain`, `class`, `gearbox`).
   Everything else is left as an explicit `TODO` string for now. The console output is tagged
   `[NEW - no bundled template yet]` and lists every parameter that **needs one screenshot** to
   fill in (`NEEDS SCREENSHOT` instead of the refresh-path's silent carry-over) — always the same
   bounded set: `Tyre Type`, the six brake-part display strings, the master-cylinder fields, and
   any per-car setting the game leaves at a shared definition default with no previous template
   to inherit it from.
3. **Run `python ../torque-curves/extract_torque_curves.py`** (it only writes into templates that
   already exist, so this must come *after* step 2). Renders the power/torque chart, writes the
   `engine_curve:` block, and **backfills the `max_power`/`max_torque` TODOs** with the engine
   curve's own peaks (clearly labelled `ACR engine-curve peak`, never silently — see
   `backfill_todo_specs()`). Treat those as a starting value to confirm against a real spec sheet,
   not a final one — README.md's own note about forced-induction disagreement applies. A car with
   no `FC_*_Torque` asset (Peugeot 206 WRC) gets no chart, no `engine_curve:` block, and its
   `max_power`/`max_torque` stay `TODO` — there's no game data to backfill from.
4. **Run `python ../gearing-charts/make_gearing_chart.py --car <slug>`** for the gearing chart (and
   final-drive chart, if the car's final drive is adjustable — the tool says so on the cars that
   aren't, e.g. Peugeot 208 Rally4 and VW Polo GTI R5). Needs step 3's `engine_curve:` block first
   (it reads the redline from it) — a car with no engine curve (206 WRC) can't get one yet either.
5. **Finish from the in-game car-info screen — one screenshot per car.** That screen carries
   `car` (display name + year), `engine`, `max_power`, `max_torque`, `weight` and `steering_lock`
   in one place, so the header comes down to a single capture. Two traps, both hit on real cars:
   - **The steering-lock figure is sometimes the per-side angle.** The VW Polo GTI R5 reads
     `280°` where lock-to-lock is `560°`. Every other car so far reads a sane 720–1170, so a
     half-sized number is the tell — double it.
   - **The engine description can be wrong.** The Audi Quattro Gr.4 screen says `Inline 4`; the
     real car is a 2.1L inline-5. Write the true layout in `engine_layout` and note the
     disagreement in the same line, the way that template does.

   Two fields the screen does *not* carry: `weight_bias` (rarely published for rally cars — an
   estimate marked `(estimated — no published figure)` is the established convention, see the
   Fiat 131 template) and the `engine_layout` detail beyond cylinder count (orientation,
   displacement, valve gear) — a quick spec-sheet lookup. Until `car:` stops being the literal
   string `"TODO"`, the template is a draft — don't let the skill auto-onboard a car from it, and
   note that the gearing charts title themselves from `car:`, so rendering them before this step
   puts the word "TODO" on the chart.
6. **Capture the one screen the files can't replace:** the brake setup screen, for
   `Brake Discs Front`/`Rear` and `Brake Calipers Front`/`Rear` (plus `Engine Map` /
   `Throttle Map` / `Proportioning Preload` on the rare car that has them) — everything the run
   flags `NEEDS SCREENSHOT`. `DT_DiscsLists` / `DT_CalipersLists` tell you **how many options to
   expect per axle**, so you can check the capture is complete before typing it in. Worth typing
   carefully: the hand-entered values in the older templates contain real typos — `TYPE 2` with a
   stray space, `Typ1` truncated, and a `355/248` that the game files say is `355/249`.

## Chart titles come from two places — keep them in sync

`extract_torque_curves.py` titles the power/torque chart from its `CAR_MAP` display name;
`../gearing-charts/make_gearing_chart.py` titles its charts from the template's own `car:` field.
They must match exactly or one car ships charts under two names (the Lancia Fulvia ran for a
while with `Coupé` in the template and `Coupe` on its chart). After changing either, re-check:

```bash
python - <<'PY'
import os, re, sys; sys.path.insert(0, '../torque-curves')
from extract_torque_curves import CAR_MAP
T = '../../.claude/skills/acr-setup-engineer/car-templates'
for _, (slug, display) in sorted(CAR_MAP.items()):
    p = os.path.join(T, slug + '.yaml')
    if not os.path.exists(p):
        continue
    car = re.search(r'car: "([^"]+)"', open(p, encoding='utf-8').read()).group(1)
    if car != display:
        print(f'MISMATCH {slug}: chart="{display}" yaml="{car}"')
PY
```

Both chart tools take `--car <slug>` to re-render a single car, which is how you avoid rewriting
the other templates (and spraying phantom line-ending diffs) when only one car changed.
