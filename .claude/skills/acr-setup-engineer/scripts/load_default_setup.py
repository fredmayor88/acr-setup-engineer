#!/usr/bin/env python3
"""Read the game's own default setup for a car out of the skill's bundled files.

A build starts from the game's default setup (`SKILL.md` -> *Baseline first*). For a car with
a file in `car-setups/`, that anchor ships inside the skill: no screenshots, no Notion
`default` rows, no network. `tools/car-catalog/extract_default_setups.py` writes those files
straight out of the installed game; this script is the only thing that reads them.

Usage:
  # One entry as JSON: {"car","version","surface","preset","fallback","values"}
  python scripts/load_default_setup.py --car <slug> --surface Tarmac
  python scripts/load_default_setup.py --car <slug> --surface Gravel --preset Aggressive

  # What the file has: {"car","version","setups":[{"surface","preset"}, ...]}
  python scripts/load_default_setup.py --list <slug>

  # The game version every bundled file is stamped with:
  python scripts/load_default_setup.py --game-version

Options:
  --surface S    Any surface name. The bundled files carry `Tarmac` and `Gravel` on every car
                 and `Snow` on two, but the name is not checked against a list: a surface this
                 car has no entry for is answered from the data (see below), not refused as a
                 usage error.
  --preset NAME  Defaults to `Balanced`, which every car has. Pass another name only when the
                 user asked for it by name (`Aggressive` exists on a couple of cars).
  --pretty       Indent the JSON, for a human reading the output.
  --dir DIR      Read from DIR instead of the skill's own `car-setups/` (tests).

A surface the file has no entry for falls back **Snow -> Gravel**, and the output's
`"fallback"` then names the surface the values actually came from (`"surface"` stays the one
that was asked for). There is no other fallback: any other surface the file lacks exits 1 with
stderr naming the surfaces it has.

Exit codes: 0 success · 1 the file is missing, the surface has no entry and no fallback, or
the preset is not in the file (stderr names the ones that are) · 2 usage error.
stdlib only (the code sandbox has no PyYAML). Output is always UTF-8, whatever the console
locale is - a car name can carry an accent.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SETUPS_DIR = os.path.join(SKILL, 'car-setups')
GAME_VERSION_FILE = os.path.join(SKILL, 'GAME_VERSION')

HEADER_FIELDS = ('car', 'game', 'version', 'source', 'written_at')

# The only surface substitution there is: a car the game gives no Snow presets to is driven on
# its gravel ones. Spec -> Global Constraints.
FALLBACKS = {'Snow': 'Gravel'}

USAGE = ('usage: load_default_setup.py --car <slug> --surface <Surface>\n'
         '                             [--preset NAME] [--pretty] [--dir DIR]\n'
         '       load_default_setup.py --list <slug> [--pretty] [--dir DIR]\n'
         '       load_default_setup.py --game-version')


class SetupError(Exception):
    """A bundled setups file that can't be read, or has no entry for what was asked."""


def use_utf8_output():
    """Print UTF-8 whatever the console's locale is.

    Same reason as `load_catalog.py`: the skill always runs this with stdout piped, and on
    Windows Python would otherwise encode a car name's accent with the ANSI code page while
    the reader decodes it as UTF-8. Guarded because stdout may be a plain object with no
    `reconfigure` (a test capturing output, an embedded runner).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            try:
                reconfigure(encoding='utf-8')
            except (ValueError, OSError):        # already detached / not reconfigurable
                pass


def fail(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def unquote(text):
    """Strip one pair of matching surrounding quotes, if any."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        return text[1:-1]
    return text


def parse_value(text):
    """One `values` entry: a JSON string when quoted, else an int, else a float."""
    text = text.strip()
    if text[:1] in ('"', "'"):
        try:
            return json.loads(text) if text[0] == '"' else unquote(text)
        except json.JSONDecodeError:
            return unquote(text)
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def load_file(path):
    """Parse one `car-setups/<slug>.yaml`.

        {'car','game','version','source','written_at',
         'setups': [{'surface','preset','values': {adjustment: value}}]}

    Deliberately minimal, stdlib-only parsing of the one flat shape the extractor writes
    (spec -> *Data model*), the same approach `load_catalog.py` takes to the templates: header
    keys at column 0, then `setups:` and its items. Entries keep the file's order, which is
    the order the game lists the surfaces in.
    """
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise SetupError(f'cannot read bundled setups file: {exc}')

    doc = {field: '' for field in HEADER_FIELDS}
    doc['setups'] = []
    entry, in_setups, in_values = None, False, False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if line[:1].strip():                                  # a top-level key, column 0
            key, sep, value = stripped.partition(':')
            in_setups = key == 'setups'
            in_values, entry = False, None
            if sep and not in_setups and key in HEADER_FIELDS:
                doc[key] = unquote(value)
            continue
        if not in_setups:
            continue
        if stripped.startswith('- '):
            entry = {'surface': '', 'preset': '', 'values': {}}
            doc['setups'].append(entry)
            stripped, in_values = stripped[2:].strip(), False
        if entry is None:
            continue
        if stripped == 'values:':
            in_values = True
            continue
        key, sep, value = stripped.partition(':')
        if not sep:
            continue
        if in_values and key[:1] == '"':
            entry['values'][unquote(key)] = parse_value(value)
        elif key in ('surface', 'preset'):
            entry[key] = unquote(value)
            in_values = False
    if not doc['setups']:
        raise SetupError(f'no setups found in {path}')
    return doc


def pick(doc, surface, preset='Balanced'):
    """(entry, fallback) for one surface and preset.

    `fallback` is None when the file has the surface, and the surface the values came from
    when it doesn't - today only `'Gravel'`, standing in for Snow. Raises `SetupError` when
    there is no entry and no fallback, or when the preset isn't in the file.
    """
    have = [e['surface'] for e in doc['setups']]
    used, fallback = surface, None
    if surface not in have:
        alternative = FALLBACKS.get(surface)
        if alternative is None or alternative not in have:
            raise SetupError(f'{doc["car"]}: no {surface} setup in the bundled file '
                             f'(it has {", ".join(sorted(set(have)))})')
        used, fallback = alternative, alternative
    presets = [e['preset'] for e in doc['setups'] if e['surface'] == used]
    if preset not in presets:
        raise SetupError(f'{doc["car"]}: no {preset} preset on {used} '
                         f'(it has {", ".join(presets)})')
    entry = next(e for e in doc['setups'] if e['surface'] == used and e['preset'] == preset)
    return entry, fallback


def path_for(slug, directory=None):
    return os.path.join(directory or SETUPS_DIR, slug + '.yaml')


def read_game_version(path=GAME_VERSION_FILE):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read().strip()
    except OSError as exc:
        raise SetupError(f'cannot read GAME_VERSION: {exc}')


def main():
    use_utf8_output()
    args = sys.argv[1:]
    car = surface = listing = directory = None
    preset, flags = 'Balanced', set()
    takes_value = ('--car', '--surface', '--preset', '--list', '--dir')
    i = 0
    while i < len(args):
        a = args[i]
        if a in takes_value:
            if i + 1 >= len(args):
                fail(f'{a} requires a value\n{USAGE}', 2)
            value = args[i + 1]
            if a == '--car':
                car = value
            elif a == '--surface':
                surface = value
            elif a == '--preset':
                preset = value
            elif a == '--list':
                listing = value
            else:
                directory = value
            i += 2
            continue
        if a not in ('--pretty', '--game-version'):
            fail(f'unknown option {a}\n{USAGE}', 2)
        flags.add(a)
        i += 1

    indent = 2 if '--pretty' in flags else None

    if '--game-version' in flags:
        if car or surface or listing:
            fail(f'--game-version takes no other options\n{USAGE}', 2)
        try:
            print(read_game_version())
        except SetupError as exc:
            fail(str(exc))
        sys.exit(0)

    if listing is not None:
        if car or surface:
            fail(f'--list takes no --car or --surface\n{USAGE}', 2)
        try:
            doc = load_file(path_for(listing, directory))
        except SetupError as exc:
            fail(str(exc))
        print(json.dumps({'car': doc['car'], 'version': doc['version'],
                          'setups': [{'surface': e['surface'], 'preset': e['preset']}
                                     for e in doc['setups']]},
                         indent=indent, ensure_ascii=False))
        sys.exit(0)

    if not car or not surface:
        fail(USAGE, 2)
    # `--surface` is not checked against a list of names. A surface this car has no entry for is
    # a data question, not a usage error: `pick` answers it with the Snow -> Gravel fallback or
    # exits 1 naming the surfaces the file does have, which is the one error path the caller can
    # act on. Hard-coding three names here would turn a new surface in a game update into a
    # usage error from the wrong script.
    try:
        doc = load_file(path_for(car, directory))
        entry, fallback = pick(doc, surface, preset)
    except SetupError as exc:
        fail(str(exc))
    print(json.dumps({'car': doc['car'], 'version': doc['version'], 'surface': surface,
                      'preset': entry['preset'], 'fallback': fallback,
                      'values': entry['values']}, indent=indent, ensure_ascii=False))
    sys.exit(0)


if __name__ == '__main__':
    main()
