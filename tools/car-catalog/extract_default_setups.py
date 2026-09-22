#!/usr/bin/env python3
"""Default setups out of the ACR game files -> car-setups/<slug>.yaml.

Each car's presets asset holds a base setup (PhysicsCarSetup), per-surface overrides and named
presets (Balanced on every car; Aggressive on a few). decode_setups.py reads them; this tool
composes every (surface, preset) into a complete setup keyed by the car's template parameter
names, checks each against the template's ranges with the skill's own load_catalog.py, and
writes the bundled file. Re-run after a game update (`make extract-setups`), read the diff.

Maintainer tooling: it needs a local Assetto Corsa Rally install and never ships inside the
skill. Idempotent - a second run with nothing changed reports zero changes and rewrites no
file, because `written_at` is only moved when something else moved too.

Usage:
  python extract_default_setups.py [--dry-run] [--car SLUG] [--paks DIR]
"""

import argparse
import datetime
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

from acrpkg import Package                                     # noqa: E402
from datatable import rows as dt_rows                          # noqa: E402
import decode_setups as D                                      # noqa: E402
import extract_car_catalog as ECC                              # noqa: E402

SKILL = ECC.SKILL
TEMPLATES = ECC.TEMPLATES
SETUPS = os.path.join(SKILL, 'car-setups')
sys.path.insert(0, os.path.join(SKILL, 'scripts'))

import load_catalog as LC                                      # noqa: E402
import load_default_setup as LDS                               # noqa: E402

# The catalog extractor reads ranges, so it never needs the part lists; resolving a *value*
# does - a disc and a caliper are written as their position in the car's own option list.
SETUP_TABLES = ['DT_DiscsLists', 'DT_CalipersLists']

# ---------------------------------------------------------------------------------------
# Values the game's own presets ship off the template's grid.
#
# `load_catalog.py --check` rejects them and it is right to: they are not values a user could
# dial in on the setup screen. But they are what the game ships, and a bundled default setup
# is a copy of the game's data, not a corrected version of it - so they are written as-is and
# excused here, one line of evidence each. Anything else illegal stops the run.
#
# A new one is never added silently: the extractor names it with its value and legal range, and
# `tests/test_car_setups.py::test_every_allowlisted_off_grid_value_is_really_in_its_file`
# fails if an entry here stops describing the file, so the list can't outlive the game update
# that made it necessary.
KNOWN_OFF_GRID = {
    # The 208's tarmac base slow bump. Its grid steps by 105 Ns/m (... 4185, 4290, 4395 ...), so
    # 4285 is 5 below a step - the closest the screen can dial is 4290.
    ('peugeot-208-rally4', 'Tarmac', 'Balanced', 'Slow Bump Front'): 4285,
    # Aggressive does not override slow bump, so it inherits the same off-grid value.
    ('peugeot-208-rally4', 'Tarmac', 'Aggressive', 'Slow Bump Front'): 4285,
    # The Polo's tarmac front anti-roll bar: 19500 against a template Max of 17500, so the game
    # ships its own preset 2000 N/m outside the range it advertises for that parameter.
    ('volkswagen-polo-gti-r5-2018', 'Tarmac', 'Balanced', 'Anti-roll Bar Stiffness Front'): 19500,
    # The Mini's gravel brake proportioning - the same pressure as the template's own "3.50"
    # step, spelled with one decimal. `check_values` compares the text of a discrete step, not
    # the number, so it rejects a value that is on the grid.
    ('mini-cooper-s-1964', 'Gravel', 'Balanced', 'Proportioning Preload'): 3.5,
}


# -------------------------------------------------------------------------- rendering

def order_index(template_rows):
    """{adjustment: Order} from a template, the baseline row winning over a surface row."""
    orders = {}
    for row in template_rows:
        name = row['adjustment']
        if name not in orders or not row.get('surface'):
            orders[name] = row['order']
    return orders


def numeric_adjustments(catalog_rows):
    """The adjustments whose catalog row is a plain numeric range, on every surface.

    A master cylinder is stored in the game as a DataTable row *named* after its bore
    (`MasterCylinders/19.05`), so `decode_setups.resolve` hands it back as the text `'19.05'`.
    Its template row is millimetres between a Min and a Max, with no enumerated steps - and
    the setup screen shows a number - so the bundled file has to write a number, or the
    skill's own `--check` rejects the game's own value as "not a number".

    An adjustment that enumerates its steps anywhere is excluded, so `Gear Set` stays the text
    `"1"` its steps spell and a disc keeps its exact step string.
    """
    by_adjustment = {}
    for row in catalog_rows:
        by_adjustment.setdefault(row['Adjustment'], []).append(row)
    out = set()
    for adjustment, rows in by_adjustment.items():
        if any(LC.steps_of(row) for row in rows):
            continue
        base = next((row for row in rows if not row.get('Surface')), None)
        if base and all(isinstance(base.get(k), (int, float)) for k in ('Min', 'Max')):
            out.add(adjustment)
    return out


def clean(name, value, numeric):
    """One value as the bundled file spells it.

    float32 storage turns the game's 0.048 into 0.04800000041723251; writing that would put a
    number in the file that is on no grid and reads as a decoding bug. Six significant digits
    is well past anything a setup screen shows. An integral float is written as an int, the way
    the templates write theirs, and a `numeric` adjustment's text is parsed back to a number.
    """
    if isinstance(value, str) and name in numeric:
        try:
            value = float(value)
        except ValueError:
            return value
    if isinstance(value, float):
        value = float(f'{value:.6g}')
        return int(value) if value.is_integer() else value
    return value


def render(doc, orders):
    lines = [f'car: "{doc["car"]}"', 'game: "ACR"', f'version: "{doc["version"]}"',
             'source: "game-files"', f'written_at: "{doc["written_at"]}"', 'setups:']
    for entry in doc['setups']:
        lines += [f'  - surface: "{entry["surface"]}"', f'    preset: "{entry["preset"]}"',
                  '    values:']
        for key in sorted(entry['values'], key=lambda k: (orders.get(k, 10 ** 6), k)):
            value = entry['values'][key]
            bare = isinstance(value, (int, float)) and not isinstance(value, bool)
            lines.append(f'      "{key}": {value if bare else json.dumps(value)}')
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------------- validation

def illegal(slug, surface, preset, report):
    """The problems `check_values` found that the game doesn't itself ship. Lines of text."""
    out = []
    for problem in report['problems']:
        name, value = problem['Adjustment'], problem['value']
        if KNOWN_OFF_GRID.get((slug, surface, preset, name)) == value:
            continue
        legal = problem.get('legal')
        if isinstance(legal, list) and len(legal) == 2 and all(
                isinstance(b, (int, float)) for b in legal):
            legal = f'{legal[0]}..{legal[1]}'
        elif isinstance(legal, list):
            legal = ', '.join(str(step) for step in legal)
        out.append(f'{slug} {surface}/{preset}: {name} = {value!r} - '
                   f'{problem["reason"]} (legal: {legal})')
    return out


def allowlisted(slug, surface, preset, values):
    """[(adjustment, value)] this entry carries that KNOWN_OFF_GRID excuses."""
    return [(name, value) for name, value in sorted(values.items())
            if KNOWN_OFF_GRID.get((slug, surface, preset, name)) == value]


# ------------------------------------------------------------------------------ diffing

def previous(path):
    """(text, {(surface, preset): values}, written_at) for the file on disk, or three Nones.

    Parsed with the skill's own `load_default_setup.load_file`, so the diff is read through the
    same parser the skill reads the file with - a file this tool writes but that loader can't
    parse fails here, on the machine that can fix it.
    """
    if not os.path.exists(path):
        return None, None, None
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    doc = LDS.load_file(path)
    return (text, {(e['surface'], e['preset']): e['values'] for e in doc['setups']},
            doc['written_at'])


def differences(old, new):
    """(added, dropped, [(key, adjustment, was, now)]) between two {(surface,preset): values}."""
    added = sorted(set(new) - set(old))
    dropped = sorted(set(old) - set(new))
    changed = []
    for key in sorted(set(old) & set(new)):
        was, now = old[key], new[key]
        for name in sorted(set(was) | set(now)):
            if was.get(name) != now.get(name):
                changed.append((key, name, was.get(name), now.get(name)))
    return added, dropped, changed


# --------------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=ECC.DEFAULT_PAKS)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--car', help='only this template slug')
    args = ap.parse_args()

    slugs = [args.car] if args.car else sorted(ECC.CAR_MAP)
    unknown = [s for s in slugs if s not in ECC.CAR_MAP]
    if unknown:
        raise SystemExit(f'no presets asset mapped for {", ".join(unknown)}')
    table_names = list(ECC.WANTED_TABLES) + SETUP_TABLES
    wanted = set(table_names) | {ECC.CAR_MAP[s] for s in slugs}
    today = datetime.date.today().isoformat()
    totals, problems, pending = {'changed': 0, 'added': 0, 'dropped': 0}, [], []

    with tempfile.TemporaryDirectory() as tmp:
        paths = ECC.extract(args.paks, wanted, tmp)
        tables = {}
        for name in table_names:
            if name in paths:
                with open(paths[name], 'rb') as fh:
                    tables[name] = dt_rows(Package(fh.read()))

        for slug in slugs:
            with open(paths[ECC.CAR_MAP[slug]], 'rb') as fh:
                pkg = Package(fh.read())
            template_path = os.path.join(TEMPLATES, slug + '.yaml')
            if not os.path.exists(template_path):
                raise SystemExit(f'{slug}: no bundled template - run extract-catalogs first')
            decoded = D.decode_car(pkg, tables)
            car_keys = D.car_keys_from(pkg)
            _, template_rows = ECC.read_old(template_path)         # decode_setups' row shape
            orders = order_index(template_rows)
            header, raw_rows = LC.load_template(template_path)     # load_catalog's row shape
            catalog_rows = LC.build_rows(header, raw_rows)
            numeric = numeric_adjustments(catalog_rows)

            entries, unfilled, excused = [], {}, []
            for surface, preset in D.surfaces_and_presets(decoded):
                values = D.compose(decoded, surface, preset)
                adjustments, missing = D.to_adjustments(values, template_rows, tables, car_keys)
                adjustments = {k: clean(k, v, numeric) for k, v in adjustments.items()}
                problems += illegal(slug, surface, preset,
                                    LC.check_values(catalog_rows, adjustments, surface))
                excused += [(surface, preset, name, value) for name, value
                            in allowlisted(slug, surface, preset, adjustments)]
                entries.append({'surface': surface, 'preset': preset, 'values': adjustments})
                unfilled[(surface, preset)] = missing

            doc = {'car': header.get('car', ''), 'version': ECC.GAME_VERSION,
                   'written_at': today, 'setups': entries}
            path = os.path.join(SETUPS, slug + '.yaml')
            old_text, old_values, old_date = previous(path)
            text = render(doc, orders)
            # `written_at` alone is not a change: re-running the extraction on an unchanged
            # game must leave the tree clean, or every run looks like a game update.
            if old_text is not None and old_date:
                dated = render(dict(doc, written_at=old_date), orders)
                if dated == old_text:
                    text = dated

            new_values = {(e['surface'], e['preset']): e['values'] for e in entries}
            added, dropped, changed = differences(old_values or {}, new_values)
            totals['added'] += len(added)
            totals['dropped'] += len(dropped)
            totals['changed'] += len(changed)

            print(f'\n{slug}  ({len(entries)} setups, {sum(len(e["values"]) for e in entries)} '
                  f'values)' + ('  [NEW - no bundled file yet]' if old_values is None else ''))
            for entry in entries:
                print(f'    . {entry["surface"]}/{entry["preset"]:12} '
                      f'{len(entry["values"]):3} values')
            for (surface, preset), name, was, now in changed:
                print(f'    ~ {surface}/{preset} {name:34} {was!r} -> {now!r}')
            for surface, preset in (added if old_values is not None else []):
                print(f'    + {surface}/{preset}')
            for surface, preset in dropped:
                print(f'    - {surface}/{preset}')
            for (surface, preset), names in unfilled.items():
                if names:
                    print(f'    ! unfilled on {surface}/{preset}: {", ".join(names)}')
            for surface, preset, name, value in excused:
                print(f'    ! off the grid, written as the game ships it: '
                      f'{surface}/{preset} {name} = {value}')
            for note in decoded['notes']:
                print(f'    ! note: {note}')
            for required in ('Tarmac', 'Gravel'):
                if required not in {e['surface'] for e in entries}:
                    problems.append(f'{slug}: no {required} setup in the presets asset')

            if text != old_text:
                pending.append((path, text))

    # Nothing is written until every car validated: a run that stops on an illegal value must
    # not leave half the bundled files refreshed and the other half stale.
    if problems:
        raise SystemExit('\n'.join(
            ['', 'illegal values - nothing was written:'] + [f'  {line}' for line in problems] +
            ['', 'Either the game moved (refresh the templates with `make extract-catalogs`) '
             'or the value belongs in KNOWN_OFF_GRID with its evidence.']))
    if not args.dry_run and pending:
        os.makedirs(SETUPS, exist_ok=True)
        for path, text in pending:
            with open(path, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
    print(f'\n{"would change" if args.dry_run else "changed"} {totals["changed"]} value(s), '
          f'{"add" if args.dry_run else "added"} {totals["added"]} and '
          f'{"drop" if args.dry_run else "dropped"} {totals["dropped"]} setup(s) '
          f'across {len(slugs)} car(s); '
          f'{"would write" if args.dry_run else "wrote"} {len(pending)} file(s)')


if __name__ == '__main__':
    main()
