"""Validate scripts/load_catalog.py — the skill's reader for a bundled car template.

A template car's parameter catalog is the YAML file inside the skill, not the Notion
`Parameters` DB, so this script is what every read workflow runs in place of a REST query.
Its rows must come out in exactly the shape `references/notion-rest-read.md` -> *Output*
describes, so every downstream rule consumes them unchanged.

The script itself is stdlib-only (it runs in the user's code sandbox, which has no PyYAML);
this test may use PyYAML, and does, to prove the --snapshot output is real YAML.

Run: python -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SCRIPT = os.path.join(SKILL, 'scripts', 'load_catalog.py')
STRATOS = os.path.join(SKILL, 'car-templates', 'lancia-stratos.yaml')

# The keys a Parameters row has when it comes back from the REST read
# (references/notion-rest-read.md -> Output). `Surface` is omitted on baseline rows.
REST_KEYS = {'Adjustment', 'Section', 'Min', 'Max', 'Unit', 'Discrete steps', 'Order', 'Car'}

FIXTURE = '''\
car: "Test Car 1999"
game: "ACR"
drivetrain: "AWD"
version: "0.6"
source: "game-files"
gearing_tool: "https://example.invalid/test-car/gears/"
engine_curve:
  source: "ACR game files - FC_TestCar_Torque"
  peak_torque: "300 Nm at 4000 rpm"

parameters:
  - section: "Gearbox"
    adjustment: "Primary Gear"
    order: 1020
    min: "—"
    max: "—"
    unit: ""
    discrete_steps: "35//30*33//28, 33//28*32//31"
  - section: "Suspensions"
    adjustment: "Spring Stiffness Front"
    order: 2020
    min: 40000
    max: 80000
    unit: "N/m"
    discrete_steps: ""
  - section: "Suspensions"
    adjustment: "Spring Stiffness Front"
    order: 2020
    min: 20000
    max: 50000
    unit: "N/m"
    discrete_steps: ""
    surface: "Gravel"
  - section: "Axles"
    adjustment: "Anti-roll Bar Stiffness Rear"
    order: 4020
    min: 1
    max: 8
    unit: ""
    discrete_steps: "1, 2, 3, 4, 5, 6, 7, 8"
  - section: "Brakes"
    adjustment: "Brake Discs Front"
    order: 7010
    min: "—"
    max: "—"
    unit: ""
    discrete_steps: ""
'''


TARMAC_ROW_FIXTURE = '''\
car: "Surfaced Car 2001"
game: "ACR"
version: "0.6"
source: "community"

parameters:
  - section: "Suspensions"
    adjustment: "Ride Height Front"
    order: 2010
    min: 80
    max: 120
    unit: "mm"
    discrete_steps: ""
  - section: "Suspensions"
    adjustment: "Ride Height Front"
    order: 2010
    min: 50
    max: 70
    unit: "mm"
    discrete_steps: ""
    surface: "Tarmac"
'''


def run(*args, expect=0):
    """Run the script and return (stdout, stderr), asserting the exit code.

    Decoded as **UTF-8 explicitly**, never with the ambient locale: the script always writes
    UTF-8, and letting `text=True` pick the console code page would both mangle `—` here and
    hide a real encoding bug in the script (TestOutputEncoding checks the raw bytes).
    """
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding='utf-8', cwd=REPO)
    assert proc.returncode == expect, (
        f'exit {proc.returncode} (expected {expect})\nstdout: {proc.stdout}\nstderr: {proc.stderr}')
    return proc.stdout, proc.stderr


class LoadCatalogTestCase(unittest.TestCase):
    """Base class giving every test the small Gravel-row fixture on disk."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.fixture = os.path.join(cls._tmp.name, 'test-car.yaml')
        with open(cls.fixture, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(FIXTURE)
        # a second fixture carrying an explicit Tarmac row, which only a community export
        # would have — the bundled templates only ever tag Gravel
        cls.surfaced_fixture = os.path.join(cls._tmp.name, 'tarmac-row-car.yaml')
        with open(cls.surfaced_fixture, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(TARMAC_ROW_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def write_values(self, values):
        path = os.path.join(self._tmp.name, 'values.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(values, fh)
        return path


class TestRowShape(LoadCatalogTestCase):
    def test_rows_match_the_rest_read_output_shape(self):
        out, err = run(STRATOS)
        self.assertEqual(err, '', 'output must be pristine')
        rows = json.loads(out)
        self.assertGreater(len(rows), 20)
        for row in rows:
            with self.subTest(adjustment=row.get('Adjustment')):
                extra = set(row) - REST_KEYS - {'Surface'}
                self.assertEqual(extra, set(), f'keys outside the REST read shape: {extra}')
                self.assertEqual(REST_KEYS - set(row), set(), 'a REST read key is missing')
                self.assertEqual(row['Car'], 'Lancia Stratos HF 1976')

    def test_numbers_are_numbers_and_dashes_are_strings(self):
        rows = json.loads(run(STRATOS)[0])
        by_adj = {r['Adjustment']: r for r in rows}
        gear_set = by_adj['Gear Set']
        self.assertEqual(gear_set['Min'], 1)
        self.assertEqual(gear_set['Max'], 3)
        self.assertIsInstance(gear_set['Min'], int)
        self.assertEqual(gear_set['Order'], 1010)
        primary = by_adj['Primary Gear']
        self.assertEqual(primary['Min'], '—')
        self.assertEqual(primary['Max'], '—')
        ring = by_adj['Adjuster Ring Front']
        self.assertEqual(ring['Max'], 0.25)
        self.assertEqual(ring['Discrete steps'], '', 'a blank steps cell is "" , never None')

    def test_compound_gear_values_keep_their_asterisk(self):
        rows = json.loads(run(STRATOS)[0])
        steps = next(r['Discrete steps'] for r in rows if r['Adjustment'] == 'Primary Gear')
        self.assertIn('35//30*33//28', steps)

    def test_baseline_and_surface_rows_are_both_emitted_without_a_surface_flag(self):
        rows = json.loads(run(self.fixture)[0])
        springs = [r for r in rows if r['Adjustment'] == 'Spring Stiffness Front']
        self.assertEqual(len(springs), 2)
        self.assertNotIn('Surface', springs[0], 'baseline rows omit Surface')
        self.assertEqual(springs[1]['Surface'], 'Gravel')


class TestSurfaceResolution(LoadCatalogTestCase):
    def test_snow_falls_back_to_the_gravel_row(self):
        rows = json.loads(run(self.fixture, '--surface', 'Snow')[0])
        springs = [r for r in rows if r['Adjustment'] == 'Spring Stiffness Front']
        self.assertEqual(len(springs), 1, 'one row per Adjustment once resolved')
        self.assertEqual(springs[0]['Min'], 20000)
        self.assertEqual(springs[0]['Resolved from'], 'Gravel')

    def test_gravel_uses_its_own_row_and_tarmac_the_baseline(self):
        gravel = json.loads(run(self.fixture, '--surface', 'Gravel')[0])
        springs = next(r for r in gravel if r['Adjustment'] == 'Spring Stiffness Front')
        self.assertEqual(springs['Min'], 20000)
        self.assertEqual(springs['Resolved from'], 'Gravel')

        tarmac = json.loads(run(self.fixture, '--surface', 'Tarmac')[0])
        springs = next(r for r in tarmac if r['Adjustment'] == 'Spring Stiffness Front')
        self.assertEqual(springs['Min'], 40000)
        self.assertEqual(springs['Resolved from'], 'baseline')

    def test_resolved_output_has_one_row_per_adjustment(self):
        rows = json.loads(run(self.fixture, '--surface', 'Gravel')[0])
        adjustments = [r['Adjustment'] for r in rows]
        self.assertEqual(len(adjustments), len(set(adjustments)))

    def test_unknown_surface_is_a_usage_error(self):
        run(self.fixture, '--surface', 'Mud', expect=2)


class TestCheck(LoadCatalogTestCase):
    def test_legal_values_pass_with_exit_zero(self):
        values = self.write_values({
            'Spring Stiffness Front': 50000,
            'Anti-roll Bar Stiffness Rear': 4,
            'Primary Gear': '33//28*32//31',
        })
        out, err = run(self.fixture, '--check', values)
        self.assertEqual(err, '')
        report = json.loads(out)
        self.assertEqual(report['problems'], [])
        self.assertEqual(len(report['ok']), 3)

    def test_out_of_range_number_is_flagged(self):
        values = self.write_values({'Spring Stiffness Front': 120000})
        out, _ = run(self.fixture, '--check', values, expect=3)
        problem = json.loads(out)['problems'][0]
        self.assertEqual(problem['Adjustment'], 'Spring Stiffness Front')
        self.assertEqual(problem['value'], 120000)
        self.assertEqual(problem['legal'], [40000, 80000])

    def test_value_outside_the_discrete_steps_is_flagged(self):
        values = self.write_values({'Anti-roll Bar Stiffness Rear': 9})
        out, _ = run(self.fixture, '--check', values, expect=3)
        problem = json.loads(out)['problems'][0]
        self.assertEqual(problem['Adjustment'], 'Anti-roll Bar Stiffness Rear')
        self.assertEqual(problem['legal'], ['1', '2', '3', '4', '5', '6', '7', '8'])

    def test_unknown_adjustment_is_flagged_as_not_in_catalog(self):
        values = self.write_values({'Nose Cone Angle': 3})
        out, _ = run(self.fixture, '--check', values, expect=3)
        problem = json.loads(out)['problems'][0]
        self.assertEqual(problem['reason'], 'not in catalog')

    def test_a_dash_row_with_no_steps_reports_range_unknown(self):
        values = self.write_values({'Brake Discs Front': 'Some Disc'})
        out, _ = run(self.fixture, '--check', values, expect=3)
        problem = json.loads(out)['problems'][0]
        self.assertEqual(problem['reason'], 'range unknown')

    def test_a_collapsed_compound_gear_value_is_repaired(self):
        values = self.write_values({'Primary Gear': '35//3033//28'})
        out, _ = run(self.fixture, '--check', values)
        entry = json.loads(out)['ok'][0]
        self.assertEqual(entry['value'], '35//30*33//28')
        self.assertTrue(entry['repaired'])

    def test_without_a_surface_the_baseline_row_is_used(self):
        """No --surface means the baseline row, never a surface-tagged one — the same
        "most parameters have only the baseline row" default the catalog rules assume."""
        values = self.write_values({'Ride Height Front': 90})       # baseline 80..120
        out, _ = run(self.surfaced_fixture, '--check', values)
        self.assertEqual(json.loads(out)['problems'], [])

        values = self.write_values({'Ride Height Front': 55})       # only legal on Tarmac
        out, _ = run(self.surfaced_fixture, '--check', values, expect=3)
        self.assertEqual(json.loads(out)['problems'][0]['legal'], [80, 120])

        out, _ = run(self.surfaced_fixture, '--check', values, '--surface', 'Tarmac')
        self.assertEqual(json.loads(out)['problems'], [])

    def test_check_resolves_against_the_named_surface(self):
        values = self.write_values({'Spring Stiffness Front': 25000})
        run(self.fixture, '--check', values, '--surface', 'Gravel')       # legal on gravel
        run(self.fixture, '--check', values, '--surface', 'Tarmac', expect=3)

    def test_a_missing_values_file_exits_one(self):
        run(self.fixture, '--check', os.path.join(self._tmp.name, 'nope.json'), expect=1)


class TestSnapshot(LoadCatalogTestCase):
    def test_snapshot_parses_as_yaml_and_counts_its_rows(self):
        out, err = run(STRATOS, '--snapshot')
        self.assertEqual(err, '')
        doc = yaml.safe_load(out)
        self.assertEqual(doc['car'], 'Lancia Stratos HF 1976')
        self.assertEqual(doc['source'], 'bundled template v0.6')
        self.assertEqual(doc['row_count'], len(doc['rows']))
        self.assertEqual(doc['row_count'], len(json.loads(run(STRATOS)[0])))
        with open(os.path.join(SKILL, 'VERSION'), encoding='utf-8') as fh:
            self.assertEqual(doc['skill_version'], fh.read().strip())

    def test_snapshot_rows_mirror_the_rest_read_keys(self):
        doc = yaml.safe_load(run(STRATOS, '--snapshot')[0])
        for row in doc['rows']:
            with self.subTest(adjustment=row.get('Adjustment')):
                self.assertEqual(set(row) - REST_KEYS - {'Surface'}, set())
                self.assertEqual(REST_KEYS - set(row) - {'Car'}, set())

    def test_snapshot_keeps_the_compound_gear_asterisk(self):
        raw = run(STRATOS, '--snapshot')[0]
        self.assertIn('35//30*33//28', raw)
        doc = yaml.safe_load(raw)
        steps = next(r['Discrete steps'] for r in doc['rows'] if r['Adjustment'] == 'Primary Gear')
        self.assertIn('35//30*33//28', steps)

    def test_snapshot_quotes_the_em_dash_and_keeps_surface_rows(self):
        doc = yaml.safe_load(run(self.fixture, '--snapshot')[0])
        primary = next(r for r in doc['rows'] if r['Adjustment'] == 'Primary Gear')
        self.assertEqual(primary['Min'], '—')
        surfaced = [r for r in doc['rows'] if r.get('Surface') == 'Gravel']
        self.assertEqual(len(surfaced), 1)


class TestPrettyAndUsage(LoadCatalogTestCase):
    def test_pretty_prints_the_header_and_one_line_per_row(self):
        out, err = run(STRATOS, '--pretty')
        self.assertEqual(err, '')
        self.assertIn('Lancia Stratos HF 1976', out)
        self.assertIn('game-files', out)
        self.assertIn('0.6', out)
        rows = json.loads(run(STRATOS)[0])
        self.assertGreaterEqual(len(out.strip().splitlines()), len(rows))

    def test_no_arguments_is_a_usage_error(self):
        run(expect=2)

    def test_an_unknown_flag_is_a_usage_error(self):
        """A typo must not quietly fall through to the default JSON output."""
        run(STRATOS, '--pretyy', expect=2)
        run(STRATOS, '--snapshot', '--surfaces', 'Gravel', expect=2)

    def test_a_missing_template_exits_one(self):
        run(os.path.join(self._tmp.name, 'no-such-car.yaml'), expect=1)


class TestOutputEncoding(unittest.TestCase):
    """Stdout must be UTF-8 whatever the console's locale is.

    An executing Claude runs this script with its output piped, and on Windows Python then
    encodes stdout with the ANSI code page (cp1252 here), which turns the catalog's `—`
    (used for Min/Max on named-selection params) into a single 0x97 byte. Whoever reads it
    back as UTF-8 — the Catalog snapshot, the chat transcript — sees mojibake. So the bytes
    are decoded here explicitly, never with `text=True` (which would decode with the same
    wrong locale and hide the bug).
    """

    EM_DASH = '—'

    def raw(self, *args):
        proc = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_default_json_output_is_utf8(self):
        out = self.raw(STRATOS)
        self.assertIn(self.EM_DASH, out.decode('utf-8'))

    def test_snapshot_output_is_utf8(self):
        out = self.raw(STRATOS, '--snapshot')
        self.assertIn(self.EM_DASH, out.decode('utf-8'))


class TestSkillVersionResolution(unittest.TestCase):
    """`--snapshot` records the skill version per SKILL.md -> *Skill version*: the VERSION
    file when it holds a real version, and for the literal `dev` (an unreleased source
    checkout) a `git describe --tags --always --dirty` from the script's own repo, falling
    back to `dev` when git can't answer. None of this test needs git to succeed.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(SCRIPT))
        import load_catalog
        cls.mod = load_catalog

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def root_with(self, version):
        if version is not None:
            with open(os.path.join(self._tmp.name, 'VERSION'), 'w', encoding='utf-8') as fh:
                fh.write(version + '\n')
        return self._tmp.name

    def test_a_released_version_file_wins(self):
        self.assertEqual(self.mod.skill_version(self.root_with('v0.18.0')), 'v0.18.0')

    def test_git_describe_returns_none_when_it_cannot_answer(self):
        """A directory that is not a git checkout (or no git at all) yields None, never a
        crash and never a stray error message treated as a version."""
        self.assertIsNone(self.mod.git_describe(self._tmp.name))

    def test_dev_falls_back_to_dev_when_git_cannot_answer(self):
        self.assertEqual(self.mod.skill_version(self.root_with('dev')), 'dev')

    def test_a_missing_version_file_still_returns_something(self):
        value = self.mod.skill_version(self.root_with(None))
        self.assertTrue(value)

    def test_dev_uses_git_describe_when_git_answers(self):
        with unittest.mock.patch.object(self.mod, 'git_describe',
                                        return_value='v0.18.0-3-gdbc15b1'):
            self.assertEqual(self.mod.skill_version(self.root_with('dev')),
                             'v0.18.0-3-gdbc15b1')


if __name__ == '__main__':
    unittest.main()
