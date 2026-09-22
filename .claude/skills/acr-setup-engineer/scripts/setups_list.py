#!/usr/bin/env python3
"""The `Setup index` on a car's `Setups` page — write a line, read the lines back.

Each car's `Setups` page carries a plain list of links to the setups the skill saved, one line per
setup, newest at the top, under an H2 `Setup index`. On Claude's Free plan the code sandbox can't
reach api.notion.com, so the REST query that lists `Setups` rows can't run; the skill reads this
list instead, picks the few pages a build needs, and fetches those through the Notion connector
(`references/setups-list-read.md`). This script owns the line format — nothing writes or parses a
line by hand.

Line (six fields, ` - ` separator, blank field `-`), optionally a seventh the user adds by hand:

  - [Name](url) - Source - Stage - Surface - Conditions - YYYY-MM-DD
  - [Name](url) - Source - Stage - Surface - Conditions - YYYY-MM-DD - learn: yes|no

Usage:
  python scripts/setups_list.py --line --name N --url U --source S --stage ST --surface SU --conditions C --date D
  python scripts/setups_list.py --pick page.md --stage ST --surface SU --conditions C [--limit 6] [--names A B …]
  python scripts/setups_list.py --find NAME page.md
  python scripts/setups_list.py --overrides page.md
Exit codes: 0 ok · 1 a value can't be written as a line (--line) · 2 bad usage.
"""
import argparse
import json
import re
import sys

SEP = ' - '
BLANK = '-'
HEADING = 'Setup index'
FIELDS = ('source', 'stage', 'surface', 'conditions', 'date')
LINE_RE = re.compile(r'^\s*[-*]\s+\[(?P<name>[^\]]+)\]\((?P<url>[^)\s]+)\)\s+-\s+(?P<rest>.*\S)\s*$')
BULLET_RE = re.compile(r'^\s*[-*]\s+\S')
HEADING_RE = re.compile(r'^\s*#{1,6}\s*' + re.escape(HEADING) + r'\s*$', re.I)
LEARN_RE = re.compile(r'^learn:\s*(yes|no)$', re.I)


def format_line(name, url, source, stage, surface, conditions, date):
    """One index line, six fields. Raises ValueError when a value could not be parsed back."""
    values = {'name': name, 'source': source, 'stage': stage, 'surface': surface,
              'conditions': conditions}
    for label, value in values.items():
        if SEP in (value or ''):
            raise ValueError(f'{label} contains {SEP!r}: {value!r}')
    if ']' in name or not name.strip():
        raise ValueError(f'name cannot be written as a link: {name!r}')
    if ')' in url or not url.strip():
        raise ValueError(f'url cannot be written as a link: {url!r}')
    if any(c.isspace() for c in url.strip()):
        raise ValueError(f'url cannot contain whitespace: {url!r}')
    stage = (stage or '').strip() or BLANK
    conditions = (conditions or '').strip() or BLANK
    date = (date or '').strip()[:10]
    return f'- [{name.strip()}]({url.strip()}){SEP}{source.strip()}{SEP}{stage}{SEP}{surface.strip()}{SEP}{conditions}{SEP}{date}'


def parse_line(text):
    """The dict for one index line, or None when the line isn't one."""
    m = LINE_RE.match(text)
    if not m:
        return None
    parts = [p.strip() for p in m.group('rest').split(SEP)]
    if len(parts) not in (5, 6):
        return None
    entry = dict(zip(FIELDS, parts[:5]))
    entry['learn'] = None
    if len(parts) == 6:
        lm = LEARN_RE.match(parts[5])
        if not lm:
            return None
        entry['learn'] = lm.group(1).lower()
    for key in ('stage', 'conditions'):
        if entry[key] == BLANK:
            entry[key] = ''
    entry['name'] = m.group('name').strip()
    entry['url'] = m.group('url')
    return entry


def parse_text(text):
    """(entries, malformed): every index line after the `Setup index` heading (or in the whole
    text when there is no heading), and the count of bullet lines that didn't parse."""
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if HEADING_RE.match(line):
            start = i + 1
            break
    entries, malformed = [], 0
    for line in lines[start:]:
        if not BULLET_RE.match(line):
            continue
        entry = parse_line(line)
        if entry is None:
            malformed += 1
        else:
            entries.append(entry)
    return entries, malformed


def find(entries, name):
    """Lines matching a setup name: exact, else case-insensitive, else substring."""
    wanted = name.strip()
    exact = [e for e in entries if e['name'] == wanted]
    if exact:
        return exact
    ci = [e for e in entries if e['name'].lower() == wanted.lower()]
    if ci:
        return ci
    return [e for e in entries if wanted.lower() in e['name'].lower()]


def _norm(value):
    return (value or '').strip().lower()


def _context_matches(entry, stage, surface, conditions):
    return (_norm(entry['stage']) == _norm(stage)
            and _norm(entry['surface']) == _norm(surface)
            and _norm(entry['conditions']) == _norm(conditions))


def _newest_first(entries):
    return sorted(entries, key=lambda e: e['date'], reverse=True)


def pick(entries, stage, surface, conditions, limit, names, malformed):
    """What a build fetches on Free: the matching default, the other defaults, the learn
    candidates (forced `learn: yes` first, then same stage, same surface, newest), a skipped count."""
    defaults = [e for e in entries if _norm(e['source']) == 'default']
    matching = [e for e in defaults if _context_matches(e, stage, surface, conditions)]
    default = _newest_first(matching)[0] if matching else None
    other_defaults = _newest_first([e for e in defaults if e is not default])
    pool = [e for e in entries if _norm(e['source']) != 'default']
    out = {'default': default, 'other_defaults': other_defaults, 'malformed': malformed}

    if names:
        learn, not_found = [], []
        for wanted in names:
            hits = find(pool, wanted)
            if hits:
                learn.extend(h for h in hits if h not in learn)
            else:
                not_found.append(wanted)
        out.update(learn=learn, skipped=0, not_found=not_found)
        return out

    forced = _newest_first([e for e in pool if e['learn'] == 'yes'])
    candidates = [e for e in pool if e['learn'] is None]
    candidates.sort(key=lambda e: (_norm(e['stage']) == _norm(stage),
                                   _norm(e['surface']) == _norm(surface),
                                   e['date']), reverse=True)
    limit = max(0, limit)
    out.update(learn=forced + candidates[:limit], skipped=max(0, len(candidates) - limit))
    return out


def overrides(entries, malformed):
    """The names the user marked by hand: `learn: yes` and `learn: no`."""
    return {'yes': [e['name'] for e in entries if e['learn'] == 'yes'],
            'no': [e['name'] for e in entries if e['learn'] == 'no'],
            'malformed': malformed}


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Write or read `Setup index` lines.')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--line', action='store_true', help='print one formatted line')
    mode.add_argument('--pick', metavar='FILE', help='pick the default and learn candidates')
    mode.add_argument('--find', nargs=2, metavar=('NAME', 'FILE'), help='lines matching a name')
    mode.add_argument('--overrides', metavar='FILE', help='names with learn: yes / learn: no')
    ap.add_argument('--name')
    ap.add_argument('--url')
    ap.add_argument('--source')
    ap.add_argument('--stage', default='')
    ap.add_argument('--surface', default='')
    ap.add_argument('--conditions', default='')
    ap.add_argument('--date')
    ap.add_argument('--limit', type=int, default=6)
    ap.add_argument('--names', nargs='+')
    args = ap.parse_args(argv)

    if args.line:
        missing = [k for k in ('name', 'url', 'source', 'surface', 'date') if not getattr(args, k)]
        if missing:
            ap.error('--line needs ' + ', '.join('--' + k for k in missing))
        try:
            print(format_line(args.name, args.url, args.source, args.stage, args.surface,
                              args.conditions, args.date))
        except ValueError as exc:
            sys.stderr.write(f'setups_list: {exc}\n')
            return 1
        return 0

    if args.find:
        name, path = args.find
        entries, malformed = parse_text(_read(path))
        _emit({'matches': find(entries, name), 'malformed': malformed})
        return 0

    if args.pick:
        entries, malformed = parse_text(_read(args.pick))
        _emit(pick(entries, args.stage, args.surface, args.conditions, args.limit, args.names,
                   malformed))
        return 0

    entries, malformed = parse_text(_read(args.overrides))
    _emit(overrides(entries, malformed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
