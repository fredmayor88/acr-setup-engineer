import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from export_car_data import build_car_json  # noqa: E402


def stratos_inputs():
    """A trimmed but real Lancia Stratos, read from the game files on 2026-09-12."""
    sets = [
        [('42//15', 2.800), ('40//19', 2.053), ('37//23', 1.619),
         ('33//25', 1.320), ('30//26', 1.154)],
        [('44//14', 3.143), ('38//17', 2.235), ('37//21', 1.762),
         ('34//24', 1.417), ('30//26', 1.154)],
    ]
    curve = [(3000, 198.0), (6000, 260.0), (7750, 240.0), (8750, 192.0)]
    fd = {
        'adjustment': 'Differential Ratio Rear',
        'primaries': [('35//30*33//28', 1.375), ('33//31*31//30', 1.100)],
        'options': [('65//17', 3.8235), ('65//19', 3.4211)],
        'stock_option': '65//19',
        'rest': 1.0,
    }
    tyres = {'Tarmac_Dry': ('PirelliT03', 0.2960),
             'Montecarlo': ('PirelliTM00', 0.3135)}
    return sets, curve, fd, tyres


class BuildCarJson(unittest.TestCase):
    def setUp(self):
        sets, curve, fd, tyres = stratos_inputs()
        self.doc = build_car_json('lancia-stratos', 'Lancia Stratos HF', 'Rear',
                                  sets, curve, fd, tyres, '2026-09-12')

    def test_identity_fields(self):
        self.assertEqual(self.doc['slug'], 'lancia-stratos')
        self.assertEqual(self.doc['name'], 'Lancia Stratos HF')
        self.assertEqual(self.doc['axle'], 'Rear')
        self.assertEqual(self.doc['generated'], '2026-09-12')

    def test_redline_is_the_highest_rpm_in_the_curve(self):
        self.assertEqual(self.doc['engine']['redline'], 8750)

    def test_curve_carries_power_in_kw(self):
        # kW = Nm * rpm / 9549
        row = [r for r in self.doc['engine']['curve'] if r[0] == 6000][0]
        self.assertEqual(row[1], 260.0)
        self.assertAlmostEqual(row[2], 260.0 * 6000 / 9549, places=3)

    def test_peaks_are_located_by_value_not_assumed(self):
        self.assertEqual(self.doc['engine']['peak_torque_rpm'], 6000)
        self.assertEqual(self.doc['engine']['peak_power_rpm'], 7750)

    def test_gear_sets_carry_label_spelling_and_value(self):
        first = self.doc['gear_sets'][0]
        self.assertEqual(first['label'], 'Gear set 1')
        self.assertEqual(first['gears'][0], {'name': '42//15', 'value': 2.800})
        self.assertEqual(len(self.doc['gear_sets'][1]['gears']), 5)

    def test_tyres_carry_free_radius_not_circumference(self):
        # the browser applies the loaded-radius factor, so the stored value is the
        # free radius and nothing else
        self.assertEqual(self.doc['tyres']['Tarmac_Dry'],
                         {'asset': 'PirelliT03', 'free_radius': 0.2960})

    def test_default_factor_is_exported(self):
        self.assertEqual(self.doc['defaults']['loaded_radius_factor'], 0.9562)

    def test_final_drive_options_carry_spelling_and_value(self):
        fd = self.doc['final_drive']
        self.assertEqual(fd['adjustment'], 'Differential Ratio Rear')
        self.assertEqual(fd['stock_option'], '65//19')
        self.assertEqual(fd['rest'], 1.0)
        self.assertEqual(fd['options'][0], {'name': '65//17', 'value': 3.8235})
        self.assertEqual(len(fd['primaries']), 2)

    def test_non_adjustable_final_drive_is_null(self):
        sets, curve, _, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Front', sets, curve, None, tyres, '2026-09-12')
        self.assertIsNone(doc['final_drive'])


if __name__ == '__main__':
    unittest.main()
