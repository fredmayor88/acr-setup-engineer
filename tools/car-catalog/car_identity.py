#!/usr/bin/env python3
"""Read a car's identity facts (drivetrain, class, gearbox, engine layout hints)
out of ACR's DT_Cars, for the template header fields that don't come from the
per-car presets asset extract_car_catalog.py already handles.

Maintainer tooling - needs a local Assetto Corsa Rally install, never ships
inside the skill. See README.md - Car identity facts for what this does and
does not give you.

    python car_identity.py                       # every car DT_Cars has a row for
    python car_identity.py --car AudiQuattroGr4   # one row, by its DT_Cars key
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

from iostore import Toc                # noqa: E402
from acrpkg import Package              # noqa: E402
from datatable import struct_rows       # noqa: E402

DEFAULT_PAKS = ('C:/Program Files (x86)/Steam/steamapps/common/'
                'Assetto Corsa Rally/acr/Content/Paks')

# DT_Cars row key -> template slug, for the cars currently bundled or queued.
# A row key that isn't here still prints under its raw DT_Cars name.
SLUGS = {
    'AlfaRomeoGTA1300':        'alfa-romeo-gta-1300-junior-1972',
    'AlpineA110':              'alpine-a110-1-8-1973',
    'CitroenXsaraWRC':         'citroen-xsara-wrc-2003',
    'Fiat124Abarth':           'fiat-124-abarth-rally-16v-1974',
    'Fiat131Abarth':           'fiat-131-abarth-1976',
    'HyundaiI20NRally2':       'hyundai-i20-rally2-2021',
    'LanciaRally037Evo2':      'lancia-037-evoluzione-2-1984',
    'LanciaDeltaIntegraleEvo': 'lancia-delta-integrale-evoluzione-1992',
    'LanciaFulviaHF':          'lancia-fulvia-coupe-hf-1970',
    'LanciaStratosHF':         'lancia-stratos',
    'MiniCooperS1275':         'mini-cooper-s-1964',
    'Peugeot306IIMaxiKitCar':  'peugeot-306-ii-maxi-1997',
    'SkodaFabiaRSRally2':      'skoda-fabia-rs-rally2-2022',
    'SubaruImprezaS3':         'subaru-impreza-555-s3-1993',
    # queued, no bundled template yet - see car-templates/README or the skill's
    # onboarding backlog
    'AudiQuattroGr4':          'audi-quattro-gr4-1981',
    'VWPoloGTIR5':             'volkswagen-polo-gti-r5-2018',
    'Peugeot208Rally4':        'peugeot-208-rally4',
    'Peugeot206':              'peugeot-206-wrc-1999',   # DT_Cars key omits "WRC"
}

# tags[0] MUST be the anchor - see struct_rows(). Order after that doesn't matter.
TAGS = ('Manufacturers', 'EngineTypes', 'EnginePositions', 'Inductions',
        'WheelDrives', 'GearsTypes', 'CarsClasses')

WHEELDRIVE_TO_DRIVETRAIN = {'Front': 'FWD', 'Rear': 'RWD', 'Four': 'AWD'}
INDUCTION_ADJ = {'Natural': 'naturally-aspirated', 'Turbo': 'turbocharged'}


def class_label(cars_class):
    """CarsClasses value -> the 'Group X · Y' string every template's `class:`
    field uses. Verified against all 13 bundled templates (README - Car
    identity facts); a value outside these families comes back unchanged so a
    gap is visible instead of silently wrong.
    """
    if cars_class.startswith('H'):
        return f'Group 2/4 \u00b7 {cars_class}'
    if cars_class.startswith('Rally'):
        return f'Group R \u00b7 {cars_class}'
    if cars_class.startswith('B'):
        return f'Group B \u00b7 {cars_class}'
    if cars_class == 'K11':
        return f'Group A \u00b7 {cars_class}'
    m = re.match(r'A8_Evo(\d+)', cars_class)
    if m:
        return f'Group A \u00b7 A8 EV0{m.group(1)}'
    m = re.match(r'WR\d*Evo(\d+)', cars_class)
    if m:
        return f'Group WR \u00b7 EV0{m.group(1)}'
    return cars_class


def gearbox_label(gears_type):
    """GearsTypes value -> the 'Kind N-speed' string every template's
    `gearbox:` field uses (e.g. Sequential6_7_Lever -> 'Sequential 6-speed';
    the trailing _7/_Lever/_SinglePaddle hardware detail is dropped, matching
    what every existing template already did by hand).
    """
    m = re.match(r'(Manual|Sequential)(\d+)', gears_type)
    return f'{m.group(1)} {m.group(2)}-speed' if m else gears_type


def facts_for(pkg, key):
    row = struct_rows(pkg, TAGS).get(key)
    if row is None:
        return None
    drivetrain = WHEELDRIVE_TO_DRIVETRAIN.get(row.get('WheelDrives'), row.get('WheelDrives'))
    induction = INDUCTION_ADJ.get(row.get('Inductions'), row.get('Inductions'))
    return {
        'drivetrain': drivetrain,
        'class': class_label(row['CarsClasses']) if 'CarsClasses' in row else None,
        'gearbox': gearbox_label(row['GearsTypes']) if 'GearsTypes' in row else None,
        'manufacturer': row.get('Manufacturers'),
        'engine_position': row.get('EnginePositions'),
        'engine_type': row.get('EngineTypes'),
        'induction': induction,
        # A rough engine_layout starting draft ONLY - orientation (transverse vs
        # longitudinal), displacement and valve gear aren't in this table. Every
        # existing template's engine_layout is hand-written prose; treat this as
        # a first line to edit, not a finished value.
        'engine_layout_draft': (f"{row.get('EnginePositions', '?').lower()}-mounted "
                                 f"{induction or '?'} {row.get('EngineTypes', '?')}"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--paks', default=DEFAULT_PAKS)
    ap.add_argument('--car', help='DT_Cars row key, e.g. AudiQuattroGr4 (default: all rows)')
    args = ap.parse_args()

    if not os.path.isdir(args.paks):
        sys.exit(f'ACR paks not found at {args.paks} (pass --paks)')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')   # class_label emits U+00B7

    wanted = {'DT_Cars'}
    found, jobs = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for entry in sorted(os.listdir(args.paks)):
            if not entry.endswith('.utoc'):
                continue
            try:
                toc = Toc(os.path.join(args.paks, entry))
                listing = toc.files()
            except Exception:
                continue
            cas = os.path.join(args.paks, entry[:-5] + '.ucas')
            for path, idx in listing.items():
                base = os.path.basename(path)
                if base[:-7] in wanted and base.endswith('.uasset') and base[:-7] not in found:
                    plan = toc.plan(idx, cas)
                    plan['out'] = os.path.join(tmp, base)
                    jobs.append(plan)
                    found[base[:-7]] = plan['out']
        if not jobs:
            sys.exit('DT_Cars not found - is --paks pointing at the game?')
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
            json.dump(jobs, fh)
            job_path = fh.name
        try:
            subprocess.run(['node', os.path.join(TORQUE, 'ooz_unpack.mjs'), job_path],
                           check=True, cwd=TORQUE, stdout=subprocess.DEVNULL)
        finally:
            os.unlink(job_path)

        pkg = Package(open(found['DT_Cars'], 'rb').read())
        all_rows = struct_rows(pkg, TAGS)

        keys = [args.car] if args.car else sorted(all_rows)
        for key in keys:
            if key not in all_rows:
                print(f'{key}: not a DT_Cars row (have: {", ".join(sorted(all_rows))})')
                continue
            f = facts_for(pkg, key)
            slug = SLUGS.get(key, key)
            print(f"\n{key}  ({slug})")
            for k in ('drivetrain', 'class', 'gearbox', 'manufacturer',
                      'engine_position', 'engine_type', 'induction', 'engine_layout_draft'):
                print(f'  {k:20} {f[k]}')


if __name__ == '__main__':
    main()
