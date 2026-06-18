"""Validate bundled car templates: every ACR car carries the canonical tyre list,
separate front/rear pressure parameters, and never a combined "Tyre Pressure" row.

Requires PyYAML (see requirements-dev.txt).

Run: python -m unittest discover tests   (or: python tests/test_car_templates.py)
"""
import glob
import os
import unittest

import yaml

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                              'car-setups', 'car-templates')

CANONICAL_TYRES = [
    'Tarmac Soft', 'Tarmac Medium', 'Tarmac Hard', 'Tarmac Wet', 'Tarmac Winter',
    'Tarmac Snow', 'Gravel Soft', 'Gravel Medium', 'Gravel Hard', 'Snow (Studs)',
]


def load_templates():
    paths = sorted(glob.glob(os.path.join(TEMPLATES_DIR, '*.yaml')))
    docs = []
    for path in paths:
        with open(path, encoding='utf-8') as f:
            docs.append((path, yaml.safe_load(f)))
    return docs


class TestCarTemplates(unittest.TestCase):
    def test_templates_found(self):
        self.assertTrue(load_templates(), f'no *.yaml templates found in {TEMPLATES_DIR}')

    def test_acr_templates_have_canonical_tyre_list(self):
        for path, doc in load_templates():
            if doc.get('game') != 'ACR':
                continue
            with self.subTest(template=os.path.basename(path)):
                params = doc['parameters']
                tyre_rows = [p for p in params if p.get('adjustment') == 'Tyre Type']
                self.assertEqual(
                    len(tyre_rows), 1,
                    f'expected exactly one "Tyre Type" row, found {len(tyre_rows)}')
                steps = [s.strip() for s in tyre_rows[0]['discrete_steps'].split(',')]
                self.assertEqual(steps, CANONICAL_TYRES)

    def test_acr_templates_have_separate_front_rear_pressure(self):
        for path, doc in load_templates():
            if doc.get('game') != 'ACR':
                continue
            with self.subTest(template=os.path.basename(path)):
                adjustments = {p.get('adjustment') for p in doc['parameters']}
                self.assertIn('Pressure Front', adjustments)
                self.assertIn('Pressure Rear', adjustments)
                self.assertNotIn('Tyre Pressure', adjustments,
                                  'pressure must be split into Pressure Front/Rear, '
                                  'never a single combined "Tyre Pressure" row')

    def test_parameters_have_required_fields(self):
        for path, doc in load_templates():
            with self.subTest(template=os.path.basename(path)):
                for param in doc['parameters']:
                    self.assertIsInstance(param, dict)
                    for field in ('section', 'adjustment', 'order'):
                        self.assertIn(field, param, f'missing "{field}" in {param}')


if __name__ == '__main__':
    unittest.main()
