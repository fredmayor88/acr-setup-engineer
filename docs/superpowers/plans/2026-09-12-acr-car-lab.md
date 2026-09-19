# ACR Car Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `acr-car-lab`, a free GitHub-Pages site with one interactive page per ACR car, showing the power/torque curve and four parametrizable gearing charts, fed by a one-command exporter in `acr-setup-engineer`.

**Architecture:** All pak parsing stays in `acr-setup-engineer`. A new `export_car_data.py` writes one JSON file and one page shell per car into a sibling `acr-car-lab` checkout. The site is static ES modules with zero dependencies: each chart module exports a pure `layout()` that is unit-tested under `node --test`, plus a dumb `render()` that turns that layout into SVG. Because the app code holds no numbers, a game patch is `make car-lab` plus a commit.

**Tech Stack:** Python 3 + `unittest` (exporter); vanilla ES modules + hand-rolled SVG + `node --test` (site); GitHub Pages; GoatCounter.

**Spec:** `docs/superpowers/specs/2026-09-12-acr-car-lab-design.md` — read it alongside this plan.

## Global Constraints

- **Two repos, side by side.** `acr-setup-engineer` and `acr-car-lab` share a parent directory. The exporter's default `--out` is `../acr-car-lab`.
- **Commits in `acr-setup-engineer` need Fred's explicit approval** (standing rule). Where a step says "commit" in that repo, stage the change and ask. Commits inside `acr-car-lab` are fine — it is a new repo created for this work.
- **No charting library, no runtime dependencies, no build step for the site.** Hand-rolled SVG only. External scripts would also break the "free and static" constraint.
- **Brand palette**, copied from `tools/gearing-charts/make_gearing_chart.py`:
  `WARM_WHITE #F5F2EB`, `GRAPHITE #30353A`, `DARK_GRAPHITE #212529`, `STEEL #7B858E`, `WALNUT #7A583B`, `DEEP_CYAN #148FAC`. Warning colour `#9C3B2E`. Cyan is an accent only.
  `SET_COLOURS = ["#7A583B","#148FAC","#30353A","#B07A4E","#0E6E85","#8D949B","#4FB3C9","#5A3F29"]`
- **`LOADED_RADIUS_FACTOR = 0.9562`** is the default rolling-radius factor, editable in the UI.
- **`REV_FLOOR = 3000`** rpm is the Shift points usable-revs floor.
- **Five surfaces**, keys and labels exactly: `Tarmac_Dry` "Dry tarmac", `Tarmac_Wet` "Wet tarmac", `Gravel` "Gravel", `Sweden` "Snow", `Montecarlo` "Winter tarmac". `MontecarloStudded` is out of scope for v1 and must not appear in the UI.
- **Speed formula:** `circumference = 2*PI*free_radius*factor`, then `kmh = rpm * circumference * 0.06 / total_ratio`, where `total_ratio = gear_value * primary_value * rest * option_value`.
- **Copy is sparse and factual. No defensive copy** — never justify a default or pre-empt a criticism. Avoid "quote" as a verb in UI text. Captions marked *verbatim* in the spec are exact strings; do not reword them.
- **Node 26 / Python 3.13** are installed. Site tests run with `node --test`; exporter tests run under the repo's existing `python -m unittest discover -s tests -v`.
- **Exporter tests must not require the game paks.** All pak reading lives in `main()`; everything testable is a pure function taking already-parsed values.

---

## File Structure

**`acr-setup-engineer`** (exporter side):

| File | Responsibility |
| --- | --- |
| `tools/gearing-charts/export_car_data.py` | Pure builders (`build_car_json`, `render_car_page`, `render_index_page`) plus a `main()` that does all pak reading. |
| `tests/test_export_car_data.py` | Unit tests for the pure builders, using hand-built inputs. |
| `Makefile` | New `car-lab` target. |

**`acr-car-lab`** (site side):

| File | Responsibility |
| --- | --- |
| `index.html` | Car picker. Reads `data/index.json`. |
| `app.css` | All styling. Palette tokens, control bar, panels, set list, footer. |
| `js/gearing.js` | Core math. Pure, no DOM. Unit tested. |
| `js/state.js` | State object, URL-hash read/write, input validation. Pure. Unit tested. |
| `js/svg.js` | SVG element helpers, tooltip box. No chart knowledge. |
| `js/charts/powerTorque.js` | Chart 1: `layout()` + `render()`. |
| `js/charts/finalDrive.js` | Chart 2: `layout()` + `render()`. |
| `js/charts/ladder.js` | Chart 3: `layout()` + `render()`. |
| `js/charts/shiftPoints.js` | Chart 4: `layout()` + `render()`. |
| `js/charts/speedRevs.js` | Chart 5: `layout()` + `render()`. |
| `js/tracking.js` | GoatCounter `track()` wrapper with dedupe. |
| `js/app.js` | Entry point: loads JSON, builds controls, wires cross-links, re-renders. |
| `data/<slug>.json`, `data/index.json` | Generated. Never hand-edited. |
| `<slug>/index.html` | Generated thin shell. |
| `test/*.test.js` | `node --test` unit tests for the pure modules. |
| `README.md` | What it is, and the update-after-a-game-patch procedure. |

Each chart file holds both its layout and its renderer because those two change together. The layout functions are pure so they can be tested without a DOM; the renderers are deliberately dumb.

This refines the spec's single-`app.js` sketch. The reason is testability: the math has to be importable by `node --test`, which a monolithic inline script cannot be.

---

## Task 1: Exporter — pure car JSON builder

**Files:**
- Create: `tools/gearing-charts/export_car_data.py`
- Test: `tests/test_export_car_data.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `build_car_json(slug, name, axle, gear_sets, engine_curve, final_drive, tyres, generated) -> dict`, where
  - `gear_sets` is `[[(spelling, value), ...], ...]` — outer list is gear sets, inner is forward gears in order
  - `engine_curve` is `[(rpm, torque_nm), ...]`
  - `final_drive` is `None`, or `{"adjustment": str, "primaries": [(spelling, value)], "options": [(spelling, value)], "stock_option": str, "rest": float}`
  - `tyres` is `{surface_key: (asset_name, free_radius)}`
  - `generated` is an ISO date string

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_car_data.py`:

```python
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from export_car_data import build_car_json  # noqa: E402


def stratos_inputs():
    """A trimmed but real Lancia Stratos, read from the game files on 2026-09-12."""
    sets = [
        [('42//15', 2.800), ('40//19', 2.053), ('37//23', 1.619),
         ('33//25', 1.320), ('30//26', 1.154)],
        [('44//14', 3.143), ('38//17', 2.235), ('37//21', 1.762),
         ('34//24', 1.417), ('30//26', 1.154)],
    ]
    curve = [(3000, 198.0), (6000, 260.0), (7750, 240.0), (8750, 192.0)]
    fd = {
        'adjustment': 'Differential Ratio Rear',
        'primaries': [('35//30*33//28', 1.375), ('33//31*31//30', 1.100)],
        'options': [('65//17', 3.8235), ('65//19', 3.4211)],
        'stock_option': '65//19',
        'rest': 1.0,
    }
    tyres = {'Tarmac_Dry': ('PirelliT03', 0.2960),
             'Montecarlo': ('PirelliTM00', 0.3135)}
    return sets, curve, fd, tyres


class BuildCarJson(unittest.TestCase):
    def setUp(self):
        sets, curve, fd, tyres = stratos_inputs()
        self.doc = build_car_json('lancia-stratos', 'Lancia Stratos HF', 'Rear',
                                  sets, curve, fd, tyres, '2026-09-12')

    def test_identity_fields(self):
        self.assertEqual(self.doc['slug'], 'lancia-stratos')
        self.assertEqual(self.doc['name'], 'Lancia Stratos HF')
        self.assertEqual(self.doc['axle'], 'Rear')
        self.assertEqual(self.doc['generated'], '2026-09-12')

    def test_redline_is_the_highest_rpm_in_the_curve(self):
        self.assertEqual(self.doc['engine']['redline'], 8750)

    def test_curve_carries_power_in_kw(self):
        # kW = Nm * rpm / 9549
        row = [r for r in self.doc['engine']['curve'] if r[0] == 6000][0]
        self.assertEqual(row[1], 260.0)
        self.assertAlmostEqual(row[2], 260.0 * 6000 / 9549, places=3)

    def test_peaks_are_located_by_value_not_assumed(self):
        self.assertEqual(self.doc['engine']['peak_torque_rpm'], 6000)
        self.assertEqual(self.doc['engine']['peak_power_rpm'], 7750)

    def test_gear_sets_carry_label_spelling_and_value(self):
        first = self.doc['gear_sets'][0]
        self.assertEqual(first['label'], 'Gear set 1')
        self.assertEqual(first['gears'][0], {'name': '42//15', 'value': 2.800})
        self.assertEqual(len(self.doc['gear_sets'][1]['gears']), 5)

    def test_tyres_carry_free_radius_not_circumference(self):
        # the browser applies the loaded-radius factor, so the stored value is the
        # free radius and nothing else
        self.assertEqual(self.doc['tyres']['Tarmac_Dry'],
                         {'asset': 'PirelliT03', 'free_radius': 0.2960})

    def test_default_factor_is_exported(self):
        self.assertEqual(self.doc['defaults']['loaded_radius_factor'], 0.9562)

    def test_final_drive_options_carry_spelling_and_value(self):
        fd = self.doc['final_drive']
        self.assertEqual(fd['adjustment'], 'Differential Ratio Rear')
        self.assertEqual(fd['stock_option'], '65//19')
        self.assertEqual(fd['rest'], 1.0)
        self.assertEqual(fd['options'][0], {'name': '65//17', 'value': 3.8235})
        self.assertEqual(len(fd['primaries']), 2)

    def test_non_adjustable_final_drive_is_null(self):
        sets, curve, _, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Front', sets, curve, None, tyres, '2026-09-12')
        self.assertIsNone(doc['final_drive'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_export_car_data -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'export_car_data'`

- [ ] **Step 3: Write the minimal implementation**

Create `tools/gearing-charts/export_car_data.py`:

```python
"""Export one JSON document per car for the ACR Car Lab site.

Where make_gearing_chart.py draws PNGs, this writes the same facts as data and lets the
browser do the arithmetic. The split matters for one reason: the site exposes an editable
rolling-radius factor, so the stored tyre figure has to be the free radius with no factor
baked into it.

    python export_car_data.py --all --out ../acr-car-lab
"""

LOADED_RADIUS_FACTOR = 0.9562


def _kw(torque_nm, rpm):
    """Engine power in kW from torque in Nm at a given engine speed."""
    return torque_nm * rpm / 9549


def build_car_json(slug, name, axle, gear_sets, engine_curve, final_drive, tyres,
                   generated):
    """One car's complete published record.

    Every downstream number on the site is derived from this document, so anything the
    browser cannot recompute has to be in here.
    """
    curve = [[rpm, torque, _kw(torque, rpm)] for rpm, torque in engine_curve]
    peak_torque = max(curve, key=lambda r: r[1])
    peak_power = max(curve, key=lambda r: r[2])

    doc = {
        'slug': slug,
        'name': name,
        'axle': axle,
        'engine': {
            'redline': max(r[0] for r in curve),
            'peak_torque_rpm': peak_torque[0],
            'peak_power_rpm': peak_power[0],
            'curve': curve,
        },
        'gear_sets': [
            {'label': f'Gear set {i + 1}',
             'gears': [{'name': n, 'value': v} for n, v in gears]}
            for i, gears in enumerate(gear_sets)
        ],
        'final_drive': None,
        'tyres': {key: {'asset': asset, 'free_radius': radius}
                  for key, (asset, radius) in tyres.items()},
        'defaults': {'loaded_radius_factor': LOADED_RADIUS_FACTOR},
        'generated': generated,
    }

    if final_drive is not None:
        doc['final_drive'] = {
            'adjustment': final_drive['adjustment'],
            'primaries': [{'name': n, 'value': v}
                          for n, v in final_drive['primaries']],
            'options': [{'name': n, 'value': v} for n, v in final_drive['options']],
            'stock_option': final_drive['stock_option'],
            'rest': final_drive['rest'],
        }
    return doc
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_export_car_data -v`
Expected: PASS, 9 tests.

- [ ] **Step 5: Run the full suite to confirm nothing regressed**

Run: `make test`
Expected: all existing tests still pass.

- [ ] **Step 6: Stage and ask before committing** (standing rule for this repo)

```bash
git add tools/gearing-charts/export_car_data.py tests/test_export_car_data.py
# then ask Fred before: git commit -m "feat: car-lab JSON builder"
```

---

## Task 2: Exporter — page shells and the car index

**Files:**
- Modify: `tools/gearing-charts/export_car_data.py`
- Modify: `tests/test_export_car_data.py`

**Interfaces:**
- Consumes: `build_car_json` from Task 1.
- Produces:
  - `render_car_page(slug, name) -> str` — the generated `<slug>/index.html`
  - `render_index_page(cars) -> str` — the generated root `index.html`, where `cars` is `[{"slug": str, "name": str}]`
  - `build_index_json(cars) -> dict`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_car_data.py`, above the `if __name__` block:

```python
from export_car_data import (build_index_json, render_car_page,  # noqa: E402
                             render_index_page)


class RenderPages(unittest.TestCase):
    def test_car_page_bakes_in_name_for_search(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('<title>Lancia Stratos HF — ACR Car Lab</title>', html)
        self.assertIn('<h1>Lancia Stratos HF</h1>', html)

    def test_car_page_names_its_own_slug_for_the_app_to_read(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('data-car="lancia-stratos"', html)

    def test_car_page_uses_parent_relative_asset_paths(self):
        # pages live at /<slug>/, so shared assets are one level up
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('../app.css', html)
        self.assertIn('../js/app.js', html)

    def test_car_page_escapes_the_name(self):
        html = render_car_page('x', 'A & B <script>')
        self.assertNotIn('<script>A', html)
        self.assertIn('A &amp; B &lt;script&gt;', html)

    def test_index_json_lists_cars_sorted_by_name(self):
        doc = build_index_json([{'slug': 'b', 'name': 'Zeta'},
                                {'slug': 'a', 'name': 'Alpha'}])
        self.assertEqual([c['slug'] for c in doc['cars']], ['a', 'b'])

    def test_index_page_links_every_car(self):
        html = render_index_page([{'slug': 'lancia-stratos',
                                   'name': 'Lancia Stratos HF'}])
        self.assertIn('href="lancia-stratos/"', html)
        self.assertIn('Lancia Stratos HF', html)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_export_car_data -v`
Expected: FAIL — `ImportError: cannot import name 'build_index_json'`

- [ ] **Step 3: Write the minimal implementation**

Add to `tools/gearing-charts/export_car_data.py`:

```python
import html as _html

CAR_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — ACR Car Lab</title>
<meta name="description" content="Gearing, final drive and power for the {name} in \
Assetto Corsa Rally.">
<link rel="stylesheet" href="../app.css">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap" id="app" data-car="{slug}">
  <header>
    <div class="brandrow">
      <span class="brand">ACR <b>Car Lab</b></span>
      <a class="crumb" href="../">All cars →</a>
    </div>
    <h1>{name}</h1>
  </header>
  <p class="loading">Loading…</p>
</div>
<script type="module" src="../js/app.js"></script>
</body></html>
"""

INDEX_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ACR Car Lab</title>
<meta name="description" content="Interactive gearing and power charts for every car in \
Assetto Corsa Rally.">
<link rel="stylesheet" href="app.css">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brandrow"><span class="brand">ACR <b>Car Lab</b></span></div>
    <h1>Every car, gear by gear</h1>
    <p class="sub">Gearing, final drive and power, read from the game files.</p>
  </header>
  <ul class="carlist">
{items}
  </ul>
</div>
</body></html>
"""


def render_car_page(slug, name):
    """The generated shell for one car. Title and h1 are baked in so the page is
    indexable without running the app."""
    safe = _html.escape(name)
    return CAR_PAGE.format(slug=_html.escape(slug), name=safe)


def build_index_json(cars):
    """The car list the picker reads, sorted by display name."""
    return {'cars': sorted(({'slug': c['slug'], 'name': c['name']} for c in cars),
                           key=lambda c: c['name'])}


def render_index_page(cars):
    items = '\n'.join(
        f'    <li><a href="{_html.escape(c["slug"])}/">{_html.escape(c["name"])}</a></li>'
        for c in build_index_json(cars)['cars'])
    return INDEX_PAGE.format(items=items)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_export_car_data -v`
Expected: PASS, 15 tests.

- [ ] **Step 5: Stage and ask before committing**

```bash
git add tools/gearing-charts/export_car_data.py tests/test_export_car_data.py
```

---

## Task 3: Exporter — read the paks and write the files

**Files:**
- Modify: `tools/gearing-charts/export_car_data.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `build_car_json`, `render_car_page`, `render_index_page`, `build_index_json`.
- Produces: a populated `../acr-car-lab/data/` and `../acr-car-lab/<slug>/index.html` for every car in `make_gearing_chart.CARS`, and a `make car-lab` target.

This task has no unit test — it reads the installed game. It is verified by running it and checking a known number.

- [ ] **Step 1: Add the pak-reading `main()`**

Add to `tools/gearing-charts/export_car_data.py`. It imports the existing parsers rather than reimplementing any of them:

```python
import argparse
import datetime
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'torque-curves'))

import make_gearing_chart as M                                    # noqa: E402
from gearing import gear_set, ratio, drivetrain_chain             # noqa: E402

# Only the surfaces that resolve to a real tyre asset. MontecarloStudded is excluded:
# DA_PirelliTM00Studded does not exist under the name DT_Wheels gives it.
SURFACES = ('Tarmac_Dry', 'Tarmac_Wet', 'Gravel', 'Sweden', 'Montecarlo')


def car_record(paks, slug, tmp):
    """Everything build_car_json needs for one car, read from the game files."""
    asset, wheel_key, car_asset = M.CARS[slug]
    axle = 'Front' if 'front' in slug else 'Rear'   # replaced below by the real value

    files = M.extract(paks, f'DA_{asset}_GearSet_', tmp)
    if not files:
        raise SystemExit(f'{slug}: no gear set assets')
    sets = [gear_set(f) for f in files]

    primaries, candidates, _t, _p, _max = M.template_facts(slug, 'Rear')
    fd_value, spelled, chain = M.stock_final_drive(paks, car_asset, 'Rear', tmp)
    # the driven axle decides which branch of the chain counts; try both and keep the
    # one whose adjustable ratio actually sits in the driven path
    axle = 'Rear'
    name, options, stock = M.pick_ratio(candidates, chain, axle)
    if not options:
        axle = 'Front'
        primaries, candidates, _t, _p, _max = M.template_facts(slug, axle)
        fd_value, spelled, chain = M.stock_final_drive(paks, car_asset, axle, tmp)
        name, options, stock = M.pick_ratio(candidates, chain, axle)

    final_drive = None
    if options:
        stock_primary = sets[0][1]
        rest = (ratio(stock_primary) * fd_value) / (ratio(stock_primary) * ratio(stock))
        final_drive = {
            'adjustment': name,
            'primaries': [(p, ratio(p)) for p in (primaries or [stock_primary])],
            'options': [(o, ratio(o)) for o in options],
            'stock_option': stock,
            'rest': rest,
        }

    tyres = {}
    for surface in SURFACES:
        try:
            tyre_name, _circ, _compound = M.tyre(paks, wheel_key, surface, axle, tmp)
        except SystemExit:
            continue                       # a car with no tyre for this surface
        from gearing import tyre_geometry
        from acrpkg import Package
        hits = M.extract(paks, f'DA_{tyre_name}', tmp)
        pkg = Package(open(hits[0], 'rb').read())
        geo = tyre_geometry(pkg.export_bytes(0)[1])
        tyres[surface] = (tyre_name, round(geo[1], 6))

    import re
    text = open(os.path.join(M.TEMPLATES, slug + '.yaml'), encoding='utf-8').read()
    curve = [(int(r), float(v)) for r, v in re.findall(r'\[(\d+), ([\d.]+)\]', text)]
    display = re.search(r'^name: "(.*)"', text, re.MULTILINE)
    display_name = display.group(1) if display else slug

    return display_name, axle, sets, curve, final_drive, tyres


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=M.DEFAULT_PAKS)
    ap.add_argument('--car', default='lancia-stratos')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--out', default=os.path.join(REPO, '..', 'acr-car-lab'))
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    if not os.path.isdir(out):
        raise SystemExit(f'no acr-car-lab checkout at {out}')
    os.makedirs(os.path.join(out, 'data'), exist_ok=True)

    slugs = sorted(M.CARS) if args.all else [args.car]
    today = datetime.date.today().isoformat()
    cars = []
    with tempfile.TemporaryDirectory() as tmp:
        for slug in slugs:
            name, axle, sets, curve, fd, tyres = car_record(args.paks, slug, tmp)
            gears = [[(g, ratio(g)) for g in forward] for forward, _p, _r in sets]
            doc = build_car_json(slug, name, axle, gears, curve, fd, tyres, today)
            with open(os.path.join(out, 'data', slug + '.json'), 'w',
                      encoding='utf-8', newline='\n') as fh:
                json.dump(doc, fh, indent=1)
                fh.write('\n')
            os.makedirs(os.path.join(out, slug), exist_ok=True)
            with open(os.path.join(out, slug, 'index.html'), 'w',
                      encoding='utf-8', newline='\n') as fh:
                fh.write(render_car_page(slug, name))
            cars.append({'slug': slug, 'name': name})
            print(f'{slug}: {len(gears)} gear sets, {len(tyres)} surfaces')

    if args.all:
        with open(os.path.join(out, 'data', 'index.json'), 'w',
                  encoding='utf-8', newline='\n') as fh:
            json.dump(build_index_json(cars), fh, indent=1)
            fh.write('\n')
        with open(os.path.join(out, 'index.html'), 'w',
                  encoding='utf-8', newline='\n') as fh:
            fh.write(render_index_page(cars))


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Add the Makefile target**

In `Makefile`, add `car-lab` to the `.PHONY` line, add it to the Targets comment block as
`#   make car-lab     regenerate the ACR Car Lab data in ../acr-car-lab`, and append:

```makefile
# Regenerates every ACR Car Lab JSON and page shell into the sibling acr-car-lab
# checkout. Reads the installed game's paks, so it only runs on a machine with
# Assetto Corsa Rally. Re-run after a game update, then commit in acr-car-lab.
car-lab:
	python tools/gearing-charts/export_car_data.py --all
```

- [ ] **Step 3: Create the sibling checkout so the exporter has somewhere to write**

```bash
mkdir -p ../acr-car-lab && cd ../acr-car-lab && git init && cd -
```

- [ ] **Step 4: Run the exporter for one car and read the output**

Run: `python tools/gearing-charts/export_car_data.py --car lancia-stratos`
Expected: prints `lancia-stratos: 3 gear sets, 5 surfaces`, and `../acr-car-lab/data/lancia-stratos.json` exists.

- [ ] **Step 5: Spot-check a number against the known-good figure**

```bash
python -c "
import json, math
d = json.load(open('../acr-car-lab/data/lancia-stratos.json'))
k = d['defaults']['loaded_radius_factor']
circ = 2*math.pi*d['tyres']['Tarmac_Dry']['free_radius']*k
fd = d['final_drive']
p = [x for x in fd['primaries'] if x['name'] == '33//31*31//30'][0]['value']
o = [x for x in fd['options'] if x['name'] == fd['stock_option']][0]['value']
top = min(g['value'] for g in d['gear_sets'][0]['gears'])
print(round(d['engine']['redline']*circ*0.06/(top*p*fd['rest']*o)))
"
```

Expected: `215`. This is the Stratos, gear set 1, top gear, stock final drive, dry tarmac — the same number the current PNG chart reports. If it differs, stop: the `rest` calculation or the tyre radius is wrong, and every chart on the site would inherit the error.

- [ ] **Step 6: Run the full export**

Run: `make car-lab`
Expected: one line per car for all 18, `../acr-car-lab/index.html` and `data/index.json` written. The four cars listed in the spec's Known limits (i20, Fabia, Polo R5, 208 Rally4) must show `"final_drive": null`. Verify:

```bash
python -c "
import glob, json
for f in sorted(glob.glob('../acr-car-lab/data/*.json')):
    if f.endswith('index.json'): continue
    d = json.load(open(f))
    if d['final_drive'] is None: print('no final drive:', d['slug'])
"
```

- [ ] **Step 7: Stage in acr-setup-engineer and ask; commit in acr-car-lab**

```bash
git add tools/gearing-charts/export_car_data.py Makefile
cd ../acr-car-lab && git add -A && git commit -m "chore: generated car data and page shells"
```

---

## Task 4: Site — the core math module

**Files:**
- Create: `../acr-car-lab/js/gearing.js`
- Test: `../acr-car-lab/test/gearing.test.js`

All remaining tasks happen inside `../acr-car-lab`. Run commands from that directory.

**Interfaces:**
- Consumes: the JSON shape from Task 1.
- Produces:
  - `circumference(freeRadius, factor) -> number`
  - `kmh(rpm, totalRatio, circ) -> number`
  - `rpmAt(speedKmh, totalRatio, circ) -> number`
  - `totalRatio(gearValue, primaryValue, rest, optionValue) -> number`
  - `finalDriveCombos(finalDrive) -> [{primary, option, value}]` sorted longest-ratio first (shortest gearing first)
  - `gearTops(gears, fdValue, circ, redline) -> [number]`
  - `gearAtSpeed(tops, speedKmh) -> number` — index of the lowest gear whose top speed is not yet passed
  - `DEFAULT_FACTOR`, `REV_FLOOR`, `SURFACES`, `SET_COLOURS`

- [ ] **Step 1: Write the failing test**

Create `test/gearing.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  circumference, kmh, rpmAt, totalRatio, finalDriveCombos, gearTops, gearAtSpeed,
  DEFAULT_FACTOR, REV_FLOOR, SURFACES,
} from '../js/gearing.js';

const near = (a, b, eps = 0.5) =>
  assert.ok(Math.abs(a - b) < eps, `${a} is not within ${eps} of ${b}`);

// Lancia Stratos HF, dry tarmac, read from the game files
const R = 0.2960;
const CIRC = circumference(R, DEFAULT_FACTOR);

test('circumference applies the loaded-radius factor to the free radius', () => {
  near(CIRC, 2 * Math.PI * R * 0.9562, 1e-9);
});

test('the factor is what makes the control real — a different factor moves the number', () => {
  assert.notEqual(circumference(R, 0.99), CIRC);
});

test('top gear at the rev limit on the stock final drive is 215 km/h', () => {
  const total = totalRatio(1.154, 1.100, 1.0, 3.4211);
  near(kmh(8750, total, CIRC), 215, 1);
});

test('rpmAt inverts kmh', () => {
  const total = totalRatio(1.619, 1.100, 1.0, 3.4211);
  const v = kmh(6000, total, CIRC);
  near(rpmAt(v, total, CIRC), 6000, 1e-6);
});

test('finalDriveCombos is sorted shortest gearing first', () => {
  const combos = finalDriveCombos({
    primaries: [{ name: 'a', value: 1.375 }, { name: 'b', value: 1.100 }],
    options: [{ name: 'x', value: 3.8235 }, { name: 'y', value: 3.4211 }],
    rest: 1.0,
  });
  assert.equal(combos.length, 4);
  // biggest overall ratio = shortest gearing = first
  assert.equal(combos[0].value, 1.375 * 3.8235);
  assert.ok(combos[0].value > combos[3].value);
  assert.equal(combos[0].primary.name, 'a');
  assert.equal(combos[0].option.name, 'x');
});

test('finalDriveCombos folds in rest so drivetrain layout cannot skew the ratio', () => {
  const combos = finalDriveCombos({
    primaries: [{ name: 'a', value: 2 }],
    options: [{ name: 'x', value: 3 }],
    rest: 1.5,
  });
  assert.equal(combos[0].value, 9);
});

test('gearTops gives each gear its speed at the rev limit', () => {
  const gears = [{ name: '', value: 2.8 }, { name: '', value: 1.154 }];
  const tops = gearTops(gears, 1.100 * 3.4211, CIRC, 8750);
  near(tops[0], 89, 1);
  near(tops[1], 215, 1);
});

test('gearAtSpeed picks the lowest gear that has not topped out', () => {
  const tops = [89, 121, 153, 188, 215];
  assert.equal(gearAtSpeed(tops, 132), 2);   // third gear, zero-indexed
  assert.equal(gearAtSpeed(tops, 89), 0);    // exactly at a top speed stays in that gear
  assert.equal(gearAtSpeed(tops, 0), 0);
});

test('gearAtSpeed clamps above the top gear rather than returning -1', () => {
  assert.equal(gearAtSpeed([89, 121, 153], 400), 2);
});

test('constants match the spec', () => {
  assert.equal(DEFAULT_FACTOR, 0.9562);
  assert.equal(REV_FLOOR, 3000);
  assert.deepEqual(SURFACES.map(s => s.key),
    ['Tarmac_Dry', 'Tarmac_Wet', 'Gravel', 'Sweden', 'Montecarlo']);
  assert.deepEqual(SURFACES.map(s => s.label),
    ['Dry tarmac', 'Wet tarmac', 'Gravel', 'Snow', 'Winter tarmac']);
});

test('studded Montecarlo is not offered', () => {
  assert.ok(!SURFACES.some(s => s.key.includes('Studded')));
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/gearing.js`

- [ ] **Step 3: Write the minimal implementation**

Create `js/gearing.js`:

```js
// Core gearing arithmetic. Pure — no DOM, no globals. Everything the charts show is
// derived from these five functions, which is why they are the only unit-tested surface
// that really matters.

export const DEFAULT_FACTOR = 0.9562;
export const REV_FLOOR = 3000;

export const SURFACES = [
  { key: 'Tarmac_Dry', label: 'Dry tarmac' },
  { key: 'Tarmac_Wet', label: 'Wet tarmac' },
  { key: 'Gravel', label: 'Gravel' },
  { key: 'Sweden', label: 'Snow' },
  { key: 'Montecarlo', label: 'Winter tarmac' },
];

export const SET_COLOURS = ['#7A583B', '#148FAC', '#30353A', '#B07A4E', '#0E6E85',
                            '#8D949B', '#4FB3C9', '#5A3F29'];

/** A loaded tyre rolls on a smaller radius than the stored free one. */
export const circumference = (freeRadius, factor) => 2 * Math.PI * freeRadius * factor;

/** Road speed for an engine speed and an overall ratio. */
export const kmh = (rpm, total, circ) => rpm * circ * 0.06 / total;

/** The inverse: engine speed for a road speed. */
export const rpmAt = (speed, total, circ) => speed * total / (circ * 0.06);

/** Engine-to-wheel ratio for one gear at one final-drive combination. */
export const totalRatio = (gear, primary, rest, option) => gear * primary * rest * option;

/**
 * Every selectable final-drive combination, shortest gearing first.
 * `rest` is the part of the driven path that is not adjustable; folding it in here keeps
 * km/h honest whatever the drivetrain layout.
 */
export function finalDriveCombos(fd) {
  const out = [];
  for (const primary of fd.primaries) {
    for (const option of fd.options) {
      out.push({ primary, option, value: primary.value * fd.rest * option.value });
    }
  }
  return out.sort((a, b) => b.value - a.value);
}

/** Where each gear tops out, in km/h. */
export const gearTops = (gears, fdValue, circ, redline) =>
  gears.map(g => kmh(redline, g.value * fdValue, circ));

/**
 * The gear you are in at a given speed: the lowest one that has not topped out yet.
 * Clamped to top gear, because past the last top speed there is nothing higher to pick.
 */
export function gearAtSpeed(tops, speed) {
  const i = tops.findIndex(v => v >= speed);
  return i < 0 ? tops.length - 1 : i;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add js/gearing.js test/gearing.test.js
git commit -m "feat: core gearing math"
```

---

## Task 5: Site — state and URL hash

**Files:**
- Create: `js/state.js`
- Test: `test/state.test.js`

**Interfaces:**
- Consumes: `SURFACES`, `DEFAULT_FACTOR` from `js/gearing.js`.
- Produces:
  - `defaultState(car) -> {surface, fd, set, draw, k}` — `fd` is an index into `finalDriveCombos`, `set` an index into `gear_sets`, `draw` an array of gear-set indices, `k` the factor
  - `parseHash(hash, car) -> state` — invalid or out-of-range values fall back to the default
  - `toHash(state, car) -> string`

- [ ] **Step 1: Write the failing test**

Create `test/state.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, parseHash, toHash } from '../js/state.js';

const car = {
  gear_sets: [{ label: 'Gear set 1', gears: [] }, { label: 'Gear set 2', gears: [] },
              { label: 'Gear set 3', gears: [] }],
  final_drive: {
    primaries: [{ name: 'a', value: 1.375 }, { name: 'b', value: 1.1 }],
    options: [{ name: 'x', value: 3.8 }, { name: 'y', value: 3.4 }],
    stock_option: 'y', rest: 1,
  },
  tyres: { Tarmac_Dry: {}, Gravel: {} },
  defaults: { loaded_radius_factor: 0.9562 },
};

test('the default state is dry tarmac, first gear set, first set drawn', () => {
  const s = defaultState(car);
  assert.equal(s.surface, 'Tarmac_Dry');
  assert.equal(s.set, 0);
  assert.deepEqual(s.draw, [0]);
  assert.equal(s.k, 0.9562);
});

test('exactly one gear set is drawn by default', () => {
  assert.equal(defaultState(car).draw.length, 1);
});

test('a full hash round-trips', () => {
  const s = { surface: 'Gravel', fd: 2, set: 1, draw: [0, 2], k: 0.97 };
  assert.deepEqual(parseHash(toHash(s, car), car), s);
});

test('a surface the car does not have falls back to the default', () => {
  assert.equal(parseHash('#s=Sweden', car).surface, 'Tarmac_Dry');
});

test('a surface that is not a real key falls back to the default', () => {
  assert.equal(parseHash('#s=Moon', car).surface, 'Tarmac_Dry');
});

test('an out-of-range gear set falls back to the default', () => {
  assert.equal(parseHash('#set=99', car).set, 0);
  assert.equal(parseHash('#set=-1', car).set, 0);
  assert.equal(parseHash('#set=banana', car).set, 0);
});

test('an out-of-range final drive falls back to the default', () => {
  assert.equal(parseHash('#fd=999', car).fd, defaultState(car).fd);
});

test('drawn sets drop out-of-range entries and never end up empty', () => {
  assert.deepEqual(parseHash('#draw=0,99', car).draw, [0]);
  assert.deepEqual(parseHash('#draw=99', car).draw, [0]);
  assert.deepEqual(parseHash('#draw=', car).draw, [0]);
});

test('drawn sets are de-duplicated and sorted', () => {
  assert.deepEqual(parseHash('#draw=2,0,2', car).draw, [0, 2]);
});

test('the factor is clamped to a sane range', () => {
  assert.equal(parseHash('#k=0', car).k, 0.9562);
  assert.equal(parseHash('#k=-3', car).k, 0.9562);
  assert.equal(parseHash('#k=99', car).k, 0.9562);
  assert.equal(parseHash('#k=1.02', car).k, 1.02);
});

test('an empty hash gives the default state', () => {
  assert.deepEqual(parseHash('', car), defaultState(car));
  assert.deepEqual(parseHash('#', car), defaultState(car));
});

test('a car with no adjustable final drive still parses', () => {
  const plain = { ...car, final_drive: null };
  assert.equal(parseHash('#fd=3', plain).fd, 0);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/state.js`

- [ ] **Step 3: Write the minimal implementation**

Create `js/state.js`:

```js
// Page state, and its round trip through the URL hash. A link has to reproduce exactly
// what someone was looking at, so every control's value lives here and nowhere else.
// Values arriving from a URL get the same validation as typed input.

import { DEFAULT_FACTOR, SURFACES, finalDriveCombos } from './gearing.js';

const K_MIN = 0.80;
const K_MAX = 1.10;

const surfacesFor = car =>
  SURFACES.filter(s => Object.prototype.hasOwnProperty.call(car.tyres, s.key));

const combosFor = car => (car.final_drive ? finalDriveCombos(car.final_drive) : []);

/** The combination the car ships with, so the page opens on something real. */
function stockIndex(car) {
  const combos = combosFor(car);
  if (!combos.length) return 0;
  const i = combos.findIndex(c => c.option.name === car.final_drive.stock_option);
  return i < 0 ? 0 : i;
}

export function defaultState(car) {
  const available = surfacesFor(car);
  return {
    surface: available.length ? available[0].key : 'Tarmac_Dry',
    fd: stockIndex(car),
    set: 0,
    draw: [0],
    k: car.defaults?.loaded_radius_factor ?? DEFAULT_FACTOR,
  };
}

const intOr = (raw, fallback) => {
  const n = Number.parseInt(raw, 10);
  return Number.isInteger(n) ? n : fallback;
};

export function parseHash(hash, car) {
  const base = defaultState(car);
  const q = new URLSearchParams((hash || '').replace(/^#/, ''));
  const out = { ...base };

  const surface = q.get('s');
  if (surface && surfacesFor(car).some(x => x.key === surface)) out.surface = surface;

  const combos = combosFor(car);
  const fd = intOr(q.get('fd'), -1);
  if (fd >= 0 && fd < combos.length) out.fd = fd;

  const set = intOr(q.get('set'), -1);
  if (set >= 0 && set < car.gear_sets.length) out.set = set;

  if (q.has('draw')) {
    const drawn = [...new Set((q.get('draw') || '').split(',')
      .map(v => intOr(v, -1))
      .filter(i => i >= 0 && i < car.gear_sets.length))].sort((a, b) => a - b);
    if (drawn.length) out.draw = drawn;
  }

  const k = Number.parseFloat(q.get('k'));
  if (Number.isFinite(k) && k >= K_MIN && k <= K_MAX) out.k = k;

  return out;
}

export function toHash(state, car) {
  const q = new URLSearchParams();
  q.set('s', state.surface);
  if (combosFor(car).length) q.set('fd', String(state.fd));
  q.set('set', String(state.set));
  q.set('draw', state.draw.join(','));
  q.set('k', String(state.k));
  return '#' + q.toString();
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 23 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/state.js test/state.test.js
git commit -m "feat: page state and URL hash round trip"
```

---

## Task 6: Site — SVG helpers and chart 1, power and torque

**Files:**
- Create: `js/svg.js`, `js/charts/powerTorque.js`, `app.css`
- Test: `test/powerTorque.test.js`

**Interfaces:**
- Consumes: `js/gearing.js`.
- Produces:
  - `js/svg.js`: `el(parent, tag, attrs)`, `text(parent, x, y, str, cls, attrs)`, `tipWidth(lines)`, `tip(parent, x, y, lines, warnIndex)`
  - `js/charts/powerTorque.js`: `layout(car) -> {points, peakTorque, peakPower, redline}` and `render(svgEl, car)`, plus `readout(car, rpm) -> {rpm, nm, kw, nmPct, kwPct}`

- [ ] **Step 1: Write the failing test**

Create `test/powerTorque.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { layout, readout } from '../js/charts/powerTorque.js';

const car = {
  engine: {
    redline: 8750,
    peak_torque_rpm: 6000,
    peak_power_rpm: 7750,
    curve: [[3000, 198, 198 * 3000 / 9549], [5000, 248, 248 * 5000 / 9549],
            [6000, 260, 260 * 6000 / 9549], [7750, 240, 240 * 7750 / 9549],
            [8750, 192, 192 * 8750 / 9549]],
  },
};

test('layout carries the peaks as values, not labels', () => {
  const l = layout(car);
  assert.equal(l.peakTorque.rpm, 6000);
  assert.equal(l.peakTorque.nm, 260);
  assert.equal(l.peakPower.rpm, 7750);
  assert.equal(Math.round(l.peakPower.kw), 195);
});

test('layout exposes the redline', () => {
  assert.equal(layout(car).redline, 8750);
});

test('readout gives both values as a percentage of peak', () => {
  const r = readout(car, 5000);
  assert.equal(r.nm, 248);
  assert.equal(r.nmPct, Math.round(248 / 260 * 100));
  assert.equal(r.kwPct, Math.round((248 * 5000 / 9549) / (240 * 7750 / 9549) * 100));
});

test('readout snaps to the nearest sampled rpm rather than inventing a point', () => {
  assert.equal(readout(car, 5900).rpm, 6000);
  assert.equal(readout(car, 3100).rpm, 3000);
});

test('at peak torque the torque percentage is exactly 100', () => {
  assert.equal(readout(car, 6000).nmPct, 100);
});

test('at peak power the power percentage is exactly 100', () => {
  assert.equal(readout(car, 7750).kwPct, 100);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/charts/powerTorque.js`

- [ ] **Step 3: Write `js/svg.js`**

```js
// SVG plumbing shared by every chart. Knows nothing about gearing.

const NS = 'http://www.w3.org/2000/svg';

export function el(parent, tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  for (const k in attrs) node.setAttribute(k, attrs[k]);
  parent.appendChild(node);
  return node;
}

export function text(parent, x, y, str, cls = 'axis', attrs = {}) {
  const node = el(parent, 'text', { x, y, class: cls });
  // a class-level `fill` beats a presentation attribute, so colour has to go inline
  for (const k in attrs) {
    if (k === 'fill') node.style.fill = attrs[k];
    else node.setAttribute(k, attrs[k]);
  }
  node.textContent = str;
  return node;
}

/** Width of a monospace tooltip, needed before drawing when it is right-aligned. */
export const tipWidth = lines => Math.max(...lines.map(l => l.length)) * 6.4 + 22;

export function tip(parent, x, y, lines, warnIndex = -1) {
  const w = tipWidth(lines);
  const h = lines.length * 15 + 13;
  el(parent, 'rect', { x, y, width: w, height: h, rx: 3, fill: '#212529' });
  lines.forEach((line, i) => text(parent, x + 11, y + 19 + i * 15, line, 'val', {
    fill: i === warnIndex ? '#E8A598' : '#F5F2EB', 'font-weight': '600',
  }));
  return w;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}
```

- [ ] **Step 4: Write `js/charts/powerTorque.js`**

```js
// Chart 1 — power and torque. No parameters: this one never changes with the controls.
// The peaks are annotated with their values rather than the words "peak torque" and
// "peak power": where they sit on the curve already says which is which.

import { el, text, tip, clear } from '../svg.js';

const C = { warm: '#F5F2EB', graphite: '#30353A', dark: '#212529',
            steel: '#7B858E', walnut: '#7A583B', cyan: '#148FAC' };

export function layout(car) {
  const curve = car.engine.curve;
  const at = rpm => curve.find(r => r[0] === rpm) || curve[curve.length - 1];
  const pt = at(car.engine.peak_torque_rpm);
  const pp = at(car.engine.peak_power_rpm);
  return {
    points: curve,
    redline: car.engine.redline,
    peakTorque: { rpm: pt[0], nm: pt[1] },
    peakPower: { rpm: pp[0], kw: pp[2] },
    maxNm: Math.max(...curve.map(r => r[1])),
    maxKw: Math.max(...curve.map(r => r[2])),
  };
}

/** The hover readout: both values, and how much of the peak you are giving up. */
export function readout(car, rpm) {
  const l = layout(car);
  const point = l.points.reduce((best, r) =>
    Math.abs(r[0] - rpm) < Math.abs(best[0] - rpm) ? r : best);
  return {
    rpm: point[0],
    nm: point[1],
    kw: point[2],
    nmPct: Math.round(point[1] / l.peakTorque.nm * 100),
    kwPct: Math.round(point[2] / l.peakPower.kw * 100),
  };
}

export function render(svg, car, hoverRpm = null) {
  clear(svg);
  const l = layout(car);
  const L = 64, R = 1030, T = 46, B = 292;
  const rpmMax = Math.ceil(l.redline / 1000) * 1000 + 250;
  const nmMax = Math.ceil(l.maxNm / 70) * 70;
  const kwMax = Math.ceil(l.maxKw / 70) * 70;
  const xs = r => L + (r / rpmMax) * (R - L);
  const yt = v => B - (v / nmMax) * (B - T);
  const yp = v => B - (v / kwMax) * (B - T);

  for (let v = 0; v <= nmMax; v += 70) {
    el(svg, 'line', { x1: L, x2: R, y1: yt(v), y2: yt(v),
                      stroke: C.steel, 'stroke-opacity': 0.18 });
    text(svg, L - 9, yt(v) + 3.5, v, 'axis', { 'text-anchor': 'end' });
  }
  for (let v = 0; v <= kwMax; v += 70) {
    text(svg, R + 9, yp(v) + 3.5, v, 'axis', { fill: C.cyan, 'fill-opacity': 0.8 });
  }
  for (let r = 0; r <= rpmMax; r += 1000) {
    text(svg, xs(r), B + 18, r / 1000 + 'k', 'axis', { 'text-anchor': 'middle' });
  }

  el(svg, 'line', { x1: xs(l.redline), x2: xs(l.redline), y1: T, y2: B,
                    stroke: C.graphite, 'stroke-opacity': 0.5, 'stroke-width': 1.2,
                    'stroke-dasharray': '4 4' });
  text(svg, xs(l.redline) - 7, T + 12, 'rev limit', 'lbl', { 'text-anchor': 'end' });

  let dt = '', dp = '';
  l.points.forEach(([r, nm, kw], i) => {
    dt += (i ? 'L' : 'M') + xs(r).toFixed(1) + ' ' + yt(nm).toFixed(1);
    dp += (i ? 'L' : 'M') + xs(r).toFixed(1) + ' ' + yp(kw).toFixed(1);
  });
  el(svg, 'path', { d: dp, fill: 'none', stroke: C.cyan, 'stroke-width': 2.1 });
  el(svg, 'path', { d: dt, fill: 'none', stroke: C.walnut, 'stroke-width': 2.4 });

  const mark = (x, y, label, colour) => {
    el(svg, 'circle', { cx: x, cy: y, r: 4.6, fill: colour, stroke: C.warm,
                        'stroke-width': 1.7 });
    text(svg, x, y - 12, label, 'val',
         { 'text-anchor': 'middle', fill: colour, 'font-weight': '600' });
  };
  mark(xs(l.peakTorque.rpm), yt(l.peakTorque.nm),
       `${l.peakTorque.nm.toFixed(0)} Nm  ·  ${l.peakTorque.rpm} rpm`, C.walnut);
  mark(xs(l.peakPower.rpm), yp(l.peakPower.kw),
       `${l.peakPower.kw.toFixed(0)} kW  ·  ${l.peakPower.rpm} rpm`, C.cyan);

  text(svg, L - 9, T - 16, 'Nm', 'lbl', { 'text-anchor': 'end', fill: C.walnut });
  text(svg, R + 9, T - 16, 'kW', 'lbl', { fill: C.cyan });
  text(svg, (L + R) / 2, B + 42, 'engine speed — rpm', 'lbl',
       { 'text-anchor': 'middle' });

  if (hoverRpm !== null) {
    const r = readout(car, hoverRpm);
    el(svg, 'line', { x1: xs(r.rpm), x2: xs(r.rpm), y1: T, y2: B, stroke: C.dark,
                      'stroke-opacity': 0.6, 'stroke-width': 1.2,
                      'stroke-dasharray': '3 3' });
    el(svg, 'circle', { cx: xs(r.rpm), cy: yt(r.nm), r: 4.4, fill: C.walnut,
                        stroke: C.warm, 'stroke-width': 1.6 });
    el(svg, 'circle', { cx: xs(r.rpm), cy: yp(r.kw), r: 4.4, fill: C.cyan,
                        stroke: C.warm, 'stroke-width': 1.6 });
    // parks bottom-left, where neither curve runs, so it cannot cover the peak labels
    tip(svg, L + 16, B - 76, [
      `${r.rpm} rpm`,
      `${r.nm.toFixed(0)} Nm    ${r.nmPct}% of peak`,
      `${r.kw.toFixed(0)} kW    ${r.kwPct}% of peak`,
    ]);
  }

  // rpm under the cursor, for the caller to feed back in as hoverRpm
  return { xToRpm: x => Math.max(0, Math.min(rpmMax, (x - L) / (R - L) * rpmMax)),
           plot: { L, R, T, B } };
}
```

- [ ] **Step 5: Write `app.css`**

```css
:root{
  --warm:#F5F2EB; --graphite:#30353A; --dark:#212529; --steel:#7B858E;
  --walnut:#7A583B; --cyan:#148FAC; --warn:#9C3B2E;
  --line:rgba(123,133,142,.28);
}
*{box-sizing:border-box}
body{margin:0;background:var(--warm);color:var(--graphite);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px 80px}

header{border-bottom:1px solid var(--line);margin-bottom:26px}
.brandrow{display:flex;align-items:baseline;gap:14px;padding:22px 0 4px}
.brand{font-size:12.5px;letter-spacing:.17em;text-transform:uppercase;
  color:var(--steel);font-weight:600}
.brand b{color:var(--cyan);font-weight:600}
.crumb{font-size:12.5px;color:var(--steel);text-decoration:none;margin-left:auto}
h1{font-size:31px;margin:2px 0 3px;color:var(--dark);letter-spacing:-.015em}
.sub{color:var(--steel);font-size:13.5px;margin:0 0 20px}
.sub span{color:var(--graphite)}

.bar{display:flex;gap:26px;align-items:flex-end;flex-wrap:wrap;
  background:rgba(255,255,255,.62);border:1px solid var(--line);border-radius:3px;
  padding:14px 18px 15px;margin-bottom:8px;position:sticky;top:0;z-index:5}
.ctl{display:flex;flex-direction:column;gap:5px}
.ctl label{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--steel);font-weight:600}
select{font:13.5px/1 "SF Mono",Menlo,Consolas,monospace;padding:7px 10px;
  border:1px solid var(--line);background:#fff;color:var(--graphite);
  border-radius:2px;min-width:200px}
.copy{margin-left:auto;font-size:12.5px;color:var(--cyan);
  border:1px solid rgba(20,143,172,.35);background:rgba(20,143,172,.05);
  padding:8px 14px;border-radius:2px;cursor:pointer}
.barnote{font-size:11.5px;color:var(--steel);margin:0 0 32px;padding-left:2px}

section{margin-bottom:42px}
h2{font-size:17px;margin:0 0 2px;color:var(--dark);letter-spacing:-.01em}
.cap{font-size:12.5px;color:var(--steel);margin:0 0 14px}
.cap b{color:var(--graphite);font-weight:600}
.panel{background:rgba(255,255,255,.62);border:1px solid var(--line);
  border-radius:3px;padding:16px 18px}
.panel.row{display:flex;gap:18px;align-items:flex-start}
.panel.row svg{flex:1;min-width:0}
svg{display:block;width:100%;height:auto}
.axis{font:10.5px "SF Mono",Menlo,Consolas,monospace;fill:var(--steel)}
.lbl{font:11px -apple-system,"Segoe UI",sans-serif;fill:var(--steel)}
.rowlbl{font:11px -apple-system,"Segoe UI",sans-serif;fill:var(--graphite)}
.val{font:10.5px "SF Mono",Menlo,Consolas,monospace;fill:var(--graphite)}
.pip{font:9px "SF Mono",Menlo,Consolas,monospace;fill:var(--warm);font-weight:700}
.hit{cursor:pointer}

.setlist{width:158px;flex:0 0 158px;padding-top:6px}
.setlist h4{font-size:10px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--steel);margin:0 0 8px;font-weight:600}
.opt{display:flex;align-items:center;gap:9px;padding:6px 8px;border-radius:2px;
  font:12px "SF Mono",Menlo,Consolas,monospace;color:var(--steel);
  border:1px solid transparent;cursor:pointer}
.opt i{width:12px;height:12px;border:1px solid var(--line);border-radius:2px;
  background:#fff;flex:0 0 12px}
.opt.on{color:var(--graphite);border-color:var(--line);background:#fff}
.opt small{color:var(--steel);font-size:10.5px}

.foot{border-top:1px solid var(--line);padding-top:22px;display:flex;gap:34px;
  flex-wrap:wrap;align-items:flex-start}
.foot h3{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--steel);margin:0 0 8px;font-weight:600}
.kbox{display:flex;align-items:center;gap:10px}
.kbox input{font:14px "SF Mono",Menlo,Consolas,monospace;width:104px;padding:7px 10px;
  border:1px solid var(--line);border-radius:2px;background:#fff;color:var(--graphite)}
.kbox a{font-size:12px;color:var(--cyan);text-decoration:none}
.fnote{font-size:12px;color:var(--steel);max-width:430px;margin:9px 0 0}
.limits{font-size:12px;color:var(--steel);margin:0;max-width:390px}
.limits ul{margin:0;padding-left:16px}
.limits li{margin-bottom:3px}
.notadjustable{font-size:13px;color:var(--steel);margin:0;padding:10px 2px}

.carlist{list-style:none;margin:0;padding:0;display:grid;gap:2px;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.carlist a{display:block;padding:12px 14px;text-decoration:none;color:var(--graphite);
  border:1px solid var(--line);border-radius:2px;background:rgba(255,255,255,.62)}
.carlist a:hover{border-color:var(--cyan);color:var(--cyan)}

@media (max-width:720px){
  .wrap{padding:0 16px 60px}
  .panel.row{flex-direction:column}
  .setlist{width:100%;flex:1 1 auto}
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 29 tests total.

- [ ] **Step 7: Commit**

```bash
git add js/svg.js js/charts/powerTorque.js app.css test/powerTorque.test.js
git commit -m "feat: svg helpers and the power/torque chart"
```

---

## Task 7: Site — chart 2, the final drive grid

**Files:**
- Create: `js/charts/finalDrive.js`
- Test: `test/finalDrive.test.js`

**Interfaces:**
- Consumes: `finalDriveCombos`, `kmh`, `circumference` from `js/gearing.js`; `js/svg.js`.
- Produces: `layout(car, state) -> {rows: [{primary, option, value, pct, kmh, selected}], adjustable: boolean}` and `render(svg, car, state, onPick)`.

- [ ] **Step 1: Write the failing test**

Create `test/finalDrive.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { layout } from '../js/charts/finalDrive.js';

const car = {
  engine: { redline: 8750 },
  gear_sets: [
    { label: 'Gear set 1', gears: [{ name: '', value: 2.8 }, { name: '', value: 1.154 }] },
    { label: 'Gear set 2', gears: [{ name: '', value: 3.143 }, { name: '', value: 0.9 }] },
  ],
  final_drive: {
    adjustment: 'Differential Ratio Rear',
    primaries: [{ name: 'p1', value: 1.375 }, { name: 'p2', value: 1.1 }],
    options: [{ name: 'o1', value: 3.8235 }, { name: 'o2', value: 3.4211 }],
    stock_option: 'o2', rest: 1.0,
  },
  tyres: { Tarmac_Dry: { asset: 'PirelliT03', free_radius: 0.296 } },
  defaults: { loaded_radius_factor: 0.9562 },
};
const state = { surface: 'Tarmac_Dry', fd: 0, set: 0, draw: [0], k: 0.9562 };

test('every primary x option combination gets a row', () => {
  assert.equal(layout(car, state).rows.length, 4);
});

test('rows are sorted shortest gearing first and the first row is 100%', () => {
  const rows = layout(car, state).rows;
  assert.equal(rows[0].pct, 100);
  assert.ok(rows[0].value > rows[3].value);
  assert.ok(rows[3].pct > 100);
});

test('speed uses the top gear of the selected gear set', () => {
  const a = layout(car, { ...state, set: 0 }).rows[0].kmh;
  const b = layout(car, { ...state, set: 1 }).rows[0].kmh;
  // set 2's top gear is taller (0.9 < 1.154), so it must read faster
  assert.ok(b > a);
});

test('the selected row is flagged', () => {
  const rows = layout(car, { ...state, fd: 2 }).rows;
  assert.equal(rows.filter(r => r.selected).length, 1);
  assert.equal(rows[2].selected, true);
});

test('a car with no adjustable final drive reports it instead of drawing rows', () => {
  const l = layout({ ...car, final_drive: null }, state);
  assert.equal(l.adjustable, false);
  assert.deepEqual(l.rows, []);
});

test('surface changes every speed', () => {
  const snowy = { ...car, tyres: { ...car.tyres,
    Sweden: { asset: 'PirelliS00', free_radius: 0.31 } } };
  const dry = layout(snowy, state).rows[0].kmh;
  const snow = layout(snowy, { ...state, surface: 'Sweden' }).rows[0].kmh;
  assert.ok(snow > dry);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/charts/finalDrive.js`

- [ ] **Step 3: Write the implementation**

Create `js/charts/finalDrive.js`:

```js
// Chart 2 — every selectable final drive, against the shortest one.
// Clicking a row is the main reason this beats the static PNG.

import { circumference, finalDriveCombos, kmh } from '../gearing.js';
import { el, text, clear } from '../svg.js';

const C = { warm: '#F5F2EB', graphite: '#30353A', steel: '#7B858E',
            walnut: '#7A583B', cyan: '#148FAC' };

export function layout(car, state) {
  if (!car.final_drive) return { adjustable: false, rows: [] };
  const combos = finalDriveCombos(car.final_drive);
  const circ = circumference(car.tyres[state.surface].free_radius, state.k);
  const shortest = combos[0].value;
  // quoting one stated gear set keeps the speed something a real configuration produces
  const top = Math.min(...car.gear_sets[state.set].gears.map(g => g.value));
  return {
    adjustable: true,
    rows: combos.map((c, i) => ({
      primary: c.primary,
      option: c.option,
      value: c.value,
      pct: shortest / c.value * 100,
      kmh: kmh(car.engine.redline, top * c.value, circ),
      selected: i === state.fd,
    })),
  };
}

export function render(svg, car, state, onPick) {
  clear(svg);
  const l = layout(car, state);
  if (!l.adjustable) return;

  const rows = l.rows;
  const L = 196, R = 930, T = 16, step = 26.6;
  const maxPct = Math.max(...rows.map(r => r.pct));
  const xs = v => L + ((v - 97) / (maxPct * 1.06 - 97)) * (R - L);
  const bottom = T + rows.length * step;
  svg.setAttribute('viewBox', `0 0 1100 ${bottom + 56}`);

  for (let v = 100; v <= maxPct + 6; v += 10) {
    el(svg, 'line', { x1: xs(v), x2: xs(v), y1: T, y2: bottom,
                      stroke: C.steel, 'stroke-opacity': 0.16 });
    text(svg, xs(v), bottom + 17, v + '%', 'axis', { 'text-anchor': 'middle' });
  }
  el(svg, 'line', { x1: xs(100), x2: xs(100), y1: T, y2: bottom,
                    stroke: C.steel, 'stroke-opacity': 0.75, 'stroke-width': 1.3 });

  rows.forEach((r, i) => {
    const y = T + i * step + step / 2;
    const hit = el(svg, 'rect', { x: 6, y: y - 12, width: 1080, height: 24,
                                  fill: r.selected ? C.cyan : 'transparent',
                                  'fill-opacity': r.selected ? 0.07 : 0,
                                  rx: 2, class: 'hit' });
    hit.addEventListener('click', () => onPick(i));
    el(svg, 'line', { x1: xs(100), x2: xs(r.pct), y1: y, y2: y, stroke: C.steel,
                      'stroke-opacity': 0.42, 'stroke-width': 1.3 });
    el(svg, 'circle', { cx: xs(r.pct), cy: y, r: r.selected ? 6.4 : 5,
                        fill: r.selected ? C.cyan : C.walnut, stroke: C.warm,
                        'stroke-width': 1.6 });
    text(svg, L - 12, y + 3.6, `${r.primary.name}  ·  ${r.option.name}`, 'val',
         { 'text-anchor': 'end', 'fill-opacity': r.selected ? 1 : 0.72 });
    text(svg, xs(r.pct) + 12, y + 3.6,
         `${r.pct.toFixed(0).padStart(3)}%     ${r.kmh.toFixed(0)} km/h`, 'val',
         { 'fill-opacity': r.selected ? 1 : 0.72 });
  });

  text(svg, L - 190, bottom + 40,
       '100% is the shortest combination. Speed is top gear of '
       + car.gear_sets[state.set].label.toLowerCase() + '.', 'lbl');
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 35 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/charts/finalDrive.js test/finalDrive.test.js
git commit -m "feat: final drive grid"
```

---

## Task 8: Site — chart 3, where each gear tops out

**Files:**
- Create: `js/charts/ladder.js`
- Test: `test/ladder.test.js`

**Interfaces:**
- Consumes: `circumference`, `finalDriveCombos`, `gearTops`, `gearAtSpeed`, `rpmAt` from `js/gearing.js`; `js/svg.js`.
- Produces: `fdValue(car, state) -> number` (exported here and reused by later charts), `layout(car, state) -> {lanes: [{label, tops, selected}], base, vmax}`, `hoverLine(car, state, laneIndex, speed) -> string`, `render(svg, car, state, onPickSet)`.

- [ ] **Step 1: Write the failing test**

Create `test/ladder.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fdValue, layout, hoverLine } from '../js/charts/ladder.js';

const car = {
  engine: { redline: 8750 },
  gear_sets: [
    { label: 'Gear set 1',
      gears: [2.8, 2.053, 1.619, 1.32, 1.154].map(v => ({ name: '', value: v })) },
    { label: 'Gear set 2',
      gears: [3.143, 2.235, 1.762, 1.417, 1.154].map(v => ({ name: '', value: v })) },
  ],
  final_drive: {
    adjustment: 'Differential Ratio Rear',
    primaries: [{ name: 'p', value: 1.1 }],
    options: [{ name: 'o', value: 3.4211 }],
    stock_option: 'o', rest: 1.0,
  },
  tyres: { Tarmac_Dry: { asset: 'PirelliT03', free_radius: 0.296 } },
  defaults: { loaded_radius_factor: 0.9562 },
};
const state = { surface: 'Tarmac_Dry', fd: 0, set: 0, draw: [0], k: 0.9562 };

test('every gear set gets a lane, selected or not', () => {
  const l = layout(car, state);
  assert.equal(l.lanes.length, 2);
  assert.equal(l.lanes[0].selected, true);
  assert.equal(l.lanes[1].selected, false);
});

test('changing the selected set moves the flag but drops no lane', () => {
  const l = layout(car, { ...state, set: 1 });
  assert.equal(l.lanes.length, 2);
  assert.equal(l.lanes[1].selected, true);
});

test('lane tops match the known Stratos figures', () => {
  const tops = layout(car, state).lanes[0].tops.map(Math.round);
  assert.deepEqual(tops, [89, 121, 153, 188, 215]);
});

test('base is the slowest gear across every lane, for the relative axis', () => {
  const l = layout(car, state);
  assert.equal(Math.round(l.base), 79);   // gear set 2 first gear
});

test('a car with no adjustable final drive still lays out at its stock ratio', () => {
  const plain = { ...car, final_drive: null };
  assert.ok(fdValue(plain, state) > 0);
  assert.equal(layout(plain, state).lanes.length, 2);
});

test('hover gives speed, gear and revs and nothing else', () => {
  const line = hoverLine(car, state, 0, 132);
  assert.match(line, /^132 km\/h {2}·{2} gear 3 {2}·{2} \d+ rpm$/);
});

test('hover says no more than one line — the shift comparison lives in chart 4', () => {
  assert.ok(!hoverLine(car, state, 0, 132).includes('\n'));
  assert.ok(!/upshift|downshift|↑|↓/.test(hoverLine(car, state, 0, 132)));
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/charts/ladder.js`

- [ ] **Step 3: Write the implementation**

Create `js/charts/ladder.js`:

```js
// Chart 3 — where each gear tops out, one lane per gear set, every set drawn.
// Ported from chart_gear_ladder in make_gearing_chart.py, which is already the right
// answer for a car like the 306 Maxi with ten sets of differing gear counts.

import { circumference, finalDriveCombos, gearAtSpeed, gearTops, kmh, rpmAt }
  from '../gearing.js';
import { el, text, tip, tipWidth, clear } from '../svg.js';

const C = { warm: '#F5F2EB', graphite: '#30353A', steel: '#7B858E',
            walnut: '#7A583B', cyan: '#148FAC' };

/** The selected overall final-drive ratio, or the car's fixed one. */
export function fdValue(car, state) {
  if (!car.final_drive) return 1;
  const combos = finalDriveCombos(car.final_drive);
  return (combos[state.fd] || combos[0]).value;
}

const circOf = (car, state) =>
  circumference(car.tyres[state.surface].free_radius, state.k);

export function layout(car, state) {
  const fd = fdValue(car, state);
  const circ = circOf(car, state);
  const lanes = car.gear_sets.map((set, i) => ({
    label: `${set.label}   (${set.gears.length}-speed)`,
    tops: gearTops(set.gears, fd, circ, car.engine.redline),
    selected: i === state.set,
  }));
  const all = lanes.flatMap(l => l.tops);
  return { lanes, base: Math.min(...all), vmax: Math.max(...all) * 1.05 };
}

/** Speed, gear, revs. One line. */
export function hoverLine(car, state, laneIndex, speed) {
  const l = layout(car, state);
  const tops = l.lanes[laneIndex].tops;
  const gear = gearAtSpeed(tops, speed);
  const total = car.gear_sets[laneIndex].gears[gear].value * fdValue(car, state);
  const rpm = rpmAt(speed, total, circOf(car, state));
  return `${speed.toFixed(0)} km/h  ·  gear ${gear + 1}  ·  ${rpm.toFixed(0)} rpm`;
}

export function render(svg, car, state, onPickSet, hover = null) {
  clear(svg);
  const l = layout(car, state);
  const L = 214, R = 1020, T = 56, step = 62;
  const xs = v => L + (v / l.vmax) * (R - L);
  const bottom = T + l.lanes.length * step;
  svg.setAttribute('viewBox', `0 0 1100 ${bottom + 60}`);

  for (let p = 0; p <= Math.floor(l.vmax / l.base * 100); p += 50) {
    const v = p * l.base / 100;
    if (v > l.vmax) break;
    el(svg, 'line', { x1: xs(v), x2: xs(v), y1: T - 10, y2: bottom,
                      stroke: C.steel, 'stroke-opacity': 0.16 });
    text(svg, xs(v), T - 20, p + '%', 'axis', { 'text-anchor': 'middle' });
  }
  text(svg, (L + R) / 2, T - 38, 'relative to the slowest gear', 'lbl',
       { 'text-anchor': 'middle' });
  for (let v = 0; v <= l.vmax; v += 50) {
    text(svg, xs(v), bottom + 19, v, 'axis', { 'text-anchor': 'middle' });
  }

  l.lanes.forEach((lane, i) => {
    const y = T + i * step + step / 2;
    if (lane.selected) {
      el(svg, 'rect', { x: 16, y: y - 23, width: R - 6, height: 46, rx: 2,
                        fill: C.cyan, 'fill-opacity': 0.06 });
    }
    // starts at a standing start, so first gear reads as a span like every other gear
    el(svg, 'line', { x1: xs(0), x2: xs(lane.tops[lane.tops.length - 1]), y1: y, y2: y,
                      stroke: C.steel, 'stroke-width': 1.3, 'stroke-opacity': 0.5 });
    lane.tops.forEach((v, gi) => {
      el(svg, 'circle', { cx: xs(v), cy: y, r: 9, fill: C.walnut, stroke: C.warm,
                          'stroke-width': 1.6 });
      text(svg, xs(v), y + 3.3, gi + 1, 'pip', { 'text-anchor': 'middle' });
      text(svg, xs(v), y - 15, v.toFixed(0), 'val', { 'text-anchor': 'middle' });
    });
    const name = text(svg, L - 22, y + 4, lane.label, 'rowlbl', {
      'text-anchor': 'end', fill: lane.selected ? C.cyan : C.graphite,
      'font-weight': lane.selected ? '600' : '400',
    });
    name.setAttribute('class', 'rowlbl hit');
    name.addEventListener('click', () => onPickSet(i));
    if (lane.selected) {
      text(svg, L - 22, y + 19, 'selected', 'lbl',
           { 'text-anchor': 'end', fill: C.cyan });
    }
  });

  if (hover) {
    const { lane, speed } = hover;
    const y = T + lane * step + step / 2;
    el(svg, 'line', { x1: xs(speed), x2: xs(speed), y1: T - 10, y2: bottom,
                      stroke: '#212529', 'stroke-width': 1.3, 'stroke-opacity': 0.7,
                      'stroke-dasharray': '3 3' });
    el(svg, 'circle', { cx: xs(speed), cy: y, r: 4.4, fill: '#212529', stroke: C.warm,
                        'stroke-width': 1.6 });
    const lines = [hoverLine(car, state, lane, speed)];
    const tops = l.lanes[lane].tops;
    // after the lane's last dot, clamped, so it stays inside its own lane
    tip(svg, Math.min(xs(tops[tops.length - 1]) + 16, 1096 - tipWidth(lines)),
        y - 14, lines);
  }

  text(svg, (L + R) / 2, bottom + 42,
       `speed at the ${car.engine.redline} rpm rev limit — km/h`, 'lbl',
       { 'text-anchor': 'middle' });
  return { xToSpeed: x => Math.max(0, (x - L) / (R - L) * l.vmax),
           yToLane: y => Math.max(0, Math.min(l.lanes.length - 1,
                                              Math.floor((y - T) / step))) };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 42 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/charts/ladder.js test/ladder.test.js
git commit -m "feat: gear ladder chart"
```

---

## Task 9: Site — chart 4, shift points

**Files:**
- Create: `js/charts/shiftPoints.js`
- Test: `test/shiftPoints.test.js`

**Interfaces:**
- Consumes: `fdValue` from `js/charts/ladder.js`; `circumference`, `gearTops`, `gearAtSpeed`, `kmh`, `rpmAt`, `REV_FLOOR` from `js/gearing.js`; `js/svg.js`.
- Produces: `layout(car, state) -> {bars: [{gear, from, to}], tops, vmax}`, `shiftReadout(car, state, gear, speed) -> {gear, rpm, speed, up, down, overRev}`, and `render(svg, car, state, hover)` where `hover` is `{gear, speed}` or `null`.

**Why the gear is an argument, not inferred.** The obvious move is to reuse the ladder's rule — "the gear you are in is the lowest one whose top speed you have not passed". That rule is wrong for *this* chart: it always picks the shortest usable gear, so a downshift out of it always over-revs, and the warning colour would fire on every hover. The rows are the answer — each gear has its own row, so the cursor already names a gear as well as a speed.

- [ ] **Step 1: Write the failing test**

Create `test/shiftPoints.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { layout, shiftReadout } from '../js/charts/shiftPoints.js';

const car = {
  engine: { redline: 8750 },
  gear_sets: [
    { label: 'Gear set 1',
      gears: [2.8, 2.053, 1.619, 1.32, 1.154].map(v => ({ name: '', value: v })) },
    { label: 'Gear set 2',
      gears: [3.143, 2.235, 1.762, 1.417, 1.154].map(v => ({ name: '', value: v })) },
  ],
  final_drive: {
    adjustment: 'Differential Ratio Rear',
    primaries: [{ name: 'p', value: 1.1 }],
    options: [{ name: 'o', value: 3.4211 }],
    stock_option: 'o', rest: 1.0,
  },
  tyres: { Tarmac_Dry: { asset: 'PirelliT03', free_radius: 0.296 } },
  defaults: { loaded_radius_factor: 0.9562 },
};
const state = { surface: 'Tarmac_Dry', fd: 0, set: 0, draw: [0], k: 0.9562 };

test('only the selected gear set is drawn', () => {
  assert.equal(layout(car, state).bars.length, 5);
  assert.equal(layout(car, { ...state, set: 1 }).bars.length, 5);
});

test('bars overlap — the same speed is reachable in more than one gear', () => {
  const bars = layout(car, state).bars;
  // third gear's band starts before second gear's band ends
  assert.ok(bars[2].from < bars[1].to,
    'bars must overlap; a tiled staircase hides the choice of gear');
});

test('every bar ends at its top speed and starts at the rev floor', () => {
  const bars = layout(car, state).bars;
  assert.equal(Math.round(bars[0].to), 89);
  assert.ok(bars[0].from > 0);
  assert.ok(bars[0].from < bars[0].to);
});

test('the readout reports the gear it was asked about', () => {
  assert.equal(shiftReadout(car, state, 2, 132).gear, 2);
  assert.equal(shiftReadout(car, state, 3, 132).gear, 3);
});

test('an upshift always drops the revs', () => {
  const r = shiftReadout(car, state, 2, 132);
  assert.ok(r.up.rpm < r.rpm);
  assert.equal(r.up.gear, 3);
});

test('a downshift from third at 132 km/h over-revs this engine', () => {
  const r = shiftReadout(car, state, 2, 132);
  assert.equal(r.down.gear, 1);
  assert.ok(r.down.rpm > car.engine.redline);
  assert.equal(r.overRev, true);
});

test('a downshift inside the limit is not flagged', () => {
  // fourth gear at 132 km/h: dropping to third stays under the limiter
  const r = shiftReadout(car, state, 3, 132);
  assert.ok(r.down.rpm <= car.engine.redline);
  assert.equal(r.overRev, false);
});

test('over-rev is not the normal case, or the warning colour means nothing', () => {
  const flagged = [1, 2, 3, 4].map(g => shiftReadout(car, state, g, 132).overRev);
  assert.ok(flagged.includes(false),
    'inferring the gear rather than taking it makes every downshift over-rev');
});

test('first gear has no downshift and top gear has no upshift', () => {
  assert.equal(shiftReadout(car, state, 0, 40).down, null);
  assert.equal(shiftReadout(car, state, 4, 210).up, null);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/charts/shiftPoints.js`

- [ ] **Step 3: Write the implementation**

Create `js/charts/shiftPoints.js`:

```js
// Chart 4 — the selected gear set, one row per gear.
// Bars run from a usable-revs floor to the limiter, so they OVERLAP: the same road speed
// is reachable in more than one gear, and that overlap is what the chart exists to show.
// A tiled version where each gear owned its own band was tried and rejected — it draws a
// tidy staircase that hides the choice.

import { REV_FLOOR, circumference, gearTops, kmh, rpmAt } from '../gearing.js';
import { fdValue } from './ladder.js';
import { el, text, clear } from '../svg.js';

const C = { warm: '#F5F2EB', dark: '#212529', steel: '#7B858E',
            walnut: '#7A583B', cyan: '#148FAC', warn: '#9C3B2E' };

const circOf = (car, state) =>
  circumference(car.tyres[state.surface].free_radius, state.k);

const totals = (car, state) =>
  car.gear_sets[state.set].gears.map(g => g.value * fdValue(car, state));

export function layout(car, state) {
  const circ = circOf(car, state);
  const tot = totals(car, state);
  const tops = gearTops(car.gear_sets[state.set].gears, fdValue(car, state), circ,
                        car.engine.redline);
  return {
    bars: tot.map((t, i) => ({ gear: i, from: kmh(REV_FLOOR, t, circ), to: tops[i] })),
    tops,
    vmax: tops[tops.length - 1] * 1.06,
  };
}

/**
 * `gear` is the row under the cursor, not something inferred from the speed. Inferring it
 * as "the lowest gear that has not topped out" would put you in the shortest usable gear
 * every time, so every downshift would over-rev and the warning would be meaningless.
 */
export function shiftReadout(car, state, gear, speed) {
  const circ = circOf(car, state);
  const tot = totals(car, state);
  const revsIn = i => rpmAt(speed, tot[i], circ);
  const up = gear + 1 < tot.length ? { gear: gear + 1, rpm: revsIn(gear + 1) } : null;
  const down = gear > 0 ? { gear: gear - 1, rpm: revsIn(gear - 1) } : null;
  return {
    gear,
    rpm: revsIn(gear),
    speed,
    up,
    down,
    overRev: down !== null && down.rpm > car.engine.redline,
  };
}

export function render(svg, car, state, hover = null) {
  clear(svg);
  const l = layout(car, state);
  const L = 132, R = 1012, T = 76, step = 44;
  const xs = v => L + (v / l.vmax) * (R - L);
  const bottom = T + l.bars.length * step;
  svg.setAttribute('viewBox', `0 0 1100 ${bottom + 60}`);

  const hot = hover ? hover.gear : -1;

  for (let v = 0; v <= l.vmax; v += 20) {
    el(svg, 'line', { x1: xs(v), x2: xs(v), y1: T - 6, y2: bottom,
                      stroke: C.steel, 'stroke-opacity': 0.16 });
    if (v % 40 === 0) text(svg, xs(v), bottom + 19, v, 'axis',
                           { 'text-anchor': 'middle' });
  }

  l.bars.forEach((bar, i) => {
    const y = T + i * step + step / 2;
    const on = i === hot;
    el(svg, 'line', { x1: xs(bar.from), x2: xs(bar.to), y1: y, y2: y,
                      stroke: C.walnut, 'stroke-width': on ? 11 : 8,
                      'stroke-opacity': on ? 0.95 : 0.45, 'stroke-linecap': 'round' });
    text(svg, L - 16, y + 4, 'Gear ' + (i + 1), 'rowlbl',
         { 'text-anchor': 'end', 'fill-opacity': on ? 1 : 0.7,
           'font-weight': on ? '600' : '400' });
    text(svg, xs(bar.to) + 12, y + 3.6, bar.to.toFixed(0), 'val',
         { 'fill-opacity': on ? 1 : 0.6 });
  });

  text(svg, 16, T - 44, car.gear_sets[state.set].label, 'lbl', { fill: C.cyan });

  if (hover) {
    const speed = hover.speed;
    const r = shiftReadout(car, state, hover.gear, speed);
    el(svg, 'line', { x1: xs(speed), x2: xs(speed), y1: T - 34, y2: bottom,
                      stroke: C.dark, 'stroke-width': 1.3, 'stroke-opacity': 0.7,
                      'stroke-dasharray': '3 3' });
    // the readout sits above the plot, so it covers no bar
    const label = `${speed.toFixed(0)} km/h   ·   gear ${r.gear + 1}`
                + `   ·   ${r.rpm.toFixed(0)} rpm`;
    const w = label.length * 6.4 + 24;
    const x = Math.min(Math.max(xs(speed) - w / 2, 4), 1096 - w);
    el(svg, 'rect', { x, y: T - 62, width: w, height: 25, rx: 3, fill: C.dark });
    text(svg, x + w / 2, T - 44.5, label, 'val',
         { 'text-anchor': 'middle', fill: C.warm, 'font-weight': '600' });
    el(svg, 'circle', { cx: xs(speed), cy: T + r.gear * step + step / 2, r: 5,
                        fill: C.dark, stroke: C.warm, 'stroke-width': 1.7 });

    const chip = (target, arrow, warn) => {
      const y = T + target.gear * step + step / 2;
      const t = `${arrow} ${target.rpm.toFixed(0)} rpm`
              + (warn ? '   over limit' : '');
      const cw = t.length * 6.4 + 18;
      el(svg, 'circle', { cx: xs(speed), cy: y, r: 4.4,
                          fill: warn ? C.warn : C.dark, stroke: C.warm,
                          'stroke-width': 1.6 });
      el(svg, 'rect', { x: xs(speed) + 13, y: y - 10.5, width: cw, height: 21,
                        rx: 2, fill: warn ? C.warn : C.dark });
      text(svg, xs(speed) + 13 + cw / 2, y + 3.8, t, 'val',
           { 'text-anchor': 'middle', fill: C.warm, 'font-weight': '600' });
    };
    if (r.up) chip(r.up, '↑ upshift', false);
    if (r.down) chip(r.down, '↓ downshift', r.overRev);
  }

  text(svg, (L + R) / 2, bottom + 43, 'road speed — km/h', 'lbl',
       { 'text-anchor': 'middle' });
  return {
    xToSpeed: x => Math.max(0, Math.min(l.vmax, (x - L) / (R - L) * l.vmax)),
    yToGear: y => Math.max(0, Math.min(l.bars.length - 1, Math.floor((y - T) / step))),
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 51 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/charts/shiftPoints.js test/shiftPoints.test.js
git commit -m "feat: shift points chart"
```

---

## Task 10: Site — chart 5, speed against revs

**Files:**
- Create: `js/charts/speedRevs.js`
- Test: `test/speedRevs.test.js`

**Interfaces:**
- Consumes: `fdValue` from `js/charts/ladder.js`; `circumference`, `kmh`, `SET_COLOURS` from `js/gearing.js`; `js/svg.js`.
- Produces: `layout(car, state) -> {lines: [{set, gear, total, topSpeed}], circ, vmax}`, `nearestLine(lines, redline, rpm, speed) -> line`, and `render(svg, car, state, hover)` where `hover` is `{set, gear, rpm}` or `null`.

- [ ] **Step 1: Write the failing test**

Create `test/speedRevs.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { layout, nearestLine } from '../js/charts/speedRevs.js';

const car = {
  engine: { redline: 8750 },
  gear_sets: [
    { label: 'Gear set 1',
      gears: [2.8, 2.053, 1.619, 1.32, 1.154].map(v => ({ name: '', value: v })) },
    { label: 'Gear set 2',
      gears: [3.143, 2.235, 1.762].map(v => ({ name: '', value: v })) },
    { label: 'Gear set 3',
      gears: [3.231, 2.235].map(v => ({ name: '', value: v })) },
  ],
  final_drive: {
    adjustment: 'Differential Ratio Rear',
    primaries: [{ name: 'p', value: 1.1 }],
    options: [{ name: 'o', value: 3.4211 }],
    stock_option: 'o', rest: 1.0,
  },
  tyres: { Tarmac_Dry: { asset: 'PirelliT03', free_radius: 0.296 } },
  defaults: { loaded_radius_factor: 0.9562 },
};
const state = { surface: 'Tarmac_Dry', fd: 0, set: 0, draw: [0], k: 0.9562 };

test('only the ticked gear sets are drawn', () => {
  assert.equal(layout(car, state).lines.length, 5);
  assert.equal(layout(car, { ...state, draw: [0, 2] }).lines.length, 7);
});

test('drawn sets are independent of the selected set', () => {
  const l = layout(car, { ...state, set: 2, draw: [1] });
  assert.deepEqual([...new Set(l.lines.map(x => x.set))], [1]);
});

test('each line carries its set index so it can be coloured consistently', () => {
  const l = layout(car, { ...state, draw: [0, 1] });
  assert.deepEqual([...new Set(l.lines.map(x => x.set))], [0, 1]);
});

test('top speed matches the known Stratos top gear figure', () => {
  const l = layout(car, state);
  assert.equal(Math.round(l.lines[4].topSpeed), 215);
});

test('vmax leaves headroom above the fastest drawn line', () => {
  const l = layout(car, state);
  assert.ok(l.vmax > Math.max(...l.lines.map(x => x.topSpeed)));
});

test('nearestLine picks the gear whose line passes closest to the cursor', () => {
  const l = layout(car, state);
  // every line is straight from the origin to its top speed at the rev limit, so at
  // half the rev limit each gear sits at half its top speed
  const target = l.lines[2];
  const hit = nearestLine(l.lines, car.engine.redline, 4375, target.topSpeed / 2);
  assert.equal(hit.gear, target.gear);
  assert.equal(hit.set, target.set);
});

test('nearestLine only ever returns a line that is actually drawn', () => {
  const l = layout(car, { ...state, draw: [1] });
  assert.equal(nearestLine(l.lines, car.engine.redline, 4000, 500).set, 1);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/charts/speedRevs.js`

- [ ] **Step 3: Write the implementation**

Create `js/charts/speedRevs.js`:

```js
// Chart 5 — speed against revs, one line per gear of each ticked gear set.
// Its gear-set list is separate state from the page's selected gear set.

import { SET_COLOURS, circumference, kmh } from '../gearing.js';
import { fdValue } from './ladder.js';
import { el, text, tip, tipWidth, clear } from '../svg.js';

const C = { warm: '#F5F2EB', graphite: '#30353A', steel: '#7B858E' };

export function layout(car, state) {
  const circ = circumference(car.tyres[state.surface].free_radius, state.k);
  const fd = fdValue(car, state);
  const lines = [];
  for (const si of state.draw) {
    car.gear_sets[si].gears.forEach((g, gi) => {
      const total = g.value * fd;
      lines.push({ set: si, gear: gi, total,
                   topSpeed: kmh(car.engine.redline, total, circ) });
    });
  }
  return { lines, circ, vmax: Math.max(...lines.map(l => l.topSpeed)) * 1.06 };
}

/**
 * The drawn line closest to a point. Every line runs straight from the origin to its top
 * speed at the rev limit, so the speed it shows at any rpm is a simple proportion — no
 * need for the circumference here.
 */
export function nearestLine(lines, redline, rpm, speed) {
  let best = null;
  let bestDistance = Infinity;
  for (const line of lines) {
    const distance = Math.abs(line.topSpeed * (rpm / redline) - speed);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = line;
    }
  }
  return best;
}

export function render(svg, car, state, hover = null) {
  clear(svg);
  const l = layout(car, state);
  const L = 64, R = 876, T = 22, B = 330;
  const rpmMax = Math.ceil(car.engine.redline / 1000) * 1000 + 300;
  const xs = r => L + (r / rpmMax) * (R - L);
  const ys = v => B - (v / l.vmax) * (B - T);
  svg.setAttribute('viewBox', '0 0 940 400');

  for (let v = 0; v <= l.vmax; v += 40) {
    el(svg, 'line', { x1: L, x2: R, y1: ys(v), y2: ys(v),
                      stroke: C.steel, 'stroke-opacity': 0.16 });
    text(svg, L - 9, ys(v) + 3.5, v, 'axis', { 'text-anchor': 'end' });
  }
  for (let r = 0; r <= rpmMax; r += 1000) {
    text(svg, xs(r), B + 18, r / 1000 + 'k', 'axis', { 'text-anchor': 'middle' });
  }
  el(svg, 'line', { x1: xs(car.engine.redline), x2: xs(car.engine.redline), y1: T, y2: B,
                    stroke: C.graphite, 'stroke-opacity': 0.5, 'stroke-width': 1.2,
                    'stroke-dasharray': '4 4' });
  text(svg, xs(car.engine.redline) - 7, T + 12, 'rev limit', 'lbl',
       { 'text-anchor': 'end' });

  l.lines.forEach(line => {
    const colour = SET_COLOURS[line.set % SET_COLOURS.length];
    el(svg, 'line', { x1: xs(0), x2: xs(car.engine.redline), y1: ys(0),
                      y2: ys(line.topSpeed), stroke: colour, 'stroke-width': 2.1,
                      'stroke-opacity': 0.85 });
    // one label column per gear set, so two sets never collide
    text(svg, xs(car.engine.redline) + 11 + state.draw.indexOf(line.set) * 26,
         ys(line.topSpeed) + 3.6, line.gear + 1, 'val', { fill: colour });
  });

  if (hover) {
    const line = l.lines.find(x => x.set === hover.set && x.gear === hover.gear);
    if (line) {
      const v = kmh(hover.rpm, line.total, l.circ);
      const colour = SET_COLOURS[line.set % SET_COLOURS.length];
      el(svg, 'circle', { cx: xs(hover.rpm), cy: ys(v), r: 5, fill: colour,
                          stroke: C.warm, 'stroke-width': 1.7 });
      const lines = [`${car.gear_sets[line.set].label}  ·  gear ${line.gear + 1}`,
                     `${hover.rpm.toFixed(0)} rpm    ${v.toFixed(0)} km/h`];
      tip(svg, xs(hover.rpm) - tipWidth(lines) - 13, ys(v) - 46, lines);
    }
  }

  text(svg, (L + R) / 2, B + 42, 'engine speed — rpm', 'lbl',
       { 'text-anchor': 'middle' });
  text(svg, L - 9, T + 2, 'km/h', 'lbl', { 'text-anchor': 'end' });
  return {
    atPoint(x, y) {
      const rpm = Math.max(0, Math.min(car.engine.redline, (x - L) / (R - L) * rpmMax));
      const speed = Math.max(0, (B - y) / (B - T) * l.vmax);
      const line = nearestLine(l.lines, car.engine.redline, rpm, speed);
      return line ? { set: line.set, gear: line.gear, rpm } : null;
    },
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 58 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/charts/speedRevs.js test/speedRevs.test.js
git commit -m "feat: speed against revs chart"
```

---

## Task 11: Site — tracking

**Files:**
- Create: `js/tracking.js`
- Test: `test/tracking.test.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `track(name)` and `resetTracking()` (test-only helper to clear the dedupe set).

- [ ] **Step 1: Write the failing test**

Create `test/tracking.test.js`:

```js
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { track, resetTracking, _queue } from '../js/tracking.js';

beforeEach(() => {
  resetTracking();
  globalThis.window = {};
});

test('an event fires once and only once', () => {
  track('car-lancia-stratos');
  track('car-lancia-stratos');
  assert.equal(_queue().length, 1);
});

test('different events both queue', () => {
  track('surface-Gravel');
  track('copy-link');
  assert.equal(_queue().length, 2);
});

test('events queue when goatcounter has not loaded, rather than being lost', () => {
  track('edit-factor');
  assert.equal(_queue()[0].path, 'edit-factor');
  assert.equal(_queue()[0].event, true);
});

test('the queue drains once goatcounter arrives', () => {
  track('copy-link');
  const seen = [];
  globalThis.window.goatcounter = { count: e => seen.push(e) };
  track('pick-gearset');
  assert.deepEqual(seen.map(e => e.path), ['copy-link', 'pick-gearset']);
  assert.equal(_queue().length, 0);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test test/`
Expected: FAIL — cannot find module `../js/tracking.js`

- [ ] **Step 3: Write the implementation**

Create `js/tracking.js`:

```js
// GoatCounter events, deduped. Same wrapper as gremlin-curve-converter: the script loads
// async, so events raised before it arrives are queued rather than dropped.

const seen = new Set();
let queue = [];

export function resetTracking() {
  seen.clear();
  queue = [];
}

/** Test seam: the events still waiting for goatcounter to load. */
export const _queue = () => queue;

export function track(name) {
  if (seen.has(name)) return;
  seen.add(name);
  queue.push({ path: name, title: name, event: true });
  const gc = globalThis.window && globalThis.window.goatcounter;
  if (!gc || !gc.count) return;
  while (queue.length) gc.count(queue.shift());
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test test/`
Expected: PASS, 62 tests total.

- [ ] **Step 5: Commit**

```bash
git add js/tracking.js test/tracking.test.js
git commit -m "feat: deduped goatcounter tracking"
```

---

## Task 12: Site — app wiring

**Files:**
- Create: `js/app.js`

**Interfaces:**
- Consumes: every module above.
- Produces: the running page. No new exports.

This task has no unit test — it is DOM wiring over modules that are already tested. It is verified in a browser.

- [ ] **Step 1: Write `js/app.js`**

```js
// Entry point. Loads one car's JSON, builds the control bar and the five chart sections,
// and re-renders everything on any state change. All arithmetic lives in the modules;
// this file only moves state around.

import { SURFACES, finalDriveCombos } from './gearing.js';
import { defaultState, parseHash, toHash } from './state.js';
import { track } from './tracking.js';
import * as powerTorque from './charts/powerTorque.js';
import * as finalDrive from './charts/finalDrive.js';
import * as ladder from './charts/ladder.js';
import * as shiftPoints from './charts/shiftPoints.js';
import * as speedRevs from './charts/speedRevs.js';

const root = document.getElementById('app');
const slug = root.dataset.car;

let car = null;
let state = null;
const hover = { power: null, ladder: null, shift: null, revs: null };
// each chart's render() hands back the pixel-to-value mappings its hover needs.
// They are kept here rather than on the modules: an ES module namespace object is
// frozen, so assigning a field to an imported `* as` binding throws.
const maps = {};

const SECTIONS = [
  { id: 'power', title: 'Power and torque',
    cap: 'Engine output against revs. Hover for the values and how far off peak they are.' },
  { id: 'fd', title: 'Final drive', cap: '' },
  { id: 'ladder', title: 'Where each gear tops out',
    cap: 'One lane per gear set, all of them at once. Click a lane name to select that gear set.' },
  { id: 'shift', title: 'Shift points',
    cap: 'The selected gear set, one row per gear. Each bar covers the speeds where that gear '
       + 'is usable, from 3000 rpm to the rev limit. Where bars overlap you have a choice of '
       + 'gear. Hover for the revs either side of a shift.' },
  { id: 'revs', title: 'Speed against revs', cap: 'Pick the gear sets to draw.' },
];

const h = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const k in attrs) {
    if (k === 'class') node.className = attrs[k];
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), attrs[k]);
    else node.setAttribute(k, attrs[k]);
  }
  for (const kid of kids) {
    node.appendChild(typeof kid === 'string' ? document.createTextNode(kid) : kid);
  }
  return node;
};

function buildShell() {
  root.querySelector('.loading')?.remove();

  const surfaces = SURFACES.filter(s => s.key in car.tyres);
  const combos = car.final_drive ? finalDriveCombos(car.final_drive) : [];

  const surfaceSel = h('select', { onchange: e => {
    state.surface = e.target.value;
    track('surface-' + state.surface);
    commit();
  } }, ...surfaces.map(s => h('option', { value: s.key }, s.label)));

  const fdSel = h('select', { onchange: e => {
    state.fd = Number(e.target.value);
    track('change-final-drive');
    commit();
  } }, ...combos.map((c, i) =>
    h('option', { value: String(i) }, `${c.primary.name}  ·  ${c.option.name}`)));

  const setSel = h('select', { onchange: e => {
    state.set = Number(e.target.value);
    track('pick-gearset');
    commit();
  } }, ...car.gear_sets.map((s, i) =>
    h('option', { value: String(i) }, `${s.label}  (${s.gears.length}-speed)`)));

  const bar = h('div', { class: 'bar' },
    h('div', { class: 'ctl' }, h('label', {}, 'Surface'), surfaceSel));
  if (combos.length) {
    bar.appendChild(h('div', { class: 'ctl' }, h('label', {}, 'Final drive'), fdSel));
  }
  bar.appendChild(h('div', { class: 'ctl' }, h('label', {}, 'Gear set'), setSel));
  bar.appendChild(h('button', { class: 'copy', onclick: () => {
    navigator.clipboard.writeText(location.href);
    track('copy-link');
  } }, 'Copy link'));

  root.appendChild(h('p', { class: 'sub' },
    `${car.axle === 'Rear' ? 'Rear' : 'Front'}-wheel drive · `
    + `${car.gear_sets[0].gears.length} speed · ${car.gear_sets.length} gear sets · `
    + `rev limit ${car.engine.redline} rpm`));
  root.appendChild(bar);
  root.appendChild(h('p', { class: 'barnote' },
    'Dry and wet tarmac share a carcass. Same speeds.'));

  for (const s of SECTIONS) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = 'svg-' + s.id;
    const panel = h('div', { class: s.id === 'revs' ? 'panel row' : 'panel' });
    panel.appendChild(svg);
    if (s.id === 'revs') panel.appendChild(buildSetList());
    root.appendChild(h('section', { id: 'sec-' + s.id },
      h('h2', {}, s.title), h('p', { class: 'cap' }, s.cap), panel));
  }
  root.appendChild(buildFooter());

  wireHover('power', (map, p) => map.xToRpm(p.x));
  wireHover('ladder', (map, p) => ({ lane: map.yToLane(p.y), speed: map.xToSpeed(p.x) }));
  wireHover('shift', (map, p) => ({ gear: map.yToGear(p.y), speed: map.xToSpeed(p.x) }));
  wireHover('revs', (map, p) => map.atPoint(p.x, p.y));

  return { surfaceSel, fdSel, setSel };
}

function buildSetList() {
  const list = h('div', { class: 'setlist' }, h('h4', {}, 'Gear sets'));
  car.gear_sets.forEach((s, i) => {
    list.appendChild(h('div', {
      class: 'opt' + (state.draw.includes(i) ? ' on' : ''),
      'data-set': String(i),
      onclick: () => {
        const on = state.draw.includes(i);
        if (on && state.draw.length === 1) return;   // never leave the chart empty
        state.draw = on ? state.draw.filter(x => x !== i)
                        : [...state.draw, i].sort((a, b) => a - b);
        track('toggle-drawn-set');
        commit();
      },
    }, h('i', { style: `background:${
      state.draw.includes(i) ? colourFor(i) : '#fff'};border-color:${
      state.draw.includes(i) ? colourFor(i) : 'var(--line)'}` }),
       s.label.replace('Gear set', 'Set '),
       h('small', {}, ` ${s.gears.length}sp`)));
  });
  return list;
}

const colourFor = i => ['#7A583B', '#148FAC', '#30353A', '#B07A4E', '#0E6E85',
                        '#8D949B', '#4FB3C9', '#5A3F29'][i % 8];

function buildFooter() {
  const input = h('input', { type: 'number', step: '0.0001', value: String(state.k),
    onchange: e => {
      const v = Number.parseFloat(e.target.value);
      if (Number.isFinite(v) && v >= 0.8 && v <= 1.1) {
        state.k = v;
        track('edit-factor');
        commit();
      } else {
        e.target.value = String(state.k);
      }
    } });
  return h('div', { class: 'foot' },
    h('div', {},
      h('h3', {}, 'Rolling radius factor'),
      h('div', { class: 'kbox' }, input,
        h('a', { href: '#', onclick: e => {
          e.preventDefault();
          state.k = car.defaults.loaded_radius_factor;
          input.value = String(state.k);
          commit();
        } }, 'reset')),
      h('p', { class: 'fnote' },
        'A loaded tyre rolls on a smaller radius than the stored one. This factor was '
        + 'fitted against measured in-game top speeds for the Stratos across 15 gears, '
        + 'and is applied to every car and surface. Edit it and every chart redraws.')),
    h('div', {},
      h('h3', {}, 'Known limits'),
      h('div', { class: 'limits' }, (() => {
        const ul = h('ul');
        for (const line of ['Dry and wet tarmac give identical speeds.',
                            'Compound does not change gearing. Compounds share a carcass.',
                            'Speeds are gearing alone. No drag, no slip.']) {
          ul.appendChild(h('li', {}, line));
        }
        return ul;
      })())),
    h('div', {},
      h('h3', {}, 'Data'),
      h('p', { class: 'limits' }, `Read from the game files. Generated ${car.generated}.`)));
}

/**
 * Turn a pointer position into whatever this chart's render() takes as `hover`.
 * The SVGs scale, so client pixels have to go back through the viewBox first.
 */
function wireHover(id, toHover) {
  const svg = document.getElementById('svg-' + id);
  svg.addEventListener('pointermove', e => {
    const map = maps[id];
    if (!map) return;
    const box = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const p = {
      x: (e.clientX - box.left) / box.width * (vb.width || box.width),
      y: (e.clientY - box.top) / box.height * (vb.height || box.height),
    };
    hover[id] = toHover(map, p);
    if (id === 'shift') track('shift-helper');
    draw();
  });
  svg.addEventListener('pointerleave', () => { hover[id] = null; draw(); });
}

function draw() {
  maps.power = powerTorque.render(
    document.getElementById('svg-power'), car, hover.power);
  const fdSvg = document.getElementById('svg-fd');
  const fdSection = document.getElementById('sec-fd');
  fdSection.querySelector('.notadjustable')?.remove();
  if (car.final_drive) {
    fdSection.querySelector('.cap').textContent =
      'Every selectable combination. 100% is the shortest. Speed is top gear of '
      + `${car.gear_sets[state.set].label.toLowerCase()} at the rev limit. `
      + 'Click a row to use that final drive.';
    finalDrive.render(fdSvg, car, state, i => {
      state.fd = i;
      track('change-final-drive');
      commit();
    });
  } else {
    fdSection.querySelector('.cap').textContent = '';
    fdSvg.replaceChildren();
    fdSection.querySelector('.panel').appendChild(
      h('p', { class: 'notadjustable' },
        'The final drive is not adjustable on this car.'));
  }
  maps.ladder = ladder.render(document.getElementById('svg-ladder'), car, state,
    i => { state.set = i; track('pick-gearset'); commit(); }, hover.ladder);
  maps.shift = shiftPoints.render(
    document.getElementById('svg-shift'), car, state, hover.shift);
  maps.revs = speedRevs.render(
    document.getElementById('svg-revs'), car, state, hover.revs);
}

let controls = null;

function commit() {
  history.replaceState(null, '', toHash(state, car));
  syncControls();
  draw();
}

function syncControls() {
  controls.surfaceSel.value = state.surface;
  if (controls.fdSel.options.length) controls.fdSel.value = String(state.fd);
  controls.setSel.value = String(state.set);
  document.querySelectorAll('.setlist .opt').forEach(node => {
    const i = Number(node.dataset.set);
    node.classList.toggle('on', state.draw.includes(i));
    const box = node.querySelector('i');
    box.style.background = state.draw.includes(i) ? colourFor(i) : '#fff';
    box.style.borderColor = state.draw.includes(i) ? colourFor(i) : 'var(--line)';
  });
}

async function main() {
  car = await (await fetch(`../data/${slug}.json`)).json();
  state = parseHash(location.hash, car);
  controls = buildShell();
  track('car-' + slug);
  commit();
  window.addEventListener('hashchange', () => {
    state = parseHash(location.hash, car);
    syncControls();
    draw();
  });
}

main();
```

- [ ] **Step 2: Serve the site locally**

ES modules do not load over `file://`. Run:

```bash
python -m http.server 8000
```

- [ ] **Step 3: Open the Stratos page and check it by eye**

Open `http://localhost:8000/lancia-stratos/`. Confirm, one at a time:
- All five charts draw.
- Top gear of gear set 1 reads **215 km/h** on the ladder.
- Clicking a final drive row moves the highlight and every speed on charts 3, 4 and 5 changes.
- Clicking a lane name in the ladder changes the gear set dropdown, the final drive chart's caption and km/h column, and the whole Shift points chart.
- Hovering Shift points on **gear 3's row** around 130 km/h shows an upshift chip and a red over-limit downshift chip; hovering **gear 4's row** at the same speed shows a downshift that is not flagged.
- Hovering Speed against revs picks out the nearest gear line and reads out its set, gear, revs and speed.
- Ticking a second gear set in the Speed against revs list adds its lines; un-ticking the last one is refused.
- Editing the rolling radius factor to `0.99` moves every speed, and `reset` puts it back.
- The URL hash updates on every change; pasting it into a new tab reproduces the same view.

- [ ] **Step 4: Check a car with no adjustable final drive**

Open `http://localhost:8000/skoda-fabia-rs-rally2-2022/`. The Final drive section must show *The final drive is not adjustable on this car.* and no empty chart. The other four charts must still draw.

- [ ] **Step 5: Check it at phone width**

Narrow the window to 400px. No horizontal scrolling of the page body; the Speed against revs set list stacks under the chart.

- [ ] **Step 6: Run the tests once more and commit**

```bash
node --test test/
git add js/app.js
git commit -m "feat: wire up the car page"
```

---

## Task 13: Site — car picker, README and publish

**Files:**
- Modify: `../acr-car-lab/README.md` (create)
- Verify: generated `index.html`

**Interfaces:**
- Consumes: `data/index.json` and the generated `index.html` from Task 3.
- Produces: a published site.

- [ ] **Step 1: Write `README.md`**

```markdown
# ACR Car Lab

**→ https://fredmayor88.github.io/acr-car-lab/**

Interactive gearing and power charts for every car in Assetto Corsa Rally. One page per
car: the power and torque curve, every selectable final drive, where each gear tops out,
shift points, and speed against revs.

Every number is read from the game's own files.

## How the numbers are made

Speed comes from gearing alone — no drag, no slip:

```
circumference = 2 * pi * free_tyre_radius * rolling_radius_factor
km/h          = rpm * circumference * 0.06 / total_ratio
total_ratio   = gear * primary * rest * differential
```

`rolling_radius_factor` defaults to `0.9562`. A loaded tyre rolls on a smaller radius than
the stored free one; the factor was fitted against measured in-game top speeds for the
Lancia Stratos across 15 gears, and is applied to every car and every surface. It is
editable at the foot of each car page.

## Updating after a game patch

The site holds no numbers in its code, so a patch only changes `data/`.

1. Check out `acr-setup-engineer` **as a sibling of this repo** — the exporter writes to
   `../acr-car-lab` by default:

   ```
   parent/
     acr-setup-engineer/
     acr-car-lab/
   ```

2. From `acr-setup-engineer`, with the game installed:

   ```bash
   make car-lab
   ```

3. Check the result before committing:
   - New cars appear in `data/index.json` and have their own folder.
   - No car lost a surface — every car should have five entries under `tyres`, and a
     missing one means a tyre asset stopped resolving.
   - Spot-check one top speed in game. The Stratos on gear set 1, top gear, stock final
     drive, dry tarmac should read 215 km/h. If it has drifted, the rolling radius factor
     needs refitting rather than the code changing.

4. Commit here:

   ```bash
   git add -A && git commit -m "chore: regenerate for game build <version>"
   ```

## Local development

ES modules need a server; `file://` will not work.

```bash
python -m http.server 8000
# http://localhost:8000/lancia-stratos/
```

Tests cover the pure modules — the maths, the URL state, and each chart's layout:

```bash
node --test test/
```

## Layout

| Path | What it is |
| --- | --- |
| `js/gearing.js` | Core maths. Pure. |
| `js/state.js` | Page state and the URL hash. Pure. |
| `js/svg.js` | SVG helpers. |
| `js/charts/*.js` | One file per chart: a pure `layout()` and a `render()`. |
| `js/app.js` | Wiring. |
| `data/` | Generated. Never edit by hand. |
| `<slug>/index.html` | Generated. Never edit by hand. |

## Licence

MIT.
```

- [ ] **Step 2: Check the generated picker**

Open `http://localhost:8000/`. Every car links to its page; names are readable; the grid wraps at phone width.

- [ ] **Step 3: Commit and push**

```bash
git add -A
git commit -m "docs: readme and update procedure"
git branch -M main
# create the empty repo on GitHub first, then:
git remote add origin git@github.com:fredmayor88/acr-car-lab.git
git push -u origin main
```

- [ ] **Step 4: Turn on GitHub Pages**

In the repo settings, Pages → Source → Deploy from branch → `main` / root. Wait for the
first build, then open `https://fredmayor88.github.io/acr-car-lab/` and click through to
one car page.

- [ ] **Step 5: Create the GoatCounter site**

Register `acr-car-lab` at goatcounter.com so
`https://acr-car-lab.goatcounter.com/count` is live. The script tag is already in every
generated page. Load a car page, then confirm a `car-<slug>` event appears in the
GoatCounter dashboard.

- [ ] **Step 6: Add the links to Notion**

For each car's Catalogue page in the ACR Setup Engineer Notion database, add the URL
`https://fredmayor88.github.io/acr-car-lab/<slug>/`. This is the last step because it is
the one that sends people to the site.

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: repos and regeneration → Tasks 1–3 and 13; data model → Task 1; controls → Tasks 5 and 12; charts 1–5 → Tasks 6–10; calibration control → Task 12; URL state → Task 5; tracking → Tasks 11–12; scope decisions (no studded, no compound, condition labels) → Task 4's constants and their tests; known limits → the footer copy in Task 12; tone → Global Constraints and the verbatim captions in Task 12.

**Deliberate gaps, called out rather than hidden:**
- `js/app.js` and the exporter's `main()` have no unit tests. Both are glue over tested modules and both need either a DOM or the game's paks. They are covered by the explicit manual checklists in Tasks 3 and 12 instead.
- `car_record()` in Task 3 infers the driven axle by trying `Rear` and falling back to `Front`. `make_gearing_chart.py` gets the axle from the caller. If a car comes out with wrong speeds, this is the first place to look, and the 215 km/h spot-check in Task 3 Step 5 is what catches it.
- The site's `<title>` and `<h1>` come from the template YAML's `name:` field. If that field is missing for a car, the slug is used; Task 3 Step 6 will show it in the per-car output line.
