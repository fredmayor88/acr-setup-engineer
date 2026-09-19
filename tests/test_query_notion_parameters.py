"""Unit tests for query_notion_parameters.py — no real network calls.

We mock urllib.request.urlopen to return canned Notion API responses and assert
correct property extraction, pagination, learn-only filtering, and error handling.

Run: python -m unittest discover tests   (or: python tests/test_query_notion_parameters.py)
"""
import importlib.util
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

SCRIPT = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                      'acr-setup-engineer', 'scripts', 'query_notion_parameters.py')
_spec = importlib.util.spec_from_file_location('query_notion_parameters', SCRIPT)
Q = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Q)


def make_page(properties):
    """Wrap a flat {name: (type, raw)} dict into a Notion results[] page object."""
    props = {}
    for name, (ptype, raw) in properties.items():
        if ptype == 'title':
            props[name] = {'type': 'title', 'title': [{'plain_text': raw}]}
        elif ptype == 'rich_text':
            props[name] = {'type': 'rich_text', 'rich_text': [{'plain_text': raw}] if raw else []}
        elif ptype == 'select':
            props[name] = {'type': 'select', 'select': {'name': raw} if raw else None}
        elif ptype == 'checkbox':
            props[name] = {'type': 'checkbox', 'checkbox': raw}
        elif ptype == 'number':
            props[name] = {'type': 'number', 'number': raw}
    return {'properties': props}


def make_response(pages, has_more=False, next_cursor=None):
    payload = {'results': pages, 'has_more': has_more}
    if next_cursor:
        payload['next_cursor'] = next_cursor
    body = json.dumps(payload).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


PARAM_ROW = {
    'Adjustment':     ('title',     'Spring Stiffness'),
    'Section':        ('select',    'Suspensions'),
    'Min':            ('rich_text', '42300'),
    'Max':            ('rich_text', '73100'),
    'Unit':           ('rich_text', 'N/m'),
    'Discrete steps': ('rich_text', '42300, 50000, 57700'),
    'Car':            ('select',    'Alpine A110 1.8 1973'),
}

SETUP_ROW = {
    'Name':             ('title',    'Alsace GPT1'),
    'Car':              ('select',   'Alpine A110 1.8 1973'),
    'Stage':            ('select',   'Alsace'),
    'Learn from this':  ('checkbox', True),
    'Spring Stiffness': ('number',   50000),
}


class TestExtractValue(unittest.TestCase):
    def test_title(self):
        self.assertEqual(Q.extract_value({'type': 'title', 'title': [{'plain_text': 'Hello'}]}), 'Hello')

    def test_rich_text_blank(self):
        self.assertEqual(Q.extract_value({'type': 'rich_text', 'rich_text': []}), '')

    def test_rich_text_value(self):
        self.assertEqual(Q.extract_value({'type': 'rich_text', 'rich_text': [{'plain_text': '42300'}]}), '42300')

    def test_select_name(self):
        self.assertEqual(Q.extract_value({'type': 'select', 'select': {'name': 'Suspensions'}}), 'Suspensions')

    def test_select_null(self):
        self.assertIsNone(Q.extract_value({'type': 'select', 'select': None}))

    def test_checkbox(self):
        self.assertTrue(Q.extract_value({'type': 'checkbox', 'checkbox': True}))

    def test_number(self):
        self.assertEqual(Q.extract_value({'type': 'number', 'number': 50000}), 50000)

    def test_unknown_type_returns_none(self):
        self.assertIsNone(Q.extract_value({'type': 'formula', 'formula': {}}))


class TestBuildFilter(unittest.TestCase):
    def test_simple(self):
        f = Q.build_filter('Alpine A110 1.8 1973', learn_only=False)
        self.assertEqual(f['property'], 'Car')
        self.assertEqual(f['select']['equals'], 'Alpine A110 1.8 1973')

    def test_learn_only(self):
        f = Q.build_filter('Alpine A110 1.8 1973', learn_only=True)
        self.assertIn('and', f)
        props = {clause['property'] for clause in f['and']}
        self.assertIn('Car', props)
        self.assertIn('Learn from this', props)

    def test_learn_only_excludes_default_source(self):
        # Captured stock baselines are the build anchor, never a learning example.
        f = Q.build_filter('Alpine A110 1.8 1973', learn_only=True)
        excludes = [c for c in f['and']
                    if c['property'] == 'Source'
                    and c['select'].get('does_not_equal') == Q.DEFAULT_SOURCE]
        self.assertEqual(len(excludes), 1)

    def test_source_filter(self):
        f = Q.build_filter('Alpine A110 1.8 1973', learn_only=False, source='default')
        self.assertIn('and', f)
        self.assertEqual(len(f['and']), 2)
        by_prop = {c['property']: c for c in f['and']}
        self.assertEqual(by_prop['Car']['select']['equals'], 'Alpine A110 1.8 1973')
        self.assertEqual(by_prop['Source']['select']['equals'], 'default')

    def test_source_filter_without_car(self):
        f = Q.build_filter(None, learn_only=False, source='default')
        self.assertEqual(f['property'], 'Source')
        self.assertEqual(f['select']['equals'], 'default')

    def test_source_defaults_to_none(self):
        # Existing callers that pass only (car, learn_only) are unaffected.
        f = Q.build_filter('Alpine A110 1.8 1973', learn_only=False)
        self.assertEqual(f['property'], 'Car')


class TestBuildShowOrder(unittest.TestCase):
    def test_orders_value_columns_by_order(self):
        rows = [
            {'Adjustment': 'Spring Stiffness Front', 'Order': 2020},
            {'Adjustment': 'Gear Set', 'Order': 1010},
            {'Adjustment': 'Adjuster Ring Front', 'Order': 2010},
        ]
        show = Q.build_show_order(rows)
        # Name first, then value columns ascending by Order
        self.assertTrue(show.startswith('"Name", "Gear Set", "Adjuster Ring Front", '
                                        '"Spring Stiffness Front", '))

    def test_appends_fixed_meta_list(self):
        show = Q.build_show_order([{'Adjustment': 'Gear Set', 'Order': 1010}])
        self.assertEqual(
            show,
            '"Name", "Gear Set", "Car", "Location", "Stage", "Surface", '
            '"Conditions", "Date", '
            '"Source", "Mode", "Rating", "Learn from this", "Game version", '
            '"Notes", "Model", "Skill version"',
        )

    def test_dedupes_baseline_and_surface_rows(self):
        rows = [
            {'Adjustment': 'Spring Stiffness Front', 'Order': 2020},               # baseline
            {'Adjustment': 'Spring Stiffness Front', 'Order': 2020, 'Surface': 'Gravel'},
        ]
        show = Q.build_show_order(rows)
        self.assertEqual(show.count('"Spring Stiffness Front"'), 1)

    def test_missing_order_sorts_last_by_name(self):
        rows = [
            {'Adjustment': 'Zeta', 'Order': 1010},
            {'Adjustment': 'No Order B'},   # no Order
            {'Adjustment': 'No Order A'},   # no Order
        ]
        show = Q.build_show_order(rows)
        # numbered first, then un-numbered alphabetically, all before the meta list
        self.assertTrue(show.startswith('"Name", "Zeta", "No Order A", "No Order B", "Car"'))

    def test_skips_rows_without_adjustment(self):
        rows = [{'Order': 1010}, {'Adjustment': 'Gear Set', 'Order': 1010}]
        show = Q.build_show_order(rows)
        self.assertIn('"Gear Set"', show)


class TestQuery(unittest.TestCase):
    def test_all_skips_car_filter(self):
        resp = make_response([make_page(PARAM_ROW)])
        captured = []

        def fake_urlopen(req):
            captured.append(json.loads(req.data.decode()))
            return resp

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            Q.query('fake-id', 'fake-token', None)  # car_name=None == --all

        self.assertNotIn('filter', captured[0])

    def test_single_page(self):
        resp = make_response([make_page(PARAM_ROW)])
        with patch('urllib.request.urlopen', return_value=resp):
            rows = Q.query('fake-id', 'fake-token', 'Alpine A110 1.8 1973')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Adjustment'], 'Spring Stiffness')
        self.assertEqual(rows[0]['Section'], 'Suspensions')
        self.assertEqual(rows[0]['Min'], '42300')
        self.assertEqual(rows[0]['Discrete steps'], '42300, 50000, 57700')
        # null select (Car property with value) should be present
        self.assertEqual(rows[0]['Car'], 'Alpine A110 1.8 1973')

    def test_pagination(self):
        page1 = make_response([make_page(PARAM_ROW)], has_more=True, next_cursor='cur1')
        page2 = make_response([make_page(PARAM_ROW)])
        with patch('urllib.request.urlopen', side_effect=[page1, page2]):
            rows = Q.query('fake-id', 'fake-token', 'Alpine A110 1.8 1973')
        self.assertEqual(len(rows), 2)

    def test_learn_only_filter_sent(self):
        resp = make_response([make_page(SETUP_ROW)])
        captured = []

        def fake_urlopen(req):
            captured.append(json.loads(req.data.decode()))
            return resp

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            Q.query('fake-id', 'fake-token', 'Alpine A110 1.8 1973', learn_only=True)

        sent_filter = captured[0]['filter']
        self.assertIn('and', sent_filter)

    def test_source_filter_sent(self):
        resp = make_response([make_page(SETUP_ROW)])
        captured = []

        def fake_urlopen(req):
            captured.append(json.loads(req.data.decode()))
            return resp

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            Q.query('fake-id', 'fake-token', 'Alpine A110 1.8 1973', source='default')

        clauses = captured[0]['filter']['and']
        self.assertIn({'property': 'Source', 'select': {'equals': 'default'}}, clauses)

    def test_blank_rich_text_included(self):
        row_with_blank = dict(PARAM_ROW)
        row_with_blank['Discrete steps'] = ('rich_text', '')  # blank discrete steps
        resp = make_response([make_page(row_with_blank)])
        with patch('urllib.request.urlopen', return_value=resp):
            rows = Q.query('fake-id', 'fake-token', 'x')
        self.assertIn('Discrete steps', rows[0])
        self.assertEqual(rows[0]['Discrete steps'], '')

    def test_null_select_omitted(self):
        row_null_select = dict(PARAM_ROW)
        row_null_select['Section'] = ('select', None)
        resp = make_response([make_page(row_null_select)])
        with patch('urllib.request.urlopen', return_value=resp):
            rows = Q.query('fake-id', 'fake-token', 'x')
        self.assertNotIn('Section', rows[0])

    def test_http_error_exits_1(self):
        import urllib.error
        err = urllib.error.HTTPError(url='', code=401, msg='Unauthorized',
                                     hdrs={}, fp=io.BytesIO(b'bad token'))
        with patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(SystemExit) as ctx:
                Q.query('fake-id', 'bad-token', 'x')
        self.assertEqual(ctx.exception.code, 1)

    def test_network_error_exits_1(self):
        import urllib.error
        err = urllib.error.URLError(reason='Name or service not known')
        with patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(SystemExit) as ctx:
                Q.query('fake-id', 'fake-token', 'x')
        self.assertEqual(ctx.exception.code, 1)


class TestReadTemplateRows(unittest.TestCase):
    """The token-free --from-template path: read {Adjustment, Order} from template YAML."""

    TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                                 'acr-setup-engineer', 'car-templates')

    def _write(self, text):
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_reads_real_template_adjustment_and_order(self):
        path = os.path.join(self.TEMPLATES_DIR, 'alfa-romeo-gta-1300-junior-1972.yaml')
        rows = Q.read_template_rows(path)
        by_adj = {r['Adjustment']: r.get('Order') for r in rows}
        self.assertEqual(by_adj['Gear Set'], 1010)
        self.assertEqual(by_adj['ABS Map'], 8010)
        # value-first/meta-last is then guaranteed by build_show_order (covered above)
        show = Q.build_show_order(rows)
        self.assertTrue(show.startswith('"Name", "Gear Set", '))
        self.assertTrue(show.endswith('"Skill version"'))

    def test_ignores_save_ids_and_header_fields(self):
        # save_ids is a header field (and could be a block list); it must not become a row.
        path = self._write(
            'car: "X"\n'
            'game: "ACR"\n'
            'save_ids:\n'
            '  - "SomeSaveId"\n'
            'drivetrain: "RWD"\n'
            'parameters:\n'
            '  - section: "Gearbox"\n'
            '    adjustment: "Gear Set"\n'
            '    order: 1010\n'
        )
        rows = Q.read_template_rows(path)
        self.assertEqual(rows, [{'Adjustment': 'Gear Set', 'Order': 1010}])

    def test_tolerates_missing_order(self):
        path = self._write(
            'parameters:\n'
            '  - adjustment: "No Order Param"\n'
            '  - adjustment: "Has Order"\n'
            '    order: 2020\n'
        )
        rows = Q.read_template_rows(path)
        self.assertEqual({r['Adjustment'] for r in rows}, {'No Order Param', 'Has Order'})
        self.assertNotIn('Order', next(r for r in rows if r['Adjustment'] == 'No Order Param'))

    def test_stops_at_next_top_level_key(self):
        # a top-level key after parameters: must not swallow following content as params
        path = self._write(
            'parameters:\n'
            '  - adjustment: "Gear Set"\n'
            '    order: 1010\n'
            'trailing_key: "ignored"\n'
        )
        rows = Q.read_template_rows(path)
        self.assertEqual(rows, [{'Adjustment': 'Gear Set', 'Order': 1010}])


class TestMainShowOrder(unittest.TestCase):
    """`--show-order` as the CLI runs it: templates alone, Notion alone, or both at once.

    A main / location / stage view can span a template car (no `Parameters` rows at all) and a
    screenshot car (rows in Notion). One call has to order both together, because two separate
    SHOW lists carry no `Order` left to interleave by (notion-structure.md -> Applying the order).
    """

    TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                                 'acr-setup-engineer', 'car-templates')

    def _write(self, text):
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        return path

    def _template(self):
        return self._write(
            'car: "Template Car"\n'
            'parameters:\n'
            '  - section: "Gearbox"\n'
            '    adjustment: "Gear Set"\n'
            '    order: 1010\n'
            '  - section: "Suspensions"\n'
            '    adjustment: "Spring Stiffness Front"\n'
            '    order: 2020\n'
        )

    def _run(self, argv):
        """Run main() with argv, returning (exit_code, stdout)."""
        out = io.StringIO()
        with patch.object(sys, 'argv', ['query_notion_parameters.py'] + argv), \
                patch.object(sys, 'stdout', out), \
                self.assertRaises(SystemExit) as ctx:
            Q.main()
        return ctx.exception.code, out.getvalue()

    def test_templates_only_needs_no_token_and_no_network(self):
        def boom(*a, **k):
            raise AssertionError('a templates-only --show-order must not touch the network')

        with patch('urllib.request.urlopen', side_effect=boom):
            code, out = self._run(['--show-order', '--from-template', self._template()])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith('"Name", "Gear Set", "Spring Stiffness Front", "Car"'), out)

    def test_template_and_notion_rows_are_ordered_together_in_one_call(self):
        rows = [{'Adjustment': 'Screenshot Only', 'Order': 2015},
                {'Adjustment': 'Late Column', 'Order': 9010}]
        with patch.object(Q, 'query', return_value=rows) as q:
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order',
                                   '--from-template', self._template()])
        self.assertEqual(code, 0)
        q.assert_called_once()
        self.assertEqual(q.call_args[0][2], None, 'car_name must be None for --all')
        self.assertTrue(
            out.startswith('"Name", "Gear Set", "Screenshot Only", "Spring Stiffness Front", '
                           '"Late Column", "Car"'), out)

    def test_mixed_call_passes_the_car_name_through(self):
        with patch.object(Q, 'query', return_value=[]) as q:
            code, _ = self._run(['ds-id', 'tok', 'Some Car', '--show-order',
                                 '--from-template', self._template()])
        self.assertEqual(code, 0)
        self.assertEqual(q.call_args[0][2], 'Some Car')

    def test_token_only_show_order_still_works(self):
        with patch.object(Q, 'query', return_value=[{'Adjustment': 'Gear Set', 'Order': 1010}]):
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order'])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith('"Name", "Gear Set", "Car"'), out)

    def test_legacy_rows_of_a_template_car_are_dropped_before_ordering(self):
        """A template car's catalog is its bundled file. Rows an older skill version left in
        `Parameters` for it are never read (notion-structure.md -> Where a car's catalog lives),
        so they must not reach the comparator: not to win the Order tie-break, and not to inject
        a column name the template no longer has."""
        rows = [
            # legacy rows for the template's own car — different case and padding on purpose
            {'Adjustment': 'Spring Stiffness Front', 'Order': 5, 'Car': 'template car'},
            {'Adjustment': 'Old Renamed Thing', 'Order': 1005, 'Car': '  Template Car  '},
            # a genuine screenshot car in the same table
            {'Adjustment': 'Screenshot Only', 'Order': 2015, 'Car': 'Other Car'},
        ]
        with patch.object(Q, 'query', return_value=rows):
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order',
                                   '--from-template', self._template()])
        self.assertEqual(code, 0)
        self.assertNotIn('Old Renamed Thing', out)
        self.assertTrue(
            out.startswith('"Name", "Gear Set", "Screenshot Only", "Spring Stiffness Front", '
                           '"Car"'), out)

    def test_legacy_rows_are_dropped_through_the_skill_name_normalisation(self):
        """The drop uses the skill's one car-name normalisation rule (lowercase, punctuation
        to spaces, whitespace collapsed — `onboard-car.md` step 1), so a `Car` value that
        differs from the template's `car:` only in punctuation or spacing is still the same
        car and its legacy rows still go."""
        rows = [
            {'Adjustment': 'Old Renamed Thing', 'Order': 1005, 'Car': 'Template-Car'},
            {'Adjustment': 'Also Legacy', 'Order': 1006, 'Car': 'template  car'},
            {'Adjustment': 'Screenshot Only', 'Order': 2015, 'Car': 'Other Car'},
        ]
        with patch.object(Q, 'query', return_value=rows):
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order',
                                   '--from-template', self._template()])
        self.assertEqual(code, 0)
        self.assertNotIn('Old Renamed Thing', out)
        self.assertNotIn('Also Legacy', out)
        self.assertIn('Screenshot Only', out)

    def test_the_same_adjustment_from_two_cars_keeps_the_lower_order(self):
        """Different cars legitimately share an Adjustment and collapse to one Setups column;
        the comparator keeps the lowest Order across both sources."""
        rows = [
            {'Adjustment': 'Gear Set', 'Order': 500, 'Car': 'Other Car'},
            {'Adjustment': 'Zed', 'Order': 700, 'Car': 'Other Car'},
        ]
        with patch.object(Q, 'query', return_value=rows):
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order',
                                   '--from-template', self._template()])
        self.assertEqual(code, 0)
        self.assertEqual(out.count('"Gear Set"'), 1)
        self.assertTrue(
            out.startswith('"Name", "Gear Set", "Zed", "Spring Stiffness Front", "Car"'), out)

    def test_a_notion_failure_in_a_mixed_call_prints_nothing_and_exits_1(self):
        """A half-answer is worse than none: a SHOW list missing every screenshot car's columns
        would hide them. The query must fail loudly before anything is printed."""
        import urllib.error
        err = urllib.error.URLError(reason='Name or service not known')
        with patch('urllib.request.urlopen', side_effect=err):
            code, out = self._run(['ds-id', 'tok', '--all', '--show-order',
                                   '--from-template', self._template()])
        self.assertEqual(code, 1)
        self.assertEqual(out, '')

    def test_from_template_still_requires_show_order(self):
        code, _ = self._run(['--from-template', self._template()])
        self.assertEqual(code, 2)

    def test_incomplete_positional_args_with_templates_is_a_usage_error(self):
        code, _ = self._run(['ds-id', '--show-order', '--from-template', self._template()])
        self.assertEqual(code, 2)

    def test_unreadable_template_exits_1_not_2(self):
        code, _ = self._run(['--show-order', '--from-template',
                             os.path.join(self.TEMPLATES_DIR, 'no-such-car.yaml')])
        self.assertEqual(code, 1)


class TestNormaliseCarName(unittest.TestCase):
    """The skill's one car-name normalisation (onboard-car.md step 1): lowercase, punctuation
    to spaces, whitespace collapsed. The script uses it for exact normalised equality."""

    def test_case_punctuation_and_spacing_are_normalised_away(self):
        for raw in ('Lancia Stratos HF', 'lancia-stratos-hf', '  LANCIA   STRATOS  HF ',
                    'Lancia_Stratos.HF'):
            with self.subTest(raw=raw):
                self.assertEqual(Q.normalise_car_name(raw), 'lancia stratos hf')

    def test_different_cars_do_not_collapse_together(self):
        self.assertNotEqual(Q.normalise_car_name('Peugeot 206 WRC 1999'),
                            Q.normalise_car_name('Peugeot 208 Rally4'))


class TestOutputEncoding(unittest.TestCase):
    """Stdout must be UTF-8 whatever the console's locale is: a `SHOW` list can carry a
    column name with a non-ASCII character, and on Windows a piped stdout would otherwise be
    encoded with the ANSI code page and reach Notion as mojibake."""

    def _template_with_accents(self):
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('car: "Accented Car"\n'
                     'parameters:\n'
                     '  - section: "Wheels"\n'
                     '    adjustment: "Caméra Angle °"\n'
                     '    order: 6030\n')
        self.addCleanup(os.remove, path)
        return path

    def test_show_order_output_is_utf8(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, SCRIPT, '--show-order', '--from-template',
             self._template_with_accents()], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Caméra Angle °', proc.stdout.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
