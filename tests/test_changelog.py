import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

import changelog as CL  # noqa: E402


def doc(**kw):
    d = {
        'slug': 'x', 'name': 'Car X',
        'engine': {'redline': 7500, 'redline_source': 'measured',
                   'curve': [[r, nm, nm * r / 9549] for r, nm in
                             [(3000, 300), (4000, 445), (5000, 425), (6000, 366), (7000, 322)]]},
        'gear_sets': [{'label': 'Gear set 1', 'primary': {'name': '25//25', 'value': 1.0},
                       'gears': [{'name': n, 'value': 0} for n in ('35//14', '30//19', '29//26')]}],
        'final_drive': {'adjustment': 'Differential Ratio Front', 'primaries': [],
                        'options': [{'name': '41//10', 'value': 4.1},
                                    {'name': '43//11', 'value': 43 / 11}],
                        'stock_option': '41//10', 'rest': 1.0},
        'fixed_final_drive': None,
        'tyres': {'Tarmac_Dry': {'free_radius': 0.324}, 'Gravel': {'free_radius': 0.33}},
        'steering_lock': 900,
    }
    d.update(kw)
    return d


class CarChanges(unittest.TestCase):
    def test_identical_documents_have_no_changes(self):
        self.assertEqual(CL.car_changes(doc(), doc()), [])

    def test_a_site_only_field_is_not_a_change(self):
        new = doc()
        del new['steering_lock']
        new['defaults'] = {'loaded_radius_factor': 0.978}
        self.assertEqual(CL.car_changes(doc(), new), [])

    def test_stock_final_drive(self):
        new = doc()
        new['final_drive']['stock_option'] = '43//11'
        self.assertEqual(CL.car_changes(doc(), new),
                         ['Differential Ratio Front stock: 41//10 (4.100) → 43//11 (3.909).'])

    def test_settings_stock_is_per_setting(self):
        def with_settings(stock):
            d = doc()
            d['final_drive']['settings'] = [
                {'key': k, 'adjustment': a, 'stock': stock,
                 'steps': [{'name': '35//9', 'value': 35 / 9}, {'name': '31//8', 'value': 31 / 8}]}
                for k, a in (('dfr', 'Differential Ratio Front'), ('drr', 'Differential Ratio Rear'))]
            return d
        self.assertEqual(CL.car_changes(with_settings('35//9'), with_settings('31//8')), [
            'Differential Ratio Front stock: 35//9 (3.889) → 31//8 (3.875).',
            'Differential Ratio Rear stock: 35//9 (3.889) → 31//8 (3.875).'])

    def test_a_detuned_engine(self):
        new = copy.deepcopy(doc())
        new['engine']['curve'] = [[r, nm, nm * r / 9549] for r, nm in
                                  [(3000, 300), (4000, 420), (5000, 407), (6000, 333), (7000, 279)]]
        self.assertEqual(CL.car_changes(doc(), new), [
            'Peak power: 321 hp at 7000 rpm → 290 hp at 5000 rpm.',
            'Peak torque: 445 → 420 Nm at 4000 rpm.',
            'Torque lower from 4000 to 7000 rpm, by up to 43 Nm.'])

    def test_a_change_below_the_peaks(self):
        new = copy.deepcopy(doc())
        new['engine']['curve'][0] = [3000, 320, 320 * 3000 / 9549]
        self.assertEqual(CL.car_changes(doc(), new), ['Torque higher from 3000 rpm, by up to 20 Nm.'])

    def test_gears_tyres_steering_and_rev_limit(self):
        new = copy.deepcopy(doc())
        new['gear_sets'][0]['gears'][1]['name'] = '29//19'
        new['tyres'] = {'Tarmac_Dry': {'free_radius': 0.33}}
        new['steering_lock'] = 1008
        new['engine']['redline'] = 7600
        self.assertEqual(CL.car_changes(doc(), new), [
            'Gear set 1: 2nd 30//19 → 29//19.',
            'No tyre for gravel any more.',
            'Tyre radius on dry tarmac: 0.3240 → 0.3300 m.',
            'Rev limit: 7500 → 7600 rpm.',
            'Steering lock: 900° → 1008°.'])


class UpdateChangelog(unittest.TestCase):
    def test_a_new_version_records_every_car_once(self):
        new = doc()
        new['final_drive']['stock_option'] = '43//11'
        log = CL.update_changelog({}, {'x': doc()}, {'x': new, 'y': doc(slug='y')},
                                  '0.7', '2026-11-27', '0.6')
        self.assertEqual(log['y'], [{'version': '0.7', 'date': '2026-11-27',
                                     'changes': [CL.ADDED]}])
        self.assertEqual(len(log['x'][0]['changes']), 1)
        # a later export of the same version keeps the entry, even with nothing on disk to diff
        again = CL.update_changelog(log, {'x': new}, {'x': new, 'y': doc()}, '0.7', '2026-12-01',
                                    '0.7')
        self.assertEqual(again, log)

    def test_an_unchanged_car_says_so_and_a_missing_car_keeps_its_history(self):
        log = CL.update_changelog({'gone': [{'version': '0.6', 'date': 'd', 'changes': []}]},
                                  {'x': doc()}, {'x': doc()}, '0.7', 'd', '0.6')
        self.assertEqual(log, {'gone': [{'version': '0.6', 'date': 'd', 'changes': []}],
                               'x': [{'version': '0.7', 'date': 'd', 'changes': []}]})

    def test_a_same_version_reexport_adds_nothing(self):
        self.assertEqual(CL.update_changelog({}, {'x': doc()}, {'x': doc()}, '0.7', 'd', '0.7'),
                         {'x': []})


class Page(unittest.TestCase):
    def test_entries(self):
        page = CL.render_page('Car <X>', [{'version': '0.7', 'date': '2026-11-27',
                                            'changes': ['Rev limit: 1 → 2 rpm.']},
                                           {'version': '0.6', 'date': '2026-09-20', 'changes': []}],
                              'Read from the ACR 0.7 game files.')
        self.assertIn('<h1>Car &lt;X&gt; — changelog</h1>', page)
        self.assertIn('<li>Rev limit: 1 → 2 rpm.</li>', page)
        self.assertIn('<p>No changes.</p>', page)
        self.assertIn('noindex', page)
        self.assertLess(page.index('ACR 0.7'), page.index('ACR 0.6'))

    def test_no_entries(self):
        self.assertIn('No changes recorded yet.', CL.render_page('X', [], ''))


if __name__ == '__main__':
    unittest.main()
