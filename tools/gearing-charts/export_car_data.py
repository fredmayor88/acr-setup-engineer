"""Export one JSON document per car for the ACR Car Lab site.

Where make_gearing_chart.py draws PNGs, this writes the same facts as data and lets the
browser do the arithmetic. The split matters for one reason: the site exposes an editable
rolling-radius factor, so the stored tyre figure has to be the free radius with no factor
baked into it.

    python export_car_data.py --all --out ../acr-car-lab
"""

import html as _html

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
