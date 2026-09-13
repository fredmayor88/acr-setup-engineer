import os
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

import calibration as C  # noqa: E402


def f32(*values):
    return b''.join(struct.pack('<f', v) for v in values)


def stages_blob(values, lead=b'\x00' * 40, int_before=8500, header=b'\x00\x09'):
    """A DA_<car> export shaped like the game's: the 3000.0 marker, an int, a short property
    header, then the rising stage floats, then a 1.0 that ends the group."""
    return (lead + f32(3000.0) + struct.pack('<i', int_before) + header + f32(*values)
            + f32(1.0) + b'\x00' * 16)


class RevStages(unittest.TestCase):
    def test_four_stages_after_the_marker(self):
        blob = stages_blob([7400.0, 7700.0, 7900.0, 8000.0])
        self.assertEqual(C.rev_stages(blob), [7400.0, 7700.0, 7900.0, 8000.0])

    def test_three_stages_like_the_alpine(self):
        blob = stages_blob([6400.0, 6700.0, 6900.0], int_before=7000, header=b'\x00\x07')
        self.assertEqual(C.rev_stages(blob)[-1], 6900.0)

    def test_the_header_length_does_not_matter(self):
        blob = (b'\x00' * 7 + f32(3000.0) + b'\x11\x22\x33\x44\x00\x00\x09\x00\x00'
                + f32(6700.0, 7000.0, 7250.0, 7300.0) + f32(1.0))
        self.assertEqual(C.rev_stages(blob)[-1], 7300.0)

    def test_a_marker_without_a_rising_group_is_skipped(self):
        # the Alfa carries a second 3000.0 followed by a single 5500.0
        blob = (b'\x00' * 8 + f32(3000.0, 5500.0, 0.0, 0.0, 0.0)
                + stages_blob([8000.0, 8400.0, 8450.0, 8500.0], lead=b''))
        self.assertEqual(C.rev_stages(blob), [8000.0, 8400.0, 8450.0, 8500.0])

    def test_no_marker_is_none(self):
        self.assertIsNone(C.rev_stages(b'\x00' * 64 + f32(7000.0, 7100.0, 7200.0)))

    def test_a_falling_group_is_not_a_group(self):
        self.assertIsNone(C.rev_stages(stages_blob([8000.0, 7900.0, 7800.0, 7700.0])))


class ResolveRevLimit(unittest.TestCase):
    cal = {'rev_limiters': {'lancia-stratos': {'rpm': 8450, 'game_v4': 8000}}}

    def test_measured_when_v4_is_unchanged(self):
        self.assertEqual(C.resolve_rev_limit('lancia-stratos', 8000.0, self.cal),
                         (8450, 'measured', None))

    def test_measured_stale_keeps_the_value_and_warns(self):
        rpm, source, warning = C.resolve_rev_limit('lancia-stratos', 8200.0, self.cal)
        self.assertEqual((rpm, source), (8450, 'measured-stale'))
        for part in ('lancia-stratos', '8000', '8200', 're-measure'):
            self.assertIn(part, warning)

    def test_estimated_is_v4_plus_100(self):
        self.assertEqual(C.resolve_rev_limit('new-car', 7300.0, self.cal),
                         (7400, 'estimated', None))

    def test_nothing_to_go_on_fails_that_car(self):
        with self.assertRaises(SystemExit):
            C.resolve_rev_limit('new-car', None, self.cal)


class StoredMeasurements(unittest.TestCase):
    def setUp(self):
        self.cal = C.load_calibration()

    def test_every_exported_car_has_a_measured_limiter(self):
        import make_gearing_chart as M
        self.assertEqual(sorted(self.cal['rev_limiters']), sorted(M.CARS))
        self.assertEqual(len(self.cal['rev_limiters']), 18)

    def test_the_doc_states_provenance(self):
        for part in ('Fred Mayor', 'SimHub', 'ACR 0.6', '2026-09-13', '2026-09-11'):
            self.assertIn(part, self.cal['_doc'])


class Fit(unittest.TestCase):
    def setUp(self):
        self.cal = C.load_calibration()

    def test_the_constant_is_the_fit(self):
        import gearing
        import export_car_data
        fitted = C.fit_factor(self.cal)
        self.assertEqual(gearing.LOADED_RADIUS_FACTOR, fitted)
        self.assertEqual(export_car_data.LOADED_RADIUS_FACTOR, fitted)

    def test_the_stored_fit_block_is_current(self):
        self.assertEqual(self.cal['fit'], C.fit_report(self.cal))

    def test_every_fitted_gear_is_within_3_percent(self):
        factor = C.fit_factor(self.cal)
        for run in self.cal['speed_runs']:
            rpm = self.cal['rev_limiters'][run['car']]['rpm']
            pred = C.run_predictions(run, rpm, factor)
            for gear, (m, p) in enumerate(zip(run['kmh'], pred), start=1):
                if gear < C.FIRST_FITTED_GEAR:
                    continue
                with self.subTest(car=run['car'], set=run['gear_set'], gear=gear):
                    self.assertLess(abs(p - m) / m, 0.03)

    def test_gear_1_is_not_fitted(self):
        gears = {g for _i, g, _f in C.implied_factors(self.cal)}
        self.assertNotIn(1, gears)


PAKS = None
try:
    import make_gearing_chart as _M
    PAKS = _M.DEFAULT_PAKS if os.path.isdir(_M.DEFAULT_PAKS) else None
except Exception:                                  # pragma: no cover
    PAKS = None


@unittest.skipUnless(PAKS, 'Assetto Corsa Rally is not installed')
class InstalledGame(unittest.TestCase):
    def test_v4_matches_the_value_each_limiter_was_measured_against(self):
        import make_gearing_chart as M
        cal = C.load_calibration()
        with tempfile.TemporaryDirectory() as tmp:
            for slug, (_a, _w, car_asset) in sorted(M.CARS.items()):
                path = C.car_asset(PAKS, car_asset, tmp)
                with self.subTest(car=slug):
                    stages = C.rev_stages(open(path, 'rb').read())
                    self.assertEqual(int(stages[-1]), cal['rev_limiters'][slug]['game_v4'])

    def test_the_206_borrows_the_xsara_torque_curve(self):
        import make_gearing_chart as M
        with tempfile.TemporaryDirectory() as tmp:
            path = C.car_asset(PAKS, M.CARS['peugeot-206-wrc-1999'][2], tmp)
            self.assertEqual(C.torque_curve_ref(open(path, 'rb').read()),
                             ('CitroenXsaraWRC', 'FC_CitroenXsaraWRC_Torque'))


class TorqueCurveRef(unittest.TestCase):
    def test_reads_the_folder_and_asset_of_the_torque_curve(self):
        blob = (b'\x00/Game/Data/Vehicles/Peugeot206WRC/DA_Peugeot206WRC\x00'
                b'/Game/Data/Vehicles/CitroenXsaraWRC/FC_CitroenXsaraWRC_Torque'
                b'/Game/Data/Vehicles/Common/FC_AutoBlip'
                b'/Game/Data/Vehicles/CitroenXsaraWRC/FC_CitroenXsaraWRC_Density')
        self.assertEqual(C.torque_curve_ref(blob),
                         ('CitroenXsaraWRC', 'FC_CitroenXsaraWRC_Torque'))

    def test_none_without_a_reference(self):
        self.assertIsNone(C.torque_curve_ref(b'/Game/Data/Vehicles/Common/FC_AutoBlip'))


if __name__ == '__main__':
    unittest.main()
