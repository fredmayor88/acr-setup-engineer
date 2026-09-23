# Bundled default setups — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract every car's default setups (per surface, per named preset) from the game files into bundled `car-setups/<slug>.yaml` files, give the skill a `GAME_VERSION` fact, make the bundled setup the anchor of every build for template cars, and make the whole extraction one `make extract`.

**Architecture:** Maintainer tooling in `tools/car-catalog/` (shares `acrpkg`, `zen`, `unversioned`, `datatable`, `mapping`, the pak plumbing): a decoder module turns one presets asset into `{surface: {preset: {adjustment: value}}}`, an extractor renders and validates the YAML files. Inside the skill, a stdlib loader `scripts/load_default_setup.py` prints one preset as JSON and build-setup step 4 anchors on it. `GAME_VERSION` is written by a small tool from the game's config and read everywhere else.

**Tech Stack:** Python 3 stdlib in the skill; Python 3 + node (`ooz_unpack.mjs`, already installed) in tools; `unittest` (`python -m unittest discover -s tests`, run from the repo root; 397 tests green at start); GNU Make 3.81-compatible Makefile (no `||`, no `2>/dev/null`; recipes run under cmd.exe on Windows).

**Spec:** `docs/superpowers/specs/2026-09-22-bundled-default-setups-design.md`

## Global Constraints

- Skill scripts are **stdlib only**; unknown flags **exit 2**; missing file **exit 1** with a clear message.
- `car-setups/<slug>.yaml` shape, exactly (flat quoting like the templates; `values` keyed by the template's `adjustment` names, one key per template row the extractor could fill; numbers unquoted, list values quoted exactly as the template's `discrete_steps` spell them):
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
        "Spring Stiffness Front": 65000
  ```
- Preset composition: **base (`PhysicsCarSetup`), then the surface's overrides, then the named preset's overrides**; corners collapse to axles and left must equal right (raise otherwise).
- List values resolve as the spec's table says: gear set = position in `DT_GearsSetsLists[car]` + 1 as a string; primary gear and diff ratios = the row name; LSD ramps `45_50` → `45/50`; pads = suffix upper-cased; discs and calipers = the same position in the template's `discrete_steps` as the row has in `DT_DiscsLists` / `DT_CalipersLists`.
- Every entry passes `load_catalog.py --check` against its template for its surface; a failure is an extractor **error**.
- Snow on a car without a Snow preset falls back to Gravel (loader reports `"fallback": "Gravel"`); no other fallback.
- `GAME_VERSION` (skill root) is one line, display form (`0.6`), produced by `tools/gearing-charts/game_version.py` → `display_version`. Every bundled setups file's `version` equals it. Tests fail otherwise.
- Bundled data wins: a car with a `car-setups` file never reads Notion `default` rows and never asks for default screenshots. A car without one keeps today's path unchanged.
- Writing rule (CLAUDE.md): every workflow step followable by a less capable model — exact commands, exact phrases.
- Commit after each task, short factual message, end with a blank line and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Never push. Full suite green before each commit.
- The catalog extractor (`extract_car_catalog.py`) keeps its behaviour; the only change is where it gets the game version.

---

## File structure

| File | Responsibility |
| --- | --- |
| Create `.claude/skills/acr-setup-engineer/GAME_VERSION` | The current game version, one line. |
| Create `tools/car-catalog/write_game_version.py` | Read the installed game's version, write/check `GAME_VERSION`. |
| Modify `tools/car-catalog/extract_car_catalog.py` | Read the version from `GAME_VERSION` instead of the constant. |
| Create `tools/car-catalog/decode_setups.py` | One presets asset → `{surface: {preset: {setting id: raw value}}}` plus the base; DB references resolved; corners collapsed. Pure functions. |
| Create `tools/car-catalog/extract_default_setups.py` | CLI: paks → `car-setups/*.yaml`, validation, report. |
| Create `.claude/skills/acr-setup-engineer/car-setups/*.yaml` | 18 bundled files, generated. |
| Create `.claude/skills/acr-setup-engineer/scripts/load_default_setup.py` | Loader CLI. |
| Create `tests/fixtures/paks/` | Checked-in extracted assets for decoder tests (Stratos + 037 presets, the DT list tables). |
| Create `tests/test_decode_setups.py`, `tests/test_car_setups.py`, `tests/test_load_default_setup.py`, `tests/test_game_version_file.py` | Tests. |
| Modify `references/build-setup.md`, `SKILL.md`, `references/setups-list-read.md`, `references/notion-structure.md`, `references/how-to-use-template.md`, `references/tweak-setup.md`, `references/capture-setup.md` | Skill behaviour. |
| Modify `Makefile`, `README.md`, `CLAUDE.md`, `tools/car-catalog/README.md`, `tests/test_references.py` | Tooling docs and guards. |

---

### Task 1: `GAME_VERSION` file and `write_game_version.py`

**Files:**
- Create: `.claude/skills/acr-setup-engineer/GAME_VERSION` (content `0.6\n`)
- Create: `tools/car-catalog/write_game_version.py`
- Modify: `tools/car-catalog/extract_car_catalog.py` (line 37 `GAME_VERSION = '0.6'`)
- Create: `tests/test_game_version_file.py`
- Modify: `tests/test_car_templates.py` (line ~152 imports `GAME_VERSION` from the extractor — keep working)
- Modify: `Makefile` (target `extract-version`)

**Interfaces:**
- Produces: `GAME_VERSION_FILE` path constant in `extract_car_catalog.py`; `read_game_version_file(path) -> str` there; CLI `python tools/car-catalog/write_game_version.py [--paks DIR] [--check]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_game_version_file.py`:

```python
"""GAME_VERSION — the one place the skill knows the current game version.

Written by tools/car-catalog/write_game_version.py from the game's DefaultGame.ini, read by the
catalog and default-setup extractors, the skill and these tests.

Run: python -m unittest discover -s tests
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
FILE = os.path.join(SKILL, 'GAME_VERSION')
TOOL = os.path.join(REPO, 'tools', 'car-catalog', 'write_game_version.py')
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))


class TestFile(unittest.TestCase):
    def test_exists_and_is_a_display_version(self):
        with open(FILE, encoding='utf-8') as f:
            text = f.read()
        self.assertTrue(text.endswith('\n'))
        self.assertRegex(text.strip(), r'^\d+\.\d+(\.\d+)?$')

    def test_every_template_carries_it(self):
        import glob
        version = open(FILE, encoding='utf-8').read().strip()
        for path in glob.glob(os.path.join(SKILL, 'car-templates', '*.yaml')):
            with open(path, encoding='utf-8') as f:
                self.assertIn(f'version: "{version}"', f.read(), path)

    def test_extractor_reads_the_file(self):
        import extract_car_catalog as ecc
        self.assertEqual(ecc.GAME_VERSION, open(FILE, encoding='utf-8').read().strip())


class TestTool(unittest.TestCase):
    def test_check_mode_passes_when_equal(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        open(target, 'w').write('0.6\n')
        r = subprocess.run([sys.executable, TOOL, '--check', '--version', '0.6', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_check_mode_fails_when_different(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        open(target, 'w').write('0.5\n')
        r = subprocess.run([sys.executable, TOOL, '--check', '--version', '0.6', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('0.5', r.stderr)
        self.assertIn('0.6', r.stderr)

    def test_write_mode(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        r = subprocess.run([sys.executable, TOOL, '--version', '0.7.1', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(target).read(), '0.7.1\n')

    def test_unknown_flag_exits_2(self):
        r = subprocess.run([sys.executable, TOOL, '--bogus'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify they fail** — `python -m unittest tests.test_game_version_file -v` (FileNotFoundError / no tool).

- [ ] **Step 3: Create `GAME_VERSION`** with content `0.6` and a trailing newline (LF).

- [ ] **Step 4: Write `tools/car-catalog/write_game_version.py`**

```python
#!/usr/bin/env python3
"""Write the installed game's version into the skill's GAME_VERSION file.

The number people call the game by (`0.6`) is ProjectVersion in acr/Config/DefaultGame.ini,
read out of the paks by tools/gearing-charts/game_version.py. This tool writes its display form
to .claude/skills/acr-setup-engineer/GAME_VERSION — the one place the skill, the extractors and
the tests read the current game version from. Run it first in `make extract`.

Usage:
  python write_game_version.py [--paks DIR]          # read the game, write GAME_VERSION
  python write_game_version.py --check [--paks DIR]  # exit 1 when GAME_VERSION differs from the game
  --version X.Y and --file PATH bypass the game and the default file (tests).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'gearing-charts'))
from game_version import read_game_version  # noqa: E402

DEFAULT_PAKS = ('C:/Program Files (x86)/Steam/steamapps/common/'
                'Assetto Corsa Rally/acr/Content/Paks')
DEFAULT_FILE = os.path.join(HERE, '..', '..', '.claude', 'skills', 'acr-setup-engineer',
                            'GAME_VERSION')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=DEFAULT_PAKS)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--version', help=argparse.SUPPRESS)
    ap.add_argument('--file', default=DEFAULT_FILE, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.version:
        version = args.version
    else:
        if not os.path.isdir(args.paks):
            sys.exit(f'ACR paks not found at {args.paks} (pass --paks)')
        version = read_game_version(args.paks, args.paks)

    if args.check:
        current = open(args.file, encoding='utf-8').read().strip() if os.path.exists(args.file) else ''
        if current != version:
            sys.stderr.write(f'GAME_VERSION says {current!r}, the game says {version!r}\n')
            return 1
        print(f'GAME_VERSION {version}: up to date')
        return 0
    with open(args.file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(version + '\n')
    print(f'GAME_VERSION <- {version}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

Check `read_game_version`'s real signature in `tools/gearing-charts/game_version.py` (the tests call it as `read_game_version(self.dir, self.dir)`) and match it.

- [ ] **Step 5: Make the catalog extractor read the file**

In `extract_car_catalog.py` replace `GAME_VERSION = '0.6'` with:

```python
GAME_VERSION_FILE = os.path.join(SKILL, 'GAME_VERSION')   # SKILL is the skill dir the file already defines; add it if it's named differently


def read_game_version_file(path=GAME_VERSION_FILE):
    with open(path, encoding='utf-8') as f:
        return f.read().strip()


GAME_VERSION = read_game_version_file()
```

(Locate how the file names the skill directory — it has `TEMPLATES = …car-templates`; derive the skill dir from that.)

- [ ] **Step 6: Makefile** — add to the `.PHONY` line and after `car-lab`:

```make
# Writes the installed game's version into the skill's GAME_VERSION file. First step of
# `make extract`; every bundled file is stamped with this version.
extract-version:
	python tools/car-catalog/write_game_version.py $(PAKS_FLAG)
```

and near the top: `PAKS ?=` and `PAKS_FLAG = $(if $(PAKS),--paks "$(PAKS)",)`. Add `extract-version` to the header comment's target list.

- [ ] **Step 7: Run the suite** — `python -m unittest discover -s tests` green.

- [ ] **Step 8: Commit** — `git add .claude/skills/acr-setup-engineer/GAME_VERSION tools/car-catalog/write_game_version.py tools/car-catalog/extract_car_catalog.py tests/test_game_version_file.py Makefile` — message `GAME_VERSION file, written from the game's config`.

---

### Task 2: `decode_setups.py` — one presets asset to complete setups (research task)

This is the one task that needs judgement: the `PhysicsCarSetup` export is a nested unversioned struct whose schema isn't known. Dispatch it on the most capable model.

**Files:**
- Create: `tools/car-catalog/decode_setups.py`
- Create: `tests/fixtures/paks/DA_LanciaStratosHFPresets.uasset`, `tests/fixtures/paks/DA_LanciaRally037Evo2Presets.uasset`, plus the DT list tables the decoder needs (`DT_GearsSetsLists`, `DT_PrimaryGearsLists`, `DT_RearGearsLists`, `DT_FrontGearsLists`, `DT_CentreGearsLists`, `DT_CentreToRearGearsLists`, `DT_CentreToFrontGearsLists`, `DT_DiffRampsLists`, `DT_DiscsLists`, `DT_CalipersLists`, `DT_MasterCylindersLists`) — extract them once with `extract_car_catalog.extract(DEFAULT_PAKS, names, 'tests/fixtures/paks')`. Keep the fixture set under 1 MB total; the presets assets are ~30 KB each.
- Create: `tests/test_decode_setups.py`

**Interfaces:**
- Produces: `decode_car(pkg, tables) -> dict` with shape `{'base': {setting_id: value}, 'surfaces': {surface: {'overrides': {setting_id: value}, 'presets': {name: {setting_id: value}}}}}` where a value is a float, int, bool, or for a DB reference a tuple `('db', table_hint, row_name)`; `compose(decoded, surface, preset) -> {setting_id: value}` (base ⊕ surface ⊕ preset); `to_adjustments(values, template_rows, tables, car_keys) -> ({adjustment: display value}, [unfilled adjustment names])` mapping setting ids to template adjustment names via `mapping.py` (corners collapsed, left == right asserted; DB references resolved per the Global Constraints table); `surfaces_and_presets(decoded) -> [(surface, preset)]`.
- Consumes: `acrpkg.Package`, `datatable.rows`, `mapping` tables, `unversioned.read_header`.

**What is known** (verified on 2026-09-22, see the spec's *What the game files hold*):
- `pkg.surface_variants(main)` gives `{surface: export}`; `variant_ranges` skips value overrides — write the complementary walk that keeps `CarSettingOverrideFloat` / `Integer` / `Bool` / `ValueSetDBReference` (the `(idx, num, ref)` 12-byte scan in `acrpkg.setting_pairs` is the pattern).
- Named presets: at the end of a surface export there is a map `FName → FPackageIndex` of `CarSetupVariant` exports (`… 'Balanced' → ref, 'Aggressive' → ref …`); a variant export holds the same kind of override pairs (Balanced's is 6 bytes: empty).
- A `ValueSetDBReference` export is 24 bytes: FName (table hint) at byte 4, FName (row) at byte 12.
- `PhysicsCarSetup` (one export; 516 bytes on the Stratos) holds the base. It is nested: per-axle damper blocks are visible as float runs `4750, 6250, 0.1, 0.1, 1, 1` then `6250, 7250` (front: fast bump, fast rebound, bump transition, rebound transition, ?, ?, slow bump, slow rebound) and `3750, 5250, 0.15, 0.15, 1, 1, 4250, 5750` (rear), springs `65000` with adjuster ring `0.048`, pressure `28`, camber `-2.4`, front bias `0.57`, and names `GearsSets`/`LanciaStratosSet0`, `Gears`, `LSDRampAngles` for the list-valued settings. Headers are 2-byte unversioned fragments (`unversioned.read_header`), so the struct is **not** 4-byte aligned — walk it with `read_header` recursively, one sub-struct per known section, and pin the schema by the oracle values below rather than by guessing names.
- The car asset `DA_<Car>` (e.g. `DA_LanciaStratosHF`) repeats the same suspension block; the presets asset's `PhysicsCarSetup` is the one to use (self-contained per car).

**Oracles** (the decoder is done when all hold):
- Stratos, Tarmac, Balanced: `Gear Set "1"`, `Primary Gear "33//31*31//30"`, `Differential Ratio Rear "65//19"`, `LSD Power/Coast Ramp Rear "50/65"`, `LSD Preload Rear 100`, `Plates Number Rear 4`, `Spring Stiffness Front 65000`, `Spring Stiffness Rear 42500`, `Adjuster Ring Front 0.048`, `Slow Bump Front 6250`, `Slow Rebound Front 7250`, `Fast Bump Front 4750`, `Fast Rebound Front 6250`, `Slow Bump Rear 4250`, `Slow Rebound Rear 5750`, `Fast Bump Rear 3750`, `Fast Rebound Rear 5250`, `Anti-roll Bar Stiffness Front 3250`, `Anti-roll Bar Stiffness Rear 2500`, `Front Bias 0.57`, `Camber Front -2.4`, `Camber Rear -2`, `Pressure Front 27`, `Pressure Rear 26`, `Brake Pads Front "MEDIUM"`, `Brake Discs Front "267/156X28 B TYPE1"`, `Brake Calipers Rear "4X38.1 TYPE1"`. `Tyre Type` is `"Tarmac Soft"` **if** the presets asset carries a tyre setting; if it doesn't (the car asset `DA_LanciaStratosHF` names `TarmacSoft`, the presets asset may not), leave `Tyre Type` unfilled and say so in the report — it is then a spec open point for the controller, not a failed oracle.
- Stratos, Gravel, Balanced: `Spring Stiffness Front 35000`, `Spring Stiffness Rear 20000`, `Adjuster Ring Front 0.115`, `Slow Bump Front 5000`, `Fast Bump Rear 1750`, `Front Bias 0.53`, `Camber Front -2`, `Camber Rear -3`, `Pressure Front 30`, `LSD Preload Rear 90`, `LSD Power/Coast Ramp Rear "45/50"`, `Gear Set "2"`, `Brake Discs Front "271/160X22 P TYPE1"`, `Anti-roll Bar Stiffness Front 4250`, `Anti-roll Bar Stiffness Rear 0`.
- 037, Tarmac, Balanced (from the user's 0.5 capture; values that moved between 0.5 and 0.6 may legitimately differ — treat as a sanity check, not a hard assertion, and report each mismatch): `Gear Set "2"`, `LSD Power/Coast Ramp Rear "45/55"`, `LSD Preload Rear 120`, `Plates Number Rear 6`, `Spring Stiffness Front 50000`, `Spring Stiffness Rear 35000`, `Slow Bump Front 3750`, `Fast Bump Front 3250`, `Camber Front -1.4`, `Camber Rear -1.5`, `Pressure Front 32`, `Front Bias 0.5`.
- Across all 18 cars every composed value lies on the template's grid for its surface (`load_catalog.py --check` passes) — Task 3 runs this; design the decoder so it can.

- [ ] **Step 1: Extract the fixtures** into `tests/fixtures/paks/` (one Python call to `extract_car_catalog.extract`), and write the failing `tests/test_decode_setups.py` with one test per oracle group above (hard asserts for the Stratos groups, a soft report for the 037 group that asserts at least gear set, ramps, preload and plates), plus: `surfaces_and_presets` on the Stratos is `[('Tarmac','Balanced'),('Gravel','Balanced')]`; left ≠ right raises `AssertionError` (construct by patching one corner value in a decoded dict before `to_adjustments`).

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Write the decoder.** Start from the walks that exist (`surface_variants`, `setting_pairs`), add the variant-map walk, the value-override reader and the DB-reference reader, then decode `PhysicsCarSetup` against the oracle numbers. Document the schema you pin in the module docstring, section by section, with offsets from the Stratos fixture, so the next game update can be re-verified.

- [ ] **Step 4: Run the tests** until green. Run the full suite.

- [ ] **Step 5: Commit** — `decode_setups.py: game default setups out of the presets asset` (fixtures included).

---

### Task 3: `extract_default_setups.py` and the 18 bundled files

**Files:**
- Create: `tools/car-catalog/extract_default_setups.py`
- Create: `.claude/skills/acr-setup-engineer/car-setups/<slug>.yaml` × 18 (generated)
- Create: `tests/test_car_setups.py`
- Modify: `Makefile` (`extract-setups`, `extract-catalogs`, `extract`)

**Interfaces:**
- Consumes: Task 2's `decode_car`, `compose`, `to_adjustments`, `surfaces_and_presets`; `extract_car_catalog.extract`, `CAR_MAP`, `WANTED_TABLES`, `GAME_VERSION`, `TEMPLATES`; `load_catalog.load_template` and `check_values` (import from the skill's scripts dir, as `tests/test_load_catalog.py` does) for validation.
- Produces: the YAML files, the CLI `python tools/car-catalog/extract_default_setups.py [--dry-run] [--car SLUG] [--paks DIR]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_car_setups.py`:

```python
"""The bundled default setups in car-setups/ — one per car, complete, on the catalog grid,
stamped with the current game version.

Run: python -m unittest discover -s tests
"""
import glob
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SETUPS = os.path.join(SKILL, 'car-setups')
TEMPLATES = os.path.join(SKILL, 'car-templates')
LOADER = os.path.join(SKILL, 'scripts', 'load_default_setup.py')
CATALOG = os.path.join(SKILL, 'scripts', 'load_catalog.py')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import load_default_setup as lds  # noqa: E402


def slugs():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(TEMPLATES, '*.yaml')))


class TestFiles(unittest.TestCase):
    def test_every_template_car_has_a_setups_file(self):
        missing = [s for s in slugs() if not os.path.isfile(os.path.join(SETUPS, s + '.yaml'))]
        self.assertFalse(missing, missing)

    def test_header_matches_template_and_game_version(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            with open(os.path.join(TEMPLATES, s + '.yaml'), encoding='utf-8') as f:
                tpl = f.read()
            self.assertEqual(doc['version'], GAME_VERSION, s)
            self.assertIn(f'car: "{doc["car"]}"', tpl, s)
            self.assertEqual(doc['source'], 'game-files', s)

    def test_surfaces_and_presets(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            pairs = {(e['surface'], e['preset']) for e in doc['setups']}
            self.assertIn(('Tarmac', 'Balanced'), pairs, s)
            self.assertIn(('Gravel', 'Balanced'), pairs, s)
        for s in ('alpine-a110-1-8-1973', 'fiat-131-abarth-1976'):
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            self.assertIn(('Snow', 'Balanced'), {(e['surface'], e['preset']) for e in doc['setups']}, s)
        for s in ('lancia-delta-integrale-evoluzione-1992', 'peugeot-208-rally4'):
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            self.assertIn('Aggressive', {e['preset'] for e in doc['setups']}, s)

    def test_every_entry_is_legal_for_its_surface(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            for e in doc['setups']:
                values = os.path.join(REPO, 'tests', '_tmp_values.json')
                with open(values, 'w', encoding='utf-8') as f:
                    json.dump(e['values'], f)
                r = subprocess.run([sys.executable, CATALOG, os.path.join(TEMPLATES, s + '.yaml'),
                                    '--surface', e['surface'], '--check', values],
                                   capture_output=True, text=True, encoding='utf-8')
                os.remove(values)
                self.assertEqual(r.returncode, 0, f'{s} {e["surface"]} {e["preset"]}: {r.stdout}{r.stderr}')

    def test_stratos_tarmac_balanced_known_values(self):
        doc = lds.load_file(os.path.join(SETUPS, 'lancia-stratos.yaml'))
        v = next(e for e in doc['setups'] if (e['surface'], e['preset']) == ('Tarmac', 'Balanced'))['values']
        self.assertEqual(v['Spring Stiffness Front'], 65000)
        self.assertEqual(v['Spring Stiffness Rear'], 42500)
        self.assertEqual(v['Front Bias'], 0.57)
        self.assertEqual(v['Gear Set'], '1')
        self.assertEqual(v['Primary Gear'], '33//31*31//30')
        self.assertEqual(v['Differential Ratio Rear'], '65//19')


if __name__ == '__main__':
    unittest.main()
```

(`lds.load_file` is Task 4's parser; write Task 4's `load_file` first inside this task if you run Task 3 before Task 4 — or run Tasks 3 and 4 as one dispatch. Recommended: **one dispatch for Tasks 3 and 4**.)

Check `load_catalog.py --check`'s exact interface (`--check values.json` with the JSON shape it expects: read `check_values` and the USAGE string) and match the test to it — it exits 3 with a JSON report on an illegal value, 0 when all legal.

- [ ] **Step 2: Write the extractor**

```python
#!/usr/bin/env python3
"""Default setups out of the ACR game files -> car-setups/<slug>.yaml.

Each car's presets asset holds a base setup (PhysicsCarSetup), per-surface overrides and named
presets (Balanced on every car; Aggressive on a few). decode_setups.py reads them; this tool
composes every (surface, preset) into a complete setup keyed by the car's template parameter
names, checks each against the template's ranges with the skill's own load_catalog.py, and
writes the bundled file. Re-run after a game update (`make extract-setups`), read the diff.

Usage:
  python extract_default_setups.py [--dry-run] [--car SLUG] [--paks DIR]
"""
```

Structure (mirror `extract_car_catalog.main`): parse args; `slugs`; `wanted = WANTED_TABLES | presets assets`; extract into a temp dir; load tables; for each slug: `pkg = Package(...)`, `decoded = decode_car(pkg, tables)`, template rows via `load_template`, for each `(surface, preset)`: `values = compose(...)`, `adj, unfilled = to_adjustments(values, rows, tables, car_keys)`, run `check_values(rows_for_surface, adj, surface)` in-process (import from the skill's `load_catalog`), **raise** on any illegal value with the parameter, value and legal range; render; compare with the existing file (report changed values per entry, added/dropped entries, unfilled parameters); write unless `--dry-run`. Print one block per car like the catalog extractor does. `written_at` is today's date (`datetime.date.today().isoformat()`); when nothing but `written_at` would change, keep the old date so the run is idempotent.

Render:

```python
def render(doc):
    lines = [f'car: "{doc["car"]}"', 'game: "ACR"', f'version: "{doc["version"]}"',
             'source: "game-files"', f'written_at: "{doc["written_at"]}"', 'setups:']
    for e in doc['setups']:
        lines += [f'  - surface: "{e["surface"]}"', f'    preset: "{e["preset"]}"', '    values:']
        for k in sorted(e['values'], key=order_of):       # template order, not alphabetical
            v = e['values'][k]
            lines.append(f'      "{k}": {v if isinstance(v, (int, float)) and not isinstance(v, bool) else json.dumps(v)}')
    return '\n'.join(lines) + '\n'
```

where `order_of` uses the template's `Order`. Floats: print with `repr` trimmed (`0.048`, not `0.04800000041723251`): round to 6 significant digits via `float(f'{v:.6g}')`.

- [ ] **Step 3: Makefile**

```make
extract-catalogs:
	python tools/car-catalog/extract_car_catalog.py $(PAKS_FLAG)

extract-setups:
	python tools/car-catalog/extract_default_setups.py $(PAKS_FLAG)

# Everything that reads the installed game, in order: version first (every file is stamped with
# it), then catalogs, default setups, power/torque charts, ACR Car Lab data. Re-run after a game
# update, read the diff, run `make test`, commit.
extract: extract-version extract-catalogs extract-setups charts-power car-lab
```

Header comment: add the four targets. `.PHONY`: add them.

- [ ] **Step 4: Run the extraction** — `python tools/car-catalog/extract_default_setups.py` (from the repo root). Read the report: every car must have Tarmac and Gravel Balanced; list the unfilled parameters per car in your report. Then `python -m unittest tests.test_car_setups -v` green, then the full suite.

- [ ] **Step 5: Commit** — files + tool + Makefile + test — `car-setups/: bundled default setups for every car, extract-setups target`.

---

### Task 4: `scripts/load_default_setup.py`

**Files:**
- Create: `.claude/skills/acr-setup-engineer/scripts/load_default_setup.py`
- Create: `tests/test_load_default_setup.py`

**Interfaces:**
- Produces: `load_file(path) -> {'car','game','version','source','written_at','setups':[{'surface','preset','values':{...}}]}`; `pick(doc, surface, preset='Balanced') -> (entry, fallback)`; CLI:
  - `python scripts/load_default_setup.py --car <slug> --surface <Surface> [--preset NAME] [--pretty]` → JSON `{"car","version","surface","preset","fallback","values"}`
  - `--list <slug>` → JSON `{"car","version","setups":[{"surface","preset"}]}`
  - `--game-version` → prints the `GAME_VERSION` file content
  - exit 1: file missing, surface missing with no fallback, preset missing (stderr names the available ones); exit 2: unknown flag.
- Parser: stdlib, line-based, for exactly the shape in Global Constraints: header keys at column 0 (`key: "value"`), `setups:` then items `  - surface: "…"`, `    preset: "…"`, `    values:` and `      "Key": value` lines; a value is an int, a float, or a JSON string (use `json.loads` for quoted values, `int`/`float` otherwise).

- [ ] **Step 1: Write the failing tests** (fixture written by the test into a temp dir, matching the constraint shape; cases: parse header and two entries; `pick` Tarmac; Snow → Gravel with `fallback == 'Gravel'`; Snow present → no fallback; missing surface Tarmac → error; unknown preset → exit 1 listing presets; `--list`; `--game-version` equals the file; unknown flag exit 2; missing file exit 1; float values keep 6 significant digits).

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement** with the same conventions as `check_egress.py` / `setups_list.py` (docstring with usage, `argparse`, `use_utf8_output` pattern from `load_catalog.py` for Windows).

- [ ] **Step 4: Tests green, full suite green.**

- [ ] **Step 5: Commit** — `load_default_setup.py: read a bundled default setup`.

---

### Task 5: The skill anchors on the bundled setup

**Files:**
- Modify: `references/build-setup.md` step 4 (lines ~192–228) and step 12's report list; step 11 `Game version`
- Modify: `SKILL.md` *Baseline first* (line ~147) and the scripts list (add the loader; mention `GAME_VERSION`)
- Modify: `references/setups-list-read.md` step 4 (the default anchor bullet)
- Modify: `references/notion-structure.md` → *Default (stock) baseline rows* (one paragraph: read only for cars without a bundled file)
- Modify: `references/tweak-setup.md`, `references/capture-setup.md` (`Game version` from `GAME_VERSION`)
- Modify: `references/how-to-use-template.md` (one line)
- Modify: `tests/test_references.py`

**Interfaces:** consumes the loader CLI from Task 4.

- [ ] **Step 1: Guard tests** in `TestSetupIndex` (or a new `TestBundledDefaults` class) of `tests/test_references.py`:

```python
    def test_build_anchors_on_the_bundled_setup(self):
        text = self.ref('build-setup.md')
        self.assertIn('load_default_setup.py --car', text)
        self.assertIn('car-setups/', text)

    def test_skill_md_names_the_loader_and_game_version(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('scripts/load_default_setup.py', text)
        self.assertIn('GAME_VERSION', text)

    def test_game_version_fills_the_column(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md'):
            self.assertIn('GAME_VERSION', self.ref(name), name)

    def test_free_read_path_defers_to_bundled_defaults(self):
        self.assertIn('car-setups/', self.ref('setups-list-read.md'))
```

- [ ] **Step 2: Rewrite `build-setup.md` step 4.** Replace the opening of step 4 (up to the "**Never infer how the game scopes its defaults.**" paragraph) with:

```markdown
4. **Establish the baseline (the game's default setup).**

   **A car with a bundled setups file** (`car-setups/<slug>.yaml` exists in the skill — the same
   slug as its template) anchors on it, on every plan, with no Notion read and no screenshots:
   ```
   python scripts/load_default_setup.py --car <slug> --surface {Surface}
   ```
   (add `--preset Aggressive` only when the user asked for that preset by name; run it in the
   same code-execution block as `load_catalog.py`). Its `values` are the **numeric anchor** —
   go to **step 5b**. In the report (step 12) say *"anchored on the game's {preset} default for
   {Surface} (game version {version})"*, and when the output's `fallback` is `"Gravel"`, say the
   Snow anchor is the gravel preset because the game has no Snow default for this car. Notion
   `Source = default` rows are **not read** for such a car, whatever they hold.

   **A car with no bundled setups file** (a screenshot car) uses the stored defaults: fetch this
   car's `Source = default` rows (`… --source default`, per [notion-rest-read.md](notion-rest-read.md))
   in the step 1–4 batch — or, in offline mode, the default the car's `Setup index` gives
   ([setups-list-read.md](setups-list-read.md) → *Reading a car's setups on Free*) — then match on
   the **full capture context** — stage, surface, **and conditions**. Read values from the
   **row value properties**, never the page prose (`SKILL.md` → *A setup's real values are its row*).
```

Keep the rest of step 4 (the three bullets and the screenshots-first path) as it is: it now applies only to the second branch. Step 5's heading gets one clause: `5. **Capture the default (when the screenshots arrive — screenshot cars only).**`

Step 11: `` `Game version` (if known) `` → `` `Game version` — the content of the skill's `GAME_VERSION` file (`python scripts/load_default_setup.py --game-version`), unless the user said they run another version in this chat ``. Same phrase in `tweak-setup.md` (the row write) and `capture-setup.md` step 6.

Step 12 report list: add `the anchor line from step 4 (which default, which preset, which game version; the Snow→Gravel note when it applies)`.

- [ ] **Step 3: `SKILL.md`** *Baseline first* becomes:

```markdown
- **Baseline first — anchor on the game's own default setup.** The catalog gives legal *ranges* but
  no sense of where inside them the game itself sits, so a from-scratch build is anchored on nothing.
  The anchor, in this order: **the bundled default** in `car-setups/<slug>.yaml` (every template
  car; per surface, `Balanced` unless the user names another preset; read with
  `scripts/load_default_setup.py` — no Notion read, no screenshots, on every plan); else, for a
  screenshot car, a **captured default** (`Source = default`) for this car in this context; else
  ask for **setup-screen screenshots of the in-game default first**, capture it, and **check it
  (below) before recommending a drive**. Start from the anchor's values and move only what the
  driver's reported symptoms and the build's intent justify — parameters nothing points at keep
  the anchor's value.
```

Scripts list: add `- \`scripts/load_default_setup.py\` — the bundled default setup for a car and surface (\`--car <slug> --surface Tarmac|Gravel|Snow [--preset Balanced|Aggressive]\`, JSON; Snow falls back to Gravel and says so; \`--list <slug>\`; \`--game-version\` prints the skill's \`GAME_VERSION\` file — the current game version every bundled file was extracted from).` Root files list (where `VERSION` is described, line ~94): add `GAME_VERSION`.

- [ ] **Step 4: `setups-list-read.md`** step 4, default anchor bullet: prepend `For a car with a bundled \`car-setups/<slug>.yaml\` the anchor comes from \`load_default_setup.py\` (\`build-setup.md\` step 4) and the \`default\` line here is ignored.` Also step 2: `default` / `other_defaults` are only used for screenshot cars — one sentence.

- [ ] **Step 5: `notion-structure.md`** *Default (stock) baseline rows*: add as the first bullet: `**Read only for cars without a bundled setups file.** Every template car anchors on \`car-setups/<slug>.yaml\` (\`build-setup.md\` step 4); its stored default rows are left where they are and never read.`

- [ ] **Step 6: `how-to-use-template.md`**: under *What you can ask*, after **Build a setup**: `Setups start from the game's own default for the car and surface. Say "start from the Aggressive preset" for a car that has one (Lancia Delta, Peugeot 208 Rally4).`

- [ ] **Step 7: Full suite green. Commit** — `Build anchors on the bundled default setup; Game version from GAME_VERSION`.

---

### Task 6: Maintainer docs and consistency pass

**Files:**
- Modify: `tools/car-catalog/README.md` (a *Default setups* section: what the layers are, the oracle values, `make extract`), `README.md` (the "What it creates" / tooling paragraph that mentions car-templates; the Free-plan section's "A stored game default" bullet → bundled default, no screenshots), `CLAUDE.md` (file lists: `car-setups/`, `GAME_VERSION`, the two tools, the four tests).
- Modify: `references/free-plan-template.md` — the *A saved game default is reused* bullet becomes *Setups start from the game's own default setup, built into the skill. No screenshots needed.*

- [ ] **Step 1:** grep for text that is now wrong:

```
grep -rn -i "screenshots of the default\|screenshot the default\|stored game default\|saved game default" .claude/skills/acr-setup-engineer/SKILL.md .claude/skills/acr-setup-engineer/references/ README.md
```

Every hit must either be inside the screenshot-car branch or be rewritten.

- [ ] **Step 2:** the docs edits above.

- [ ] **Step 3:** `python -m unittest discover -s tests`, `make check-zip` (the zip now includes `car-setups/` and `GAME_VERSION` — check `check_zip.py` doesn't reject unknown top-level entries; if it whitelists, add them).

- [ ] **Step 4: Commit** — `Docs: bundled default setups, make extract`.
