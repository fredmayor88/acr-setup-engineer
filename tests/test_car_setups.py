"""The bundled default setups in car-setups/ — one per car, complete, on the catalog grid,
stamped with the current game version.

Run: python -m unittest discover -s tests
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SETUPS = os.path.join(SKILL, 'car-setups')
TEMPLATES = os.path.join(SKILL, 'car-templates')
LOADER = os.path.join(SKILL, 'scripts', 'load_default_setup.py')
CATALOG = os.path.join(SKILL, 'scripts', 'load_catalog.py')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))
import load_default_setup as lds  # noqa: E402
# The values the game itself ships off its own template's grid. Imported, never retyped, so
# the allowlist the extractor writes with and the one the test skips on cannot drift.
from extract_default_setups import KNOWN_OFF_GRID  # noqa: E402


def slugs():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(TEMPLATES, '*.yaml')))


class TestFiles(unittest.TestCase):
    def test_every_template_car_has_a_setups_file(self):
        missing = [s for s in slugs() if not os.path.isfile(os.path.join(SETUPS, s + '.yaml'))]
        self.assertFalse(missing, missing)

    def test_header_matches_template_and_game_version(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            with open(os.path.join(TEMPLATES, s + '.yaml'), encoding='utf-8') as f:
                tpl = f.read()
            self.assertEqual(doc['version'], GAME_VERSION, s)
            self.assertIn(f'car: "{doc["car"]}"', tpl, s)
            self.assertEqual(doc['source'], 'game-files')

    def test_surfaces_and_presets(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            pairs = {(e['surface'], e['preset']) for e in doc['setups']}
            self.assertIn(('Tarmac', 'Balanced'), pairs, s)
            self.assertIn(('Gravel', 'Balanced'), pairs, s)
        for s in ('alpine-a110-1-8-1973', 'fiat-131-abarth-1976'):
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            self.assertIn(('Snow', 'Balanced'), {(e['surface'], e['preset']) for e in doc['setups']}, s)
        for s in ('lancia-delta-integrale-evoluzione-1992', 'peugeot-208-rally4'):
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            self.assertIn('Aggressive', {e['preset'] for e in doc['setups']}, s)

    def test_every_entry_is_legal_for_its_surface(self):
        for s in slugs():
            doc = lds.load_file(os.path.join(SETUPS, s + '.yaml'))
            for e in doc['setups']:
                # A handful of values the game's own presets ship off the template's grid are
                # written as-is and allowlisted (see KNOWN_OFF_GRID's evidence comments); the
                # catalog check can't know about them, so they are dropped before it runs.
                checked = {k: v for k, v in e['values'].items()
                           if KNOWN_OFF_GRID.get((s, e['surface'], e['preset'], k)) != v}
                fd, values = tempfile.mkstemp(suffix='.json')
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        json.dump(checked, f)
                    r = subprocess.run(
                        [sys.executable, CATALOG, os.path.join(TEMPLATES, s + '.yaml'),
                         '--surface', e['surface'], '--check', values],
                        capture_output=True, text=True, encoding='utf-8')
                finally:
                    os.remove(values)
                self.assertEqual(r.returncode, 0, f'{s} {e["surface"]} {e["preset"]}: {r.stdout}{r.stderr}')

    def test_every_allowlisted_off_grid_value_is_really_in_its_file(self):
        """KNOWN_OFF_GRID may not outlive what it excuses.

        Each entry suppresses a real catalog failure, so a stale one silently widens the
        check. If a game update moves a value back onto the grid, this fails and the entry
        goes away with it.
        """
        for (slug, surface, preset, adjustment), value in sorted(KNOWN_OFF_GRID.items()):
            doc = lds.load_file(os.path.join(SETUPS, slug + '.yaml'))
            entry, _ = lds.pick(doc, surface, preset)
            self.assertEqual(entry['values'].get(adjustment), value,
                             f'{slug} {surface}/{preset} {adjustment}')

    def test_stratos_tarmac_balanced_known_values(self):
        doc = lds.load_file(os.path.join(SETUPS, 'lancia-stratos.yaml'))
        v = next(e for e in doc['setups'] if (e['surface'], e['preset']) == ('Tarmac', 'Balanced'))['values']
        self.assertEqual(v['Spring Stiffness Front'], 65000)
        self.assertEqual(v['Spring Stiffness Rear'], 42500)
        self.assertEqual(v['Front Bias'], 0.53)            # 0.57 on ACR 0.6
        self.assertEqual(v['Gear Set'], '1')
        self.assertEqual(v['Primary Gear'], '33//31*31//30')
        self.assertEqual(v['Differential Ratio Rear'], '65//19')




class TestSideTypos(unittest.TestCase):
    """extract_default_setups.KNOWN_SIDE_TYPOS: a one-sided typo in a game preset is replaced,
    and an entry the file no longer matches stops the run."""

    def setUp(self):
        from extract_default_setups import fix_side_typos
        self.fix = fix_side_typos
        self.key = ('alpine-a110-1-8-1973', 'Tarmac', 'Balanced')

    def test_the_alpine_typo_is_replaced_by_the_other_sides_value(self):
        values = {'Dampers.RearLeft.FastBump': 3750, 'Dampers.RearRight.FastBump': 31750}
        self.assertEqual(self.fix(*self.key, values),
                         {'Dampers.RearLeft.FastBump': 3750, 'Dampers.RearRight.FastBump': 3750})

    def test_a_fixed_game_file_stops_the_run(self):
        with self.assertRaises(SystemExit):
            self.fix(*self.key, {'Dampers.RearRight.FastBump': 3750})

    def test_other_setups_are_untouched(self):
        values = {'Dampers.RearRight.FastBump': 31750}
        self.assertEqual(self.fix('alpine-a110-1-8-1973', 'Gravel', 'Balanced', values), values)


class TestScreenValues(unittest.TestCase):
    """extract_default_setups.KNOWN_SCREEN_VALUES: a default the screen shows differently."""

    def setUp(self):
        from extract_default_setups import fix_screen_values
        self.fix = fix_screen_values

    def test_the_s4_front_plates_read_as_the_screen_shows_them(self):
        got = self.fix('lancia-delta-s4-1986', 'Gravel', 'Balanced',
                       {'Plates Number Front': 0, 'Plates Number Rear': 6})
        self.assertEqual(got, {'Plates Number Front': 2, 'Plates Number Rear': 6})

    def test_a_changed_file_stops_the_run(self):
        with self.assertRaises(SystemExit):
            self.fix('lancia-delta-s4-1986', 'Gravel', 'Balanced', {'Plates Number Front': 3})

    def test_the_bundled_s4_files_carry_the_screen_value(self):
        for slug in ('lancia-delta-s4-1986', 'lancia-delta-s4-evo2-italtecnica-2021'):
            doc = lds.load_file(os.path.join(SETUPS, slug + '.yaml'))
            for e in doc['setups']:
                self.assertEqual(e['values']['Plates Number Front'], 2, (slug, e['surface']))


if __name__ == '__main__':
    unittest.main()
