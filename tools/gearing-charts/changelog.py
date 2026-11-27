"""Per-car changelog for the ACR Car Lab site: what changed in a car's data from one game
release to the next.

The log is cumulative and lives in the site, as car-changelogs.json at its root:
    {slug: [{"version": "0.7", "date": "2026-11-27", "changes": ["...", ...]}, ...]}
newest first. It cannot be rebuilt: each entry is the difference between the car's document
as the previous release exported it and as this one does, and the previous document is gone
once overwritten. So an entry is written once, on the first export of a new game version, and
kept as it is by every later export of that version.

Only the car's own data is compared (gearing, final drive, tyres, engine curve, steering lock,
rev limit), never a field the site adds or the way the site presents it.
"""
import html
import json
import os

HP_PER_KW = 1.35962
SURFACE_NAMES = {'Tarmac_Dry': 'dry tarmac', 'Tarmac_Wet': 'wet tarmac', 'Gravel': 'gravel',
                 'Sweden': 'snow', 'Montecarlo': 'Monte Carlo'}
ADDED = 'Added to the site.'
CHANGELOG_PAGE_DIR = 'changelog'


def _ordinal(n):
    return f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def _names(items):
    return [i['name'] for i in items]


def _added_removed(label, old, new):
    added = [n for n in new if n not in old]
    removed = [n for n in old if n not in new]
    parts = ([f'added {", ".join(added)}'] if added else []) + (
        [f'removed {", ".join(removed)}'] if removed else [])
    return [f'{label}: {"; ".join(parts)}.'] if parts else []


def _stock(label, old_name, new_name, value_of):
    if old_name == new_name:
        return []
    return [f'{label} stock: {old_name} ({value_of(old_name):.3f}) → '
            f'{new_name} ({value_of(new_name):.3f}).']


def gearing_changes(old, new):
    out = []
    os_, ns = old['gear_sets'], new['gear_sets']
    if len(os_) != len(ns):
        out.append(f'Gear sets: {len(os_)} → {len(ns)}.')
    for i, (a, b) in enumerate(zip(os_, ns)):
        label = f'Gear set {i + 1}'
        if a['primary']['name'] != b['primary']['name']:
            out.append(f'{label} primary: {a["primary"]["name"]} → {b["primary"]["name"]}.')
        ga, gb = _names(a['gears']), _names(b['gears'])
        if len(ga) != len(gb):
            out.append(f'{label}: {len(ga)} → {len(gb)} gears.')
            continue
        moved = [f'{_ordinal(j + 1)} {x} → {y}' for j, (x, y) in enumerate(zip(ga, gb)) if x != y]
        if moved:
            out.append(f'{label}: {", ".join(moved)}.')
    return out


def final_drive_changes(old, new):
    a, b = old.get('final_drive'), new.get('final_drive')
    if a is None and b is None:
        x, y = old.get('fixed_final_drive'), new.get('fixed_final_drive')
        return [] if x == y else [f'Fixed final drive: {x:.3f} → {y:.3f}.']
    if a is None or b is None:
        return ['The final drive is now adjustable.' if b else
                'The final drive is no longer adjustable.']
    out = _added_removed('Primary Gear options', _names(a['primaries']), _names(b['primaries']))
    if 'settings' in a and 'settings' in b:
        olds = {s['adjustment']: s for s in a['settings']}
        for s in b['settings']:
            o = olds.get(s['adjustment'])
            if o is None:
                out.append(f'New ratio setting: {s["adjustment"]}.')
                continue
            values = {st['name']: st['value'] for st in o['steps'] + s['steps']}
            out += _added_removed(f'{s["adjustment"]} options', _names(o['steps']),
                                  _names(s['steps']))
            out += _stock(s['adjustment'], o['stock'], s['stock'], values.__getitem__)
        out += [f'Ratio setting removed: {n}.' for n in olds
                if n not in {s['adjustment'] for s in b['settings']}]
        return out
    name = b['adjustment']
    values = {o['name']: o['value'] for o in a['options'] + b['options']}
    out += _added_removed(f'{name} options', _names(a['options']), _names(b['options']))
    out += _stock(name, a['stock_option'], b['stock_option'], values.__getitem__)
    if abs(a['rest'] - b['rest']) > 1e-9:
        out.append(f'Fixed ratio after {name}: {a["rest"]:.3f} → {b["rest"]:.3f}.')
    return out


def tyre_changes(old, new):
    a, b = old.get('tyres', {}), new.get('tyres', {})
    out = [f'No tyre for {SURFACE_NAMES.get(k, k)} any more.' for k in a if k not in b]
    out += [f'New tyre for {SURFACE_NAMES.get(k, k)}.' for k in b if k not in a]
    moved = {}
    for k in a:
        if k in b and abs(a[k]['free_radius'] - b[k]['free_radius']) > 5e-5:
            moved.setdefault((a[k]['free_radius'], b[k]['free_radius']), []).append(k)
    for (x, y), keys in moved.items():
        out.append(f'Tyre radius on {", ".join(SURFACE_NAMES.get(k, k) for k in keys)}: '
                   f'{x:.4f} → {y:.4f} m.')
    return out


def _peak(curve, column):
    row = max(curve, key=lambda r: r[column])
    return row[0], row[column]


def _peak_line(label, unit, old, new):
    (orpm, ov), (nrpm, nv) = old, new
    if round(ov) == round(nv) and orpm == nrpm:
        return []
    if orpm == nrpm:
        return [f'{label}: {ov:.0f} → {nv:.0f} {unit} at {nrpm} rpm.']
    return [f'{label}: {ov:.0f} {unit} at {orpm} rpm → {nv:.0f} {unit} at {nrpm} rpm.']


def engine_changes(old, new):
    a, b = old['engine']['curve'], new['engine']['curve']
    hp = lambda c: [[r, nm, kw * HP_PER_KW] for r, nm, kw in c]       # noqa: E731
    out = _peak_line('Peak power', 'hp', _peak(hp(a), 2), _peak(hp(b), 2))
    out += _peak_line('Peak torque', 'Nm', _peak(a, 1), _peak(b, 1))
    if a[-1][0] != b[-1][0]:
        out.append(f'Torque curve now ends at {b[-1][0]} rpm (was {a[-1][0]}).')
    nm_old = {r: nm for r, nm, _kw in a}
    deltas = [(r, nm - nm_old[r]) for r, nm, _kw in b if r in nm_old and abs(nm - nm_old[r]) >= 0.5]
    if deltas:
        lo, hi = deltas[0][0], deltas[-1][0]
        span = f'{lo} rpm' if lo == hi else f'{lo} to {hi} rpm'
        small, big = min(d for _r, d in deltas), max(d for _r, d in deltas)
        if small > 0:
            out.append(f'Torque higher from {span}, by up to {big:.0f} Nm.')
        elif big < 0:
            out.append(f'Torque lower from {span}, by up to {-small:.0f} Nm.')
        else:
            out.append(f'Torque changed from {span}, from −{-small:.0f} to +{big:.0f} Nm.')
    return out


def other_changes(old, new):
    out = []
    a, b = old['engine'], new['engine']
    if a['redline'] != b['redline']:
        out.append(f'Rev limit: {a["redline"]} → {b["redline"]} rpm.')
    if b.get('redline_source') == 'measured-stale' and a.get('redline_source') != 'measured-stale':
        out.append('The shift-light rev stages changed, so the measured rev limit may be out of '
                   'date.')
    x, y = old.get('steering_lock'), new.get('steering_lock')
    if x is not None and y is not None and x != y:
        out.append(f'Steering lock: {x}° → {y}°.')
    return out


def car_changes(old, new):
    """Short sentences, one per change, from the car's previous document to its new one."""
    out = []
    if old['name'] != new['name']:
        out.append(f'Renamed from {old["name"]}.')
    return (out + gearing_changes(old, new) + final_drive_changes(old, new)
            + tyre_changes(old, new) + engine_changes(old, new) + other_changes(old, new))


def update_changelog(log, old_docs, new_docs, version, date, old_version):
    """The changelog after an export of `version`.

    `old_docs` are the documents on disk before this export, written by `old_version`. A car
    with an entry for `version` already keeps it. Otherwise: a car with no previous document
    gets "Added to the site."; a car whose previous document is from another version gets
    the difference; a car re-exported within the same version gets nothing new. A car not in
    `new_docs` keeps its entries: the log is history, and a car that failed one export and
    comes back must not lose it."""
    out = {slug: list(entries) for slug, entries in log.items()}
    for slug in sorted(new_docs):
        entries = out.get(slug, [])
        if not any(e['version'] == version for e in entries):
            old = old_docs.get(slug)
            if old is None:
                changes = [ADDED]
            elif old_version != version:
                changes = car_changes(old, new_docs[slug])
            else:
                changes = None
            if changes is not None:
                entries.insert(0, {'version': version, 'date': date, 'changes': changes})
        out[slug] = entries
    return dict(sorted(out.items()))


def load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def save(path, log):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
        fh.write('\n')


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
{theme_head}
<title>{name} — changelog — ACR Car Lab</title>
<meta name="description" content="What changed in the {name}'s gearing, engine and tyre data \
from one Assetto Corsa Rally release to the next.">
<link rel="stylesheet" href="{root}app.css">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{root}favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap dt">
  <header>
    <div class="brandrow">
      <a class="brand" href="{root}">ACR <b>Car Lab</b></a>
      <span class="sep" aria-hidden="true">·</span>
      <a class="crumb" href="{root}"><span class="chev" aria-hidden="true">‹</span>All cars</a>
      <span class="sep" aria-hidden="true">·</span>
      <a class="crumb" href="../gears/">Gearing charts</a>
      {theme_button}
    </div>
    <h1>{name} — changelog</h1>
  </header>
<section class="changelog">
<p class="cap">What changed in this car's data from one game release to the next: gearing, \
final drive, tyres, engine curve, steering lock and rev limit.</p>
{entries}
</section>
  <div class="foot">
    <div>
      <h3>Data</h3>
      <p class="limits">{data_line}</p>
    </div>
  </div>
</div>
<script type="module" src="{root}js/drivetrain.js"></script>
</body></html>
"""


def entries_html(entries):
    if not entries:
        return '<p>No changes recorded yet.</p>'
    out = []
    for e in entries:
        body = ('<ul>' + ''.join(f'<li>{html.escape(c)}</li>' for c in e['changes']) + '</ul>'
                if e['changes'] else '<p>No changes.</p>')
        out.append(f'<h2>ACR {html.escape(e["version"])} <span class="when">{e["date"]}</span>'
                   f'</h2>\n{body}')
    return '\n'.join(out)


def render_page(name, entries, data_line, theme_head='', theme_button='', root='../../'):
    return PAGE.format(name=html.escape(name), root=root, theme_head=theme_head,
                       theme_button=theme_button, entries=entries_html(entries),
                       data_line=html.escape(data_line))


def write_page(out, slug, page):
    path = os.path.join(out, slug, CHANGELOG_PAGE_DIR, 'index.html')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    return path
