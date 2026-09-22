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
