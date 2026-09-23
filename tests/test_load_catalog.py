"""Validate scripts/load_catalog.py — the skill's reader for a bundled car template.

A template car's parameter catalog is the YAML file inside the skill, not the Notion
`Parameters` DB, so this script is what every read workflow runs in place of a REST query.
Its rows must come out in exactly the shape `references/notion-rest-read.md` -> *Output*
describes, so every downstream rule consumes them unchanged.

The script itself is stdlib-only (it runs in the user's code sandbox, which has no PyYAML);
this test may use PyYAML, and does, to prove the --to-template output is real YAML.

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
  - section: "Brakes"
    adjustment: "Proportioning Preload"
    order: 7045
    min: 1.75
    max: 4.00
    unit: "MPa"
    discrete_steps: "1.75, 2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50, 3.75, 4.00"
  - section: "Differentials"
    adjustment: "LSD Power/Coast Ramp Rear"
    order: 1510
    min: "—"
    max: "—"
    unit: ""
    discrete_steps: "45/50, 50/65"
'''


# The same file as it looks on a car's `Parameters` page: `--to-template` adds the three
# bookkeeping keys, and `parameter_count` is the one the loader checks on read.
PARAMETER_COUNT = FIXTURE.count('  - section:')
COUNTED_FIXTURE = FIXTURE.replace('source: "game-files"',
                                  f'source: "screenshots"\nparameter_count: {PARAMETER_COUNT}')

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

    def test_a_number_equal_to_a_step_passes_however_the_step_is_spelled(self):
        """3.5 is the template's "3.50" step — the same pressure, fewer decimals.

        A car's grid is spelled by whoever wrote the template; the value comes from the game
        (or from a bundled default setup). Comparing only the text rejects a value the setup
        screen can dial, which is how the Mini's gravel `Proportioning Preload 3.5` ended up
        needing an allowlist entry in the extractor.
        """
        values = self.write_values({'Proportioning Preload': 3.5})
        out, _ = run(self.fixture, '--check', values)
        report = json.loads(out)
        self.assertEqual(report['problems'], [])
        self.assertEqual(report['ok'][0]['value'], 3.5)

    def test_a_number_between_two_steps_is_still_rejected(self):
        values = self.write_values({'Proportioning Preload': 3.51})
        out, _ = run(self.fixture, '--check', values, expect=3)
        problem = json.loads(out)['problems'][0]
        self.assertEqual(problem['Adjustment'], 'Proportioning Preload')
        self.assertEqual(problem['reason'], 'not one of the discrete steps')

    def test_a_named_selection_still_needs_its_exact_text(self):
        """Nothing about a ramp or a brake part is a number, so only the spelling can match."""
        values = self.write_values({'LSD Power/Coast Ramp Rear': '45/50'})
        out, _ = run(self.fixture, '--check', values)
        self.assertEqual(json.loads(out)['problems'], [])

        values = self.write_values({'LSD Power/Coast Ramp Rear': '45-50'})
        out, _ = run(self.fixture, '--check', values, expect=3)
        self.assertEqual(json.loads(out)['problems'][0]['legal'], ['45/50', '50/65'])

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


class TestPrettyAndUsage(LoadCatalogTestCase):
    def test_pretty_prints_the_header_and_one_line_per_row(self):
        out, err = run(STRATOS, '--pretty')
        self.assertEqual(err, '')
        self.assertIn('Lancia Stratos HF 1976', out)
        self.assertIn('game-files', out)
        self.assertIn('0.6', out)
        rows = json.loads(run(STRATOS)[0])
        self.assertGreaterEqual(len(out.strip().splitlines()), len(rows))

    def test_pretty_leaves_parameter_count_out_of_the_facts_line(self):
        """`parameter_count` is bookkeeping, not a fact about the car.

        It exists so a truncated fetch of a `Parameters` page is caught on load
        (`references/catalog-read.md` step 5); printing it on the facts line next to the
        version and the drivetrain reads as if it described the car.
        """
        path = os.path.join(self._tmp.name, 'counted-car.yaml')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(COUNTED_FIXTURE)
        out, err = run(path, '--pretty')
        self.assertEqual(err, '')
        self.assertIn('screenshots', out)         # the facts line is there
        self.assertNotIn('parameter_count', out)

    def test_no_arguments_is_a_usage_error(self):
        run(expect=2)

    def test_an_unknown_flag_is_a_usage_error(self):
        """A typo must not quietly fall through to the default JSON output."""
        run(STRATOS, '--pretyy', expect=2)
        run(STRATOS, '--surfaces', 'Gravel', expect=2)

    def test_a_missing_template_exits_one(self):
        run(os.path.join(self._tmp.name, 'no-such-car.yaml'), expect=1)


class TestOutputEncoding(unittest.TestCase):
    """Stdout must be UTF-8 whatever the console's locale is.

    An executing Claude runs this script with its output piped, and on Windows Python then
    encodes stdout with the ANSI code page (cp1252 here), which turns the catalog's `—`
    (used for Min/Max on named-selection params) into a single 0x97 byte. Whoever reads it
    back as UTF-8 — the car's `Parameters` page block, the chat transcript — sees mojibake. So
    the bytes are decoded here explicitly, never with `text=True` (which would decode with the same
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


class TestSkillVersionResolution(unittest.TestCase):
    """`--to-template` records the skill version per SKILL.md -> *Skill version*: the VERSION
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


class TestToTemplate(LoadCatalogTestCase):
    """`--to-template rows.json` emits a complete template YAML from REST-shaped rows."""

    def _rows_json(self, header=None, rows=None):
        import tempfile
        payload = {
            'header': header if header is not None else {
                'car': 'Test Car 1999', 'drivetrain': 'AWD', 'version': '0.6',
                'source': 'screenshots', 'weight': '~1200 kg'},
            'rows': rows if rows is not None else [
                {'Adjustment': 'Spring Stiffness Front', 'Section': 'Suspensions', 'Min': 30000,
                 'Max': 60000, 'Unit': 'N/m', 'Discrete steps': '30000, 45000, 60000',
                 'Order': 2020, 'Car': 'Test Car 1999'},
                {'Adjustment': 'Spring Stiffness Front', 'Section': 'Suspensions', 'Min': 20000,
                 'Max': 40000, 'Unit': 'N/m', 'Discrete steps': '', 'Order': 2020,
                 'Surface': 'Gravel', 'Car': 'Test Car 1999'},
                {'Adjustment': 'Primary Gear', 'Section': 'Gearbox', 'Min': '—', 'Max': '—',
                 'Unit': '', 'Discrete steps': '35//30*33//28, 33//28*32//31', 'Order': 1020,
                 'Car': 'Test Car 1999'},
            ]}
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False)
        self.addCleanup(os.remove, path)
        return path

    def _to_template(self, **kw):
        out = subprocess.run([sys.executable, SCRIPT, '--to-template', self._rows_json(**kw)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_output_is_yaml_with_the_header_and_the_parameters(self):
        doc = yaml.safe_load(self._to_template())
        self.assertEqual(doc['car'], 'Test Car 1999')
        self.assertEqual(doc['source'], 'screenshots')
        self.assertEqual(doc['weight'], '~1200 kg')
        self.assertEqual(doc['parameter_count'], 3)
        self.assertEqual(len(doc['parameters']), 3)
        self.assertRegex(doc['written_at'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertTrue(doc['skill_version'])

    def test_parameters_are_sorted_by_order_baseline_before_surface(self):
        doc = yaml.safe_load(self._to_template())
        got = [(p['adjustment'], p.get('surface')) for p in doc['parameters']]
        self.assertEqual(got, [('Primary Gear', None), ('Spring Stiffness Front', None),
                               ('Spring Stiffness Front', 'Gravel')])

    def test_round_trips_through_the_loader_to_the_same_rows(self):
        import tempfile
        text = self._to_template()
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        rows = json.loads(run(path)[0])
        gear = next(r for r in rows if r['Adjustment'] == 'Primary Gear')
        self.assertEqual(gear['Discrete steps'], '35//30*33//28, 33//28*32//31')
        self.assertEqual(gear['Min'], '—')
        gravel = next(r for r in rows if r.get('Surface') == 'Gravel')
        self.assertEqual(gravel['Min'], 20000)
        self.assertEqual({r['Car'] for r in rows}, {'Test Car 1999'})

    def test_forked_from_is_carried_when_given(self):
        doc = yaml.safe_load(self._to_template(header={
            'car': 'Test Car 1999', 'version': '0.6', 'source': 'screenshots',
            'forked_from': 'bundled template v0.6'}))
        self.assertEqual(doc['forked_from'], 'bundled template v0.6')

    def test_version_is_always_quoted_so_yaml_keeps_it_a_string(self):
        """`version: 0.6` parses back as a float, and a later `0.10` would become `0.1`."""
        text = self._to_template(header={
            'car': 'Test Car 1999', 'version': '0.6', 'source': 'screenshots'})
        self.assertIn('version: "0.6"', text)
        self.assertEqual(yaml.safe_load(text)['version'], '0.6')

    def test_a_two_digit_minor_version_round_trips_as_a_string(self):
        text = self._to_template(header={
            'car': 'Test Car 1999', 'version': '0.10', 'source': 'screenshots'})
        self.assertIn('version: "0.10"', text)
        self.assertEqual(yaml.safe_load(text)['version'], '0.10')

    def test_an_empty_row_list_writes_count_zero_and_then_fails_to_load(self):
        """The designed loud failure of the migration's third source (nothing to recover).

        The file is still written by the script, never by hand, and every later load stops
        with `no parameters found` — which `catalog-read.md` step 5 turns into the re-onboard
        line.
        """
        import tempfile
        text = self._to_template(header={'car': 'Empty Car', 'version': 'unknown',
                                         'source': 'screenshots'}, rows=[])
        self.assertIn('parameter_count: 0', text)
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        _, err = run(path, expect=1)
        self.assertIn('no parameters found', err)

    def test_an_edited_copy_of_a_bundled_car_loads_to_the_same_rows_plus_the_edit(self):
        # What edit-catalog.md does on a bundled car: load, change one row, --to-template, load.
        import tempfile
        rows = json.loads(run(STRATOS)[0])
        target = next(r for r in rows if r['Adjustment'] == 'Spring Stiffness Front' and not r.get('Surface'))
        target['Max'] = 99000
        header = {'car': 'Lancia Stratos HF 1976', 'drivetrain': 'RWD', 'version': '0.6',
                  'source': 'screenshots', 'forked_from': 'bundled template v0.6'}
        text = self._to_template(header=header, rows=rows)
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        again = json.loads(run(path)[0])
        self.assertEqual(len(again), len(rows))
        self.assertEqual({r['Adjustment'] for r in again}, {r['Adjustment'] for r in rows})
        edited = next(r for r in again if r['Adjustment'] == 'Spring Stiffness Front' and not r.get('Surface'))
        self.assertEqual(edited['Max'], 99000)

    def test_missing_rows_file_exits_one(self):
        out = subprocess.run([sys.executable, SCRIPT, '--to-template', 'no-such.json'],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 1)


class TestHeader(LoadCatalogTestCase):
    """`--header` prints the file's header as one JSON object.

    It exists so no workflow ever copies header keys by eye: `edit-catalog.md` 6.1 and the
    refresh's `Catalog` rebuild both read the facts from here, and the object drops straight
    into `--to-template`'s rows.json as its `header`.
    """

    NINE_FACTS = ('drivetrain', 'engine_layout', 'weight_bias', 'weight', 'max_power',
                  'max_torque', 'class', 'gearbox', 'steering_lock')

    BLOCK_IDS_FIXTURE = ('car: "Block Car"\n'
                         'game: "ACR"\n'
                         'save_ids:\n'
                         '  - "OneId"\n'
                         '  - "TwoId"\n'
                         'drivetrain: "RWD"\n'
                         'version: "0.6"\n'
                         'source: "screenshots"\n'
                         'parameters:\n'
                         '  - section: "Brakes"\n'
                         '    adjustment: "Brake Bias"\n'
                         '    order: 7010\n'
                         '    min: 50\n'
                         '    max: 70\n')

    def write(self, text, name):
        path = os.path.join(self._tmp.name, name)
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        return path

    def header_of(self, path):
        out, err = run(path, '--header')
        self.assertEqual(err, '')
        return json.loads(out)

    def test_the_stratos_header_carries_the_nine_facts_and_its_save_id(self):
        head = self.header_of(STRATOS)
        self.assertEqual(head['car'], 'Lancia Stratos HF 1976')
        for key in self.NINE_FACTS:
            self.assertTrue(head.get(key), key)
        self.assertEqual(head['version'], '0.6')
        self.assertEqual(head['source'], 'game-files')
        self.assertEqual(head['save_ids'], ['LanciaStratosHF'])

    def test_the_engine_and_gearing_keys_are_left_out(self):
        head = self.header_of(STRATOS)
        for key in ('engine_curve', 'gearing_tool', 'power_torque_chart', 'peak_torque',
                    'torque_points', 'rpm_step'):
            self.assertNotIn(key, head)

    def test_every_bundled_template_has_all_nine_facts(self):
        """A refresh reads a template car's facts from here, so none of them may be blank."""
        for name in sorted(os.listdir(os.path.join(SKILL, 'car-templates'))):
            if not name.endswith('.yaml'):
                continue
            head = self.header_of(os.path.join(SKILL, 'car-templates', name))
            for key in self.NINE_FACTS:
                self.assertTrue(head.get(key), f'{name}: {key}')
            self.assertIsInstance(head['save_ids'], list)

    def test_a_block_list_save_ids_becomes_a_json_list(self):
        path = self.write(self.BLOCK_IDS_FIXTURE, 'block-ids.yaml')
        self.assertEqual(self.header_of(path)['save_ids'], ['OneId', 'TwoId'])

    def test_a_bare_scalar_save_ids_becomes_a_one_item_list(self):
        path = self.write(
            self.BLOCK_IDS_FIXTURE.replace('save_ids:\n  - "OneId"\n  - "TwoId"\n',
                                           'save_ids: "OnlyId"\n'), 'scalar-ids.yaml')
        self.assertEqual(self.header_of(path)['save_ids'], ['OnlyId'])

    def test_parameter_count_comes_back_as_an_int(self):
        path = self.write(COUNTED_FIXTURE, 'counted-header.yaml')
        self.assertEqual(self.header_of(path)['parameter_count'], PARAMETER_COUNT)

    def test_a_file_with_no_parameters_still_prints_its_header(self):
        """The migration's third source writes exactly that file; it stays inspectable."""
        path = self.write('car: "Empty Car"\nversion: "unknown"\nsource: "screenshots"\n'
                          'parameter_count: 0\nparameters:\n', 'empty-car.yaml')
        head = self.header_of(path)
        self.assertEqual(head['car'], 'Empty Car')
        self.assertEqual(head['parameter_count'], 0)

    def test_header_is_mutually_exclusive_with_the_other_modes(self):
        run(STRATOS, '--header', '--pretty', expect=2)
        run(STRATOS, '--header', '--surface', 'Gravel', expect=2)
        run(STRATOS, '--header', '--check', 'values.json', expect=2)
        run('--header', '--to-template', 'rows.json', expect=2)

    def test_header_needs_the_file(self):
        run('--header', expect=2)

    def test_the_header_drops_straight_into_to_template(self):
        """The round trip every reference relies on: --header -> rows.json -> --to-template."""
        import tempfile
        head = self.header_of(STRATOS)
        rows = json.loads(run(STRATOS)[0])
        fd, rows_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(rows_path, 'w', encoding='utf-8') as fh:
            json.dump({'header': head, 'rows': rows}, fh, ensure_ascii=False)
        self.addCleanup(os.remove, rows_path)
        out = subprocess.run([sys.executable, SCRIPT, '--to-template', rows_path],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('save_ids: ["LanciaStratosHF"]', out.stdout)
        doc = yaml.safe_load(out.stdout)
        self.assertEqual(doc['save_ids'], ['LanciaStratosHF'])
        for key in self.NINE_FACTS:
            self.assertEqual(doc[key], head[key], key)
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(out.stdout)
        self.addCleanup(os.remove, path)
        self.assertEqual(len(json.loads(run(path)[0])), len(rows))


class TestParameterCount(LoadCatalogTestCase):
    def _with_count(self, n):
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(f'parameter_count: {n}\n' + FIXTURE)
        self.addCleanup(os.remove, path)
        return path

    def test_matching_count_loads(self):
        rows = json.loads(run(self.fixture)[0])
        out, _ = run(self._with_count(len(rows)))
        self.assertEqual(len(json.loads(out)), len(rows))

    def test_mismatched_count_exits_one_with_a_clear_message(self):
        rows = json.loads(run(self.fixture)[0])
        _, err = run(self._with_count(len(rows) + 5), expect=1)
        self.assertIn(f'parameter_count says {len(rows) + 5} but the file has {len(rows)}', err)

    def test_snapshot_flag_is_gone(self):
        run(STRATOS, '--snapshot', expect=2)


if __name__ == '__main__':
    unittest.main()
