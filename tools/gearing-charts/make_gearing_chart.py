#!/usr/bin/env python3
"""Render a car's gearing charts from the ACR game files.

Two charts per car, for embedding next to the power/torque chart:

  <car>-gearing.png      speed against revs, every gear of every gear set
  <car>-final-drive.png  what each primary x differential combination does to all of it

Ratios are exact - they come from the game's own gear-set assets. Absolute km/h needs
a rolling circumference, which is calibrated per car against in-game measurements (see
CALIBRATION) rather than guessed; the tyre assets hold a radius but it sits behind
another layer of unversioned physics data.

    python make_gearing_chart.py --car lancia-stratos
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
TORQUE = os.path.join(REPO, 'tools', 'torque-curves')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))
sys.path.insert(0, TORQUE)

from iostore import Toc                     # noqa: E402
from acrpkg import Package                  # noqa: E402
from datatable import tagged_rows           # noqa: E402
from gearing import (gear_set, ratio, tyre_geometry,   # noqa: E402
                     rolling_circumference, drivetrain_chain, axle_final_drive)

DEFAULT_PAKS = ('C:/Program Files (x86)/Steam/steamapps/common/'
                'Assetto Corsa Rally/acr/Content/Paks')
TEMPLATES = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer', 'car-templates')

# Brand palette (yt-writing/brand-palette.md)
WARM_WHITE, GRAPHITE, DARK_GRAPHITE = '#F5F2EB', '#30353A', '#212529'
STEEL, WALNUT, DEEP_CYAN = '#7B858E', '#7A583B', '#148FAC'
# enough distinct colours for the Impreza's seven gear sets
SET_COLOURS = [WALNUT, DEEP_CYAN, GRAPHITE, '#B07A4E', '#0E6E85',
               '#8D949B', '#4FB3C9', '#5A3F29']

# template slug -> (gear-set asset name, DT_Wheels row prefix, car data asset)
CARS = {
    'alfa-romeo-gta-1300-junior-1972':        ('AlfaRomeoGiuliaGTAJunior1300',
                                               'AlfaRomeoGiuliaGTA1300Junior',
                                               'AlfaRomeoGiuliaGTAJunior1300'),
    'alpine-a110-1-8-1973':                   ('AlpineA110', 'AlpineA1101800', 'AlpineA110'),
    'citroen-xsara-wrc-2003':                 ('CitroenXsaraWRC', 'CitroenXsaraWRC',
                                               'CitroenXsaraWRC'),
    'fiat-124-abarth-rally-16v-1974':         ('Fiat124Abarth', 'FIATAbarth124Rally16V',
                                               'Fiat124Abarth'),
    'fiat-131-abarth-1976':                   ('Fiat131Abarth', 'FIATAbarth131Rally',
                                               'Fiat131Abarth'),
    'hyundai-i20-rally2-2021':                ('Hyundaii20NRally2', 'Hyundaii20NRally2',
                                               'Hyundaii20NRally2'),
    'lancia-037-evoluzione-2-1984':           ('LanciaRally037Evo2', 'LanciaRally037Evoluzione2',
                                               'LanciaRally037Evo2'),
    'lancia-delta-integrale-evoluzione-1992': ('LanciaDeltaHFIntegraleEvo',
                                               'LanciaDeltaHFIntegraleEvoluzione',
                                               'LanciaDeltaHFIntegraleEvo'),
    'lancia-fulvia-coupe-hf-1970':            ('LanciaFulviaCoupeHF',
                                               'LanciaFulviaCoupeRallye1.6HF',
                                               'LanciaFulviaCoupeHF'),
    'lancia-stratos':                         ('LanciaStratosHF', 'LanciaStratosHF',
                                               'LanciaStratosHF'),
    'mini-cooper-s-1964':                     ('MiniCooperS1275', 'MiniCooperS1275',
                                               'MiniCooperS1275'),
    'peugeot-306-ii-maxi-1997':               ('Peugeot306IIMaxi', 'Peugeot306IIMaxiKitCar',
                                               'Peugeot306IIMaxi'),
    'skoda-fabia-rs-rally2-2022':             ('SkodaFabiaRSRally2', 'SkodaFabiaRSRally2',
                                               'SkodaFabiaRSRally2'),
    'subaru-impreza-555-s3-1993':             ('SubaruImprezaS3', 'SubaruImprezaS3555',
                                               'SubaruImprezaS3'),
}

SURFACE_LABEL = {'Tarmac_Dry': 'dry tarmac', 'Tarmac_Wet': 'wet tarmac',
                 'Gravel': 'gravel', 'Sweden': 'snow', 'Montecarlo': 'winter'}


def extract(paks, prefix, out_dir):
    """Every DA_<car>_GearSet_N asset, unpacked to out_dir."""
    jobs, found = [], []
    for entry in sorted(os.listdir(paks)):
        if not entry.endswith('.utoc'):
            continue
        try:
            toc = Toc(os.path.join(paks, entry))
            listing = toc.files()
        except Exception:
            continue
        cas = os.path.join(paks, entry[:-5] + '.ucas')
        for path, idx in listing.items():
            base = os.path.basename(path)
            # case-insensitive: the Mini spells its assets DA_..._Gearset_N
            if base.lower().startswith(prefix.lower()) and base.endswith('.uasset'):
                plan = toc.plan(idx, cas)
                plan['out'] = os.path.join(out_dir, base)
                jobs.append(plan)
                found.append(plan['out'])
    if not jobs:
        return []
    unpack(jobs)
    return sorted(found)


def unpack(jobs):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
        json.dump(jobs, fh)
        job_path = fh.name
    try:
        subprocess.run(['node', os.path.join(TORQUE, 'ooz_unpack.mjs'), job_path],
                       check=True, cwd=TORQUE, stdout=subprocess.DEVNULL)
    finally:
        os.unlink(job_path)


def tyre(paks, wheel_key, surface, axle, tmp):
    """(tyre name, rolling circumference) for a car on one surface.

    Only the driven axle matters for road speed, and several cars fit a different
    tyre front and rear, so the axle is not optional.
    """
    wheels = None
    for entry in sorted(os.listdir(paks)):
        if not entry.endswith('.utoc'):
            continue
        try:
            toc = Toc(os.path.join(paks, entry)); listing = toc.files()
        except Exception:
            continue
        for path, idx in listing.items():
            if os.path.basename(path) == 'DT_Wheels.uasset':
                wheels = (toc, idx, os.path.join(paks, entry[:-5] + '.ucas'))
                break
        if wheels:
            break
    if not wheels:
        raise SystemExit('DT_Wheels not found')
    toc, idx, cas = wheels
    unpack([dict(toc.plan(idx, cas), out=os.path.join(tmp, 'DT_Wheels.uasset'))])
    rows = tagged_rows(Package(open(os.path.join(tmp, 'DT_Wheels.uasset'), 'rb').read()),
                       'Tires')
    name = rows.get(f'{wheel_key}_{surface}_{axle}')
    if not name:
        raise SystemExit(f'no tyre for {wheel_key}_{surface}_{axle}')
    hits = extract(paks, f'DA_{name}', tmp)
    if not hits:
        raise SystemExit(f'tyre asset DA_{name} not found')
    # compounds share a carcass, so the radius is the same for S/M/H - but say which
    # one is quoted, because the chart is read as a statement about a real setup
    soft = [h for h in hits if os.path.basename(h) == f'DA_{name}_S.uasset']
    exact = [h for h in hits if os.path.basename(h) == f'DA_{name}.uasset']
    compound = 'soft' if soft else None
    pkg = Package(open((soft or exact or hits)[0], 'rb').read())
    geo = tyre_geometry(pkg.export_bytes(0)[1])
    if not geo:
        raise SystemExit(f'could not read geometry from DA_{name}')
    return name, rolling_circumference(geo[1]), compound


def pick_ratio(candidates, chain, axle):
    """(adjustment name, options, the option the car ships with).

    A candidate list only describes this car's overall gearing if it contains the
    ratio the driven path actually uses; anything else scales a branch the wheels
    never see. Where several qualify, the largest reduction is the real final drive.
    """
    r = [ratio(c) for c in chain]
    path = [r[0], r[1], r[3]] if axle == 'Front' else [r[0], r[2], r[4]]
    best = None
    for name, opts in candidates.items():
        for opt in opts:
            for v in path:
                if abs(ratio(opt) - v) < 1e-4 and (best is None or v > best[3]):
                    best = (name, opts, opt, v)
    return best[:3] if best else (None, [], None)


def stock_final_drive(paks, car_asset, axle, tmp):
    """(engine-to-wheel ratio below the gearbox, its spelling) as the car ships.

    Read from the car's own data asset rather than guessed from the legal list, which
    is often ordered shortest-first and would silently pick the wrong one.
    """
    hits = [h for h in extract(paks, f'DA_{car_asset}.uasset', tmp)
            if os.path.basename(h) == f'DA_{car_asset}.uasset']
    if not hits:
        raise SystemExit(f'car asset DA_{car_asset} not found')
    chain = drivetrain_chain(Package(open(hits[0], 'rb').read()))
    value = axle_final_drive(chain, axle)
    spelled = [c for c in chain if abs(ratio(c) - 1) > 1e-6]
    return value, ' · '.join(spelled) if spelled else '1//1', chain


def template_facts(slug, axle):
    """Primary-gear and differential options plus the engine's rpm landmarks."""
    import re
    txt = open(os.path.join(TEMPLATES, slug + '.yaml'), encoding='utf-8').read()

    def steps(name):
        m = re.search(r'adjustment: "%s"\n(?:.*\n)*?\s*discrete_steps: "(.*)"' % name, txt)
        return [s.strip() for s in m.group(1).split(',')] if m and m.group(1) else []

    def rpm(field):
        m = re.search(r'%s: "[\d.]+ \w+ at (\d+) rpm"' % field, txt)
        return int(m.group(1)) if m else None

    # torque may be fractional, so the value side has to allow a decimal point -
    # matching only integers silently truncates the curve and understates the redline
    rpms = [int(v) for v in re.findall(r'\[(\d+), [\d.]+\]', txt)]
    if not rpms:
        raise SystemExit(f'no engine curve in {slug}.yaml')
    max_rpm = max(rpms)
    # Which ratio is adjustable depends on the drivetrain, not on the axle alone:
    # the Xsara adjusts its centre diff, the Impreza its front, most cars the one
    # on the driven axle. Collect the candidates and let the caller pick the one
    # that actually sits in this car's driven path.
    candidates = {}
    for name in ('Center Differential Ratio', f'Differential Ratio {axle}',
                 'Differential Ratio', 'Center Ratio to Rear'):
        opts = steps(name)
        if opts:
            candidates[name] = opts
    return (steps('Primary Gear'), candidates,
            rpm('peak_torque'), rpm('peak_power'), max_rpm)


def final_of(cal):
    """Everything between the gearbox output and the wheel."""
    below = cal.get('final_drive')
    if below is None:
        below = ratio(cal['diff'])
    return ratio(cal['primary']) * below


def kmh(rpm, total, circumference):
    """Road speed for an engine speed and an overall ratio."""
    return rpm * circumference * 0.06 / total


def _frame(ax):
    ax.set_facecolor(WARM_WHITE)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(STEEL)
    ax.spines['bottom'].set_alpha(0.45)
    ax.tick_params(colors=GRAPHITE, labelsize=9.5, length=0)


def chart_speed_vs_revs(sets, cal, t_rpm, p_rpm, redline, title, out_path):
    """Every gear of every gear set as a speed/revs line."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    C = cal['circumference']
    final = final_of(cal)
    tops = [[kmh(redline, ratio(g) * final, C) for g in gears] for gears, _, _ in sets]
    base = min(min(t) for t in tops)                  # slowest gear = 100%

    fig, ax = plt.subplots(figsize=(11.5, 7.4), dpi=160)
    fig.patch.set_facecolor(WARM_WHITE)
    _frame(ax)

    if t_rpm and p_rpm:
        ax.axvspan(t_rpm, p_rpm, color=DEEP_CYAN, alpha=0.10, zorder=0)
        ax.annotate(f'peak torque {t_rpm:,} → peak power {p_rpm:,}',
                    ((t_rpm + p_rpm) / 2, 1.004), xycoords=('data', 'axes fraction'),
                    color=DEEP_CYAN, fontsize=9, ha='center', va='bottom')

    # labelling every gear is unreadable once a car has more than a few sets -
    # past that only the top gear of each set is called out, and the km/h axis
    # carries the rest
    total_lines = sum(len(g) for g, _, _ in sets)
    label_all = total_lines <= 18

    labels = []
    for si, (gears, _, _) in enumerate(sets):
        colour = SET_COLOURS[si % len(SET_COLOURS)]
        for gi, g in enumerate(gears):
            top = kmh(redline, ratio(g) * final, C)
            ax.plot([0, redline], [0, top / base * 100], color=colour, lw=1.9,
                    alpha=0.9, zorder=3,
                    label=f'Gear set {si + 1}' if gi == 0 else None)
            if label_all:
                labels.append((top / base * 100, colour, f'{gi + 1}', top))
        if not label_all:
            top = kmh(redline, ratio(gears[-1]) * final, C)
            labels.append((top / base * 100, colour, f'set {si + 1} top', top))

    # a gutter past the rev limit so the labels never fight the km/h axis
    gutter = redline * (1.245 if label_all else 1.40)
    label_x = redline * 1.045

    labels.sort()
    placed = []
    for y, colour, text, top in labels:
        shown = y
        while any(abs(shown - q) < 8.5 for q in placed):
            shown += 8.5
        placed.append(shown)
        if abs(shown - y) > 0.5:      # leader line, so a nudged label stays attached
            ax.plot([redline, label_x], [y, shown], color=colour, lw=0.8,
                    alpha=0.45, zorder=2, clip_on=False)
        ax.annotate(f'{text}   {top:.0f} km/h', (label_x, shown), xytext=(4, 0),
                    textcoords='offset points', color=colour, fontsize=9,
                    va='center', fontweight='bold')

    ax.axvline(redline, color=STEEL, lw=1.1, ls=(0, (4, 4)), alpha=0.8, zorder=2)
    ax.annotate(f'rev limit {redline:,}', (redline, 0), xytext=(-7, 7),
                textcoords='offset points', color=STEEL, fontsize=9,
                ha='right', va='bottom')
    ax.set_xlim(0, gutter)
    ax.set_ylim(0, max(placed) * 1.05)
    ax.set_xticks(list(range(0, redline + 1, 1000)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v):,}'))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}%'))
    ax.set_xlabel('Engine speed  (rpm)', color=GRAPHITE, fontsize=10.5, labelpad=8)
    ax.set_ylabel('Speed, relative to the slowest gear', color=GRAPHITE,
                  fontsize=10.5, labelpad=9)
    ax.grid(color=STEEL, alpha=0.2, lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=10, loc='upper left')

    # the same axis, read in km/h
    ax2 = ax.twinx()
    ax2.set_ylim(0, ax.get_ylim()[1] * base / 100)
    ax2.set_ylabel('Speed  (km/h)', color=GRAPHITE, fontsize=10.5, labelpad=9)
    ax2.tick_params(colors=GRAPHITE, labelsize=9.5, length=0)
    for side in ('top', 'left', 'right'):
        ax2.spines[side].set_visible(False)

    ax.set_title(f'{title} — speed in every gear',
                 color=DARK_GRAPHITE, fontsize=14, fontweight='bold', loc='left', pad=26)
    fig.text(0.008, 0.012,
             f'Primary {cal["primary"]} · differential {cal["diff"]}'
             + (f' · {cal["tyre"]}' if cal.get('tyre') else ''),
             color=STEEL, fontsize=8.5)
    fig.subplots_adjust(left=0.075, right=0.905, top=0.87, bottom=0.105)
    fig.savefig(out_path, facecolor=WARM_WHITE)
    plt.close(fig)


def chart_gear_ladder(sets, cal, redline, title, out_path):
    """Where every gear tops out, one row per gear set.

    The line-per-gear chart stops being readable past three or four gear sets; a car
    like the 306 Maxi has ten, with a different number of gears in each. A ladder
    keeps the thing you actually compare - the spacing and the spread - legible.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    C = cal['circumference']
    final = final_of(cal)
    tops = [[kmh(redline, ratio(g) * final, C) for g in gears] for gears, _, _ in sets]
    base = min(min(t) for t in tops)

    height = 0.62 * len(sets) + 3.2
    fig, ax = plt.subplots(figsize=(11.5, height), dpi=160)
    fig.patch.set_facecolor(WARM_WHITE)
    _frame(ax)

    ys = list(range(len(sets)))[::-1]
    for y, row in zip(ys, tops):
        # the line runs from a standing start, so first gear reads as a span like
        # every other gear rather than as a bare dot floating in space
        ax.plot([0] + row, [y] * (len(row) + 1), color=STEEL, lw=1.3, alpha=0.5,
                zorder=1)
        ax.scatter(row, [y] * len(row), s=205, color=WALNUT, zorder=3,
                   edgecolor=WARM_WHITE, linewidth=1.6)
        for i, x in enumerate(row):
            ax.annotate(str(i + 1), (x, y), color=WARM_WHITE, fontsize=8.5, ha='center',
                        va='center', zorder=4, fontweight='bold')
            ax.annotate(f'{x:.0f}', (x, y + 0.27), color=GRAPHITE, fontsize=8.5,
                        ha='center', va='bottom')

    ax.set_yticks(ys)
    ax.set_yticklabels([f'Gear set {i + 1}   ({len(s[0])}-speed)'
                        for i, s in enumerate(sets)], fontsize=10)
    ax.set_ylim(-0.7, len(sets) - 0.15)
    top_speed = max(max(t) for t in tops)
    ax.set_xlim(0, top_speed * 1.04)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}'))
    ax.set_xlabel(f'Speed at the {redline:,} rpm rev limit  (km/h)',
                  color=GRAPHITE, fontsize=10.5, labelpad=8)
    ax.grid(axis='x', color=STEEL, alpha=0.2, lw=0.7)
    ax.set_axisbelow(True)

    top = ax.secondary_xaxis('top', functions=(lambda v: v / base * 100,
                                               lambda v: v * base / 100))
    top.set_xlabel('Relative to the slowest gear', color=GRAPHITE, fontsize=10, labelpad=8)
    top.tick_params(colors=GRAPHITE, labelsize=9, length=0)
    top.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}%'))
    top.spines['top'].set_visible(False)

    # in figure coordinates, so the header keeps the same inch height whatever the
    # gear-set count does to the figure
    fig.text(0.037, 1 - 0.34 / height, f'{title} — where each gear tops out',
             color=DARK_GRAPHITE, fontsize=14, fontweight='bold', va='top')
    fig.text(0.008, 0.014,
             f'Shortest final drive — primary {cal["primary"]} · differential '
             f'{cal["diff"]}' + (f' · {cal["tyre"]}' if cal.get('tyre') else ''),
             color=STEEL, fontsize=8.5)
    fig.subplots_adjust(left=0.185, right=0.975, top=1 - 1.05 / height,
                        bottom=0.72 / height)
    fig.savefig(out_path, facecolor=WARM_WHITE)
    plt.close(fig)


def chart_final_drive(sets, cal, primaries, options, stock_option, ratio_name,
                      redline, title, out_path):
    """Every selectable final-drive combination, against the shortest one.

    Only one ratio in the chain is adjustable, so each option is applied by scaling
    the car's real final drive - which keeps the km/h correct however the rest of
    the drivetrain is arranged.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    C = cal['circumference']
    rest = final_of(cal) / (ratio(cal['primary']) * ratio(stock_option))
    combos = sorted(((ratio(p) * rest * ratio(d), p, d)
                     for p in primaries for d in options), key=lambda c: -c[0])
    slowest = combos[0][0]                             # biggest ratio = shortest gearing
    # quote km/h against one stated gear set, or the number is a mix-and-match that
    # no actual configuration produces
    top_gear = min(ratio(g) for g in sets[0][0])

    fig, ax = plt.subplots(figsize=(11.5, 7.0), dpi=160)
    fig.patch.set_facecolor(WARM_WHITE)
    _frame(ax)

    for y, (total, p, d) in enumerate(combos):
        pct = slowest / total * 100
        ax.plot([100, pct], [y, y], color=STEEL, alpha=0.4, lw=1.3, zorder=1)
        ax.scatter([pct], [y], s=115, zorder=3, edgecolor=WARM_WHITE, linewidth=1.4,
                   color=WALNUT)
        v = kmh(redline, top_gear * total, C)
        ax.annotate(f'{pct:.0f}%    {v:.0f} km/h', (pct, y), xytext=(10, 0),
                    textcoords='offset points', color=GRAPHITE, fontsize=8.8, va='center')

    ax.axvline(100, color=STEEL, lw=1.2, alpha=0.7, zorder=2)
    ax.set_yticks(range(len(combos)))
    single = len(primaries) == 1
    ax.set_yticklabels([d if single else f'{p}   ·   {d}' for _, p, d in combos],
                       fontsize=8.8, fontfamily='monospace')
    ax.set_ylim(-0.8, len(combos) - 0.2)
    ax.set_xlim(97, max(slowest / c[0] * 100 for c in combos) * 1.075)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}%'))
    ax.set_xlabel('Overall gearing — every gear scales by this. km/h is top gear of '
                  'gear set 1 at the rev limit, on gearing alone.',
                  color=GRAPHITE, fontsize=10.5, labelpad=8)
    ax.grid(axis='x', color=STEEL, alpha=0.2, lw=0.7)
    ax.set_axisbelow(True)
    heading = (ratio_name if single else f'primary gear × {ratio_name.lower()}')
    ax.set_title(f'{title} — {heading}',
                 color=DARK_GRAPHITE, fontsize=14, fontweight='bold', loc='left', pad=14)
    fig.text(0.008, 0.012, '100% is the shortest combination available.',
             color=STEEL, fontsize=8.5)
    fig.subplots_adjust(left=0.205, right=0.965, top=0.9, bottom=0.115)
    fig.savefig(out_path, facecolor=WARM_WHITE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=DEFAULT_PAKS)
    ap.add_argument('--car', default='lancia-stratos')
    ap.add_argument('--all', action='store_true', help='every car in CARS')
    ap.add_argument('--charts', default='both',
                    choices=('both', 'gearing', 'final-drive'))
    ap.add_argument('--out', default=os.path.join(REPO, 'car-charts'))
    ap.add_argument('--style', default='ladder', choices=('auto', 'lines', 'ladder'),
                    help='ladder is the default; lines is only readable for a few sets')
    ap.add_argument('--surface', default='Tarmac_Dry',
                    help='Tarmac_Dry, Tarmac_Wet, Gravel, Sweden, Montecarlo')
    args = ap.parse_args()

    if args.all:
        failed = []
        for slug in sorted(CARS):
            args.car = slug
            try:
                render_car(args)
            except SystemExit as e:          # one unreadable car must not stop the batch
                failed.append(f'{slug}: {e}')
        for f in failed:
            print(f'  !! {f}')
        print(f'{len(CARS) - len(failed)}/{len(CARS)} cars rendered')
        return
    render_car(args)


def render_car(args):
    asset, wheel_key, car_asset = CARS[args.car]
    import re as _re
    txt = open(os.path.join(TEMPLATES, args.car + '.yaml'), encoding='utf-8').read()
    display = _re.search(r'car: "([^"]+)"', txt).group(1)
    drivetrain = _re.search(r'drivetrain: "([^"]+)"', txt).group(1)
    axle = 'Front' if drivetrain == 'FWD' else 'Rear'
    primaries, candidates, t_rpm, p_rpm, redline = template_facts(args.car, axle)

    with tempfile.TemporaryDirectory() as tmp:
        sets = [gear_set(f) for f in extract(args.paks, f'DA_{asset}_GearSet_', tmp)]
        if not sets:
            raise SystemExit(f'no gear sets for {args.car}')
        # a car with no adjustable primary still has one built into the gear set
        stock_primary = sets[0][1]
        if not primaries:
            primaries = [stock_primary]
        fd, spelled, chain = stock_final_drive(args.paks, car_asset, axle, tmp)
        ratio_name, options, stock_option = pick_ratio(candidates, chain, axle)

        # Draw at the shortest final drive the car can be given, which is what the
        # final-drive chart calls 100%. The two charts then compose: read a speed off
        # the ladder, scale it by the percentage. Drawing at stock instead would put
        # the ladder somewhere in the middle of the other chart with nothing saying so.
        if options:
            rest = fd / ratio(stock_option)     # the part of the chain that never moves
            below, option = max(((rest * ratio(o), o) for o in options))
            primary = max(primaries, key=ratio)
            cal = {'primary': primary, 'final_drive': below, 'diff': option}
        else:
            cal = {'primary': stock_primary, 'final_drive': fd, 'diff': spelled}
        name, circumference, compound = tyre(args.paks, wheel_key, args.surface,
                                             axle, tmp)
    cal['circumference'] = circumference
    surface_label = SURFACE_LABEL.get(args.surface, args.surface)
    cal['tyre'] = (f'{surface_label} {compound} tyres ({name})' if compound
                   else f'{surface_label} tyres ({name})')
    os.makedirs(args.out, exist_ok=True)

    a = os.path.join(args.out, f'{args.car}-gearing.png')
    b = os.path.join(args.out, f'{args.car}-final-drive.png')
    if args.charts in ('both', 'gearing'):
        if args.style == 'ladder' or (args.style == 'auto'
                                      and sum(len(g) for g, _, _ in sets) > 18):
            chart_gear_ladder(sets, cal, redline, display, a)
        else:
            chart_speed_vs_revs(sets, cal, t_rpm, p_rpm, redline, display, a)
        print(f'wrote {a}')
    if args.charts in ('both', 'final-drive') and len(primaries) * len(options) > 1:
        chart_final_drive(sets, cal, primaries, options, stock_option, ratio_name,
                          redline, display, b)
        print(f'wrote {b}   (varying {ratio_name})')
    else:
        print('  no final-drive chart: this car\'s final drive is not adjustable')

    print(f'  tyre: {cal["tyre"]}, {cal["circumference"]:.4f} m rolling circumference')
    print(f'  final drive: primary {cal["primary"]} x {cal["diff"]} = {final_of(cal):.4f}')
    final = final_of(cal)
    for i, (gears, _, _) in enumerate(sets):
        speeds = '  '.join(f'{kmh(redline, ratio(g) * final, cal["circumference"]):5.1f}'
                           for g in gears)
        print(f'  set {i + 1} top speeds (km/h): {speeds}')


if __name__ == '__main__':
    main()
