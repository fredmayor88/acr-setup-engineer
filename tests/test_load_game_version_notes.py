"""scripts/load_game_version_notes.py — which game-versions/<version>.md applies.

Exact match on GAME_VERSION, else the newest lower version with a note line, else exit 1.
Stdlib only: it runs in the user's code sandbox.

Run: python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SCRIPT = os.path.join(SKILL, 'scripts', 'load_game_version_notes.py')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()
sys.path.insert(0, os.path.join(SKILL, 'scripts'))

import load_game_version_notes as lgn  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class TestFunctions(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(lgn.parse_version('0.6'), (0, 6))
        self.assertEqual(lgn.parse_version('0.6.1'), (0, 6, 1))
        self.assertIsNone(lgn.parse_version('README'))
        self.assertIsNone(lgn.parse_version('0.6a'))

    def test_available_ignores_non_version_files(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('0.5.md', '0.6.md', 'README.md', 'notes.txt'):
                open(os.path.join(d, name), 'w').close()
            self.assertEqual([v for v, _, _ in lgn.available(d)], [(0, 5), (0, 6)])

    def test_resolve_exact_lower_and_none(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('0.5.md', '0.6.md'):
                open(os.path.join(d, name), 'w').close()
            self.assertEqual(lgn.resolve('0.6', d)[1], '0.6')
            self.assertEqual(lgn.resolve('0.6.1', d)[1], '0.6')
            self.assertEqual(lgn.resolve('0.5.9', d)[1], '0.5')
            self.assertIsNone(lgn.resolve('0.4', d))


class TestCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        for name in ('0.5.md', '0.6.md', 'README.md'):
            open(os.path.join(self.tmp.name, name), 'w').close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_match_prints_the_path_only(self):
        r = run('--version', '0.6', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines(), [os.path.join(self.tmp.name, '0.6.md')])

    def test_lower_version_fallback_adds_a_note(self):
        r = run('--version', '0.6.1', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(lines[0], os.path.join(self.tmp.name, '0.6.md'))
        self.assertEqual(lines[1], 'note: no notes for 0.6.1; using 0.6')

    def test_nothing_at_or_below_exits_1(self):
        r = run('--version', '0.4', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 1)
        self.assertIn('no version notes for 0.4', r.stderr)

    def test_unknown_flag_exits_2(self):
        r = run('--bogus')
        self.assertEqual(r.returncode, 2)
        self.assertIn('Usage', r.stderr)

    def test_default_resolves_the_skills_game_version_exactly(self):
        r = run()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(os.path.basename(lines[0]), GAME_VERSION + '.md')
        self.assertEqual(len(lines), 1, 'the current version must have its own file')


if __name__ == '__main__':
    unittest.main()
