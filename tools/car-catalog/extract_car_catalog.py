#!/usr/bin/env python3
"""Rebuild every bundled car template's `parameters:` block from the ACR game files.

Maintainer tooling - it needs a local Assetto Corsa Rally install and never ships
inside the skill. See README.md for provenance and for what it deliberately does
not touch.

    python extract_car_catalog.py --dry-run    # report only, writes nothing
    python extract_car_catalog.py              # rewrite the templates
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
TORQUE = os.path.join(REPO, 'tools', 'torque-curves')
sys.path.insert(0, HERE)
sys.path.insert(0, TORQUE)

from iostore import Toc                      # noqa: E402  (shared with torque-curves)
from acrpkg import Package                   # noqa: E402
from datatable import rows as dt_rows        # noqa: E402
import mapping as M                          # noqa: E402
import car_identity as CI                    # noqa: E402  (bootstrap_header only)
sys.path.insert(0, os.path.join(REPO, 'tools', 'gearing-charts'))
import make_gearing_chart as GC              # noqa: E402  (DT_Wheels prefix per slug)

DEFAULT_PAKS = ('C:/Program Files (x86)/Steam/steamapps/common/'
                'Assetto Corsa Rally/acr/Content/Paks')
TEMPLATES = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer', 'car-templates')
GAME_VERSION = '0.6'

# template slug -> presets asset basename
CAR_MAP = {
    'alfa-romeo-gta-1300-junior-1972':        'DA_AlfaRomeoGiuliaGTAJunior1300Presets',
    'alpine-a110-1-8-1973':                   'DA_AlpineA1101800Presets',
    'citroen-xsara-wrc-2003':                 'DA_CitroenXsaraWRCPresets',
    'fiat-124-abarth-rally-16v-1974':         'DA_Fiat124AbarthPresets',
    'fiat-131-abarth-1976':                   'DA_Fiat131AbarthPresets',
    'hyundai-i20-rally2-2021':                'DA_Hyundaii20NRally2Presets',
    'lancia-037-evoluzione-2-1984':           'DA_LanciaRally037Evo2Presets',
    'lancia-delta-integrale-evoluzione-1992': 'DA_LanciaDeltaHFIntegraleEvoPresets',
    'lancia-fulvia-coupe-hf-1970':            'DA_LanciaFulviaCoupeHFPresets',
    'lancia-stratos':                         'DA_LanciaStratosHFPresets',
    'mini-cooper-s-1964':                     'DA_MiniCooperS1275Presets',
    'peugeot-306-ii-maxi-1997':               'DA_Peugeot306IIMaxiPresets',
    'skoda-fabia-rs-rally2-2022':             'DA_SkodaFabiaRSRally2Presets',
    'subaru-impreza-555-s3-1993':             'DA_SubaruImprezaS3Presets',
    'audi-quattro-gr4-1981':                  'DA_AudiQuattroGr4Presets',
    'volkswagen-polo-gti-r5-2018':            'DA_VWPoloGTIR5Presets',
    'peugeot-208-rally4':                     'DA_Peugeot208Rally4Presets',
    'peugeot-206-wrc-1999':                   'DA_Peugeot206WRCPresets',
}

# the hint FName inside a DB-set override -> the DataTable that actually holds it
TABLE_ALIASES = {'LSDRampAnglesLists': 'DT_DiffRampsLists'}

WANTED_TABLES = ['DT_RearGearsLists', 'DT_FrontGearsLists', 'DT_CentreGearsLists',
                 'DT_CentreToRearGearsLists', 'DT_CentreToFrontGearsLists',
                 'DT_PrimaryGearsLists', 'DT_GearsSetsLists', 'DT_DiffRampsLists',
                 # bores for Front/Rear Cylinder, keyed by the car's DT_Wheels prefix
                 'DT_MasterCylindersLists']


# ---------------------------------------------------------------- pak plumbing

def extract(paks, wanted, out_dir):
    """Pull each wanted basename out of the paks. Returns {basename: file path}."""
    jobs, found = [], {}
    for entry in sorted(os.listdir(paks)):
        if not entry.endswith('.utoc'):
            continue
        try:
            toc = Toc(os.path.join(paks, entry))
            listing = toc.files()
        except Exception:
            continue          # a few containers use formats we don't parse; none hold this data
        cas = os.path.join(paks, entry[:-5] + '.ucas')
        for path, idx in listing.items():
            base = os.path.basename(path)
            if base[:-7] in wanted and base.endswith('.uasset') and base[:-7] not in found:
                plan = toc.plan(idx, cas)
                plan['out'] = os.path.join(out_dir, base)
                jobs.append(plan)
                found[base[:-7]] = plan['out']
    if not jobs:
        raise SystemExit('no assets found - is --paks pointing at the game?')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
        json.dump(jobs, fh)
        job_path = fh.name
    try:
        subprocess.run(['node', os.path.join(TORQUE, 'ooz_unpack.mjs'), job_path],
                       check=True, cwd=TORQUE, stdout=subprocess.DEVNULL)
    finally:
        os.unlink(job_path)
    return found


# ------------------------------------------------------------------ formatting

def snap(v):
    """Drop float32 storage noise: 9.999999747e-05 is the game's 0.0001."""
    return float(f'{v:.7g}')


def num(v):
    """Render a value the way the templates do: no trailing .0, no float noise."""
    if isinstance(v, str):
        return v
    if isinstance(v, int):
        return str(v)
    r = round(v, 6)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return repr(r).rstrip('0').rstrip('.')


def discrete_cap(adjustment):
    """How many entries this parameter may enumerate before min/max says it better."""
    for stem, cap in M.DISCRETE_CAP.items():
        if adjustment.startswith(stem):
            return cap
    return M.MAX_DISCRETE


def steps_list(mn, mx, step, cap=M.MAX_DISCRETE):
    """The explicit value list, or '' when a min/max/step line already says it."""
    if not step or step <= 0 or mx <= mn:
        return ''
    n = (mx - mn) / step
    if abs(n - round(n)) > 1e-6:
        return ''
    count = int(round(n)) + 1
    if count < 2 or count > cap:
        return ''
    return ', '.join(num(mn + i * step) for i in range(count))


# --------------------------------------------------------------- car catalogue

def collapse(ov, pkg):
    """{(group, axle, suffix): range} with left/right corners merged.

    Raises if a car ever disagrees side to side - that would mean the export map
    join had slipped, and silently averaging it would hide the bug.
    """
    out = {}
    for sid, exp in ov.items():
        if sid in M.IGNORED:
            continue
        group, where, suffix = sid.split('.', 2)
        cls = pkg.exports[exp][2]
        if 'RangeFloat' in cls:
            f = {k: snap(v) for k, v in pkg.floats(exp).items()}
            # neither bound serialised means "inherit" - a real 0..0 range never happens
            stored = 0 in f or 1 in f
            val = ('float' if stored else 'inherit', f.get(0, 0.0), f.get(1, 0.0), f.get(2, 0.0))
        elif 'RangeInteger' in cls:
            n = pkg.ints(exp)
            stored = 0 in n or 1 in n
            val = ('int' if stored else 'inherit', n.get(0, 0), n.get(1, 0), n.get(2, 0))
        elif 'RangeBool' in cls:
            val = ('bool', 0, 1, 0)
        elif 'DBReference' in cls:
            val = ('db', exp, None, None)
        else:
            continue
        axle = where.replace('Left', '').replace('Right', '')
        key = (group, axle, suffix)
        if key in out and out[key] != val and val[0] != 'db':
            raise AssertionError(f'left/right mismatch for {sid}: {out[key]} vs {val}')
        out[key] = val
    return out


def db_values(pkg, exp, tables):
    """The legal value list behind a DB-set override, or None if unresolvable."""
    _, blob = pkg.export_bytes(exp)
    i = blob.find(b'Values\x00')
    if i < 0:
        return None
    import struct
    p = i + 7 + 2                                   # past the FString and the 2-byte header
    if p + 16 > len(blob):
        return None
    hint = pkg.name(*struct.unpack_from('<II', blob, p))
    row = pkg.name(*struct.unpack_from('<II', blob, p + 8))
    table = tables.get(TABLE_ALIASES.get(hint, 'DT_' + hint))
    if not table or row not in table:
        return None
    return table[row]


def build_rows(pkg, tables):
    """Every template parameter row this car should carry, from the game files."""
    ov = pkg.overrides(pkg.main_export())
    merged = collapse(ov, pkg)
    rows, notes = [], []

    def add(section, adjustment, order, unit, mn, mx, step, steps=None, inherit=False):
        if adjustment in M.DEFINITION_RANGES:
            mn, mx, inherit = *M.DEFINITION_RANGES[adjustment], False
        if inherit:
            rows.append({'section': section, 'adjustment': adjustment, 'order': order,
                         'unit': unit, 'inherit': True,
                         'discrete_steps': steps if steps is not None else ''})
            return
        rows.append({
            'section': section, 'adjustment': adjustment, 'order': order,
            'min': num(mn), 'max': num(mx), 'unit': unit,
            'discrete_steps': (steps if steps is not None
                               else steps_list(mn, mx, step, discrete_cap(adjustment))),
        })

    for (group, axle, suffix), val in merged.items():
        kind, a, b, c = val
        sec = M.SECTIONS.get(group, group)

        if group == 'Gearbox' and suffix in M.GEARBOX:
            name, order, unit = M.GEARBOX[suffix]
            vals = db_values(pkg, a, tables) if kind == 'db' else None
            if suffix == 'GearsSet' and vals:
                listed = ', '.join(str(i + 1) for i in range(len(vals)))
                add(sec, name, order, unit, 1, len(vals), 1, listed)
            elif vals:
                add(sec, name, order, unit, '—', '—', 0, ', '.join(vals))
            else:
                notes.append(f'unresolved DB set: {group}.{axle}.{suffix}')
            continue

        if group == 'Suspensions' and suffix in M.SUSPENSION:
            stem, fo, ro, unit = M.SUSPENSION[suffix]
            add(sec, f'{stem} {axle}', fo if axle == 'Front' else ro, unit, a, b, c,
                inherit=(kind == 'inherit'))
            continue

        if group == 'Dampers' and suffix in M.DAMPERS:
            stem, fo, ro, unit = M.DAMPERS[suffix]
            add(sec, f'{stem} {axle}', fo if axle == 'Front' else ro, unit, a, b, c,
                inherit=(kind == 'inherit'))
            continue

        if group == 'Axles' and suffix in M.AXLES:
            stem, fo, ro, unit = M.AXLES[suffix]
            add(sec, f'{stem} {axle}', fo if axle == 'Front' else ro, unit, a, b, c,
                inherit=(kind == 'inherit'))
            continue

        if group == 'Differentials' and suffix in M.DIFFS:
            stem, unit, orders = M.DIFFS[suffix]
            if axle not in orders:
                notes.append(f'unmapped differential axle: {axle}.{suffix}')
                continue
            # always axle-qualified: the previous templates were inconsistent here
            name = stem if stem.startswith('Center') else                 f'{stem} {"Center" if axle == "Centre" else axle}'
            if kind == 'db':
                vals = db_values(pkg, a, tables)
                if vals is None:
                    notes.append(f'unresolved DB set: {group}.{axle}.{suffix}')
                    continue
                pretty = [v.replace('_', '/') for v in vals] if suffix == 'LSDRamps' else vals
                add(sec, name, orders[axle], unit, '—', '—', 0, ', '.join(pretty))
            else:
                add(sec, name, orders[axle], unit, a, b, c, inherit=(kind == 'inherit'))
            continue

        if group == 'Wheels' and suffix in M.WHEELS:
            stem, fo, ro, unit = M.WHEELS[suffix]
            add(sec, f'{stem} {axle}', fo if axle == 'Front' else ro, unit, a, b, c,
                inherit=(kind == 'inherit'))
            continue

        if group == 'Brakes' and suffix in M.BRAKES_MAIN:
            name, order, unit = M.BRAKES_MAIN[suffix]
            if name in M.CARRIED_OVER:
                continue                     # keeps the previous template's display strings
            add(sec, name, order, unit, a, b, c, inherit=(kind == 'inherit'))
            continue

        if group == 'Brakes' and suffix in M.BRAKE_PARTS:
            continue                         # display strings carried over, see CARRIED_OVER

        if group == 'Other' and suffix in M.ELECTRONICS:
            name, order, unit = M.ELECTRONICS[suffix]
            if kind == 'bool':
                add(sec, name, order, unit, '—', '—', 0, 'ON')
            else:
                add(sec, name, order, unit, a, b, c, inherit=(kind == 'inherit'))
            continue

        notes.append(f'unmapped setting: {group}.{axle}.{suffix}')

    # surface variants may narrow a range for gravel; emit those as extra rows
    for surface, vi in pkg.surface_variants(pkg.main_export()).items():
        vr = pkg.variant_ranges(vi)
        if not vr:
            continue
        for (group, axle, suffix), val in collapse(vr, pkg).items():
            kind, a, b, c = val
            if kind not in ('float', 'int'):
                continue
            table = {'Suspensions': M.SUSPENSION, 'Dampers': M.DAMPERS,
                     'Axles': M.AXLES, 'Wheels': M.WHEELS}.get(group)
            if not table or suffix not in table:
                notes.append(f'unmapped {surface} variant range: {group}.{axle}.{suffix}')
                continue
            stem, fo, ro, unit = table[suffix]
            name = f'{stem} {axle}'
            base = next((r for r in rows if r['adjustment'] == name), None)
            if base and (base.get('min'), base.get('max')) == (num(a), num(b)):
                continue                       # same as the base range, nothing to say
            rows.append({
                'section': M.SECTIONS.get(group, group), 'adjustment': name,
                'order': fo if axle == 'Front' else ro, 'min': num(a), 'max': num(b),
                'unit': unit, 'surface': surface,
                'discrete_steps': steps_list(a, b, c, discrete_cap(name)),
            })

    return rows, notes, merged


# ------------------------------------------------------------------- templates

PARAM_RE = re.compile(
    r'- section: "([^"]*)"\s*\n\s*adjustment: "([^"]*)"\s*\n\s*order: (\d+)\s*\n'
    r'\s*min: (.*?)\n\s*max: (.*?)\n\s*unit: "([^"]*)"\s*\n\s*discrete_steps: "(.*)"'
    r'(?:\s*\n\s*surface: "([^"]*)")?')

# screenshot-era spellings -> the canonical name
RENAMES = {
    'Discs Front': 'Brake Discs Front', 'Discs Rear': 'Brake Discs Rear',
    'Calipers Front': 'Brake Calipers Front', 'Calipers Rear': 'Brake Calipers Rear',
    'Pads/Shoe Front': 'Brake Pads Front', 'Pads/Shoe Rear': 'Brake Pads Rear',
}

# carried-over parameter -> the game setting that proves the car still has it
CARRIED_PROOF = {
    'Brake Discs Front': ('Brakes', 'Front', 'Disc'),
    'Brake Discs Rear': ('Brakes', 'Rear', 'Disc'),
    'Brake Calipers Front': ('Brakes', 'Front', 'Caliper'),
    'Brake Calipers Rear': ('Brakes', 'Rear', 'Caliper'),
    'Brake Pads Front': ('Brakes', 'Front', 'PadCompound'),
    'Brake Pads Rear': ('Brakes', 'Rear', 'PadCompound'),
    'Front Cylinder': ('Brakes', 'BrakesMain', 'MasterCylinderFront'),
    'Rear Cylinder': ('Brakes', 'BrakesMain', 'MasterCylinderRear'),
    'Master Cylinder': ('Brakes', 'BrakesMain', 'MasterCylinder'),
    'Tyre Type': None,                      # every car has tyres
}

CARRIED_ORDER = {
    'Brake Discs Front': (7010, ''), 'Brake Calipers Front': (7020, ''),
    'Brake Pads Front': (7030, ''), 'Front Cylinder': (7050, 'mm'),
    'Rear Cylinder': (7060, 'mm'), 'Master Cylinder': (7050, ''),
    'Brake Discs Rear': (7080, ''), 'Brake Calipers Rear': (7090, ''),
    'Brake Pads Rear': (7100, ''), 'Tyre Type': (6010, ''),
}


def unquote(v):
    v = v.strip()
    return v[1:-1] if len(v) > 1 and v[0] == v[-1] == '"' else v


def quoted(v):
    """Numbers go in bare; the em-dash placeholder keeps its quotes."""
    return v if re.fullmatch(r'-?\d+(\.\d+)?', v) else f'"{v}"'


def read_old(path):
    """('', []) for a car with no bundled template yet - see bootstrap_header()."""
    if not os.path.exists(path):
        return '', []
    txt = open(path, encoding='utf-8').read()
    out = []
    for m in PARAM_RE.finditer(txt):
        sec, adj, order, mn, mx, unit, steps, surface = m.groups()
        out.append({'section': sec, 'adjustment': RENAMES.get(adj.strip(), adj.strip()),
                    'order': int(order), 'min': unquote(mn), 'max': unquote(mx),
                    'unit': unit, 'discrete_steps': steps, 'surface': surface or ''})
    return txt, out


def render(rows):
    lines = ['parameters:']
    last = None
    for r in sorted(rows, key=lambda r: (r['order'], r['adjustment'], r.get('surface') or '')):
        if last is not None and r['section'] != last:
            lines.append('')
        last = r['section']
        lines += [f'  - section: "{r["section"]}"',
                  f'    adjustment: "{r["adjustment"]}"',
                  f'    order: {r["order"]}',
                  f'    min: {quoted(r["min"])}',
                  f'    max: {quoted(r["max"])}',
                  f'    unit: "{r["unit"]}"',
                  f'    discrete_steps: "{r["discrete_steps"]}"']
        if r.get('surface'):
            lines.append(f'    surface: "{r["surface"]}"')
    return '\n'.join(lines) + '\n'


def derived_steps(name, cylinders):
    """A CARRIED_OVER row's values recovered from the game files rather than from a
    previous template, or None when only a screenshot can supply them.

    Covers the game-wide constants (tyre compounds, pad compounds) and the per-car
    master-cylinder bores. Brake discs and calipers are NOT here: their setup-screen
    strings (`250/140X22 P TYPE1`) carry a middle number and a TYPE index that aren't
    in DT_Discs/DT_Calipers, the per-part DataAssets, or the part ids - see
    README.md - What it doesn't touch.
    """
    if name in M.CONSTANT_STEPS:
        steps = M.CONSTANT_STEPS[name]
        return '—', '—', steps
    if name in M.MASTER_CYLINDER_ROWS and cylinders:
        return cylinders[0], cylinders[-1], ', '.join(cylinders)
    return None


def merge(new_rows, old_rows, merged, cylinders=()):
    """Game-derived rows, plus what only the previous template can supply.

    Two kinds get carried over: parameters whose legal values are DB part records
    the UI spells itself, and parameters the game leaves at their definition
    default so the per-car asset holds no bound at all. Where the game files can
    actually supply one of those (see derived_steps), a car with no previous
    template gets it from there instead of needing a screenshot; an existing
    template's own wording still wins, so refreshing never rewrites it.
    """
    old_by_name = {r['adjustment']: r for r in old_rows if not r.get('surface')}
    out, carried, missing, derived = [], [], [], []

    for r in new_rows:
        if not r.pop('inherit', False):
            out.append(r)
            continue
        old = old_by_name.get(r['adjustment'])
        if old is None:
            missing.append(r['adjustment'])
            continue
        r['min'], r['max'] = old['min'], old['max']
        if not r['discrete_steps']:
            r['discrete_steps'] = old['discrete_steps']
        out.append(r)
        carried.append(r['adjustment'])

    have = {r['adjustment'] for r in out}
    for name, proof in CARRIED_PROOF.items():
        if proof is not None and proof not in merged:
            continue                                    # the car no longer has that part
        if name in have:
            continue
        old = old_by_name.get(name)
        order, unit = CARRIED_ORDER[name]
        if old is None:
            got = derived_steps(name, cylinders)
            if got is None:
                missing.append(name)
                continue
            mn, mx, steps = got
            out.append({'section': 'Wheels' if name == 'Tyre Type' else 'Brakes',
                        'adjustment': name, 'order': order, 'min': mn, 'max': mx,
                        'unit': unit, 'discrete_steps': steps})
            derived.append(name)
            continue
        out.append({'section': old['section'], 'adjustment': name, 'order': order,
                    'min': old['min'], 'max': old['max'], 'unit': old['unit'] or unit,
                    'discrete_steps': old['discrete_steps']})
        carried.append(name)
    return out, carried, missing, derived


def bootstrap_header(slug):
    """A starter header for a car with no bundled template yet.

    Pre-fills what DT_Cars gives cleanly (drivetrain, class, gearbox - see
    car_identity.py, validated against every existing template). `max_power` /
    `max_torque` start as a TODO here too, but `../torque-curves/extract_torque_curves.py`
    fills them in from the engine curve's own peaks on the very next step of the
    onboarding recipe (see README.md - Onboarding a brand-new car) - run that
    tool second and these two are no longer TODO when you open the file.
    Everything else DT_Cars doesn't hold as a plain FName - the exact display
    name/year, weight, weight distribution, steering lock, and the precise
    engine_layout prose (orientation, displacement, valve gear) - stays a `TODO`
    placeholder for one look at the game's car-info screen, which shows the
    display name, year, engine, max power, max torque, weight and steering lock
    directly. Two cautions when reading that screen:

    - **The steering-lock figure can be a per-side angle.** The VW Polo GTI R5's
      screen reads `280°` where the real lock-to-lock is `560°`. Sanity-check it
      against the other cars (most read 720-1170) and double it when it looks
      half-sized.
    - **The engine description can be wrong.** The Audi Quattro Gr.4's screen
      says `Inline 4`; the real car is a 2.1L inline-5. Write the real layout in
      `engine_layout` and note the disagreement.

    Steering lock is *not* in the game data as a plain number: neither `DT_Cars`'
    `SteeringAngle` field nor the `DT_SteeringAngles` table it points into holds a
    lock-angle for any car (a byte-level scan for every existing template's known
    `steering_lock` value found zero matches) - `DT_SteeringAngles` looks to be
    about the visual wheel prop. Don't re-check those two tables for it; read the
    car-info screen instead.
    """
    # save_ids is the string ACR writes into a .sav, which is the DT_Cars ROW KEY - not the
    # Vehicles/ folder name. The two differ on several cars (folder AlfaRomeoGiuliaGTA1300Junior
    # vs key AlfaRomeoGTA1300, LanciaDeltaHFIntegraleEvo vs LanciaDeltaIntegraleEvo,
    # LanciaFulviaCoupeHF vs LanciaFulviaHF, Peugeot306IIMaxi vs Peugeot306IIMaxiKitCar,
    # Peugeot206WRC vs Peugeot206). Verified: every car id in the repo's sample .sav files is a
    # DT_Cars key, 13 for 13, including all four discriminating cases.
    key = {v: k for k, v in CI.SLUGS.items()}.get(slug)
    facts = (CI.facts_for(_dt_cars_pkg[0], key) if key and _dt_cars_pkg[0] else None) or {}
    lines = [
        f'car: "TODO - exact display name + year (see the car-info screen)"',
        'game: "ACR"',
        f'save_ids: ["{key or "TODO - the car\'s DT_Cars row key"}"]',
        f'drivetrain: "{facts.get("drivetrain") or "TODO"}"',
        f'engine_layout: "{facts.get("engine_layout_draft") or "TODO"} '
        f'- TODO verify orientation/displacement/valve gear from the car-info screen"',
        'weight_bias: "TODO - from the car-info screen"',
        'weight: "TODO - real-world spec (see README.md: this is not game output)"',
        'max_power: "TODO - real-world spec (see README.md: this is not game output)"',
        'max_torque: "TODO - real-world spec (see README.md: this is not game output)"',
        f'class: "{facts.get("class") or "TODO"}"',
        f'gearbox: "{facts.get("gearbox") or "TODO"}"',
        'steering_lock: "TODO - from the car-info screen; double it if it reads '
        'half-sized (that screen sometimes shows the per-side angle - see bootstrap_header)"',
        f'version: "{GAME_VERSION}"',
    ]
    return '\n'.join(lines)


# populated by main() once, only when at least one requested slug is new;
# a single-item list so bootstrap_header can see it without a global rebind
_dt_cars_pkg = [None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=DEFAULT_PAKS)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--car', help='only this template slug')
    args = ap.parse_args()

    slugs = [args.car] if args.car else sorted(CAR_MAP)
    new_slugs = {s for s in slugs if not os.path.exists(os.path.join(TEMPLATES, s + '.yaml'))}
    wanted = set(WANTED_TABLES) | {CAR_MAP[s] for s in slugs}
    if new_slugs:
        wanted.add('DT_Cars')
    with tempfile.TemporaryDirectory() as tmp:
        paths = extract(args.paks, wanted, tmp)
        tables = {}
        for t in WANTED_TABLES:
            if t in paths:
                tables[t] = dt_rows(Package(open(paths[t], 'rb').read()))
        if 'DT_Cars' in paths:
            _dt_cars_pkg[0] = Package(open(paths['DT_Cars'], 'rb').read())

        total_changed = 0
        for slug in slugs:
            asset = CAR_MAP[slug]
            pkg = Package(open(paths[asset], 'rb').read())
            new_rows, notes, merged = build_rows(pkg, tables)
            path = os.path.join(TEMPLATES, slug + '.yaml')
            is_new = slug in new_slugs
            txt, old_rows = read_old(path)
            # DT_MasterCylindersLists is keyed by the car's DT_Wheels prefix, which
            # gearing-charts already maps per slug - reuse it rather than add a 5th map
            wheels_key = GC.CARS.get(slug, (None, None, None))[1]
            cylinders = tables.get('DT_MasterCylindersLists', {}).get(wheels_key, ())
            rows, carried, missing, derived = merge(new_rows, old_rows, merged, cylinders)

            def key(r):
                return (r['adjustment'] + (f' [{r["surface"]}]' if r.get('surface') else ''))
            old_by = {key(r): r for r in old_rows}
            new_by = {key(r): r for r in rows}
            added = sorted(set(new_by) - set(old_by))
            dropped = sorted(set(old_by) - set(new_by))
            changed = [n for n in sorted(set(new_by) & set(old_by))
                       if (new_by[n]['min'], new_by[n]['max'], new_by[n]['discrete_steps'])
                       != (old_by[n]['min'], old_by[n]['max'], old_by[n]['discrete_steps'])]
            total_changed += len(changed) + len(added) + len(dropped)

            print(f'\n{slug}  ({len(rows)} params, was {len(old_rows)})'
                  + ('  [NEW - no bundled template yet]' if is_new else ''))
            for n in changed:
                o, w = old_by[n], new_by[n]
                if (o['min'], o['max']) != (w['min'], w['max']):
                    print(f'    ~ {n:34} {o["min"]}..{o["max"]}  ->  {w["min"]}..{w["max"]}')
                else:
                    print(f'    ~ {n:34} steps: "{o["discrete_steps"][:30]}"'
                          f'  ->  "{w["discrete_steps"][:30]}"')
            for n in added:
                print(f'    + {n:34} {new_by[n]["min"]}..{new_by[n]["max"]}')
            for n in dropped:
                print(f'    - {n}')
            for n in notes:
                print(f'    ! {n}')
            if is_new:
                for n in missing:
                    print(f'    ! NEEDS SCREENSHOT (not in the game files): {n}')
            else:
                for n in missing:
                    print(f'    ! no game range and no previous value: {n}')
            if derived:
                print(f'    + filled from the game files: {", ".join(sorted(derived))}')
            if carried:
                print(f'    = carried over from the previous template: {", ".join(sorted(carried))}')

            if is_new:
                head = bootstrap_header(slug)
                print(f'    = new template header pre-filled from DT_Cars: drivetrain, class, '
                      f'gearbox - the rest is TODO, see the written file')
            else:
                head = txt.split('\nparameters:')[0].rstrip('\n')
                head = re.sub(r'^version: ".*"$', f'version: "{GAME_VERSION}"',
                              head, flags=re.M)
            out = head + '\n\n' + render(rows)
            if not args.dry_run:
                open(path, 'w', encoding='utf-8', newline='\n').write(out)

    print(f'\n{"would change" if args.dry_run else "changed"} {total_changed} parameter(s) '
          f'across {len(slugs)} template(s)')


if __name__ == '__main__':
    main()
