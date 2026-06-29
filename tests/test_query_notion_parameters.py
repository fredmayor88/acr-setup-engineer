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
                      'car-setups', 'scripts', 'query_notion_parameters.py')
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
        self.assertEqual(len(f['and']), 2)
        props = {clause['property'] for clause in f['and']}
        self.assertIn('Car', props)
        self.assertIn('Learn from this', props)


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
            '"Name", "Gear Set", "Car", "Location", "Stage", "Surface", "Date", '
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
                                 'car-setups', 'car-templates')

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


if __name__ == '__main__':
    unittest.main()
