#!/usr/bin/env python3
"""Shared game-file readers for the car's gearing data (gear sets, tyres, final drives,
template facts), used by the ACR Car Lab exporter (`export_car_data.py`) and by
`calibration.py` / `game_version.py`. The PNG gearing and final-drive charts this module
used to render were replaced by the ACR Car Lab web tool; the power/torque chart (built
separately, by `tools/torque-curves`) is the only chart still generated as an image.

Ratios are exact - they come from the game's own gear-set assets. Absolute km/h needs
a rolling circumference, which is calibrated per car against in-game measurements (see
CALIBRATION) rather than guessed; the tyre assets hold a radius but it sits behind
another layer of unversioned physics data.
"""
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
    'audi-quattro-gr4-1981':                  ('AudiQuattroGr4', 'AudiQuattroGr.4',
                                               'AudiQuattroGr4'),
    'volkswagen-polo-gti-r5-2018':            ('VWPoloGTIR5', 'VolkswagenPoloGTIR5',
                                               'VWPoloGTIR5'),
    'peugeot-208-rally4':                     ('Peugeot208Rally4', 'Peugeot208Rally4',
                                               'Peugeot208Rally4'),
    'peugeot-206-wrc-1999':                   ('Peugeot206WRC', 'Peugeot206WRC',
                                               'Peugeot206WRC'),
}


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


def template_facts(slug, axle, require_curve=True):
    """Primary-gear and differential options plus the engine's rpm landmarks.

    `require_curve=False` is for the site exporter, which finds a curve for a template that has
    none (the 206 WRC) through the car asset; the max rpm then comes back None."""
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
    if not rpms and require_curve:
        raise SystemExit(f'no engine curve in {slug}.yaml')
    max_rpm = max(rpms) if rpms else None
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

