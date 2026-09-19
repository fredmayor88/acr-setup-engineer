#!/usr/bin/env python3
"""Read a bundled car template and print its parameter catalog.

For a **template car** (one that has a file in `car-templates/`), the template inside the
skill IS the parameter catalog: there are no `Parameters` rows in Notion to read. This script
is what every read workflow runs in place of the REST query in
`references/notion-rest-read.md` — no token, no network, works on every plan.

The rows it prints have **exactly** the shape that doc's *Output* section describes, so every
downstream rule (surface resolution, value legality, SHOW order) consumes them unchanged.

Usage:
  # The whole catalog — baseline rows and surface rows, as a JSON array:
  python scripts/load_catalog.py car-templates/<car>.yaml

  # One row per Adjustment, resolved for a surface (adds "Resolved from"):
  python scripts/load_catalog.py car-templates/<car>.yaml --surface Gravel

  # Validate values against the catalog (exit 3 when something is illegal):
  python scripts/load_catalog.py car-templates/<car>.yaml --check values.json [--surface Snow]

  # The `Catalog snapshot` YAML body for the car's Notion Catalog page:
  python scripts/load_catalog.py car-templates/<car>.yaml --snapshot

  # Human-readable listing (header fields + one line per row):
  python scripts/load_catalog.py car-templates/<car>.yaml --pretty

Options:
  --surface S    Tarmac | Gravel | Snow. Resolve each Adjustment to the single row that
                 applies on surface S, per notion-rest-read.md -> "Resolving the range for a
                 surface" (the S row, else a Gravel row when S is Snow, else the baseline
                 row). Each output row gains "Resolved from": the surface whose row was used,
                 or "baseline". Without it, every row is printed.
  --check FILE   FILE is JSON: {"<Adjustment>": <value>, ...}. Each value is checked against
                 its row for --surface, or against its baseline row when no --surface is
                 given: it must be one of the `Discrete steps` when the row has them, else
                 inside the numeric Min..Max. Prints
                 {"ok": [...], "problems": [...]}. A collapsed compound gear value
                 (`35//3033//28`, asterisks eaten by markdown) is repaired against the steps
                 and reported with "repaired": true (SKILL.md -> Compound gear values).
  --snapshot     Print the `Catalog snapshot` YAML body (notion-structure.md ->
                 *Catalog snapshot*), with today's date and the skill version resolved
                 per SKILL.md -> *Skill version* (the bundled VERSION file; for the
                 literal `dev`, `git describe --tags --always --dirty` in the skill's
                 repo, else `dev`).
  --pretty       One line per row, for a human reading the output.

Exit codes: 0 success, 1 file/parse error, 2 usage error, 3 --check found problems.
stdlib only (the code sandbox has no PyYAML). Output is always UTF-8, whatever the
console locale is — the catalog carries `—` and `°`.
"""
import datetime
import json
import os
import re
import subprocess
import sys

SURFACES = ('Tarmac', 'Gravel', 'Snow')

# Flags taking no value. `--surface` and `--check` take one and are parsed separately.
FLAGS = ('--snapshot', '--pretty')

# Template header fields this script reads. Everything else (engine_curve, save_ids, …) is
# ignored: only top-level, column-0 keys count, so the indented keys inside engine_curve
# (which include its own `source:`) can never be mistaken for header fields.
HEADER_FIELDS = ('car', 'version', 'source', 'drivetrain', 'gearing_tool')

# template parameter key -> the key name the REST read uses for it
PARAM_KEYS = {
    'section': 'Section',
    'adjustment': 'Adjustment',
    'order': 'Order',
    'min': 'Min',
    'max': 'Max',
    'unit': 'Unit',
    'discrete_steps': 'Discrete steps',
    'surface': 'Surface',
}

# Key order inside a snapshot row (notion-structure.md -> Catalog snapshot).
SNAPSHOT_KEYS = ('Adjustment', 'Section', 'Surface', 'Min', 'Max', 'Unit',
                 'Discrete steps', 'Order')

# These snapshot values are always quoted, so a `*` in a compound gear value and a bare `—`
# both survive the round trip through markdown and YAML.
ALWAYS_QUOTED = ('Unit', 'Discrete steps')


def use_utf8_output():
    """Print UTF-8 whatever the console's locale is.

    The catalog is full of non-ASCII: `—` for a named-selection Min/Max, `°` in a unit. With
    stdout piped — how the skill always runs this script — Python on Windows would otherwise
    encode it with the ANSI code page, and the reader (the `Catalog snapshot`, the chat
    transcript) decodes it as UTF-8 and gets mojibake. Guarded because stdout may be a plain
    object with no `reconfigure` (a test capturing output, an embedded runner).
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


def scalar(text):
    """Return a value parsed from a template: a number when it looks like one, else a string."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def load_template(path):
    """Return (header, rows) read from a bundled template YAML.

    Deliberately minimal, stdlib-only parsing of the flat, export-enforced template shape
    (references/export-car-template.md), extending the same approach as
    query_notion_parameters.py's read_template_rows. Header keys are taken only from column 0;
    parameter items are collected from the `parameters:` list.
    """
    header, rows, cur, in_params = {}, [], None, False
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError as exc:
        fail(f'cannot read template: {exc}')

    for line in lines:
        stripped = line.strip()
        if not in_params:
            if stripped == 'parameters:':
                in_params = True
                continue
            if line[:1].strip():                          # a top-level key, column 0
                m = re.match(r'([a-z_]+):\s*(.*)$', stripped)
                if m and m.group(1) in HEADER_FIELDS and m.group(2):
                    header[m.group(1)] = m.group(2).strip().strip('"\'')
            continue
        if line[:1].strip() and not stripped.startswith('-'):
            break                                         # next top-level key ends the block
        if stripped.startswith('- '):
            if cur and cur.get('Adjustment'):
                rows.append(cur)
            cur = {}
            stripped = stripped[2:].strip()
        if cur is None:
            continue
        m = re.match(r'([a-z_]+):\s*(.*)$', stripped)
        if not m:
            continue
        key = PARAM_KEYS.get(m.group(1))
        if key is None:
            continue
        raw = m.group(2).strip()
        quoted = len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in '"\''
        value = raw[1:-1] if quoted else raw
        if key == 'Order':
            try:
                cur[key] = int(value)
            except ValueError:
                pass
        elif key in ('Min', 'Max') and not quoted:
            cur[key] = scalar(value)
        else:
            cur[key] = value
    if cur and cur.get('Adjustment'):
        rows.append(cur)

    if not rows:
        fail(f'no parameters found in {path}')
    return header, rows


def build_rows(header, raw_rows):
    """Turn parsed template entries into REST-read-shaped rows."""
    car = header.get('car', '')
    rows = []
    for raw in raw_rows:
        row = {
            'Adjustment': raw.get('Adjustment', ''),
            'Section': raw.get('Section', ''),
            'Min': raw.get('Min', '—'),
            'Max': raw.get('Max', '—'),
            'Unit': raw.get('Unit', ''),
            'Discrete steps': raw.get('Discrete steps', ''),
            'Order': raw.get('Order'),
            'Car': car,
        }
        if raw.get('Surface'):
            row['Surface'] = raw['Surface']
        rows.append(row)
    return rows


def resolve_for_surface(rows, surface):
    """One row per Adjustment, resolved for `surface`, each carrying "Resolved from".

    The rule is notion-rest-read.md -> *Resolving the range for a surface*: the row tagged
    with that surface, else a Gravel row when the surface is Snow, else the baseline row.
    """
    by_adjustment = {}
    for row in rows:
        by_adjustment.setdefault(row['Adjustment'], []).append(row)

    resolved = []
    for adjustment, candidates in by_adjustment.items():
        tagged = {c.get('Surface'): c for c in candidates}
        for source in (surface, 'Gravel' if surface == 'Snow' else None, None):
            if source in tagged:
                picked = dict(tagged[source])
                picked['Resolved from'] = source or 'baseline'
                resolved.append(picked)
                break
    return resolved


def steps_of(row):
    """The row's Discrete steps as a list (empty when the cell is blank)."""
    raw = row.get('Discrete steps') or ''
    return [s.strip() for s in raw.split(',') if s.strip()]


def as_text(value):
    """Spell a value the way the catalog spells it, so it can be compared to a step."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def repair_compound_gear(value, steps):
    """Restore the `*` markdown ate from a compound gear value (`35//3033//28`).

    Returns the matching catalog step, or None when the value isn't a collapsed compound or
    doesn't match exactly one step (SKILL.md -> Compound gear values: ask, never guess).
    """
    if not isinstance(value, str) or '*' in value or value.count('//') < 2:
        return None
    matches = [s for s in steps if s.replace('*', '') == value]
    return matches[0] if len(matches) == 1 else None


def check_values(rows, values, surface):
    """Validate {Adjustment: value} against the catalog resolved for `surface`.

    With no `surface`, each Adjustment is checked against its **baseline** row (the one with
    no `Surface`) — a surface-tagged row never wins by default, because nothing has said which
    surface the values are for.
    """
    if surface is None:
        catalog = {r['Adjustment']: r for r in rows if not r.get('Surface')}
    else:
        catalog = {r['Adjustment']: r for r in resolve_for_surface(rows, surface)}
    ok, problems = [], []

    for adjustment, value in values.items():
        row = catalog.get(adjustment)
        if row is None:
            problems.append({'Adjustment': adjustment, 'value': value,
                             'reason': 'not in catalog', 'legal': None})
            continue

        entry = {'Adjustment': adjustment, 'value': value}
        steps = steps_of(row)
        if steps:
            repaired = repair_compound_gear(value, steps)
            if repaired is not None:
                entry['value'] = value = repaired
                entry['repaired'] = True
            if as_text(value) in steps:
                ok.append(entry)
            else:
                entry.update(reason='not one of the discrete steps', legal=steps)
                problems.append(entry)
            continue

        lo, hi = row.get('Min'), row.get('Max')
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            entry.update(reason='range unknown', legal=None)
            problems.append(entry)
        elif not isinstance(value, (int, float)) or isinstance(value, bool):
            entry.update(reason='not a number, but the catalog row is a numeric range',
                         legal=[lo, hi])
            problems.append(entry)
        elif lo <= value <= hi:
            ok.append(entry)
        else:
            entry.update(reason='outside Min..Max', legal=[lo, hi])
            problems.append(entry)

    return {'ok': ok, 'problems': problems}


def git_describe(root):
    """`git describe --tags --always --dirty` run in `root`, or None when git can't answer.

    Never raises and never returns a git error message: no git on PATH, `root` outside a
    checkout, or a non-zero exit all give None.
    """
    try:
        proc = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'],
                              cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or '').strip()
    return out if proc.returncode == 0 and out else None


def skill_version(root=None):
    """The skill's own version, per SKILL.md -> *Skill version*.

    The bundled VERSION file beside the scripts folder decides it. The literal `dev` means an
    unreleased source checkout: describe it from git instead, and fall back to `dev` when git
    can't answer.
    """
    root = root or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    try:
        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as fh:
            version = fh.read().strip()
    except OSError:
        version = ''
    if version and version != 'dev':
        return version
    return git_describe(root) or 'dev'


def yaml_scalar(key, value):
    """Render one snapshot value: quoted where the snapshot format requires it."""
    if isinstance(value, bool) or value is None:
        return 'null'
    if isinstance(value, (int, float)) and key not in ALWAYS_QUOTED:
        return str(value)
    text = str(value)
    if key in ALWAYS_QUOTED or not re.match(r'^[A-Za-z0-9][\w \-/.()%°]*$', text):
        return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return text


def snapshot(header, rows):
    """The `Catalog snapshot` YAML body (notion-structure.md -> Catalog snapshot)."""
    today = datetime.date.today().isoformat()
    out = [
        f'car: {yaml_scalar("car", header.get("car", ""))}',
        f'written_at: {today}',
        f'skill_version: {skill_version()}',
        f'source: bundled template v{header.get("version", "unknown")}',
        f'row_count: {len(rows)}',
        'rows:',
    ]
    for row in rows:
        first = True
        for key in SNAPSHOT_KEYS:
            if key not in row or row[key] is None:
                continue
            lead = '  - ' if first else '    '
            out.append(f'{lead}{key}: {yaml_scalar(key, row[key])}')
            first = False
    return '\n'.join(out)


def pretty(header, rows):
    out = [f'{header.get("car", "?")} — {len(rows)} parameters']
    facts = [f'{name}: {header[name]}' for name in HEADER_FIELDS
             if name != 'car' and header.get(name)]
    if facts:
        out.append('  ' + ' | '.join(facts))
    for row in rows:
        bits = f'{row["Min"]}..{row["Max"]}'
        if row.get('Unit'):
            bits += f' {row["Unit"]}'
        if row.get('Discrete steps'):
            bits += f'  steps: {row["Discrete steps"]}'
        tags = ''
        if row.get('Surface'):
            tags += f' ({row["Surface"]})'
        if row.get('Resolved from'):
            tags += f' [resolved from {row["Resolved from"]}]'
        out.append(f'  {row["Order"]} {row["Adjustment"]}{tags} [{row["Section"]}]: {bits}')
    return '\n'.join(out)


USAGE = ('usage: load_catalog.py <template.yaml> [--surface Tarmac|Gravel|Snow]\n'
         '                       [--check values.json] [--snapshot] [--pretty]')


def main():
    use_utf8_output()
    args = sys.argv[1:]
    positional, flags, surface, check_path = [], set(), None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('--surface', '--check'):
            if i + 1 >= len(args):
                fail(f'{a} requires a value\n{USAGE}', 2)
            if a == '--surface':
                surface = args[i + 1]
            else:
                check_path = args[i + 1]
            i += 2
            continue
        if a.startswith('--'):
            if a not in FLAGS:
                fail(f'unknown option {a}\n{USAGE}', 2)
            flags.add(a)
        else:
            positional.append(a)
        i += 1

    if len(positional) != 1:
        fail(USAGE, 2)
    if surface is not None and surface not in SURFACES:
        fail(f'--surface must be one of {", ".join(SURFACES)}\n{USAGE}', 2)

    header, raw_rows = load_template(positional[0])
    rows = build_rows(header, raw_rows)

    if check_path is not None:
        try:
            with open(check_path, encoding='utf-8') as fh:
                values = json.load(fh)
        except OSError as exc:
            fail(f'cannot read values file: {exc}')
        except json.JSONDecodeError as exc:
            fail(f'values file is not valid JSON: {exc}')
        if not isinstance(values, dict):
            fail('values file must be a JSON object {"<Adjustment>": <value>, ...}', 2)
        report = check_values(rows, values, surface)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(3 if report['problems'] else 0)

    if '--snapshot' in flags:
        print(snapshot(header, rows))
        sys.exit(0)

    if surface is not None:
        rows = resolve_for_surface(rows, surface)

    print(pretty(header, rows) if '--pretty' in flags
          else json.dumps(rows, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == '__main__':
    main()
