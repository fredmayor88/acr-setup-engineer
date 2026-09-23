"""GAME_VERSION — the one place the skill knows the current game version.

Written by tools/car-catalog/write_game_version.py from the game's DefaultGame.ini, read by the
catalog and default-setup extractors, the skill and these tests.

Run: python -m unittest discover -s tests
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
FILE = os.path.join(SKILL, 'GAME_VERSION')
TOOL = os.path.join(REPO, 'tools', 'car-catalog', 'write_game_version.py')
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))


class TestFile(unittest.TestCase):
    def test_exists_and_is_a_display_version(self):
        with open(FILE, encoding='utf-8') as f:
            text = f.read()
        self.assertTrue(text.endswith('\n'))
        self.assertRegex(text.strip(), r'^\d+\.\d+(\.\d+)?$')

    def test_every_template_carries_it(self):
        import glob
        version = open(FILE, encoding='utf-8').read().strip()
        for path in glob.glob(os.path.join(SKILL, 'car-templates', '*.yaml')):
            with open(path, encoding='utf-8') as f:
                self.assertIn(f'version: "{version}"', f.read(), path)

    def test_extractor_reads_the_file(self):
        import extract_car_catalog as ecc
        self.assertEqual(ecc.GAME_VERSION, open(FILE, encoding='utf-8').read().strip())


class TestTool(unittest.TestCase):
    def test_check_mode_passes_when_equal(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        open(target, 'w').write('0.6\n')
        r = subprocess.run([sys.executable, TOOL, '--check', '--version', '0.6', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_check_mode_fails_when_different(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        open(target, 'w').write('0.5\n')
        r = subprocess.run([sys.executable, TOOL, '--check', '--version', '0.6', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('0.5', r.stderr)
        self.assertIn('0.6', r.stderr)

    def test_write_mode(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, 'GAME_VERSION')
        r = subprocess.run([sys.executable, TOOL, '--version', '0.7.1', '--file', target],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(target).read(), '0.7.1\n')

    def test_unknown_flag_exits_2(self):
        r = subprocess.run([sys.executable, TOOL, '--bogus'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
