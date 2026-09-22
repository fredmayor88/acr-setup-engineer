# Setup index for the Free plan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every car a `Setup index` section on its `Setups` page (a plain list of links to the setups the skill saved) so that on Claude's Free plan, where the REST query can't run, a build still finds its stored game default and the user's `Learn from this` setups by fetching a few pages through the connector.

**Architecture:** A stdlib script `scripts/setups_list.py` owns the line format (writes it, parses it, picks candidates, finds by name, lists overrides). Four workflows write one line per saved row; a new reference `setups-list-read.md` is the only Free-plan read path for `Setups`; `notion-rest-read.md` → *Offline mode* routes there instead of "empty". Reads on paid plans stay on REST, except that the `learn:` override on a line is honoured everywhere.

**Tech Stack:** Markdown references executed by an LLM; Python 3 stdlib scripts (no PyYAML); `unittest` (`python -m unittest discover -s tests`, run from the repo root).

**Spec:** `docs/superpowers/specs/2026-09-22-setups-list-for-free-plan-design.md`

## Global Constraints

- Scripts are **stdlib only**; unknown flags **exit 2**; every script runs from the skill directory (`.claude/skills/acr-setup-engineer`) as `python scripts/<name>.py`.
- The section heading is exactly **`Setup index`** (an H2 in Notion).
- Line shape, six or seven fields, separator ` - ` (hyphen with one space each side), blank field `-`:
  `- [{Name}]({page url}) - {Source} - {Stage} - {Surface} - {Conditions} - {YYYY-MM-DD}` optionally followed by ` - learn: yes` or ` - learn: no`.
- The skill **never writes the `learn:` field** and **never hand-formats a line**: lines come from `setups_list.py --line`.
- The section is **add-only, newest at the top**. No refresh, re-onboard or save ever rewrites or removes it. A save never creates the `Setups` page.
- On Free (`egress: none`) the default candidate cap is **6** learn lines; `learn: yes` lines come first and don't count against the cap; `learn: no` lines are never fetched for learning.
- Writing rule from `CLAUDE.md`: every workflow step must be followable by a less capable model — one action per step, exact phrases where the user copies them, no judgement calls where a script can decide.
- Commit after each task with a short factual message; never push. Attribution line per the session's reminder.
- Run the full suite before each commit: `python -m unittest discover -s tests` (from `C:\Users\fred\w\acr-setup-engineer`). It must stay green.

---

## File structure

| File | Responsibility |
| --- | --- |
| Create `.claude/skills/acr-setup-engineer/scripts/setups_list.py` | Line format: `--line` (format), `--pick` (candidates), `--find` (by name), `--overrides` (learn: yes/no names). Pure functions + CLI. |
| Create `tests/test_setups_list.py` | Unit + CLI tests for the script. |
| Create `.claude/skills/acr-setup-engineer/references/setups-list-read.md` | The Free-plan read path for `Setups`, "load more", named-setup lookup, adding a setup by pasted link. |
| Modify `references/notion-structure.md` | `Setups` page shape; new *Adding a line to `Setup index`* section; refresh never touches it. |
| Modify `references/onboard-car.md`, `references/refresh-notion.md` | Refresh rule: `Setup index` is never written or removed. |
| Modify `references/build-setup.md`, `tweak-setup.md`, `capture-setup.md`, `import-savegame.md` | Add the line after the row write; build steps 4 and 7 name the Free path. |
| Modify `references/notion-rest-read.md` | Offline mode routes `Setups` slices to `setups-list-read.md`; new once-per-chat text; paid-plan `--overrides` step. |
| Modify `references/review-setup.md`, `ask-setups.md`, `share-setup.md`, `tweak-setup.md` | List-first lookup by name on Free. |
| Modify `references/free-plan-template.md`, `how-to-use-template.md`, `README.md`, `SKILL.md`, `CLAUDE.md` | User-facing and maintainer text. |
| Modify `tests/test_references.py`, `tests/test_notion_docs_pages.py` | Guards. |

---

### Task 1: `setups_list.py` — format and parse one line, `--find`

**Files:**
- Create: `.claude/skills/acr-setup-engineer/scripts/setups_list.py`
- Create: `tests/test_setups_list.py`

**Interfaces:**
- Produces: `format_line(name, url, source, stage, surface, conditions, date) -> str` (raises `ValueError` when a value contains ` - ` or `name` contains `]`); `parse_line(text) -> dict | None` with keys `name, url, source, stage, surface, conditions, date, learn` (`learn` is `'yes'`, `'no'` or `None`; blank stage/conditions are `''`); `parse_text(text) -> (entries: list[dict], malformed: int)`; `find(entries, name) -> list[dict]`. CLI: `--line …`, `--find NAME FILE`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setups_list.py`:

```python
"""Validate scripts/setups_list.py — the `Setup index` line format on a car's `Setups` page.

The skill writes one line per setup it saves; on Claude's Free plan it reads the lines back to know
which setup pages to fetch. The line is `- [Name](url) - Source - Stage - Surface - Conditions -
YYYY-MM-DD`, optionally `- learn: yes|no` added by the user. Nothing parses a line by eye.

Run: python -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRIPTS = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer', 'scripts')
SCRIPT = os.path.join(SCRIPTS, 'setups_list.py')
sys.path.insert(0, SCRIPTS)

import setups_list  # noqa: E402

URL = 'https://www.notion.so/3dd9abc6c7738173bc65c954d9d85ece'

PAGE = """*Kept up to date by the skill, but your own edits to these setups are never overwritten.*
<database url="https://app.notion.com/p/x" inline="true" data-source-url="collection://y"></database>

## Setup index

- [newest](https://www.notion.so/a1) - generated - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-20
- [forced](https://www.notion.so/a2) - screenshot - Saverne - Tarmac - Wet - 2026-09-01 - learn: yes
- [skipme](https://www.notion.so/a3) - generated - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-19 - learn: no
- [same surface](https://www.notion.so/a4) - imported - Saverne - Tarmac - - - 2026-09-18
- [other surface](https://www.notion.so/a5) - generated - Greece - Gravel - Dry - 2026-09-21
- [monte](https://www.notion.so/a6) - generated - Monte-Carlo - Tarmac - Dry - 2026-09-10
- [turini def](https://www.notion.so/d1) - default - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-12
- [saverne def](https://www.notion.so/d2) - default - Saverne - Tarmac - - - 2026-09-15
- [broken](https://www.notion.so/b1) - generated - Col de Turini (Uphill) - Tarmac
- not a setup line at all
"""


def run(*args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True,
                          input=stdin, encoding='utf-8')


def write(text):
    fd, path = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


class TestFormatLine(unittest.TestCase):
    def test_full_line(self):
        line = setups_list.format_line('MC-ilDrago-0.6-v2', URL, 'screenshot',
                                       'Col de Turini (Uphill)', 'Tarmac', 'Dry',
                                       '2026-09-16T12:47:00.000Z')
        self.assertEqual(line, f'- [MC-ilDrago-0.6-v2]({URL}) - screenshot - Col de Turini (Uphill)'
                               ' - Tarmac - Dry - 2026-09-16')

    def test_blank_stage_and_conditions_become_hyphen(self):
        line = setups_list.format_line('x', URL, 'imported', '', 'Gravel', '   ', '2026-09-16')
        self.assertTrue(line.endswith(' - imported - - - Gravel - - - 2026-09-16'))

    def test_never_writes_learn_field(self):
        line = setups_list.format_line('x', URL, 'generated', 'S', 'Tarmac', 'Dry', '2026-09-16')
        self.assertNotIn('learn:', line)

    def test_value_with_separator_is_refused(self):
        with self.assertRaises(ValueError):
            setups_list.format_line('a - b', URL, 'generated', 'S', 'Tarmac', 'Dry', '2026-09-16')
        with self.assertRaises(ValueError):
            setups_list.format_line('a', URL, 'generated', 'Saverne - up', 'Tarmac', 'Dry', '2026-09-16')

    def test_round_trip(self):
        line = setups_list.format_line('turini def', URL, 'default', 'Col de Turini (Uphill)',
                                       'Tarmac', '', '2026-09-12')
        entry = setups_list.parse_line(line)
        self.assertEqual(entry['name'], 'turini def')
        self.assertEqual(entry['url'], URL)
        self.assertEqual(entry['source'], 'default')
        self.assertEqual(entry['stage'], 'Col de Turini (Uphill)')
        self.assertEqual(entry['surface'], 'Tarmac')
        self.assertEqual(entry['conditions'], '')
        self.assertEqual(entry['date'], '2026-09-12')
        self.assertIsNone(entry['learn'])


class TestParse(unittest.TestCase):
    def test_learn_override_parsed(self):
        e = setups_list.parse_line('- [f](https://x/a) - screenshot - S - Tarmac - Wet - 2026-09-01 - learn: yes')
        self.assertEqual(e['learn'], 'yes')
        e = setups_list.parse_line('- [f](https://x/a) - screenshot - S - Tarmac - Wet - 2026-09-01 - Learn: NO')
        self.assertEqual(e['learn'], 'no')

    def test_plain_hyphen_inside_a_stage_name_is_fine(self):
        e = setups_list.parse_line('- [m](https://x/a) - generated - Monte-Carlo - Tarmac - Dry - 2026-09-10')
        self.assertEqual(e['stage'], 'Monte-Carlo')

    def test_malformed_lines(self):
        self.assertIsNone(setups_list.parse_line('- [b](https://x/a) - generated - S - Tarmac'))
        self.assertIsNone(setups_list.parse_line('- [b](https://x/a) - generated - S - Tarmac - Dry - 2026-09-10 - extra'))
        self.assertIsNone(setups_list.parse_line('- [b](https://x/a) - generated - S - Tarmac - Dry - 2026-09-10 - learn: maybe'))
        self.assertIsNone(setups_list.parse_line('- no link here - a - b - c - d - e'))
        self.assertIsNone(setups_list.parse_line('plain text'))

    def test_parse_text_starts_after_heading_and_counts_malformed(self):
        entries, malformed = setups_list.parse_text(PAGE)
        self.assertEqual([e['name'] for e in entries],
                         ['newest', 'forced', 'skipme', 'same surface', 'other surface', 'monte',
                          'turini def', 'saverne def'])
        self.assertEqual(malformed, 2)  # 'broken' and 'not a setup line at all' are bullets

    def test_parse_text_without_heading_parses_everything(self):
        entries, malformed = setups_list.parse_text(
            '- [a](https://x/a) - generated - S - Tarmac - Dry - 2026-09-10\n')
        self.assertEqual(len(entries), 1)
        self.assertEqual(malformed, 0)


class TestFind(unittest.TestCase):
    def setUp(self):
        self.entries, _ = setups_list.parse_text(PAGE)

    def test_exact_then_case_insensitive_then_substring(self):
        self.assertEqual([e['name'] for e in setups_list.find(self.entries, 'monte')], ['monte'])
        self.assertEqual([e['name'] for e in setups_list.find(self.entries, 'MONTE')], ['monte'])
        self.assertEqual([e['name'] for e in setups_list.find(self.entries, 'def')],
                         ['turini def', 'saverne def'])
        self.assertEqual(setups_list.find(self.entries, 'nothing like it'), [])


class TestCli(unittest.TestCase):
    def test_line_mode(self):
        r = run('--line', '--name', 'x', '--url', URL, '--source', 'generated', '--stage', '',
                '--surface', 'Tarmac', '--conditions', 'Dry', '--date', '2026-09-16T10:00:00Z')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), f'- [x]({URL}) - generated - - - Tarmac - Dry - 2026-09-16')

    def test_line_mode_refuses_separator_in_value(self):
        r = run('--line', '--name', 'a - b', '--url', URL, '--source', 'generated', '--stage', 'S',
                '--surface', 'Tarmac', '--conditions', 'Dry', '--date', '2026-09-16')
        self.assertEqual(r.returncode, 1)
        self.assertIn(' - ', r.stderr)

    def test_find_mode(self):
        path = write(PAGE)
        r = run('--find', 'monte', path)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual([e['name'] for e in out['matches']], ['monte'])
        self.assertEqual(out['malformed'], 2)

    def test_unknown_flag_exits_2(self):
        self.assertEqual(run('--bogus').returncode, 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from the repo root: `python -m unittest tests.test_setups_list -v`
Expected: `ModuleNotFoundError: No module named 'setups_list'`.

- [ ] **Step 3: Write the script (Task 1 scope: format, parse, find, CLI skeleton)**

Create `.claude/skills/acr-setup-engineer/scripts/setups_list.py`:

```python
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
```

`pick` and `overrides` are written in Task 2; for now add two stubs above `main` so the module imports:

```python
def pick(entries, stage, surface, conditions, limit, names, malformed):
    raise NotImplementedError


def overrides(entries, malformed):
    raise NotImplementedError
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_setups_list -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/scripts/setups_list.py tests/test_setups_list.py
git commit -m "setups_list.py: format, parse and find Setup index lines"
```

---

### Task 2: `setups_list.py` — `--pick` and `--overrides`

**Files:**
- Modify: `.claude/skills/acr-setup-engineer/scripts/setups_list.py` (replace the two stubs)
- Modify: `tests/test_setups_list.py`

**Interfaces:**
- Consumes: `parse_text`, entries dicts from Task 1.
- Produces: `pick(entries, stage, surface, conditions, limit, names, malformed) -> dict` with keys `default` (entry or `None`), `other_defaults` (list, newest first), `learn` (list), `skipped` (int), `malformed` (int), and `not_found` (list of names, only when `names` given); `overrides(entries, malformed) -> {'yes': [names], 'no': [names], 'malformed': int}`.

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_setups_list.py` before the `TestCli` class:

```python
class TestPick(unittest.TestCase):
    def setUp(self):
        self.entries, self.malformed = setups_list.parse_text(PAGE)

    def pick(self, **kw):
        base = dict(stage='Col de Turini (Uphill)', surface='Tarmac', conditions='Dry',
                    limit=6, names=None, malformed=self.malformed)
        base.update(kw)
        return setups_list.pick(self.entries, **base)

    def test_matching_default_and_other_defaults(self):
        out = self.pick()
        self.assertEqual(out['default']['name'], 'turini def')
        self.assertEqual([e['name'] for e in out['other_defaults']], ['saverne def'])

    def test_no_matching_default(self):
        out = self.pick(stage='Greece', surface='Gravel')
        self.assertIsNone(out['default'])
        self.assertEqual([e['name'] for e in out['other_defaults']], ['saverne def', 'turini def'])

    def test_blank_conditions_match_only_blank(self):
        out = self.pick(stage='Saverne', conditions='')
        self.assertEqual(out['default']['name'], 'saverne def')
        out = self.pick(stage='Saverne', conditions='Dry')
        self.assertIsNone(out['default'])

    def test_matching_is_case_insensitive_and_trimmed(self):
        out = self.pick(stage='  col de turini (uphill) ', surface='tarmac', conditions='DRY')
        self.assertEqual(out['default']['name'], 'turini def')

    def test_learn_order_forced_first_then_stage_then_surface_then_date(self):
        out = self.pick()
        self.assertEqual([e['name'] for e in out['learn']],
                         ['forced', 'newest', 'same surface', 'monte', 'other surface'])
        self.assertEqual(out['skipped'], 0)
        self.assertEqual(out['malformed'], 2)

    def test_learn_no_is_never_a_candidate(self):
        out = self.pick(limit=50)
        self.assertNotIn('skipme', [e['name'] for e in out['learn']])

    def test_limit_excludes_forced_and_counts_skipped(self):
        out = self.pick(limit=2)
        self.assertEqual([e['name'] for e in out['learn']], ['forced', 'newest', 'same surface'])
        self.assertEqual(out['skipped'], 2)  # monte, other surface

    def test_names_bypass_ordering_and_report_missing(self):
        out = self.pick(names=['skipme', 'Monte', 'ghost'])
        self.assertEqual([e['name'] for e in out['learn']], ['skipme', 'monte'])
        self.assertEqual(out['learn'][0]['learn'], 'no')
        self.assertEqual(out['not_found'], ['ghost'])
        self.assertEqual(out['skipped'], 0)

    def test_defaults_never_in_learn(self):
        out = self.pick(limit=50)
        self.assertFalse([e for e in out['learn'] if e['source'] == 'default'])


class TestOverrides(unittest.TestCase):
    def test_lists_yes_and_no(self):
        entries, malformed = setups_list.parse_text(PAGE)
        out = setups_list.overrides(entries, malformed)
        self.assertEqual(out, {'yes': ['forced'], 'no': ['skipme'], 'malformed': 2})
```

And inside `TestCli`:

```python
    def test_pick_mode(self):
        path = write(PAGE)
        r = run('--pick', path, '--stage', 'Col de Turini (Uphill)', '--surface', 'Tarmac',
                '--conditions', 'Dry', '--limit', '1')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['default']['name'], 'turini def')
        self.assertEqual([e['name'] for e in out['learn']], ['forced', 'newest'])
        self.assertEqual(out['skipped'], 3)

    def test_pick_mode_with_names(self):
        path = write(PAGE)
        r = run('--pick', path, '--stage', 'x', '--surface', 'Tarmac', '--names', 'monte', 'ghost')
        out = json.loads(r.stdout)
        self.assertEqual([e['name'] for e in out['learn']], ['monte'])
        self.assertEqual(out['not_found'], ['ghost'])

    def test_overrides_mode(self):
        path = write(PAGE)
        r = run('--overrides', path)
        self.assertEqual(json.loads(r.stdout)['yes'], ['forced'])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_setups_list -v`
Expected: the new tests fail with `NotImplementedError`.

- [ ] **Step 3: Replace the stubs**

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_setups_list -v`
Expected: all PASS. Then `python -m unittest discover -s tests` — whole suite green.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/scripts/setups_list.py tests/test_setups_list.py
git commit -m "setups_list.py: --pick candidates and --overrides"
```

---

### Task 3: Data model — the `Setup index` section in `notion-structure.md`, and the refresh rule

**Files:**
- Modify: `.claude/skills/acr-setup-engineer/references/notion-structure.md` (section `### \`Setups\` page`, around line 793; the `Car page` table row for `Setups`, around line 565)
- Modify: `.claude/skills/acr-setup-engineer/references/onboard-car.md` (refresh step 7 and *What a refresh never touches*, around lines 165–170; re-onboard step 5, around line 210)
- Modify: `.claude/skills/acr-setup-engineer/references/refresh-notion.md` (*What it never touches*, line 16)
- Modify: `tests/test_references.py`

**Interfaces:**
- Produces: the section name `notion-structure.md` → *Adding a line to `Setup index`* that Tasks 4 and 5 point at.

- [ ] **Step 1: Write the failing guard tests**

Add to `tests/test_references.py`, inside `TestNoRemovedMachinery` (or a new class `TestSetupIndex` in the same file):

```python
class TestSetupIndex(unittest.TestCase):
    def ref(self, name):
        return read(os.path.join(SKILL, 'references', name))

    def test_data_model_has_the_section(self):
        text = self.ref('notion-structure.md')
        self.assertIn('### Adding a line to `Setup index`', text)
        self.assertIn('setups_list.py --line', text)

    def test_refresh_docs_never_write_the_index(self):
        for name in ('onboard-car.md', 'refresh-notion.md'):
            self.assertIn('`Setup index`', self.ref(name), name)
            self.assertRegex(self.ref(name), r'`Setup index`[^\n]*never', name)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m unittest tests.test_references -v` — the two new tests FAIL.

- [ ] **Step 3: Rewrite the `Setups` page section in `notion-structure.md`**

Replace the current `### \`Setups\` page` section (the paragraph "Holds its maintenance line, then the … linked view and nothing else … per *Applying the order*.") with:

````markdown
### `Setups` page

Holds, in this order and nothing else:

1. its maintenance line (*Car page* table above);
2. the **`Setups[Car=this]` filtered linked view** (hide blank columns) — created with
   `notion-create-view` per *Creating an inline linked view*; the column order is set from
   `--show-order` on every write, per *Applying the order*;
3. an H2 heading **`Setup index`**, then one bulleted line per setup the skill saved for this car,
   **newest at the top**.

The maintenance line is worth having because the view is *live database rows*: the skill adds
setups, but anything the user changes in a row stays changed.

**`Setup index`** is the list of links the skill uses to find this car's setups **without the REST
query** (on Claude's Free plan — `setups-list-read.md`). Each line is written by
`scripts/setups_list.py --line` and has exactly this shape (the separator is a hyphen with one
space on each side; a blank field is `-`):

```
- [{Name}]({page url}) - {Source} - {Stage} - {Surface} - {Conditions} - {YYYY-MM-DD}
```

Example: `- [turini dry def](https://www.notion.so/3a89abc6c7738129ba47e0d23b52b4c9) - default - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-12`

- The six fields are facts that never change after the save. `Rating`, `Notes` and `Learn from
  this` are **not** on the line — they are read live from the setup page, because the user sets
  them later.
- **The `learn:` override.** The user may add a seventh field by hand, ` - learn: yes` or
  ` - learn: no`, on any plan. `learn: yes` makes the setup learn material whatever its checkbox
  says, and it is read ahead of every other candidate; `learn: no` means the setup is never read
  for learning. **The skill never writes this field.** How it is honoured: `setups-list-read.md`
  (Free) and `notion-rest-read.md` → *The `learn:` override on paid plans*.
- **Add-only, newest first.** A new line goes directly under the heading. The skill never edits,
  reorders or removes a line, and never rewrites the section. A deleted setup keeps its line; the
  reader skips a page that can't be fetched and says so.
- **A refresh, a re-onboard and a save never write, rewrite or remove this section.** The only
  writes are the one-line inserts in *Adding a line to `Setup index`* below. The section starts
  when the first line is added — a save creates the heading when it is missing; a refresh never
  does.

### Adding a line to `Setup index`

Every workflow that creates a `Setups` row does this **right after the row is created, on every
plan** — `build-setup.md` (the built setup, and a captured game default), `tweak-setup.md`,
`capture-setup.md`, `import-savegame.md`:

1. Take the new row's page URL from the create call's result.
2. Build the line — never by hand:
   ```
   python scripts/setups_list.py --line --name "{Name}" --url "{page url}" --source {Source} --stage "{Stage}" --surface {Surface} --conditions "{Conditions}" --date "{Date}"
   ```
   Pass a blank `--stage` / `--conditions` when the row's is blank; pass the row's `Date` as
   written (the script keeps its first 10 characters). If the script exits 1, print its message
   and skip the line — the row is saved, only the index line is missing; say so in one sentence.
3. Fetch the car's `Setups` page (it was fetched already when the column order was asserted —
   reuse it).
   - **It has a `Setup index` heading** → insert the line **directly under the heading**, above
     the first existing line (`notion-update-page`, insert after the heading block).
   - **It has none** → append, at the bottom of the page, the H2 `Setup index` and then the line.
   - **The car has no `Setups` page** (a car from an old layout that was never refreshed) → don't
     create it. Say once: *"The {Car} has no `Setups` page yet, so this setup isn't in its index.
     Say 'refresh the {Car} in my Notion' once and new setups will be listed."*
4. Several rows in one call (an import) → **one insert** holding all the lines, newest first.

**Adding a setup the user points at** (a pasted Notion link) is in `setups-list-read.md` →
*Adding a setup by link*.
````

Also update the `Car page` table row for `Setups` (around line 565) from `Holds the \`Setups[Car=this]\` filtered linked view` to `Holds the \`Setups[Car=this]\` filtered linked view, then the \`Setup index\` list`.

- [ ] **Step 4: State the refresh rule in `onboard-car.md` and `refresh-notion.md`**

In `onboard-car.md`, the paragraph beginning `**What a refresh never touches:**` (around line 169) becomes:

```markdown
**What a refresh never touches:** the content of the `Guidelines` page, the content of the `Log`
page, `Setups` rows (append-only, as always), and the **`Setup index`** section on the car's
`Setups` page — a refresh recreates the linked view only when it is missing and never writes,
rewrites or removes the index (`notion-structure.md` → *`Setups` page*).
```

In `onboard-car.md` re-onboard step 5 (around line 210), after "the linked view is recreated on the `Setups` page", add the sentence: `The \`Setup index\` section on that page is left exactly as it is — never rewritten, never removed.`

In `refresh-notion.md`, *What it never touches* (line 16) becomes:

```markdown
## What it never touches
The content of `Config`, `Tuning guidelines`, any car's `Guidelines`, the user's notes and the
skill's entries on any car's `Log`, every `Setups` row, and every car's `Setup index` (the list
under the view on its `Setups` page — never written, rewritten or removed by a refresh). Same
rules as the per-car refresh — this workflow only runs it for every car.
```

- [ ] **Step 5: Run the suite**

Run: `python -m unittest discover -s tests` — green (the two new guards pass; `test_banned_phrases` still passes: check the new text contains none of the banned phrases — it doesn't).

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/notion-structure.md .claude/skills/acr-setup-engineer/references/onboard-car.md .claude/skills/acr-setup-engineer/references/refresh-notion.md tests/test_references.py
git commit -m "Data model: Setup index section on the car's Setups page"
```

---

### Task 4: The savers write the line — build, tweak, capture, import

**Files:**
- Modify: `references/build-setup.md` (step 5 — the default capture write; step 11 — the built row, after the "Apply the column order" bullet)
- Modify: `references/tweak-setup.md` (the save step, after the `Create one new row` bullet block, around line 200)
- Modify: `references/capture-setup.md` (after step 7 "Assert the column order", around line 122)
- Modify: `references/import-savegame.md` (after step 5.5's row list, around line 296)
- Modify: `tests/test_references.py`

**Interfaces:**
- Consumes: `notion-structure.md` → *Adding a line to `Setup index`* (Task 3).

- [ ] **Step 1: Write the failing guard test**

Add to `TestSetupIndex` in `tests/test_references.py`:

```python
    def test_every_saver_adds_an_index_line(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md', 'import-savegame.md'):
            text = self.ref(name)
            self.assertIn('Adding a line to `Setup index`', text, name)

    def test_build_indexes_the_default_too(self):
        text = self.ref('build-setup.md')
        self.assertEqual(text.count('Adding a line to `Setup index`'), 2,
                         'build-setup must add a line for the built setup AND for a captured default')
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_references -v` — both FAIL.

- [ ] **Step 3: Add the bullet to each saver**

`build-setup.md` step 11 — add this bullet right after the **Apply the column order — MANDATORY** bullet:

```markdown
   - **Add the setup to the car's `Setup index`** — `notion-structure.md` → *Adding a line to
     `Setup index`*: run `scripts/setups_list.py --line` with this row's `Name`, page URL,
     `Source = generated`, `Stage`, `Surface`, `Conditions` and `Date`, and insert the line under
     the heading on the car's `Setups` page (you fetched that page for the column order — reuse
     it). On every plan. The build is not done without it.
```

`build-setup.md` step 5 — where the captured default row is written (the `default` row for this context; find the sentence that writes the `Source = default` row in step 5, after the values are read and validated), add:

```markdown
   After the `default` row is written, **add it to the car's `Setup index`** the same way
   (`notion-structure.md` → *Adding a line to `Setup index`*), with `Source = default` and this
   row's stage, surface, conditions and date — this is the line a later build on Claude's Free
   plan finds the stored default by.
```

`tweak-setup.md` — after the `Create one new row` bullet block (after the `Learn from this` unchecked sentence, before the page-body instructions), add:

```markdown
- **Add the new row to the car's `Setup index`** — `notion-structure.md` → *Adding a line to
  `Setup index`*: `scripts/setups_list.py --line` with the new row's `Name`, page URL,
  `Source = generated`, `Stage`, `Surface`, `Conditions`, `Date`; insert it under the heading on
  the car's `Setups` page. On every plan.
```

`capture-setup.md` — add a step 8 after step 7:

```markdown
8. **Add the row to the car's `Setup index`** — `notion-structure.md` → *Adding a line to `Setup
   index`*: `scripts/setups_list.py --line` with the row's `Name`, page URL, `Source = screenshot`,
   `Stage`, `Surface`, `Conditions` (blank when not given), `Date`; insert it under the heading
   on the car's `Setups` page (fetched in step 7 — reuse it). On every plan.
```

`import-savegame.md` — after the 5.5 row list, add:

```markdown
Then **add every imported row to its car's `Setup index`** — `notion-structure.md` → *Adding a
line to `Setup index`*: one `scripts/setups_list.py --line` per row (`Source = imported`, blank
`--conditions`, the row's `Stage` or blank, its `Surface`, its `Date`), and **one insert per car**
holding that car's lines newest first, under the heading on that car's `Setups` page. On every
plan. A car with no `Setups` page gets the one sentence that section gives, once.
```

- [ ] **Step 4: Run the suite**

Run: `python -m unittest discover -s tests` — green.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/build-setup.md .claude/skills/acr-setup-engineer/references/tweak-setup.md .claude/skills/acr-setup-engineer/references/capture-setup.md .claude/skills/acr-setup-engineer/references/import-savegame.md tests/test_references.py
git commit -m "Every saved setup gets a Setup index line"
```

---

### Task 5: `setups-list-read.md` — the Free-plan read path, and the routing from offline mode

**Files:**
- Create: `.claude/skills/acr-setup-engineer/references/setups-list-read.md`
- Modify: `references/notion-rest-read.md` (*Offline mode*, lines 110–142; add *The `learn:` override on paid plans* after the query section)
- Modify: `references/build-setup.md` (step 4 first sentence; step 7 `learn` bullet)
- Modify: `SKILL.md` (scripts list around line 110; references list around line 51; the *Reading a catalog* rule around line 357; routing table: a new row for a pasted setup link)
- Modify: `tests/test_references.py`, `tests/test_notion_docs_pages.py` will be touched in Task 7 for `Covers:`.

**Interfaces:**
- Consumes: `setups_list.py --pick/--find/--overrides` (Tasks 1–2); *Adding a line to `Setup index`* (Task 3).
- Produces: section names used by Task 6: `setups-list-read.md` → *Finding one setup by name*, *Adding a setup by link*.

- [ ] **Step 1: Write the failing guard tests**

Add to `TestSetupIndex`:

```python
    def test_free_read_path_exists_and_never_searches(self):
        path = os.path.join(SKILL, 'references', 'setups-list-read.md')
        self.assertTrue(os.path.isfile(path))
        text = read(path)
        for section in ('## Reading a car\'s setups on Free', '## Load more',
                        '## Finding one setup by name', '## Adding a setup by link'):
            self.assertIn(section, text, section)
        self.assertNotIn('notion-search', text.replace('never `notion-search`', ''))

    def test_offline_mode_routes_to_the_list(self):
        text = self.ref('notion-rest-read.md')
        self.assertIn('setups-list-read.md', text)
        self.assertNotIn("can't read your saved setups", text)
        self.assertIn('--overrides', text)

    def test_build_names_the_free_path(self):
        self.assertIn('setups-list-read.md', self.ref('build-setup.md'))

    def test_skill_md_lists_the_script_and_the_reference(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('scripts/setups_list.py', text)
        self.assertIn('references/setups-list-read.md', text)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m unittest tests.test_references -v` — the four FAIL.

- [ ] **Step 3: Create `references/setups-list-read.md`**

````markdown
# Reading `Setups` without the REST query — the car's `Setup index`

**The only way to read a car's setups when `scripts/check_egress.py` printed `egress: none`** in
this chat (`notion-rest-read.md` → *Offline mode*). With `egress: ok` this file is not used: the
REST query is the source. Catalogs are never read here (`catalog-read.md`).

The index is the `Setup index` list on the car's `Setups` page (`notion-structure.md` →
*`Setups` page*): one line per setup the skill saved, newest first. This workflow reads the list,
picks the few pages a build needs, fetches each one with `notion-fetch`, and reads `Learn from
this`, `Rating` and the values from the page's properties. **Never `notion-search` for a car's
setups** — it is capped, semantic and mixes cars.

## Reading a car's setups on Free

1. **Fetch the car's `Setups` page** (`notion-fetch`; the page is a child of `{Car}` under
   `ACR Setup Engineer`, resolved by name per `notion-structure.md`). Save the page's whole
   text to `setups/<slug>.md` in the sandbox (`<slug>` as in `catalog-read.md`). The script
   starts reading after the `Setup index` heading by itself.
   - No `Setup index` heading, or no `Setups` page → the list is empty. Say the once-per-chat
     line (*Telling the user*) if not yet said, and go on with **no stored default and no learn
     pool** — exactly `build-setup.md`'s no-default and no-prior-setups paths.
2. **Pick the candidates** — one command, in code execution:
   ```
   python scripts/setups_list.py --pick setups/<slug>.md --stage "{Stage}" --surface {Surface} --conditions "{Conditions}"
   ```
   Pass the build's stage, surface and conditions as settled in `build-setup.md` step 3 (blank
   `--conditions` when they were left blank; blank `--stage` when there is none). It prints JSON:
   - `default` — the `Source = default` line whose stage, surface and conditions all match, or
     `null`;
   - `other_defaults` — every other `default` line for the car, newest first;
   - `learn` — up to 6 non-default lines: every `learn: yes` line first, then the others ordered
     same stage, then same surface, then newest. `learn: no` lines are never here;
   - `skipped` — how many non-default lines were left out by the cap;
   - `malformed` — how many bullet lines under the heading couldn't be read.
3. **Fetch the picked pages** — `notion-fetch` on each `url` in `learn`, and on `default` if it
   isn't `null`; if `default` is `null` and `other_defaults` isn't, fetch **only the newest** of
   `other_defaults` (for `build-setup.md` step 4's "a default in a differing context" question).
   Fire the fetches together (parallel tool calls). Read every value from the page's
   **properties**, never from its body (`SKILL.md` → *A setup's real values are its row*). A page
   that fails to fetch is dropped and named in the report.
4. **Build the two results** and hand them to the calling workflow where the REST rows would have
   gone:
   - **The default anchor** (`build-setup.md` step 4): the fetched `default` page — same stage,
     surface, conditions as the build — or the fetched newest `other_defaults` page for the
     "does this match what the game gives you here?" question. Nothing → the screenshots-first
     path, unchanged (it explains what the anchor is for and builds without one if the user says
     so).
   - **The learn pool** (`build-setup.md` step 7): the fetched non-default pages whose
     `Learn from this` property is ticked, **plus every fetched page whose line says
     `learn: yes`**, whatever its checkbox. `Rating` and `Notes` come from the same fetch. None →
     *"no prior setups used"*, as today.
5. **Report**, one line in the build's report (`build-setup.md` step 12), always:
   *"Read {n} saved setups from the {Car}'s index ({names}); {k} count as `Learn from this`;
   {skipped} more not read — say "also learn from my other {Car} setups" to include them."*
   If `malformed` > 0, add: *"{malformed} line(s) in the `Setup index` couldn't be read — open the
   {Car}'s `Setups` page and check them against the format on the line above them."*

## Telling the user

Once per chat, the first time offline mode changes what a workflow does (this replaces the older
"I can't read your saved setups" wording — never say that any more):

> *This chat can't reach Notion's API. That's normal on Claude's Free plan. I can still use the
> setups the skill saved from v{version} on: I read the ones closest to this stage, up to 6, and
> take the ones you ticked `Learn from this`. Older setups count only if you paste their link
> here. Say "also learn from my other {Car} setups" to read more. The `Claude Free plan` page in
> your Notion has the details.*

`{version}` is the skill version (`SKILL.md` → *Skill version*); `{Car}` the car in scope, or
"this car's" when none is yet.

## Load more

When the user asks to learn from more setups (*"also learn from my other Stratos setups"*, *"read
all of them"*) or names some (*"learn from turini fast and monte v2 too"*):

1. Re-run the picker on the same file — `--limit 100` for "more / all", or `--names "{a}" "{b}"`
   for named ones (`--names` returns exactly those lines, a `learn: no` line included when named
   — say the user marked it `learn: no` and ask whether to use it anyway).
2. Fetch **only** the pages not already fetched in this chat.
3. Redo the step that used the learn pool (`build-setup.md` step 7 onward, or the tweak's
   reasoning) with the larger pool, and say in one line what was added. Names in `not_found`
   are reported as not in the index, with the paste-a-link hint (*Adding a setup by link*).

## Finding one setup by name

For a workflow that needs **one named setup** (`review-setup.md`, `tweak-setup.md`,
`ask-setups.md`, `share-setup.md`) when `egress: none`:

1. The car is known from the request, or from the setup just built or loaded in this chat. If it
   isn't, ask *"Which car is that setup for?"* before reading anything.
2. Fetch the car's `Setups` page, save it to `setups/<slug>.md`, and run
   ```
   python scripts/setups_list.py --find "{name}" setups/<slug>.md
   ```
   It prints `matches` (exact name first; else case-insensitive; else lines whose name contains
   the text) and `malformed`.
3. **One match** → `notion-fetch` its `url`; that page's properties are the row. **Several** →
   list them (Name / Stage / Date) and ask the user to pick. **None** → fall back to the lookup
   the workflow uses today (the setup may predate the index, or was made by hand), and if that
   also finds nothing, say the setup isn't in the {Car}'s index and can be added by pasting its
   link (*Adding a setup by link*).

## Adding a setup by link

The user pastes a Notion link to a setup, in any wording that says to use it, learn from it, or
add it (*"add this one to the index"*, *"learn from this: <link>"*). On every plan:

1. `notion-fetch` the link.
2. Check it is a setup: its `<parent-data-source>` is the `Setups` data source under
   `ACR Setup Engineer`, and its `Car` property names a car with a `{Car}` page under the root.
   Anything else → *"That page isn't one of your setups, so I can't add it."* and stop.
3. Build the line from the page's properties — `Name`, the page URL, `Source`, `Stage`,
   `Surface`, `Conditions`, `Date` — with `scripts/setups_list.py --line`, and insert it per
   `notion-structure.md` → *Adding a line to `Setup index`*. If `--find` already lists the same
   URL, don't add it twice; say it's already there.
4. Say in one line that it's in the {Car}'s index now, and — when the user asked to learn from it
   — use it in this chat as a fetched learn-pool page (its `Learn from this` checkbox still
   decides, unless the user says to count it: then treat it as `learn: yes` for this chat and
   suggest they add ` - learn: yes` to its line so it always counts).

## Rules
- **Only on `egress: none`** for reads; the REST query stays the source whenever it can run.
- **Never `notion-search` for a car's setups.** The index and pasted links are the only way in.
- **Values from properties, never from the page body.**
- **The cap is 6 and the user can lift it** — always say what was read and how to read more.
- **The skill never writes the `learn:` field** and never edits an existing line.
- Stay within `ACR Setup Engineer` scope, as always.
````

- [ ] **Step 4: Route offline mode there in `notion-rest-read.md`**

In *Offline mode*, replace the bullet `every **\`Setups\` slice** (the learn pool, a stored default, any other) → **empty**, as rung 2 describes;` with:

```markdown
  - every **`Setups` slice** (the learn pool, a stored default) → **read from the car's `Setup
    index` instead**, per [setups-list-read.md](setups-list-read.md): the list of links on the
    car's `Setups` page, a capped set of page fetches through the connector. Never empty by
    default, never a search;
  - a **named setup** (review, tweak, ask, share) → `setups-list-read.md` → *Finding one setup by
    name*;
```

Replace the quoted once-per-chat message (the `> *This chat can't reach Notion's API…*` block and the sentence after it) with:

```markdown
- **Tell the user once per chat, in plain words** — the exact text is in `setups-list-read.md` →
  *Telling the user*. Say it the first time offline mode changes what a workflow does, never
  before each read, never as an error. Never say the skill "can't read your saved setups": it can,
  for the setups the skill saved from this version on.
```

Rung 2 of the fallback ladder (`Setups` slice reads have no fallback … proceed as if empty) stays
as it is — add one sentence at its end: `This rung is for a plan **with** egress whose query
failed; it never applies in offline mode, which reads the index instead.`

After the `## The query — run the bundled script` section's output description, add:

```markdown
## The `learn:` override on paid plans

The user may mark a line in the car's `Setup index` by hand with ` - learn: yes` or
` - learn: no` (`notion-structure.md` → *`Setups` page*). It means the same thing on every plan,
so a build that read its learn pool over REST honours it too — one extra page fetch, once per
build, right after the REST queries:

1. Fetch the car's `Setups` page (it's fetched anyway for the column order), save it to
   `setups/<slug>.md`, run `python scripts/setups_list.py --overrides setups/<slug>.md` → JSON
   `{"yes": [names], "no": [names], "malformed": n}`.
2. **Drop** from the learn pool every row whose `Name` is in `no`.
3. **Add** every row whose `Name` is in `yes` and isn't in the pool yet — its row is in the plain
   `Setups` slice for the car (the same query **without** `--learn-only`, run in the same
   code-execution block), so no extra REST call is needed.
4. Both lists empty → nothing to do, say nothing.
```

- [ ] **Step 5: Name the Free path in `build-setup.md` steps 4 and 7**

Step 4, first sentence: `Fetch this car's \`Source = default\` rows (\`… --source default\`, per [notion-rest-read.md](notion-rest-read.md)) in the step 1–4 batch` → append: `— or, in offline mode, the default the car's \`Setup index\` gives ([setups-list-read.md](setups-list-read.md) → *Reading a car's setups on Free*, whose step 4 hands back the same two cases: a matching default, or one from a differing context) —`.

Step 7 `learn` bullet: after `(the compound-filter query in [notion-rest-read.md](notion-rest-read.md);` add `in offline mode the fetched pages from [setups-list-read.md](setups-list-read.md), whose \`learn: yes\` lines count whatever their checkbox says; on a paid plan apply \`notion-rest-read.md\` → *The \`learn:\` override on paid plans*;`.

- [ ] **Step 6: `SKILL.md`**

Scripts list: after the `check_egress.py` bullet add:

```markdown
- `scripts/setups_list.py` — the `Setup index` line on a car's `Setups` page: `--line` formats the
  line every saver writes (**never hand-format it**); `--pick`, `--find` and `--overrides` read
  the list back — the Free-plan way to find a car's setups (`references/setups-list-read.md`) and
  the `learn:` override on every plan.
```

References list: after the `notion-rest-read.md` bullet, change its last sentence from "`Setups` slices degrade to empty, stated plainly" to "`Setups` slices are read from the car's `Setup index` instead" and add:

```markdown
- `references/setups-list-read.md` — **the only way to read a car's setups without the REST
  query** (offline mode): the `Setup index` list on the car's `Setups` page, a capped set of page
  fetches, `Learn from this` and `Rating` read live. Also: finding one setup by name on Free,
  "load more", and adding a setup the user pastes a link to.
```

The rule bullet *Reading a catalog* (around line 357): replace `and on \`egress: none\` run no REST query for the rest of the chat (that doc's *Offline mode*). Never substitute connector row-listing, never guess.` with `and on \`egress: none\` run no REST query for the rest of the chat — read the car's \`Setup index\` instead (\`references/setups-list-read.md\`). Never substitute connector row-listing, never guess.`

Routing table: add a row after the *Share a setup* row:

```markdown
| **Add a setup by its link** — the user pastes a Notion link to a setup and says to use it, learn from it, or add it to the index | `references/setups-list-read.md` → *Adding a setup by link* |
```

- [ ] **Step 7: Run the suite**

Run: `python -m unittest discover -s tests`. `tests/test_notion_docs_pages.py::test_covers_every_routed_workflow` fails because `setups-list-read.md` is now routed but not in `Covers:`. Fix it in this task: append ` setups-list-read.md` to the `Covers:` line of `references/how-to-use-template.md` (Task 7 adds the page's line of text for it). Re-run; the whole suite is green.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/setups-list-read.md .claude/skills/acr-setup-engineer/references/notion-rest-read.md .claude/skills/acr-setup-engineer/references/build-setup.md .claude/skills/acr-setup-engineer/SKILL.md .claude/skills/acr-setup-engineer/references/how-to-use-template.md tests/test_references.py
git commit -m "Offline mode reads the car's Setup index instead of nothing"
```

---

### Task 6: Named-setup workflows look the name up in the index on Free

**Files:**
- Modify: `references/review-setup.md` (step 1, lines 27–36)
- Modify: `references/ask-setups.md` (step 3a, lines 83–92)
- Modify: `references/share-setup.md` (step 1, lines 14–16)
- Modify: `references/tweak-setup.md` (step 1, the "For a saved setup" sentence, around line 33)
- Modify: `tests/test_references.py`

**Interfaces:**
- Consumes: `setups-list-read.md` → *Finding one setup by name* (Task 5).

- [ ] **Step 1: Write the failing guard test**

```python
    def test_named_setup_workflows_use_the_index_on_free(self):
        for name in ('review-setup.md', 'ask-setups.md', 'share-setup.md', 'tweak-setup.md'):
            self.assertIn('Finding one setup by name', self.ref(name), name)
```

- [ ] **Step 2: Run to verify it fails** — `python -m unittest tests.test_references -v`.

- [ ] **Step 3: Add the same sentence to each lookup step**

In each of the four steps, right after the sentence that says to find the row by name in `ACR Setup Engineer → Setups`, add:

```markdown
**In offline mode** (`egress: none` this chat — `notion-rest-read.md` → *Offline mode*) look the
name up in the car's `Setup index` first: [setups-list-read.md](setups-list-read.md) → *Finding
one setup by name* (`scripts/setups_list.py --find`), then `notion-fetch` the matched page — its
properties are the row. Only when the name isn't in the index fall back to the lookup above.
```

For `share-setup.md` step 1, which says "Fetch the car's `Setups` DB rows (filtered to that car)", also change that to: "Fetch the car's `Setups` DB rows (filtered to that car, per `notion-rest-read.md`)" so the REST path is explicit, then add the offline sentence.

- [ ] **Step 4: Run the suite** — `python -m unittest discover -s tests` — green.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/review-setup.md .claude/skills/acr-setup-engineer/references/ask-setups.md .claude/skills/acr-setup-engineer/references/share-setup.md .claude/skills/acr-setup-engineer/references/tweak-setup.md tests/test_references.py
git commit -m "Named-setup workflows find the setup in the index on Free"
```

---

### Task 7: User-facing text — `Claude Free plan`, `How to use`, README, CLAUDE.md

**Files:**
- Modify: `references/free-plan-template.md`
- Modify: `references/how-to-use-template.md`
- Modify: `README.md` (lines 209–211, 827–847, 858–863)
- Modify: `CLAUDE.md` (the file lists: references, scripts, tests)
- Modify: `tests/test_notion_docs_pages.py`, `tests/test_references.py`

**Interfaces:** none new.

- [ ] **Step 1: Write the failing tests**

In `tests/test_notion_docs_pages.py`, add to `TestHowToUsePage`:

```python
    def test_mentions_the_setup_index_override(self):
        _, body = split(HOW_TO)
        self.assertIn('learn: yes', body)
        self.assertIn('paste', body.lower())
```

Add a class:

```python
class TestFreePlanPage(unittest.TestCase):
    def test_no_longer_claims_setups_cannot_be_read(self):
        _, body = split(FREE)
        self.assertNotIn("can't be read back", body)
        self.assertIn('Setup index', body)
        self.assertIn('up to 6', body)
        self.assertIn('learn: yes', body)
```

In `tests/test_references.py` `TestSetupIndex`:

```python
    def test_readme_no_longer_says_no_setup_history(self):
        text = read(os.path.join(SKILL, '..', '..', '..', 'README.md'))
        self.assertNotIn('**No setup history.**', text)
        self.assertIn('Setup index', text)
```

- [ ] **Step 2: Run to verify they fail** — `python -m unittest tests.test_notion_docs_pages tests.test_references -v`.

- [ ] **Step 3: Rewrite the body of `free-plan-template.md`**

Replace everything from `## What doesn't work` to the end with:

```markdown
## What's different

- **Your saved setups are read from a list, not from the table.** Every setup the skill saves
  from v{version} on is listed on the car's `Setups` page, under the heading `Setup index`. When
  you build, the skill reads the listed setups closest to your stage, **up to 6**, and uses the
  ones you ticked **`Learn from this`**, with their ratings. It tells you which ones it read. Say
  **"also learn from my other {Car} setups"** to read more.
- **Older setups aren't on the list.** Setups saved before v{version}, and setups you made by hand
  in Notion, don't count until you add them: paste the setup's Notion link in the chat and say
  **"learn from this one too"**.
- **A saved game default is reused when it's on the list.** If the skill saved the default for
  this stage from v{version} on, it finds it. Otherwise it asks for screenshots of the default,
  and builds without them if you'd rather not.
- **You can force a setup in or out.** On the car's `Setups` page, add ` - learn: yes` to the end
  of a setup's line to always learn from it, or ` - learn: no` to never read it. Only edit the end
  of the line; the skill never writes that part.

## What works

- Building, changing, reviewing, sharing and saving setups.
- Importing a save file, and saving your own setups from photos.
- **Every car, fully** — bundled ones and the ones you onboarded from screenshots. Their parameter
  lists never need the connection. A car set up by a much older version of the skill may need one
  re-onboard from screenshots. The skill tells you which.
- Anything you give it in the current chat, like screenshots or values you type.

## Things to know

- **Skip the token on the `Config` page.** It needs the connection Free doesn't have.
- **Long chats can hit Free's limits.** Some requests run several steps, and each saved setup the
  skill reads costs a step. If a chat stops, start a new one and ask again.

## Moving to Pro or Max

Open Settings → Capabilities → Network egress, choose **All domains**, set up the token on the
`Config` page, and start a new chat. The skill then reads your whole `Setups` table, including
setups made before v{version} and by hand. The `learn: yes` / `learn: no` marks keep working.
```

Also change the sentence in the intro `Nothing is broken. This is what changes.` → keep.

- [ ] **Step 4: `how-to-use-template.md`**

`Covers:` line: Task 5 already appended ` setups-list-read.md`; check it is there.

In *What you can ask*, after the **Share a setup** bullet add:

```markdown
- **Use an older setup on Claude's Free plan** — paste the setup's Notion link in the chat and
  say "learn from this one too". Setups the skill saves are listed on the car's `Setups` page
  under `Setup index`; add ` - learn: yes` to the end of a line to always learn from that setup,
  or ` - learn: no` to never read it.
```

In *Which page is whose*, the `Setups` bullet becomes: `Each car's **\`Setups\`** — the skill adds setups and keeps the \`Setup index\` list under the table; your own edits to setups are never overwritten, and the only part of the list you edit is a \` - learn: yes\` / \` - learn: no\` at the end of a line.`

- [ ] **Step 5: `README.md`**

Line 209–211 bullet becomes:

```markdown
- **Claude's Free plan runs a reduced mode** — every car works fully, and setups the skill saves
  from this version on are learned from through the car's `Setup index`. Older setups need their
  link pasted once. Details in
  [What Claude's Free plan can't do](#what-claudes-free-plan-cant-do).
```

Section `## What Claude's Free plan can't do`: replace the **No setup history** bullet with:

```markdown
- **Setup history comes from a list, not the table.** Every setup the skill saves from this
  version on is listed under `Setup index` on the car's `Setups` page. A build reads the listed
  setups closest to the stage, up to 6, and learns from the ones you ticked `Learn from this`; say
  "also learn from my other {car} setups" to read more. Setups saved by older versions or made by
  hand aren't listed — paste a setup's link in the chat and say "learn from this one too" to add
  it. Add ` - learn: yes` or ` - learn: no` to the end of a line to force a setup in or out.
- **A stored game default is found the same way** — only when the skill saved it from this version
  on. Otherwise you're asked to screenshot it, and can say no.
```

Troubleshooting bullet (lines 858–863): `so your setup history can't be read — by design` → `so your setup history is read from each car's \`Setup index\` — by design`.

- [ ] **Step 6: `CLAUDE.md`**

In the workflows list add `setups-list-read.md` next to `catalog-read.md` with one line: `the **one** path that reads a car's setups when the REST query can't run (offline mode): the \`Setup index\` list on the car's \`Setups\` page, parsed by \`scripts/setups_list.py\`.` In the scripts sentence mention `setups_list.py` (line format, never hand-formatted). In the tests sentence mention `tests/test_setups_list.py` and that `test_references.py` also guards the `Setup index` rules (every saver adds a line, refresh never writes it).

- [ ] **Step 7: Run the suite** — `python -m unittest discover -s tests` — green.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/free-plan-template.md .claude/skills/acr-setup-engineer/references/how-to-use-template.md README.md CLAUDE.md tests/test_notion_docs_pages.py tests/test_references.py
git commit -m "Docs: Free plan reads the Setup index; How to use and README updated"
```

---

### Task 8: Whole-branch consistency pass

**Files:** all touched references.

- [ ] **Step 1: Grep for leftovers**

From the skill directory:

```
grep -rn -i "can't read your saved setups\|can't be read back\|No setup history\|degrade to empty\|slices degrade" SKILL.md references/ ../../../README.md
```

Expected: no hits. Fix any.

- [ ] **Step 2: Check every `→ *Section*` pointer added in Tasks 3–7 resolves**

```
grep -rn -o "setups-list-read.md.*→ \*[^*]*\*" references/ SKILL.md | sort -u
grep -n "^## \|^### " references/setups-list-read.md
```

Every named section must exist with that exact title. Same for `notion-structure.md → *Adding a line to \`Setup index\`*` and `notion-rest-read.md → *The \`learn:\` override on paid plans*`.

- [ ] **Step 3: Run the suite and the zip check**

```
python -m unittest discover -s tests
make check-zip
```

- [ ] **Step 4: Commit any fixes**

```bash
git add -A .claude/skills/acr-setup-engineer README.md CLAUDE.md tests
git commit -m "Setup index: consistency fixes"
```

(No VERSION bump and no RELEASE_NOTES entry in this plan — the release is prepared separately, together with the catalog-as-file change.)
