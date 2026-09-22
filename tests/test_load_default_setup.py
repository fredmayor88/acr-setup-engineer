"""scripts/load_default_setup.py — the skill's reader for a bundled default setup.

A build anchors on the game's own default setup, which ships inside the skill as
`car-setups/<slug>.yaml` (written by `tools/car-catalog/extract_default_setups.py`). This
script is what a workflow runs to read one entry out of that file: stdlib only, because it
runs in the user's code sandbox, which has no PyYAML and no network.

The fixtures here are written by the tests into a temp dir, so this file passes before the
18 bundled files exist and keeps passing however their contents change.

Run: python -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SCRIPT = os.path.join(SKILL, 'scripts', 'load_default_setup.py')
GAME_VERSION_FILE = os.path.join(SKILL, 'GAME_VERSION')
sys.path.insert(0, os.path.join(SKILL, 'scripts'))

import load_default_setup as lds                              # noqa: E402

FIXTURE = '''\
car: "Test Car 1999"
game: "ACR"
version: "0.6"
source: "game-files"
written_at: "2026-09-22"
setups:
  - surface: "Tarmac"
    preset: "Balanced"
    values:
      "Gear Set": "1"
      "Primary Gear": "33//31*31//30"
      "Spring Stiffness Front": 65000
      "Adjuster Ring Front": 0.048
      "Camber Rear": -1.9
  - surface: "Gravel"
    preset: "Balanced"
    values:
      "Gear Set": "2"
      "Spring Stiffness Front": 35000
  - surface: "Gravel"
    preset: "Aggressive"
    values:
      "Gear Set": "3"
      "Spring Stiffness Front": 36000
'''

SNOW_FIXTURE = '''\
car: "Snow Car 1973"
game: "ACR"
version: "0.6"
source: "game-files"
written_at: "2026-09-22"
setups:
  - surface: "Gravel"
    preset: "Balanced"
    values:
      "Spring Stiffness Front": 35000
  - surface: "Snow"
    preset: "Balanced"
    values:
      "Spring Stiffness Front": 30000
'''

GRAVEL_ONLY = '''\
car: "Gravel Only 1980"
game: "ACR"
version: "0.6"
source: "game-files"
written_at: "2026-09-22"
setups:
  - surface: "Gravel"
    preset: "Balanced"
    values:
      "Spring Stiffness Front": 35000
'''


def write_dir(**files):
    """A temp car-setups directory holding {slug: text}. Returns its path."""
    directory = tempfile.mkdtemp()
    for slug, text in files.items():
        path = os.path.join(directory, slug + '.yaml')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    return directory


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding='utf-8')


class TestParser(unittest.TestCase):
    def setUp(self):
        self.dir = write_dir(**{'test-car': FIXTURE})
        self.doc = lds.load_file(os.path.join(self.dir, 'test-car.yaml'))

    def test_header(self):
        self.assertEqual(self.doc['car'], 'Test Car 1999')
        self.assertEqual(self.doc['game'], 'ACR')
        self.assertEqual(self.doc['version'], '0.6')
        self.assertEqual(self.doc['source'], 'game-files')
        self.assertEqual(self.doc['written_at'], '2026-09-22')

    def test_every_entry(self):
        self.assertEqual([(e['surface'], e['preset']) for e in self.doc['setups']],
                         [('Tarmac', 'Balanced'), ('Gravel', 'Balanced'),
                          ('Gravel', 'Aggressive')])

    def test_values_keep_their_types(self):
        values = self.doc['setups'][0]['values']
        self.assertEqual(values['Gear Set'], '1')
        self.assertEqual(values['Primary Gear'], '33//31*31//30')
        self.assertEqual(values['Spring Stiffness Front'], 65000)
        self.assertIsInstance(values['Spring Stiffness Front'], int)

    def test_float_values_keep_six_significant_digits(self):
        values = self.doc['setups'][0]['values']
        self.assertEqual(values['Adjuster Ring Front'], 0.048)
        self.assertEqual(repr(values['Adjuster Ring Front']), '0.048')
        self.assertEqual(values['Camber Rear'], -1.9)

    def test_a_missing_file_raises(self):
        with self.assertRaises(lds.SetupError):
            lds.load_file(os.path.join(self.dir, 'no-such-car.yaml'))


class TestPick(unittest.TestCase):
    def setUp(self):
        self.dir = write_dir(**{'test-car': FIXTURE, 'snow-car': SNOW_FIXTURE,
                                'gravel-only': GRAVEL_ONLY})

    def doc(self, slug):
        return lds.load_file(os.path.join(self.dir, slug + '.yaml'))

    def test_tarmac(self):
        entry, fallback = lds.pick(self.doc('test-car'), 'Tarmac')
        self.assertIsNone(fallback)
        self.assertEqual(entry['preset'], 'Balanced')
        self.assertEqual(entry['values']['Spring Stiffness Front'], 65000)

    def test_a_named_preset(self):
        entry, fallback = lds.pick(self.doc('test-car'), 'Gravel', 'Aggressive')
        self.assertIsNone(fallback)
        self.assertEqual(entry['values']['Gear Set'], '3')

    def test_snow_falls_back_to_gravel(self):
        entry, fallback = lds.pick(self.doc('test-car'), 'Snow')
        self.assertEqual(fallback, 'Gravel')
        self.assertEqual(entry['surface'], 'Gravel')
        self.assertEqual(entry['values']['Spring Stiffness Front'], 35000)

    def test_snow_present_does_not_fall_back(self):
        entry, fallback = lds.pick(self.doc('snow-car'), 'Snow')
        self.assertIsNone(fallback)
        self.assertEqual(entry['values']['Spring Stiffness Front'], 30000)

    def test_a_surface_with_no_fallback_raises(self):
        with self.assertRaises(lds.SetupError) as ctx:
            lds.pick(self.doc('gravel-only'), 'Tarmac')
        self.assertIn('Gravel', str(ctx.exception))

    def test_an_unknown_preset_raises_and_names_the_ones_it_has(self):
        with self.assertRaises(lds.SetupError) as ctx:
            lds.pick(self.doc('test-car'), 'Tarmac', 'Aggressive')
        self.assertIn('Balanced', str(ctx.exception))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.dir = write_dir(**{'test-car': FIXTURE, 'snow-car': SNOW_FIXTURE,
                                'gravel-only': GRAVEL_ONLY})

    def test_prints_one_entry(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Tarmac')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['car'], 'Test Car 1999')
        self.assertEqual(out['version'], '0.6')
        self.assertEqual(out['surface'], 'Tarmac')
        self.assertEqual(out['preset'], 'Balanced')
        self.assertIsNone(out['fallback'])
        self.assertEqual(out['values']['Spring Stiffness Front'], 65000)
        self.assertEqual(out['values']['Adjuster Ring Front'], 0.048)

    def test_preset_flag(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Gravel',
                '--preset', 'Aggressive')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['values']['Gear Set'], '3')

    def test_snow_fallback_is_reported(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Snow')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['surface'], 'Snow')
        self.assertEqual(out['fallback'], 'Gravel')

    def test_a_surface_with_no_fallback_exits_1(self):
        r = run('--dir', self.dir, '--car', 'gravel-only', '--surface', 'Tarmac')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Gravel', r.stderr)

    def test_an_unrecognised_surface_is_a_data_error_not_a_usage_error(self):
        """A surface name this script has never heard of still exits 1, not 2.

        The script keeps no list of legal surface names: a surface the file lacks is answered
        from the file (the Snow fallback, or exit 1 naming what it has), so a new surface in a
        game update can't come back as a usage error from the wrong script.
        """
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Ice')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('Ice', r.stderr)
        self.assertIn('Tarmac', r.stderr)
        self.assertIn('Gravel', r.stderr)

    def test_an_unknown_preset_exits_1_and_lists_the_presets(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Tarmac',
                '--preset', 'Aggressive')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Balanced', r.stderr)

    def test_pretty(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Tarmac', '--pretty')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('\n', r.stdout.strip())
        self.assertEqual(json.loads(r.stdout)['surface'], 'Tarmac')

    def test_list(self):
        r = run('--dir', self.dir, '--list', 'test-car')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['car'], 'Test Car 1999')
        self.assertEqual(out['version'], '0.6')
        self.assertEqual(out['setups'], [{'surface': 'Tarmac', 'preset': 'Balanced'},
                                         {'surface': 'Gravel', 'preset': 'Balanced'},
                                         {'surface': 'Gravel', 'preset': 'Aggressive'}])

    def test_game_version_is_the_file(self):
        r = run('--game-version')
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(GAME_VERSION_FILE, encoding='utf-8') as fh:
            self.assertEqual(r.stdout.strip(), fh.read().strip())

    def test_a_missing_file_exits_1(self):
        r = run('--dir', self.dir, '--car', 'no-such-car', '--surface', 'Tarmac')
        self.assertEqual(r.returncode, 1)
        self.assertIn('no-such-car', r.stderr)

    def test_an_unknown_flag_exits_2(self):
        r = run('--dir', self.dir, '--car', 'test-car', '--surface', 'Tarmac', '--bogus')
        self.assertEqual(r.returncode, 2)

    def test_no_arguments_exits_2(self):
        r = run()
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
