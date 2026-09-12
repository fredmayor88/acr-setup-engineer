"""Export one JSON document per car for the ACR Car Lab site.

Where make_gearing_chart.py draws PNGs, this writes the same facts as data and lets the
browser do the arithmetic. The split matters for one reason: the site exposes an editable
rolling-radius factor, so the stored tyre figure has to be the free radius with no factor
baked into it.

    python export_car_data.py --all --out ../acr-car-lab
"""

import argparse
import datetime
import html as _html
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'torque-curves'))

import make_gearing_chart as M                                    # noqa: E402
from gearing import gear_set, ratio, tyre_geometry                # noqa: E402
from acrpkg import Package                                        # noqa: E402

# Only the surfaces that resolve to a real tyre asset. MontecarloStudded is excluded:
# DA_PirelliTM00Studded does not exist under the name DT_Wheels gives it.
SURFACES = ('Tarmac_Dry', 'Tarmac_Wet', 'Gravel', 'Sweden', 'Montecarlo')

LOADED_RADIUS_FACTOR = 0.9562


def _kw(torque_nm, rpm):
    """Engine power in kW from torque in Nm at a given engine speed."""
    return torque_nm * rpm / 9549


def build_car_json(slug, name, axle, gear_sets, engine_curve, final_drive, tyres,
                   generated, fixed_final_drive=None):
    """One car's complete published record.

    Every downstream number on the site is derived from this document, so anything the
    browser cannot recompute has to be in here.

    `fixed_final_drive` covers the cars whose final drive cannot be adjusted, where
    `final_drive` is None and the combinations that would otherwise carry the ratio do
    not exist. It is the whole engine-to-wheel ratio below the gearbox — primary gear
    included — so speed is always `rpm * circumference * 0.06 / (gear * fixed)`, the
    same shape as the adjustable case. The two fields are mutually exclusive: when
    `final_drive` is present this is forced to None, because those combinations already
    carry the ratio and a second copy could drift out of step with them.
    """
    if final_drive is not None:
        fixed_final_drive = None
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
        'fixed_final_drive': fixed_final_drive,
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


def car_record(paks, slug, tmp):
    """Everything build_car_json needs for one car, read from the game files."""
    asset, wheel_key, car_asset = M.CARS[slug]
    text = open(os.path.join(M.TEMPLATES, slug + '.yaml'), encoding='utf-8').read()

    files = M.extract(paks, f'DA_{asset}_GearSet_', tmp)
    if not files:
        raise SystemExit(f'{slug}: no gear set assets')
    sets = [gear_set(f) for f in files]

    # The driven axle decides which branch of the drivetrain chain counts, and which
    # tyre row to read. Start from the template's declared drivetrain — the same
    # Front-if-FWD rule make_gearing_chart.render_car uses, so the site and the PNG
    # charts agree. Only if that axle's chain holds none of the adjustable ratios do
    # we probe the other one: a few cars adjust a ratio that sits on the far branch.
    drivetrain = re.search(r'^drivetrain: "([^"]+)"', text, re.MULTILINE)
    axle = 'Front' if drivetrain and drivetrain.group(1) == 'FWD' else 'Rear'

    def read(ax):
        primaries, candidates, _t, _p, _max = M.template_facts(slug, ax)
        fd_value, spelled, chain = M.stock_final_drive(paks, car_asset, ax, tmp)
        return (primaries, fd_value) + M.pick_ratio(candidates, chain, ax)

    primaries, fd_value, name, options, stock = read(axle)
    if not options:
        other = 'Rear' if axle == 'Front' else 'Front'
        probe = read(other)
        if probe[3]:                    # the far branch is where the adjustment lives
            axle = other
            primaries, fd_value, name, options, stock = probe
        # else: nothing is adjustable either way — keep the declared axle, so the
        # published axle and tyre stay truthful rather than reporting the last probe

    final_drive = None
    fixed_final_drive = None
    stock_primary = sets[0][1]
    if not options:
        # Nothing below the gearbox is adjustable, so there are no combinations to carry
        # the ratio — publish it on its own or the site has no way to reach an absolute
        # km/h for this car. Primary gear folded in, so it is the same quantity
        # make_gearing_chart's final_of() draws these cars with. Every car on this branch
        # today has a 1:1 primary (25//25), so the multiply is a no-op now and insurance
        # against a future car that isn't.
        fixed_final_drive = ratio(stock_primary) * fd_value
    else:
        # the part of the chain that never moves: everything below the gearbox with the
        # adjustable ratio divided back out. Same quantity chart_final_drive computes.
        rest = fd_value / ratio(stock)
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
        hits = M.extract(paks, f'DA_{tyre_name}', tmp)
        # DA_<name> is a prefix, so it also catches longer siblings (…Studded). Pick the
        # same file M.tyre picks — soft compound first, then the bare asset.
        soft = [h for h in hits if os.path.basename(h) == f'DA_{tyre_name}_S.uasset']
        exact = [h for h in hits if os.path.basename(h) == f'DA_{tyre_name}.uasset']
        pkg = Package(open((soft or exact or hits)[0], 'rb').read())
        geo = tyre_geometry(pkg.export_bytes(0)[1])
        tyres[surface] = (tyre_name, round(geo[1], 6))

    curve = [(int(r), float(v)) for r, v in re.findall(r'\[(\d+), ([\d.]+)\]', text)]
    display = re.search(r'^car: "(.*)"', text, re.MULTILINE)
    display_name = display.group(1) if display else slug

    return display_name, axle, sets, curve, final_drive, fixed_final_drive, tyres


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
    cars, failed = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for slug in slugs:
            # One unreadable car must not lose the other seventeen — the same policy
            # make_gearing_chart's --all uses. A car with no engine_curve block in its
            # template (the 206 WRC today) has no chart either, so it is simply absent
            # from the site rather than published with a missing power curve.
            try:
                name, axle, sets, curve, fd, fixed_fd, tyres = car_record(
                    args.paks, slug, tmp)
            except SystemExit as e:
                if not args.all:
                    raise
                failed.append(f'{slug}: {e}')
                continue
            gears = [[(g, ratio(g)) for g in forward] for forward, _p, _r in sets]
            doc = build_car_json(slug, name, axle, gears, curve, fd, tyres, today,
                                 fixed_final_drive=fixed_fd)
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
        for f in failed:
            print(f'  !! skipped {f}')
        print(f'{len(cars)}/{len(slugs)} cars exported')


if __name__ == '__main__':
    main()
