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
from gearing import (CHAIN_SLOTS, LOADED_RADIUS_FACTOR, gear_set,  # noqa: E402
                     ratio, tyre_geometry)
from acrpkg import Package                                        # noqa: E402
from game_version import read_game_version                        # noqa: E402
import calibration as CAL                                         # noqa: E402
import drivetrain_page as DP                                      # noqa: E402
from extract_torque_curves import (CAR_MAP as CURVE_CARS,         # noqa: E402
                                   parse_rich_curve, summarise)

# Only the surfaces that resolve to a real tyre asset. MontecarloStudded is excluded:
# DA_PirelliTM00Studded does not exist under the name DT_Wheels gives it.
SURFACES = ('Tarmac_Dry', 'Tarmac_Wet', 'Gravel', 'Sweden', 'Montecarlo')

# Cars known to be unexportable for a reason that is not a regression, so a partial
# export is still a successful one. Empty today: the 206 WRC, once listed here for want of
# an engine curve, now exports on the Xsara WRC curve its car asset points at.
# Any car failing that is NOT listed here fails the run — see the end of main().
KNOWN_MISSING = set()

# LOADED_RADIUS_FACTOR is imported from gearing.py, the one copy. It is refitted from
# calibration.json (python calibration.py) and a test holds the two in step.


def _kw(torque_nm, rpm):
    """Engine power in kW from torque in Nm at a given engine speed."""
    return torque_nm * rpm / 9549


def build_car_json(slug, name, axle, gear_sets, engine_curve, final_drive, tyres,
                   fixed_final_drive=None, rev_limit=None):
    """One car's complete published record.

    `rev_limit` is `{'rpm', 'source', 'game_v4', 'curve_source', 'curve_from'}`: the resolved
    rev limit and where it came from (see calibration.resolve_rev_limit), the game's v4 value
    it was checked against, the vehicle folder the torque curve was read from, and — only when
    that curve belongs to another car — that car's `{'slug', 'name'}`. The rev limit is not
    the end of the curve: the curve is kept whole so the power chart can draw all of it.

    Every downstream number on the site is derived from this document, so anything the
    browser cannot recompute has to be in here.

    `gear_sets` is a list of `(gears, primary)`, where `primary` is that set's own
    `(spelling, value)`. The primary belongs to the gear set, not to the car: four cars
    ship a different primary in each set, so a single car-level primary is only true for
    set 1 and overstates the others by up to 26%. Speed therefore composes as
    `gear * set primary * rest * option`.

    `final_drive['primaries']` is a different thing and stays separate: it is the list of
    primaries the player can *select*, which only one car in the game has. When it is
    empty the primary is fixed at the gear set's own, and `gear_sets[i]['primary']` is
    also the default selection when it is not.

    `fixed_final_drive` covers the cars whose final drive cannot be adjusted, where
    `final_drive` is None and the combinations that would otherwise carry the ratio do
    not exist. It is the engine-to-wheel ratio below the gearbox *excluding* the primary,
    exactly like `final_drive['rest']`, because the primary now travels with the gear
    set — so speed is `rpm * circ * 0.06 / (gear * set primary * fixed)`. The two fields
    are mutually exclusive: when `final_drive` is present this is forced to None, because
    those combinations already carry the ratio and a second copy could drift out of step.
    """
    if final_drive is not None:
        fixed_final_drive = None
    curve = [[rpm, torque, _kw(torque, rpm)] for rpm, torque in engine_curve]
    peak_torque = max(curve, key=lambda r: r[1])
    peak_power = max(curve, key=lambda r: r[2])

    if rev_limit is None:
        raise ValueError(f'{slug}: a resolved rev limit is required')

    doc = {
        'slug': slug,
        'name': name,
        'axle': axle,
        'engine': {
            'redline': rev_limit['rpm'],
            'redline_source': rev_limit['source'],
            'game_v4': rev_limit.get('game_v4'),
            'peak_torque_rpm': peak_torque[0],
            'peak_power_rpm': peak_power[0],
            'curve_source': rev_limit.get('curve_source'),
            'curve_from': rev_limit.get('curve_from'),
            'curve': curve,
        },
        'gear_sets': [
            {'label': f'Gear set {i + 1}',
             'primary': {'name': primary[0], 'value': primary[1]},
             'gears': [{'name': n, 'value': v} for n, v in gears]}
            for i, (gears, primary) in enumerate(gear_sets)
        ],
        'final_drive': None,
        'fixed_final_drive': fixed_final_drive,
        'tyres': {key: {'asset': asset, 'free_radius': radius}
                  for key, (asset, radius) in tyres.items()},
        'defaults': {'loaded_radius_factor': LOADED_RADIUS_FACTOR},
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
        # the averaged-axle cars only (see averaged_final_drive); every other car's
        # document keeps exactly the five fields above
        for field in ('settings', 'formula', 'rows'):
            if field in final_drive:
                doc['final_drive'][field] = final_drive[field]
    return doc


# Ruling R51, measured in game: on these cars the centre differential averages its two
# outputs, so the ratio below the gearbox is
#     fixed_pre * prod(pre) * (fixed_front * prod(front) + fixed_rear * prod(rear)) / 2
# and every ratio the setup screen offers on the chain is published as its own setting. The
# Audi has no centre differential and cannot be measured (it is undriveable with front and
# rear apart); the same formula is assumed. Not generalised to any other car.
AVERAGED_AXLE_CARS = frozenset({
    'lancia-delta-integrale-evoluzione-1992',
    'peugeot-206-wrc-1999',
    'subaru-impreza-555-s3-1993',
    'citroen-xsara-wrc-2003',
    'audi-quattro-gr4-1981',
})

# Of those, the cars with no centre differential: front and rear are geared together, and
# ratios set apart make the axles fight. Fred's ruling for the Audi (R51); its template has no
# centre adjustment of any kind.
NO_CENTRE_DIFFERENTIAL = frozenset({'audi-quattro-gr4-1981'})

# Short, stable URL-hash keys for the ratio settings. Never rename one: links carry them.
SETTING_KEYS = {
    'Center Differential Ratio': 'cdr',
    'Center Ratio to Front': 'ctf',
    'Center Ratio to Rear': 'ctr',
    'Differential Ratio Front': 'dfr',
    'Differential Ratio Rear': 'drr',
}


def template_ratio_settings(text):
    """[(adjustment, [step spellings])] for every drivetrain-chain ratio a car template makes
    selectable, in the template's (setup screen) order. Primary Gear is not a chain ratio."""
    out = []
    for block in re.split(r'\n\s*- section: ', text)[1:]:
        name = re.search(r'adjustment: "([^"]+)"', block)
        steps = re.search(r'discrete_steps: "(.*)"', block)
        if name and name.group(1) in CHAIN_SLOTS and steps and steps.group(1).strip():
            out.append((name.group(1), [s.strip() for s in steps.group(1).split(',')]))
    return out


def averaged_final_drive(text, chain, primaries, centre_differential=True, measured=True):
    """The `final_drive` record of an averaged-axle car, from its template and the drivetrain
    chain in its DA_<car> asset (drivetrain_chain: centre diff, centre->front, centre->rear,
    front diff, rear diff).

    - `settings`: every selectable chain ratio in template order, `{key, adjustment, steps:
      [{name, value}], stock}`; `stock` is the spelling in the car's own chain.
    - `formula`: which setting keys sit before the split (`pre`), on the front path and on the
      rear path, and the product of the chain ratios on each part that are not selectable;
      `centre_differential` (False: the axles are locked together) and `measured` (False: the
      formula is assumed for this car, no speed run backs it).
    - `rows`: the setting keys a Final drive chart row sets together — both differentials
      where both are selectable, otherwise the centre differential. `options` are the steps
      those settings share by name, in the first one's order.
    - `adjustment`, `options`, `stock_option` and `rest` keep their meaning for every other
      car, with every other setting at stock: below = rest * option.
    """
    settings = []
    for adjustment, steps in template_ratio_settings(text):
        stock = chain[CHAIN_SLOTS[adjustment]]
        if stock not in steps:
            raise SystemExit(f'{adjustment}: the car ships with {stock}, which is not one of '
                             f'its steps')
        settings.append({'key': SETTING_KEYS[adjustment], 'adjustment': adjustment,
                         'steps': [{'name': s, 'value': ratio(s)} for s in steps],
                         'stock': stock})
    by_slot = {CHAIN_SLOTS[s['adjustment']]: s['key'] for s in settings}

    def part(slots):
        fixed = 1.0
        for i in slots:
            if i not in by_slot:
                fixed *= ratio(chain[i])
        return [by_slot[i] for i in slots if i in by_slot], fixed

    pre, fixed_pre = part([0])
    front, fixed_front = part([1, 3])
    rear, fixed_rear = part([2, 4])
    # The notes on the site name a path by its settings alone, so a fixed ratio sharing a path
    # with a setting would make them wrong while the numbers stayed right: fail instead.
    for name, keys, fixed in (('pre', pre, fixed_pre), ('front', front, fixed_front),
                              ('rear', rear, fixed_rear)):
        if keys and abs(fixed - 1.0) > 1e-12:
            raise SystemExit(f'the {name} path has settings {keys} and a fixed ratio {fixed}; '
                             f'the site notes cannot describe that yet')
    formula = {'pre': pre, 'front': front, 'rear': rear,
               'fixed_pre': fixed_pre, 'fixed_front': fixed_front, 'fixed_rear': fixed_rear,
               'centre_differential': centre_differential, 'measured': measured}

    keyed = {s['key']: s for s in settings}
    rows = ['dfr', 'drr'] if 'dfr' in keyed and 'drr' in keyed else ['cdr']
    if any(k not in keyed for k in rows):
        raise SystemExit(f'no selectable {rows} to build the final drive rows from')
    names = [{st['name'] for st in keyed[k]['steps']} for k in rows]
    shared = [st['name'] for st in keyed[rows[0]]['steps']
              if all(st['name'] in n for n in names)]
    stock_row = keyed[rows[0]]['stock']
    if any(keyed[k]['stock'] != stock_row for k in rows):
        raise SystemExit(f'the car ships with different {rows} ratios, so no row is stock')
    return {
        'adjustment': ' + '.join(keyed[k]['adjustment'] for k in rows),
        'primaries': [(p, ratio(p)) for p in primaries],
        'options': [(o, ratio(o)) for o in shared],
        'stock_option': stock_row,
        'rest': averaged_below(formula, {s['key']: ratio(s['stock']) for s in settings})
        / ratio(stock_row),
        'settings': settings,
        'formula': formula,
        'rows': rows,
    }


def averaged_below(formula, values):
    """below the gearbox from a `formula` record and `{key: ratio}` for its settings."""
    def prod(keys):
        out = 1.0
        for k in keys:
            out *= values[k]
        return out
    return (formula['fixed_pre'] * prod(formula['pre'])
            * (formula['fixed_front'] * prod(formula['front'])
               + formula['fixed_rear'] * prod(formula['rear'])) / 2)


# The site's theme key. js/theme.js in acr-car-lab writes the same one.
THEME_KEY = 'acr-car-lab-theme'

# Runs before the stylesheet so a stored light/dark choice is on <html> by first paint.
# With nothing stored the page follows the OS through CSS alone, so there is no else.
# The function wrapper keeps `t` off window.
THEME_HEAD = (
    '<meta name="color-scheme" content="light dark">\n'
    f"<script>(function(){{try{{var t=localStorage.getItem('{THEME_KEY}');"
    "if(t==='dark'||t==='light')document.documentElement.dataset.theme=t}catch(e){}})()"
    '</script>')

# The label names the theme a click switches to; app.css shows the right one. Each label
# carries its icon inside its own span, so the same CSS swaps both at first paint. The
# icons draw in currentColor and are hidden from assistive tech: the button's aria-label
# already says what a click does.
_ICON = ('<svg class="icon {name}" viewBox="0 0 12 12" width="12" height="12" '
         'aria-hidden="true" focusable="false" fill="none" stroke="currentColor" '
         'stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">{shape}</svg>')
MOON = _ICON.format(name='moon', shape='<path d="M10.2 7.6A4.6 4.6 0 0 1 4.4 1.8'
                                       'a4.6 4.6 0 1 0 5.8 5.8z"/>')
SUN = _ICON.format(name='sun', shape='<circle cx="6" cy="6" r="2.2"/>'
                                     '<path d="M6 .9v1.2M6 9.9v1.2M.9 6h1.2M9.9 6h1.2'
                                     'M2.4 2.4l.85.85M8.75 8.75l.85.85M2.4 9.6l.85-.85'
                                     'M8.75 3.25l.85-.85"/>')
THEME_BUTTON = (f'<button class="theme" type="button"><span class="to-dark">{MOON}Dark</span>'
                f'<span class="to-light">{SUN}Light</span></button>')

# A car's gearing page lives at <slug>/gears/, leaving <slug>/ free for more pages about the
# same car. CAR_ROOT is the way back to the site root from there: every shared asset and the
# picker link go through it, so moving the page again is one change here.
CAR_PAGE_DIR = 'gears'
CAR_ROOT = '../../'
# The car's drivetrain notes: a static page beside gears/, built by drivetrain_page.py.
DRIVETRAIN_PAGE_DIR = 'drivetrain'
# The drivetrain pages are generated and kept current, but not linked from anywhere on the site
# yet (and carry noindex). True puts back both links: the picker's "Drivetrain notes" section
# and the "Drivetrain notes" crumb on every gears page.
PUBLISH_DRIVETRAIN_LINKS = False
DRIVETRAIN_CRUMB = f'<a class="crumb" href="../{DRIVETRAIN_PAGE_DIR}/">Drivetrain notes</a>'

CAR_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{theme_head}
<title>{name} — ACR Car Lab</title>
<meta name="description" content="Gearing, final drive and power for the {name} in \
Assetto Corsa Rally.">
<link rel="stylesheet" href="{root}app.css">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap" id="app" data-car="{slug}">
  <header>
    <div class="brandrow">
      <span class="brand">ACR <b>Car Lab</b></span>
      {drivetrain_crumb}<a class="crumb" href="{root}">All cars →</a>
      {theme_button}
    </div>
    <h1>{name}</h1>
  </header>
  <p class="loading">Loading…</p>
</div>
<script type="module" src="{root}js/app.js"></script>
</body></html>
"""

# <slug>/ was the car page before it moved under gears/, and links to it are already out
# there. The script keeps the query and hash (the page state), so it runs before the refresh;
# the refresh only covers a browser with scripts off. No GoatCounter: the page it forwards to
# counts the visit.
REDIRECT_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<title>{name} — ACR Car Lab</title>
<link rel="canonical" href="{page}/">
<script>location.replace('{page}/'+location.search+location.hash)</script>
<meta http-equiv="refresh" content="0; url={page}/">
</head>
<body>
<p><a href="{page}/">{name}</a></p>
</body></html>
"""

INDEX_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{theme_head}
<title>ACR Car Lab</title>
<meta name="description" content="Interactive gearing and power charts for {count} cars in \
Assetto Corsa Rally.">
<link rel="stylesheet" href="app.css">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brandrow">
      <span class="brand">ACR <b>Car Lab</b></span>
      {theme_button}
    </div>
    <h1>{count} cars, gear by gear</h1>
    <p class="sub">Gearing, final drive and power, read from the game files.</p>
  </header>
  <ul class="carlist">
{items}
  </ul>
{drivetrain_section}  <div class="foot">
    <p class="promo">Want a setup, not just the numbers? <a href="https://github.com/fredmayor88/acr-setup-engineer">ACR Setup Engineer</a> — a free Claude skill that tunes a car to how you drive and saves it to your Notion. · <a href="https://github.com/fredmayor88/acr-car-lab/issues">Issues and feedback</a></p>
  </div>
</div>
<script type="module" src="js/theme.js"></script>
</body></html>
"""


DRIVETRAIN_SECTION = """  <section class="dtlist">
    <h2>Drivetrain notes</h2>
    <p class="cap">Per car: layout, the settings that change the gearing, how the final drive is worked out, and what was measured in game.</p>
    <ul class="carlist minor">
{drivetrain_items}
    </ul>
  </section>
"""


def render_car_page(slug, name, publish_drivetrain=None):
    """The generated shell for one car. Title and h1 are baked in so the page is
    indexable without running the app. `publish_drivetrain` (default
    PUBLISH_DRIVETRAIN_LINKS) adds the crumb to the car's drivetrain page."""
    if publish_drivetrain is None:
        publish_drivetrain = PUBLISH_DRIVETRAIN_LINKS
    safe = _html.escape(name)
    crumb = DRIVETRAIN_CRUMB + '\n      ' if publish_drivetrain else ''
    return CAR_PAGE.format(slug=_html.escape(slug), name=safe, root=CAR_ROOT,
                           theme_head=THEME_HEAD, theme_button=THEME_BUTTON,
                           drivetrain_crumb=crumb)


def render_redirect_page(slug, name):
    """What stays at <slug>/index.html: a forward to <slug>/gears/, hash intact."""
    return REDIRECT_PAGE.format(name=_html.escape(name), page=CAR_PAGE_DIR)


def write_car_pages(out, slug, name):
    """The car page under <slug>/gears/ and the forward at <slug>/. Returns both paths."""
    pages = [((slug, CAR_PAGE_DIR, 'index.html'), render_car_page(slug, name)),
             ((slug, 'index.html'), render_redirect_page(slug, name))]
    for parts, html in pages:
        path = os.path.join(out, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(html)
    return ['/'.join(parts) for parts, _html_text in pages]


def render_drivetrain_page(doc, template_text, calibration, notes, game_version=None,
                           generated=None):
    """<slug>/drivetrain/index.html for one exported car document, with the site's shared head
    and theme toggle."""
    return DP.render_drivetrain_page(doc, template_text, calibration, notes, game_version,
                                     generated, theme_head=THEME_HEAD,
                                     theme_button=THEME_BUTTON, root=CAR_ROOT)


def write_drivetrain_page(out, doc, template_text, calibration, notes, game_version=None,
                          generated=None):
    """Write the drivetrain page under <slug>/drivetrain/. Returns its path."""
    parts = (doc['slug'], DRIVETRAIN_PAGE_DIR, 'index.html')
    path = os.path.join(out, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(render_drivetrain_page(doc, template_text, calibration, notes, game_version,
                                        generated))
    return '/'.join(parts)


def build_index_json(cars, generated=None, game_version=None):
    """The car list the picker reads, sorted by display name.

    The build date and game version live here and nowhere else. Stamping the date into
    every car document made a no-op re-run on a later day a diff in every car file, which buries
    a real change.
    """
    doc = {'cars': sorted(({'slug': c['slug'], 'name': c['name']} for c in cars),
                          key=lambda c: c['name'])}
    if generated is not None:
        doc['generated'] = generated
    if game_version is not None:
        doc['game_version'] = game_version
    return doc


def site_game_version(paks, whole_site):
    """The game version the site's footer names, read from the install ('0.6').

    Only a whole-site export writes index.json, so only that needs it. It is read before
    any car, so a version that cannot be read fails the run before anything is written.
    """
    if not whole_site:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        return read_game_version(paks, tmp)


def existing_index_facts(out):
    """(game_version, generated) from the site's current data/index.json, or (None, None).

    A single-car export neither reads the version from the paks nor writes index.json, so its
    drivetrain page names the version and date the rest of the site already shows."""
    try:
        with open(os.path.join(out, 'data', 'index.json'), encoding='utf-8') as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None, None
    return doc.get('game_version'), doc.get('generated')


def export_car(out, slug, record, calibration, notes, game_version, generated, template_text):
    """Write one car's data document, gears page, forward and drivetrain page from its
    car_record tuple. Returns (document, gear set count).

    The drivetrain page is rendered before anything is written. A car whose notes no longer fit
    its data (say a game patch dropped a gear a placeholder reads) then fails as a whole, as a
    SystemExit, exactly like a car whose game files could not be read: main() skips it, finishes
    the others, and fails the run at the end."""
    name, axle, sets, curve, fd, fixed_fd, tyres, engine = record
    # each set keeps its own primary — four cars ship a different one per set
    gears = [([(g, ratio(g)) for g in forward], (p, ratio(p))) for forward, p, _r in sets]
    doc = build_car_json(slug, name, axle, gears, curve, fd, tyres,
                         fixed_final_drive=fixed_fd, rev_limit=engine)
    try:
        page = render_drivetrain_page(doc, template_text, calibration, notes, game_version,
                                      generated)
    except Exception as e:                  # noqa: BLE001 - any failure building the prose
        raise SystemExit(f'drivetrain page failed: {type(e).__name__}: {e}') from e
    with open(os.path.join(out, 'data', slug + '.json'), 'w',
              encoding='utf-8', newline='\n') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    write_car_pages(out, slug, name)
    path = os.path.join(out, slug, DRIVETRAIN_PAGE_DIR, 'index.html')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    return doc, len(gears)


def render_index_page(cars, publish_drivetrain=None):
    """The picker. `publish_drivetrain` (default PUBLISH_DRIVETRAIN_LINKS) adds the list of
    drivetrain pages after the gearing list."""
    if publish_drivetrain is None:
        publish_drivetrain = PUBLISH_DRIVETRAIN_LINKS
    listed = build_index_json(cars)['cars']
    items = '\n'.join(
        f'    <li><a href="{_html.escape(c["slug"])}/{CAR_PAGE_DIR}/">'
        f'{_html.escape(c["name"])}</a></li>'
        for c in listed)
    drivetrain_items = '\n'.join(
        f'      <li><a href="{_html.escape(c["slug"])}/{DRIVETRAIN_PAGE_DIR}/">'
        f'{_html.escape(c["name"])}</a></li>'
        for c in listed)
    section = (DRIVETRAIN_SECTION.format(drivetrain_items=drivetrain_items)
               if publish_drivetrain else '')
    return INDEX_PAGE.format(items=items, drivetrain_section=section, count=len(cars),
                             theme_head=THEME_HEAD, theme_button=THEME_BUTTON)


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
        primaries, candidates, _t, _p, _max = M.template_facts(slug, ax, require_curve=False)
        fd_value, spelled, chain = M.stock_final_drive(paks, car_asset, ax, tmp)
        return (primaries, fd_value, chain) + M.pick_ratio(candidates, chain, ax)

    primaries, fd_value, chain, name, options, stock = read(axle)
    if not options:
        other = 'Rear' if axle == 'Front' else 'Front'
        probe = read(other)
        if probe[4]:                    # the far branch is where the adjustment lives
            axle = other
            primaries, fd_value, chain, name, options, stock = probe
        # else: nothing is adjustable either way — keep the declared axle, so the
        # published axle and tyre stay truthful rather than reporting the last probe

    final_drive = None
    fixed_final_drive = None
    if not options:
        # Nothing below the gearbox is adjustable, so there are no combinations to carry
        # the ratio — publish it on its own or the site has no way to reach an absolute
        # km/h for this car. The primary is NOT folded in: it travels on each gear set
        # now, so folding it here would double-count it.
        fixed_final_drive = fd_value
    else:
        # the part of the chain that never moves: everything below the gearbox with the
        # adjustable ratio divided back out. Same quantity chart_final_drive computes,
        # and like fixed_final_drive it excludes the primary.
        rest = fd_value / ratio(stock)
        final_drive = {
            'adjustment': name,
            # Only genuinely selectable primaries. The old `or [stock_primary]` fallback
            # published set 1's primary as if it were the car's, which is the bug that
            # overstated the other gear sets. An empty list means "not selectable" and
            # the gear set's own primary stands.
            'primaries': [(p, ratio(p)) for p in primaries],
            'options': [(o, ratio(o)) for o in options],
            'stock_option': stock,
            'rest': rest,
        }
    if slug in AVERAGED_AXLE_CARS:
        # the axle and tyre row above stay as they were: every one of these reads Rear
        measured = any(r['car'] == slug for r in CAL.load_calibration()['speed_runs'])
        final_drive = averaged_final_drive(text, chain, primaries,
                                           centre_differential=slug not in NO_CENTRE_DIFFERENTIAL,
                                           measured=measured)
        fixed_final_drive = None

    tyres = {}
    for surface in SURFACES:
        try:
            tyre_name, _circ, _compound = M.tyre(paks, wheel_key, surface, axle, tmp)
        except SystemExit:
            continue                       # a car with no tyre for this surface
        hits = M.extract(paks, f'DA_{tyre_name}', tmp)
        # DA_<name> is a prefix, so it also catches longer siblings (…Studded). Pick the
        # same file M.tyre picks — soft compound first, then the bare asset.
        #
        # THIS MUST STAY IN LOCKSTEP WITH M.tyre's selection rule (make_gearing_chart.py,
        # the `soft`/`exact` lines in tyre()). The duplication is deliberate: M.tyre
        # returns a rolling circumference and the site needs the free radius, and
        # changing its return signature would break the PNG generator that depends on it.
        # If that rule ever changes there, change it here too or the site and the charts
        # will quietly quote different tyres.
        soft = [h for h in hits if os.path.basename(h) == f'DA_{tyre_name}_S.uasset']
        exact = [h for h in hits if os.path.basename(h) == f'DA_{tyre_name}.uasset']
        pkg = Package(open((soft or exact or hits)[0], 'rb').read())
        geo = tyre_geometry(pkg.export_bytes(0)[1])
        tyres[surface] = (tyre_name, round(geo[1], 6))

    # A car with no winter tyre is normal; a car with no tyre at all is not. Without this
    # floor a pak rename turns "DT_Wheels not found" — a batch-wide failure — into a full
    # set of documents with an empty tyres map and a clean exit.
    if not tyres:
        raise SystemExit(f'{slug}: no tyre resolved on any of {len(SURFACES)} surfaces')

    display = re.search(r'^car: "(.*)"', text, re.MULTILINE)
    display_name = display.group(1) if display else slug

    engine = engine_facts(paks, slug, car_asset, text, tmp)
    return (display_name, axle, sets, engine.pop('curve'), final_drive, fixed_final_drive,
            tyres, engine)


def template_curve(text):
    """(curve points, vehicle folder) from a template's engine_curve block, or ([], None)."""
    curve = [(int(r), float(v)) for r, v in re.findall(r'\[(\d+), ([\d.]+)\]', text)]
    source = re.search(r'source: "ACR game files - FC_(\w+?)_Torque"', text)
    return curve, (source.group(1) if source else None)


def curve_from(folder, own_slug):
    """{'slug', 'name'} of the car a borrowed curve belongs to; None when it is the car's own."""
    owner = CURVE_CARS.get(folder)
    if owner is None or owner[0] == own_slug:
        return None
    return {'slug': owner[0], 'name': owner[1]}


def engine_facts(paks, slug, car_asset, text, tmp):
    """The torque curve and the resolved rev limit, with where each came from.

    The curve comes from the template's engine_curve block. A car without one (the 206 WRC)
    has no FC_*_Torque asset of its own either: its DA_<car> asset points at another car's,
    so that curve is read from the game files with the torque-curve extractor's own parser.
    """
    blob = open(CAL.car_asset(paks, car_asset, tmp), 'rb').read()
    curve, folder = template_curve(text)
    if not curve:
        ref = CAL.torque_curve_ref(blob)
        if ref is None:
            raise SystemExit(f'{slug}: no engine curve in the template and no FC_*_Torque '
                             f'reference in DA_{car_asset}')
        folder, asset = ref
        want = asset + '.uasset'
        hits = [h for h in M.extract(paks, want, tmp) if os.path.basename(h) == want]
        keys = parse_rich_curve(open(hits[0], 'rb').read()) if hits else None
        if not keys:
            raise SystemExit(f'{slug}: could not read the borrowed curve {asset}')
        curve = [(r, float(v)) for r, v in summarise(keys)['points']]

    stages = CAL.rev_stages(blob)
    v4 = stages[-1] if stages else None
    rpm, source, warning = CAL.resolve_rev_limit(slug, v4, CAL.load_calibration())
    if warning:
        print(f'  !! {warning}')
    return {'curve': curve, 'rpm': rpm, 'source': source,
            'game_v4': int(round(v4)) if v4 is not None else None,
            'curve_source': folder, 'curve_from': curve_from(folder, slug)}


def prune(out, exported):
    """Delete the generated files of cars this run did not export.

    Step 7 of the build commits with `git add -A`, so a car that drops out — removed from
    CARS, or broken by a game patch — would otherwise leave a stale data/<slug>.json and
    an orphaned <slug>/index.html committed and reachable while being absent from the
    index. Only `data/*.json` and the matching pages — <slug>/gears/index.html,
    <slug>/drivetrain/index.html and the forward at <slug>/index.html — are considered, so nothing hand-written (app.css, js/,
    anything Task 4 adds) is ever in scope. A folder is removed only once it is empty.
    """
    removed = []
    data = os.path.join(out, 'data')
    for entry in sorted(os.listdir(data)):
        stem, ext = os.path.splitext(entry)
        if ext != '.json' or stem == 'index' or stem in exported:
            continue
        os.remove(os.path.join(data, entry))
        removed.append(f'data/{entry}')
        for parts in ((stem, CAR_PAGE_DIR, 'index.html'),
                      (stem, DRIVETRAIN_PAGE_DIR, 'index.html'), (stem, 'index.html')):
            page = os.path.join(out, *parts)
            if os.path.isfile(page):
                os.remove(page)
                removed.append('/'.join(parts))
        for folder in ((stem, CAR_PAGE_DIR), (stem, DRIVETRAIN_PAGE_DIR), (stem,)):
            try:
                os.rmdir(os.path.join(out, *folder))
            except OSError:
                pass                   # missing, or not empty: something else lives there
    return removed


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

    game_version = site_game_version(args.paks, args.all)
    slugs = sorted(M.CARS) if args.all else [args.car]
    today = datetime.date.today().isoformat()
    # the drivetrain page's footer and rev-limit line name these; a single-car export keeps
    # what the site's index already says
    page_version, page_date = ((game_version, today) if args.all
                               else existing_index_facts(out))
    cars, failed = [], []
    calibration = CAL.load_calibration()
    notes = DP.load_notes()
    with tempfile.TemporaryDirectory() as tmp:
        for slug in slugs:
            # One unreadable car must not lose the others — the same policy
            # make_gearing_chart's --all uses. A car whose engine curve cannot be found
            # (neither in its template nor through its car asset) is simply absent from
            # the site rather than published with a missing power curve.
            try:
                record = car_record(args.paks, slug, tmp)
                with open(os.path.join(M.TEMPLATES, slug + '.yaml'), encoding='utf-8') as fh:
                    template_text = fh.read()
                doc, n_sets = export_car(out, slug, record, calibration, notes, page_version,
                                         page_date, template_text)
            except SystemExit as e:
                if not args.all:
                    raise SystemExit(f'{slug}: {e}') from e
                print(f'  !! {slug}: {e}')
                failed.append(f'{slug}: {e}')
                continue
            cars.append({'slug': slug, 'name': doc['name']})
            print(f'{slug}: {n_sets} gear sets, {len(doc["tyres"])} surfaces, rev limit '
                  f'{doc["engine"]["redline"]} ({doc["engine"]["redline_source"]}), '
                  f'curve ends {doc["engine"]["curve"][-1][0]}')

    if args.all:
        pruned = prune(out, {c['slug'] for c in cars})
        with open(os.path.join(out, 'data', 'index.json'), 'w',
                  encoding='utf-8', newline='\n') as fh:
            json.dump(build_index_json(cars, today, game_version), fh, indent=1)
            fh.write('\n')
        with open(os.path.join(out, 'index.html'), 'w',
                  encoding='utf-8', newline='\n') as fh:
            fh.write(render_index_page(cars))
        for p in pruned:
            print(f'  -- pruned {p}')
        for f in failed:
            print(f'  !! skipped {f}')
        print(f'{len(cars)}/{len(slugs)} cars exported, game version {game_version}')

        # A partial export must not look like a complete one. index.json and index.html
        # have just been rebuilt from the survivors, so a car that broke in a game patch
        # would otherwise vanish from the site with `make car-lab` still reporting
        # success. KNOWN_MISSING is for a documented, long-standing gap that would make
        # the target permanently red — anything else is a real regression and fails.
        unexpected = [f for f in failed if f.split(':')[0] not in KNOWN_MISSING]
        if unexpected:
            raise SystemExit('export incomplete: '
                             + '; '.join(unexpected))


if __name__ == '__main__':
    main()
