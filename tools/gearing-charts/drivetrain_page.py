"""The drivetrain page of one car for the ACR Car Lab site: /<slug>/drivetrain/.

Static HTML built from the car's published document (build_car_json), its template, the
measurements in calibration.json and the prose in drivetrain_notes.json. Three parts:

1. the facts, for everyone: layout, the settings that change the gearing, how the final drive
   is worked out, the rev limit, the engine curve, and handling notes where test drives showed some;
2. "How we worked it out": the reasoning and the runs behind the formula, for this car;
3. "Measured in game": the raw measurements, where there are any.

Every number in the prose is computed here from the runs and the data, through placeholders in
drivetrain_notes.json (see `fill`), never typed into the notes.
"""
import html as _html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(HERE, 'drivetrain_notes.json')

from gearing import LOADED_RADIUS_FACTOR, ratio, with_settings  # noqa: E402
import calibration as CAL                                        # noqa: E402

LAYOUTS = {'FWD': 'Front-wheel drive', 'RWD': 'Rear-wheel drive', 'AWD': 'Four-wheel drive'}

REV_LIMIT_SOURCES = {
    'measured': 'measured in game with telemetry',
    'estimated': 'estimated from the game files',
    'measured-stale': 'measured on an earlier game version',
}

SURFACE_NAMES = {'Tarmac_Dry': 'dry tarmac', 'Tarmac_Wet': 'wet tarmac', 'Gravel': 'gravel',
                 'Sweden': 'snow', 'Montecarlo': 'winter tarmac'}

NUMBER_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                'ten']

WORKINGS_EVENT = 'read-drivetrain-workings'


def load_notes(path=NOTES):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def template_facts(text):
    """(layout code, whether setup offers a Gear Set setting) from a car template."""
    m = re.search(r'^drivetrain: "([^"]+)"', text, re.MULTILINE)
    return (m.group(1) if m else None), 'adjustment: "Gear Set"' in text


def esc(s):
    return _html.escape(str(s))


def join_words(items):
    items = list(items)
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def number_word(n):
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


# ---- the facts -----------------------------------------------------------------------------

def formula_note(fd):
    """The same line as the Final drive note on the gears page (js/charts/finalDrive.js
    formulaNote) for the averaged-axle cars; '' for every other car."""
    if not fd or 'settings' not in fd:
        return ''
    f = fd['formula']
    names = {s['key']: s['adjustment'] for s in fd['settings']}

    def product(keys, fixed):
        """A chain's settings by game name, then its fixed ratio where it is not 1; '1' if empty."""
        parts = [names[k] for k in keys] + ([] if abs(fixed - 1) < 1e-9 else [f'{fixed:.3f}'])
        return ' × '.join(parts) or '1'

    pre = product(f['pre'], f['fixed_pre'])
    axles = (f'({product(f["front"], f["fixed_front"])} + '
             f'{product(f["rear"], f["fixed_rear"])}) ÷ 2')
    fixed = (' (the front and rear differentials are fixed)'
             if not f['front'] and not f['rear'] else '')
    return f'Final drive = {"" if pre == "1" else pre + " × "}{axles}{fixed}'


def final_drive_lines(doc):
    """(plain sentence, formula) for how the final drive is worked out."""
    fd = doc['final_drive']
    if fd is None:
        return ('Nothing below the gearbox is adjustable.',
                f'Final drive is fixed at {doc["fixed_final_drive"]:.3f}.')
    if 'settings' in fd:
        if fd['formula'].get('centre_differential') is False:
            # assumed, not measured: the axles cannot be run apart to test it
            return ('The final drive is taken as (front axle ratio + rear axle ratio) ÷ 2.',
                    formula_note(fd))
        return ('The drive splits to the front and rear axles, and the gearbox output turns at '
                '(front axle ratio + rear axle ratio) ÷ 2 times wheel speed.', formula_note(fd))
    rest = '' if abs(fd['rest'] - 1) < 1e-9 else f' × {fd["rest"]:.3f}'
    return ('One ratio sits below the gearbox, and setup offers it.',
            f'Final drive = {fd["adjustment"]}{rest}.')


def runs_of_length(values):
    """[(first index, last index, value)] for runs of equal neighbours."""
    out = []
    for i, v in enumerate(values):
        if out and out[-1][2] == v:
            out[-1] = (out[-1][0], i, v)
        else:
            out.append((i, i, v))
    return out


def gear_sets_text(doc, has_setting):
    counts = [len(s['gears']) for s in doc['gear_sets']]
    n = len(counts)
    if n == 1:
        text = f'1 gear set, {counts[0]}-speed'
    elif len(set(counts)) == 1:
        text = f'{n} gear sets, all {counts[0]}-speed'
    else:
        parts = [(f'set {a + 1}' if a == b else f'sets {a + 1}–{b + 1}') + f' {v}-speed'
                 for a, b, v in runs_of_length(counts)]
        text = f'{n} gear sets: ' + ', '.join(parts)
    return text if has_setting else text + ' (setup has no Gear Set setting)'


def steps_html(steps, stock):
    """A setting's steps: the count and the stock one up front, the full list folded away."""
    names = [s['name'] for s in steps]
    listed = ', '.join(esc(x) for x in names)
    stock_part = f' · stock <span class="mono">{esc(stock)}</span>' if stock else ''
    if len(names) <= 3:
        return f'<span class="mono">{listed}</span>{stock_part}'
    return (f'{len(names)} steps{stock_part}'
            f'<details><summary>All {len(names)} steps</summary>'
            f'<p class="mono steps">{listed}</p></details>')


def gearing_settings(doc, has_gear_set_setting):
    """[(game name or label, html)] for every setting that changes the gearing, in game order."""
    fd = doc['final_drive']
    rows = [('Gear Set' if has_gear_set_setting else 'Gear sets',
             esc(gear_sets_text(doc, has_gear_set_setting)))]
    if fd and fd['primaries']:
        set_primaries = {s['primary']['name'] for s in doc['gear_sets']}
        steps = fd['primaries']
        stock = next((s['name'] for s in steps if s['name'] in set_primaries), None)
        html = steps_html(steps, stock)
        if stock is None:
            html += (' · no stock step: the gear sets store '
                     + ', '.join(f'<span class="mono">{esc(p)}</span>'
                                 for p in sorted(set_primaries)))
        rows.append(('Primary Gear', html))
    if fd is None:
        rows.append(('Final drive', f'fixed at {doc["fixed_final_drive"]:.3f}, no selectable '
                                    'ratio'))
    elif 'settings' in fd:
        for s in fd['settings']:
            rows.append((s['adjustment'], steps_html(s['steps'], s['stock'])))
    else:
        rows.append((fd['adjustment'], steps_html(fd['options'], fd['stock_option'])))
    return rows


def primary_text(doc):
    fd = doc['final_drive']
    if fd and fd['primaries']:
        opens = fd['primaries'][0]['name']
        set_primaries = sorted({s['primary']['name'] for s in doc['gear_sets']})
        if any(p['name'] in set_primaries for p in fd['primaries']):
            return 'The Primary Gear you pick replaces the gear set\'s own primary.'
        return (f'The Primary Gear you pick replaces the gear set\'s own primary '
                f'({join_words(set_primaries)}). The gearing page starts on {opens}.')
    primaries = [s['primary']['name'] for s in doc['gear_sets']]
    if len(set(primaries)) == 1:
        return (f'No Primary Gear setting: each gear set\'s own primary applies '
                f'({primaries[0]} on every set).')
    parts = [(f'set {a + 1}' if a == b else f'sets {a + 1}–{b + 1}') + f' {v}'
             for a, b, v in runs_of_length(primaries)]
    return 'No Primary Gear setting: each gear set\'s own primary applies (' \
           + ', '.join(parts) + ').'


def rev_limit_text(doc, measurement, game_version):
    engine = doc['engine']
    source = REV_LIMIT_SOURCES.get(engine['redline_source'], 'source unknown')
    version = game_version
    if engine['redline_source'] == 'measured-stale' and measurement:
        version = measurement.get('game_version')
    return f'{engine["redline"]} rpm, {source}' + (f' (ACR {version})' if version else '') + '.'


def engine_curve_text(doc):
    owner = doc['engine'].get('curve_from')
    if owner:
        return f'Uses the {owner["name"]} engine curve in the game files.'
    return 'Own curve.'


# ---- the workings: placeholders ------------------------------------------------------------

_PLACEHOLDER = re.compile(r'\{([a-z_]+)(?::([^{}]*))?\}')


def car_runs(cal, slug):
    return [r for r in cal['speed_runs'] if r['car'] == slug]


def set_primary(doc, label):
    return next(s['primary']['value'] for s in doc['gear_sets'] if s['label'] == label)


def run_ratios(doc, run, hypothesis):
    """(primary, below the gearbox) for one stored run under a named explanation.

    A hypothesis is `{}` (the formula the site uses), or any of:
    - `path`: 'average' (default), 'front' or 'rear' — on a run that stores its settings, the
      front or rear axle chain alone instead of their average;
    - `settings`: `{game name: spelling}` put over the run's settings;
    - `primary`: a spelling that replaces the run's, or 'times_set' — the run's primary
      multiplied by the gear set's own.
    """
    if 'settings' in run:
        chain = [ratio(c) for c in with_settings(run['chain'],
                                                 {**run['settings'],
                                                  **hypothesis.get('settings', {})})]
        path = hypothesis.get('path', 'average')
        below = {'average': chain[0] * (chain[1] * chain[3] + chain[2] * chain[4]) / 2,
                 'front': chain[0] * chain[1] * chain[3],
                 'rear': chain[0] * chain[2] * chain[4]}[path]
    else:
        if 'path' in hypothesis or 'settings' in hypothesis:
            raise ValueError('path and settings need a run that stores its settings')
        below = run['rest'] * ratio(run['option'])
    primary = ratio(run['primary'])
    if hypothesis.get('primary') == 'times_set':
        primary *= set_primary(doc, run['gear_set'])
    elif 'primary' in hypothesis:
        primary = ratio(hypothesis['primary'])
    return primary, below


def run_kmh(cal, doc, run, hypothesis, factor):
    primary, below = run_ratios(doc, run, hypothesis)
    rpm = cal['rev_limiters'][run['car']]['rpm']
    return [CAL.predicted_kmh(rpm, ratio(g), primary, below, run['free_radius'], factor)
            for g in run['gears'][:len(run['kmh'])]]


class Context:
    """Everything a placeholder can read for one car."""

    def __init__(self, doc, cal, notes, factor=LOADED_RADIUS_FACTOR):
        self.doc, self.cal, self.notes, self.factor = doc, cal, notes, factor
        self.slug = doc['slug']
        self.runs = car_runs(cal, self.slug)
        entry = notes['cars'][self.slug]
        self.hypotheses = {'formula': {}, **entry.get('hypotheses', {})}

    def run(self, n):
        i = int(n)
        if not 1 <= i <= len(self.runs):
            raise ValueError(f'run {n}: {self.slug} has {len(self.runs)} runs')
        return self.runs[i - 1]

    def hyp(self, name):
        if name not in self.hypotheses:
            raise ValueError(f'unknown hypothesis {name!r} for {self.slug}')
        return self.hypotheses[name]

    def gear(self, run, g):
        g = int(g)
        if not 1 <= g <= len(run['kmh']):
            raise ValueError(f'gear {g}: the run measured {len(run["kmh"])} gears')
        return g

    def value(self, name, arg):
        a = arg.split(':') if arg else []
        doc, cal = self.doc, self.cal
        if name == 'factor':
            return f'{self.factor:.4f}'
        if name == 'fit_runs':
            return str(len(cal['speed_runs']))
        if name in ('fit_cars', 'fit_car_count'):
            cars = list(dict.fromkeys(r['car'] for r in cal['speed_runs']))
            if name == 'fit_car_count':
                return number_word(len(cars))
            return join_words(self.notes['cars'][c]['short'] for c in cars)
        if name == 'rev_limit':
            return str(doc['engine']['redline'])
        if name == 'adjustment':
            return doc['final_drive']['adjustment']
        if name == 'fixed':
            return f'{doc["fixed_final_drive"]:.3f}'
        if name in ('fixed_front', 'fixed_rear'):
            return f'{doc["final_drive"]["formula"][name]:.3f}'
        if name == 'fixed_apart':
            f = doc['final_drive']['formula']
            return f'{abs(f["fixed_front"] / f["fixed_rear"] - 1) * 100:.1f}'
        if name == 'ratio':
            return f'{ratio(a[0]):.3f}'
        if name == 'measured':
            run = self.run(a[0])
            return str(run['kmh'][self.gear(run, a[1]) - 1])
        if name == 'kmh':
            run = self.run(a[1])
            g = self.gear(run, a[2])
            return str(round(run_kmh(cal, doc, run, self.hyp(a[0]), self.factor)[g - 1]))
        if name == 'apart':
            run = self.run(a[2])
            p1, b1 = run_ratios(doc, run, self.hyp(a[0]))
            p2, b2 = run_ratios(doc, run, self.hyp(a[1]))
            return str(round(abs(p1 * b1 / (p2 * b2) - 1) * 100))
        if name == 'off':
            run = self.run(a[1])
            pred = run_kmh(cal, doc, run, self.hyp(a[0]), self.factor)
            errs = [(p - m) / m * 100 for g, (m, p) in enumerate(zip(run['kmh'], pred), start=1)
                    if CAL.fitted(run, g)]
            return str(round(abs(sum(errs) / len(errs))))
        if name == 'speedratio':
            r1, r2 = self.run(a[0]), self.run(a[1])
            both = [g for g in range(1, min(len(r1['kmh']), len(r2['kmh'])) + 1)
                    if CAL.fitted(r1, g) and CAL.fitted(r2, g)]
            return f'{sum(r1["kmh"][g - 1] / r2["kmh"][g - 1] for g in both) / len(both):.2f}'
        raise ValueError(f'unknown placeholder {name!r}')


def fill(text, ctx):
    """Every `{name}` or `{name:args}` in `text` replaced by its computed value. An unknown
    placeholder, or one whose arguments do not resolve, raises ValueError."""
    out = _PLACEHOLDER.sub(lambda m: ctx.value(m.group(1), m.group(2)), text)
    if '{' in out or '}' in out:
        raise ValueError(f'unresolved placeholder in {out!r}')
    return out


def workings_paragraphs(doc, cal, notes, factor=LOADED_RADIUS_FACTOR):
    """The filled paragraphs of "How we worked it out" for one car: the common intro, the
    rev-limit line for its source, then the car's own, where `@name` pulls in a shared one."""
    ctx = Context(doc, cal, notes, factor)
    common = notes['common']
    source = doc['engine']['redline_source']
    items = list(common['intro']) + [common['rev_limit'][source]]
    for item in notes['cars'][doc['slug']]['workings']:
        items.append(common[item[1:]] if item.startswith('@') else item)
    return [fill(p, ctx) for p in items]


# ---- measured ------------------------------------------------------------------------------

def run_settings(doc, run):
    """[(game name, spelling)] a run was driven on, in the car's setup order."""
    fd = doc['final_drive']
    if 'settings' in run:
        order = ['Primary Gear'] + [s['adjustment'] for s in (fd.get('settings') or [])]
        known = [(n, run['settings'][n]) for n in order if n in run['settings']]
        rest = [(n, v) for n, v in run['settings'].items() if n not in order]
        return known + rest
    out = []
    if fd['primaries']:
        out.append(('Primary Gear', run['primary']))
    out.append((fd['adjustment'], run['option']))
    return out


def measured_html(doc, cal):
    """The "Measured in game" section, or '' when nothing was measured on this car."""
    slug = doc['slug']
    limiter = cal['rev_limiters'].get(slug)
    measured_limit = limiter if doc['engine']['redline_source'] != 'estimated' else None
    runs = car_runs(cal, slug)
    if not measured_limit and not runs:
        return ''
    readings = ([] if not measured_limit else ['rev limit from telemetry']) + (
        ['top speed per gear from the in-game speedometer at the rev limiter'] if runs else [])
    parts = ['<section class="measured" id="measured">', '<h2>Measured in game</h2>',
             f'<p class="cap">Raw in-game readings: {", ".join(readings)}.</p>']
    if measured_limit:
        bits = [f'{measured_limit["rpm"]} rpm', 'SimHub telemetry']
        if measured_limit.get('game_version'):
            bits.append(f'ACR {measured_limit["game_version"]}')
        if measured_limit.get('measured'):
            bits.append(measured_limit['measured'])
        parts.append('<dl class="facts"><dt>Rev limit</dt><dd>' + esc(' · '.join(bits))
                     + '</dd></dl>')
    for run in runs:
        head = [run['gear_set'], SURFACE_NAMES.get(run['surface'], run['surface'])]
        if run.get('measured'):
            head.append(run['measured'])
        settings = ' · '.join(f'{esc(n)} <span class="mono">{esc(v)}</span>'
                              for n, v in run_settings(doc, run))
        excluded = set(run.get('exclude_gears', ()))
        cells = ''.join(f'<th scope="col">{g}</th>' for g in range(1, len(run['kmh']) + 1))
        speeds = ''.join(f'<td>{kmh}{"*" if g in excluded else ""}</td>'
                         for g, kmh in enumerate(run['kmh'], start=1))
        parts.append('<div class="run">'
                     f'<h3>{esc(" · ".join(head))}</h3>'
                     f'<p class="runset">{settings}</p>'
                     '<div class="tablewrap"><table class="speeds">'
                     f'<tr><th scope="row">Gear</th>{cells}</tr>'
                     f'<tr><th scope="row">km/h</th>{speeds}</tr>'
                     '</table></div>'
                     + ('<p class="cap runnote">* did not reach the rev limiter.</p>'
                        if excluded else '')
                     + '</div>')
    parts.append('</section>')
    return '\n'.join(parts)


# ---- the page ------------------------------------------------------------------------------

def data_line(game_version, generated):
    """The footer's data line, worded as js/footer.js dataLine."""
    return (f'Read from the ACR {game_version + " " if game_version else ""}game files.'
            + (f' Generated {generated}.' if generated else ''))


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{theme_head}
<title>{name} — drivetrain — ACR Car Lab</title>
<meta name="description" content="How the {name} turns engine revs into road speed in \
Assetto Corsa Rally: layout, gearing settings, final drive formula and measurements.">
<link rel="stylesheet" href="{root}app.css">
<script data-goatcounter="https://acr-car-lab.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<div class="wrap dt">
  <header>
    <div class="brandrow">
      <span class="brand">ACR <b>Car Lab</b></span>
      <a class="crumb" href="../gears/">Gearing charts</a>
      <a class="crumb" href="{root}">All cars →</a>
      {theme_button}
    </div>
    <h1>{name} — drivetrain</h1>
  </header>
{facts}
{workings}
{measured}
  <div class="foot">
    <div>
      <h3>Data</h3>
      <p class="limits">{data_line}</p>
    </div>
    <p class="promo">{promo}</p>
  </div>
</div>
<script type="module" src="{root}js/drivetrain.js"></script>
</body></html>
"""

PROMO = ('Want a setup, not just the numbers? <a href="https://github.com/fredmayor88/'
         'acr-setup-engineer" data-track="click-setup-engineer">ACR Setup Engineer</a> — a free '
         'Claude skill that tunes a car to how you drive and saves it to your Notion. · '
         '<a href="https://github.com/fredmayor88/acr-car-lab/issues" '
         'data-track="click-issues">Issues and feedback</a>')


def facts_html(doc, template_text, cal, notes, game_version):
    layout, has_gear_set = template_facts(template_text)
    sentence, formula = final_drive_lines(doc)
    settings = ''.join(f'<li><span class="setname">{esc(name)}</span> {html}</li>'
                       for name, html in gearing_settings(doc, has_gear_set))
    rows = [
        ('Layout', esc(LAYOUTS.get(layout, layout or 'unknown'))),
        ('Gearing settings', f'<ul class="settings">{settings}</ul>'),
        ('Final drive', f'{esc(sentence)}<br><span class="formula">{esc(formula)}</span>'),
        ('Primary gear', esc(primary_text(doc))),
        ('Rev limit', esc(rev_limit_text(doc, cal['rev_limiters'].get(doc['slug']),
                                         game_version))),
        ('Engine curve', esc(engine_curve_text(doc))),
    ]
    handling = notes['cars'][doc['slug']].get('handling')
    if handling:
        rows.append(('Handling', f'<span class="handling">{esc(handling)}</span>'))
    body = ''.join(f'<dt>{t}</dt><dd>{d}</dd>' for t, d in rows)
    return f'<section class="top" id="facts">\n<dl class="facts">{body}</dl>\n</section>'


def workings_html(doc, cal, notes):
    paras = workings_paragraphs(doc, cal, notes)
    first, rest = paras[0], paras[1:]
    return ('<section class="workings" id="workings">\n'
            '<div class="workhead" data-event="' + WORKINGS_EVENT + '">'
            '<h2>How we worked it out</h2>'
            '<p class="cap">The reasoning and the in-game runs behind the numbers above.</p>'
            f'<p>{esc(first)}</p></div>\n'
            + '\n'.join(f'<p>{esc(p)}</p>' for p in rest)
            + '\n</section>')


def render_drivetrain_page(doc, template_text, cal, notes, game_version=None, generated=None,
                           theme_head='', theme_button='', root='../../'):
    """The whole page for one car."""
    return PAGE.format(
        name=esc(doc['name']), root=root, theme_head=theme_head, theme_button=theme_button,
        facts=facts_html(doc, template_text, cal, notes, game_version),
        workings=workings_html(doc, cal, notes),
        measured=measured_html(doc, cal),
        data_line=esc(data_line(game_version, generated)),
        promo=PROMO)
