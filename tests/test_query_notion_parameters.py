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


class TestQuery(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
