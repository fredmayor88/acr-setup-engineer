# Bundled default setups from the game files, and a known game version

**Status:** approved 2026-09-22 · **Date:** 2026-09-22

## Summary

A build starts from the game's own default setup (`SKILL.md` → *Baseline first*). Today that
anchor comes from screenshots the user takes of the in-game setup screens, saved as
`Source = default` rows in Notion. It costs the user a screenshot round per car and context, it is
read by a model (your Stratos capture reads springs `65400` where the game's grid only has
`65000`), and it goes stale on every game update.

The game files hold every default setup for every car. This design extracts them once per game
update into bundled files inside the skill, next to the catalogs, and makes them the anchor. It
also gives the skill one authoritative fact for the current game version, read from the game's
own config by the same extraction and stamped on every bundled file.

## Goals

- Every bundled car has its default setups inside the skill: one per surface the game defines for
  it, and one per named preset where the game has more than one.
- A build anchors on the bundled default. Template cars never ask for default screenshots again.
- The skill knows the current game version from one file, and every bundled file says which
  version it came from.
- One Makefile command repeats the whole extraction after a game update.

## Non-goals

- Overriding bundled defaults from screenshots, or per-stage defaults. The game's defaults are
  per surface; the maintainer refreshes them after each game release.
- Migrating or deleting the `Source = default` rows already in users' Notion. They stop being
  read; nothing deletes them.
- Changing the catalog extraction, the torque curves or the car-lab export, beyond sharing the
  game-version step and the Makefile entry.

## Decisions taken with the user (2026-09-22)

- Bundled data wins. A screenshot-onboarded car keeps today's screenshot-default path only
  while no bundled setups file exists for it; once one exists, the bundled file is the anchor.
- The current game version is `0.6`.
- The whole extraction runs as one Makefile target so a game update is a re-run.

## What the game files hold

Verified on 2026-09-22 against the installed 0.6 paks with the parser in `tools/car-catalog`.

Each car has one presets asset, `acr/Content/Data/CarSetups/DA_<Car>Presets.uasset`, already
mapped per car in `extract_car_catalog.py` → `CAR_MAP`. Inside it, three layers:

1. **`PhysicsCarSetup`** — one export, the car's base setup: every tunable's value before any
   surface or preset override. For the Stratos: springs 65000, slow bump 6250, slow rebound 7250,
   fast bump 4750, pressure 28, camber -2.4, front bias 0.57, adjuster ring 0.048. Its values
   sit on the catalog's grid. It is a nested struct, not a flat property list; its schema has to
   be decoded once (the flat `read_header` walk reads only the outer five slots).
2. **`CarSetupVariantsSurface`** — one export per surface, mapped from the main export by the
   `SurfaceTypes` tag (`acrpkg.surface_variants` already resolves them). Each holds value
   overrides on the base: `CarSettingOverrideFloat` / `Integer` / `Bool` for numbers, and
   `CarSettingOverrideValueSetDBReference` (a `{table hint, row}` FName pair at bytes 4 and 12
   of the export) for list-valued settings: discs, calipers, pads, gear set, primary gear,
   differential ratios, LSD ramps. Range overrides in the same map are the catalog's business
   and are ignored here. Every car has Tarmac and Gravel; the Alpine A110 and the Fiat 131 also
   have Snow.
3. **`CarSetupVariant`** — named presets per surface, held in a `{name → export}` map at the
   end of the surface export. Every car has `Balanced`, whose export is empty: Balanced equals
   the surface layer. The Lancia Delta and the Peugeot 208 Rally4 also have `Aggressive`, a
   small further override set.

A complete preset is therefore: **base, then the surface's overrides, then the preset's
overrides**, corner values collapsed to axles (left and right are asserted equal, as the
catalog extractor does).

Resolving list values to what the setup screen shows, all through tables the catalog extractor
already reads (`WANTED_TABLES`, `datatable.rows`):

| Setting | Stored as | Displayed as |
| --- | --- | --- |
| Gear set | `GearsSets → LanciaStratosSet0` | position in `DT_GearsSetsLists[car]` + 1 → `1` |
| Primary gear, diff ratios | `Gears → 33//31*31//30` | the row name as is |
| LSD ramps | `LSDRampAngles → 45_50` | `45/50` |
| Pads | `Pads → Type13_Medium` | the suffix, upper-cased: `MEDIUM` |
| Discs, calipers | `Discs → APLockheed_CP4448-81_267x28_…` | position in `DT_DiscsLists[<car>_<Surface>_<Axle>]`, taken as the same position in the template's `Discrete steps` for that parameter (the display strings aren't in the game data; the order is) |

Checked against the user's screen capture of the Stratos tarmac Balanced: gear set, primary
gear, diff ratio, ramps, pads, front bias, camber and every damper match. Springs differ
(65400 captured vs 65000 stored) — the stored value is on the grid, the captured one is not.

## Data model

### Bundled setups file — `car-setups/<slug>.yaml`

One file per bundled car, same slug as its `car-templates/<slug>.yaml`, stdlib-parseable YAML
in the same flat quoting style as the templates:

```yaml
car: "Lancia Stratos HF"
game: "ACR"
version: "0.6"
source: "game-files"
written_at: "2026-09-22"
setups:
  - surface: "Tarmac"
    preset: "Balanced"
    values:
      "Gear Set": "1"
      "Primary Gear": "33//31*31//30"
      "Spring Stiffness Front": 65000
      "Spring Stiffness Rear": 42500
      "Brake Discs Front": "267/156X28 B TYPE1"
      "Tyre Type": "Tarmac Soft"
      …
  - surface: "Gravel"
    preset: "Balanced"
    values: { … }
```

- `values` is keyed by the template's `Adjustment` names, one key per parameter the car's
  template has. A parameter the game leaves at its base value is still written — the file is a
  complete setup, never an override list. A parameter with no source in the game data (a
  template row the extractor can't fill) is omitted and named in the extractor's report.
- Numbers are numbers, list values are strings exactly as the template's `Discrete steps`
  spell them, so `load_catalog.py --check` passes on every entry.
- `version` is the game version the file was extracted from; `written_at` the extraction date.
- Tyre type: the base setup's tyre (`TireCompounds → TarmacSoft` in the car asset) written in
  the skill's canonical name.

### `GAME_VERSION` file

`.claude/skills/acr-setup-engineer/GAME_VERSION`: one line, the display version (`0.6`), the
same format `tools/gearing-charts/game_version.py` → `display_version` produces. Written by the
extraction, read by the skill. It replaces the `GAME_VERSION = '0.6'` constant in
`extract_car_catalog.py`, which now reads the file the extraction wrote.

### Loader — `scripts/load_default_setup.py`

Stdlib only, like `load_catalog.py`. Modes:

- `--car <slug> --surface <Surface> [--preset <name>]` prints the matching entry as JSON:
  `{"car", "version", "surface", "preset", "fallback": null | "Gravel", "values": {…}}`.
  `--preset` defaults to `Balanced`. A surface the file lacks falls back: Snow → Gravel,
  anything else → error. A preset the file lacks → exit 1 with the names it has.
- `--list <slug>` prints the surfaces and presets the file has.
- `--game-version` prints the `GAME_VERSION` file's content.
- Unknown flags exit 2; a missing file exits 1 with a clear message.

## Extraction — `tools/car-catalog/extract_default_setups.py`

Maintainer tooling, runs on a machine with the game, shares `acrpkg`, `zen`, `unversioned`,
`datatable`, `mapping` and the pak plumbing with `extract_car_catalog.py`.

1. Extract the presets assets and the DB list tables, once, into a temp dir (existing `extract`).
2. Per car: decode the `PhysicsCarSetup` struct into `{setting id → value}` (the new decoding
   work: schema for the nested structs, done once and asserted by tests on the Stratos numbers
   above); apply each surface's overrides; for each named preset apply its overrides on top.
3. Collapse corners to axles (assert left = right), map setting ids to template `Adjustment`
   names through `mapping.py`, resolve DB references through the tables and the car's template
   `Discrete steps`.
4. Validate every entry with `load_catalog.py --check` against the car's bundled template; a
   failure is an extractor error, not a warning.
5. Write `car-setups/<slug>.yaml`, and print a report per car: surfaces and presets written,
   parameters that couldn't be filled, values that changed since the previous file.

Flags: `--dry-run`, `--car <slug>`, `--paks <dir>`, same as the catalog extractor. Idempotent.

### Game version — `tools/car-catalog/write_game_version.py`

Reads the installed game's version with `tools/gearing-charts/game_version.py` →
`read_game_version` and writes `GAME_VERSION`. `--check` exits 1 when the file differs from the
game. Both extractors stamp the version they read into their files.

### Makefile

```
make extract            game version, catalogs, default setups, power/torque charts, car-lab
make extract-version    write GAME_VERSION from the game's config
make extract-catalogs   python tools/car-catalog/extract_car_catalog.py
make extract-setups     python tools/car-catalog/extract_default_setups.py
```

`extract` runs the four in that order, then `charts-power` and `car-lab` (existing targets).
Each step fails if the game isn't at the default Steam path (`PAKS=… make extract` overrides).
Header comment and target list updated. After a run: read the diff, run `make test`, commit.

## Using the bundled defaults in the skill

### Build — `build-setup.md` step 4

Step 4 becomes, for a car with a bundled setups file:

1. Run `python scripts/load_default_setup.py --car <slug> --surface {Surface}` (`--preset
   Aggressive` only when the user asked for it by name). One command, in the same
   code-execution block as `load_catalog.py`.
2. Its `values` are the anchor. Go to step 5b (the sanity check) as today. Say in one line
   which preset anchored the build and the game version it came from; when `fallback` is set,
   say the Snow anchor is the gravel preset.
3. No Notion `default` rows are read, no screenshots are asked for, on any plan.

For a car with **no** bundled setups file (a screenshot car): today's step 4 unchanged — stored
`default` rows, then the screenshots-first path. The moment a bundled file exists for that car
(a later skill version ships it), the bundled file wins and the stored rows are ignored.

Step 5 (capturing the default from screenshots) and the `Source = default` write stay, but only
reachable from that branch. `SKILL.md` → *Baseline first* is rewritten to state the order:
bundled file, else captured default, else screenshots.

### Game version everywhere

- `build-setup.md` step 11, `tweak-setup.md`, `capture-setup.md`: the `Game version` column
  is filled from `GAME_VERSION` when the user didn't say otherwise ("I'm on 0.7" in chat wins
  for that chat, and the skill says the bundled data is from 0.6).
- `notion-structure.md` → `Catalog` page source line already carries the template's version;
  unchanged.
- `How to use` page: one line, *"Setups start from the game's own default setup for the car and
  surface (game version {game_version}). Say 'start from the Aggressive preset' for cars that
  have one."*

### What stops being read

- `Source = default` rows in Notion, for template cars. The `default` lines in the `Setup index`
  are still written (a screenshot car still captures) but a template car's build never asks the
  picker for them. `setups-list-read.md` step 4 says so.
- The screenshots-first message for template cars.

## Tests

- `tests/test_car_setups.py`: every `car-templates/<slug>.yaml` has a `car-setups/<slug>.yaml`
  with the same `car` and `version`; every file's `version` equals `GAME_VERSION`; every
  entry passes `load_catalog.py --check` against its template; every car has Tarmac and Gravel;
  Alpine and 131 have Snow; Delta and 208 have Aggressive; the Stratos tarmac Balanced holds
  the numbers verified above (springs 65000/42500, front bias 0.57, gear set `1`, primary
  `33//31*31//30`, diff `65//19`).
- `tests/test_load_default_setup.py`: each mode, the Snow fallback, unknown preset, unknown
  flag, missing file.
- `tools/car-catalog` decoding tests on a checked-in Stratos presets asset fixture: base
  decode, override application, DB resolution, corner collapse.
- `tests/test_references.py` guards: build-setup step 4 names `load_default_setup.py`; no
  reference tells a template car to ask for default screenshots; `GAME_VERSION` is named in
  SKILL.md.
- Manual: one build per surface on the Stratos on a Free chat; compare the anchor with the
  in-game screen on 0.6.

## Open points to settle during implementation, not design

- The exact schema of `PhysicsCarSetup`'s nested structs (found by decoding, asserted by the
  Stratos test values).
- Whether a Snow preset overrides the same fields as Gravel or fewer (data will tell).
- Tyre type's location when a surface variant changes it (the base asset names `TarmacSoft`;
  gravel presumably overrides it inside the variant).
