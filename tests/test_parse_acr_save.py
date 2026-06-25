"""Synthetic unit tests for the ACR save parser — no real save data needed.

We build a tiny in-memory buffer of UE-style FStrings that mimics the save's body
(metadata strings + key/value parameter pairs), and assert the parser's behaviour:
faithful extraction, generic Left/Right collapse, unknown-key passthrough, mismatch
warnings, structural confidence, and graceful failure on garbage.

Run: python -m unittest discover tests   (or: python tests/test_parse_acr_save.py)
"""
import importlib.util
import os
import struct
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                      'car-setups', 'scripts', 'parse_acr_save.py')
_spec = importlib.util.spec_from_file_location('parse_acr_save', SCRIPT)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def fstr(s):
    b = s.encode('utf-8')
    return struct.pack('<i', len(b) + 1) + b + b'\x00'


def make_save(setups):
    """setups: list of (meta_strings, [(key, value), ...]); returns raw bytes."""
    out = b'NOTGVASJUNKHEADER'  # not a GVAS header → parser scans from offset 0
    for meta, params in setups:
        for m in meta:
            out += fstr(m)
        for k, v in params:
            out += fstr(k) + fstr(v)
    return out


def parse_bytes(b):
    with tempfile.NamedTemporaryFile(suffix='.sav', delete=False) as f:
        f.write(b)
        path = f.name
    try:
        return P.parse(path)
    finally:
        os.unlink(path)


SETUP_ONE = (
    ['test one', '0.4.0.1', 'TestCarAWD', 'TestTrack', 'Gravel'],
    [
        ('Suspensions.FrontLeft.AdjusterRing', '0.050000'),
        ('Suspensions.FrontRight.AdjusterRing', '0.050000'),
        ('Suspensions.RearLeft.AdjusterRing', '0.080000'),
        ('Suspensions.RearRight.AdjusterRing', '0.080000'),
        ('Differentials.Centre.LSDPreload', '30.000000'),
        ('Differentials.Front.SomeNewParam', '5'),
        ('Differentials.Rear.LSDRamps', '(LSDRampAngles:60_70)'),
        ('Brakes.BrakesMain.FrontBias', '0.550000'),
        ('Other.Electronic.ABS', '1'),
        ('Wheels.FrontLeft.Camber', '-1.000000'),
        ('Wheels.FrontRight.Camber', '-1.500000'),  # mismatch on purpose
    ],
)
SETUP_TWO = (
    ['test two', '0.4.0.1', 'TestCarFWD', 'OtherTrack', 'Tarmac'],
    [
        ('Suspensions.FrontLeft.SpringStiffness', '50000.000000'),
        ('Suspensions.FrontRight.SpringStiffness', '50000.000000'),
        ('Axles.Front.ARBStiffness', '2000.000000'),
        ('Axles.Rear.ARBStiffness', '3000.000000'),
        ('Brakes.BrakesMain.FrontBias', '0.600000'),
        ('Gearbox.GearboxMain.GearsSet', '(GearsSets:TestSet1)'),
        ('Other.Electronic.TCS', '0'),
    ],
)


class TestParser(unittest.TestCase):
    def setUp(self):
        self.res = parse_bytes(make_save([SETUP_ONE, SETUP_TWO]))

    def test_finds_both_setups_confidently(self):
        self.assertTrue(self.res['ok'])
        self.assertEqual(self.res['setup_count'], 2)

    def test_metadata(self):
        s = self.res['setups'][0]
        self.assertEqual(s['name'], 'test one')
        self.assertEqual(s['car'], 'TestCarAWD')
        self.assertEqual(s['surface'], 'Gravel')
        self.assertEqual(s['game_version'], '0.4.0.1')

    def test_dispatch_fields(self):
        # version-aware dispatch metadata is always present
        self.assertEqual(self.res['handler_used'], 'parse_structural')
        self.assertEqual(self.res['game_versions'], ['0.4.0.1'])
        self.assertIn('save_format', self.res)
        self.assertFalse(self.res['save_format']['gvas'])   # synthetic save has no GVAS header
        self.assertGreater(self.res['nul_count'], 0)
        # 0.4 is a tested family → no untested-version note
        self.assertFalse(any('not in the tested set' in n for n in self.res['notes']))

    def _vals(self, setup):
        return {p['key']: p['value'] for p in setup['params']}

    def test_generic_left_right_collapse(self):
        v = self._vals(self.res['setups'][0])
        self.assertEqual(v.get('Suspensions.Front.AdjusterRing'), '0.05')  # collapsed + trimmed
        self.assertEqual(v.get('Suspensions.Rear.AdjusterRing'), '0.08')
        self.assertNotIn('Suspensions.FrontLeft.AdjusterRing', v)          # raw corner gone

    def test_unknown_key_passes_through(self):
        v = self._vals(self.res['setups'][0])
        self.assertEqual(v.get('Differentials.Front.SomeNewParam'), '5')
        label = next(p['label'] for p in self.res['setups'][0]['params']
                     if p['key'] == 'Differentials.Front.SomeNewParam')
        self.assertIn('Some New Param', label)  # humanized, not dropped

    def test_centre_diff_and_value_cleaning(self):
        v = self._vals(self.res['setups'][0])
        self.assertEqual(v.get('Differentials.Centre.LSDPreload'), '30')
        self.assertEqual(v.get('Differentials.Rear.LSDRamps'), '60_70')  # wrapper stripped

    def test_symmetry_mismatch_warns(self):
        warns = self.res['setups'][0]['warnings']
        self.assertTrue(any('Wheels.Front.Camber' in w for w in warns), warns)

    def test_garbage_is_low_confidence(self):
        res = parse_bytes(bytes(range(256)) * 20)
        self.assertFalse(res['ok'])
        self.assertEqual(res['setup_count'], 0)


class TestNulStripped(unittest.TestCase):
    """A save whose NUL bytes were turned into spaces (0x00 → 0x20) — seen on v0.2/v0.3
    samples — must still be recovered, via the NUL-tolerant dispatch handler."""

    def setUp(self):
        raw = make_save([SETUP_ONE, SETUP_TWO])
        self.res = parse_bytes(raw.replace(b'\x00', b'\x20'))

    def test_recovered_via_nul_tolerant_handler(self):
        self.assertEqual(self.res['nul_count'], 0)
        self.assertEqual(self.res['handler_used'], 'parse_nul_tolerant')
        self.assertTrue(self.res['ok'])
        self.assertEqual(self.res['setup_count'], 2)

    def test_param_values_intact(self):
        # the collapsed corner value survives the length-agnostic content read
        v = {p['key']: p['value'] for p in self.res['setups'][0]['params']}
        self.assertEqual(v.get('Suspensions.Front.AdjusterRing'), '0.05')
        self.assertEqual(v.get('Differentials.Rear.LSDRamps'), '60_70')

    def test_multiword_name_rejoined(self):
        # a setup name with an internal space ("test one") is recovered, not split
        self.assertEqual(self.res['setups'][0]['name'], 'test one')


class TestUntestedVersion(unittest.TestCase):
    """A confidently-parsed save from a version outside TESTED_VERSIONS is flagged, not failed."""

    def setUp(self):
        future = (['future setup', '9.9.0.1', 'TestCarFWD', 'OtherTrack', 'Tarmac'],
                  SETUP_TWO[1])
        self.res = parse_bytes(make_save([future]))

    def test_parsed_but_flagged(self):
        self.assertTrue(self.res['ok'])
        self.assertEqual(self.res['game_versions'], ['9.9.0.1'])
        self.assertTrue(any('9.9.0.1' in n and 'not in the tested set' in n
                            for n in self.res['notes']), self.res['notes'])


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'save_v0.4_multicar.sav')
OLD_FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'save_v0.2-0.3_nonul.sav')


@unittest.skipUnless(os.path.exists(FIXTURE), 'sample save fixture not present')
class TestRealFixture(unittest.TestCase):
    """Regression test against a real multi-car ACR save (PII-checked)."""

    @classmethod
    def setUpClass(cls):
        cls.res = P.parse(FIXTURE)

    def test_all_setups_parsed_confidently(self):
        self.assertTrue(self.res['ok'])
        self.assertEqual(self.res['setup_count'], 10)
        self.assertGreaterEqual(self.res['recognized_fraction'], 0.99)

    def test_dispatch_metadata(self):
        self.assertEqual(self.res['handler_used'], 'parse_structural')
        self.assertTrue(self.res['game_versions'])
        self.assertTrue(self.res['save_format']['gvas'])

    def test_expected_cars_and_drivetrains(self):
        dt = {}
        for s in self.res['setups']:
            dt[s['car']] = s['drivetrain']
        self.assertEqual(dt.get('LanciaStratosHF'), 'RWD')
        self.assertEqual(dt.get('SubaruImprezaS3'), 'AWD')
        self.assertEqual(dt.get('Peugeot306IIMaxiKitCar'), 'FWD')
        self.assertEqual(dt.get('MiniCooperS1275'), 'FWD')

    def _keys(self, car):
        s = next(s for s in self.res['setups'] if s['car'] == car)
        return [p['key'] for p in s['params']]

    def test_awd_has_centre_diff_and_transitions(self):
        keys = self._keys('SubaruImprezaS3')
        self.assertTrue(any(k.startswith('Differentials.Centre') for k in keys))
        self.assertIn('Dampers.Front.BumpTransition', keys)

    def test_fwd_has_front_only_diff(self):
        keys = self._keys('MiniCooperS1275')
        self.assertTrue(any(k.startswith('Differentials.Front') for k in keys))
        self.assertFalse(any(k.startswith('Differentials.Rear') for k in keys))
        self.assertFalse(any(k.startswith('Differentials.Centre') for k in keys))


@unittest.skipUnless(os.path.exists(OLD_FIXTURE), 'old v0.2/0.3 fixture not present')
class TestOldNulStrippedFixture(unittest.TestCase):
    """Regression test against a real v0.2.3/v0.3.0 save delivered without NUL terminators —
    recovered deterministically by the NUL-tolerant handler (PII-checked: Stratos setups +
    track names only)."""

    @classmethod
    def setUpClass(cls):
        cls.res = P.parse(OLD_FIXTURE)

    def test_recovered_confidently_via_nul_tolerant(self):
        self.assertTrue(self.res['ok'])
        self.assertEqual(self.res['setup_count'], 6)
        self.assertEqual(self.res['handler_used'], 'parse_nul_tolerant')
        self.assertEqual(self.res['nul_count'], 0)

    def test_versions_span_v02_v03(self):
        fams = sorted({'.'.join(v.split('.')[:2]) for v in self.res['game_versions']})
        self.assertEqual(fams, ['0.2', '0.3'])

    def test_known_param_value_recovered(self):
        s = self.res['setups'][0]
        v = {p['key']: p['value'] for p in s['params']}
        self.assertEqual(s['car'], 'LanciaStratosHF')
        # a front adjuster-ring value from the first setup
        self.assertEqual(v.get('Suspensions.Front.AdjusterRing'), '0.041')
        # large spring-stiffness value survives the corrupted length byte (printable-run read)
        self.assertEqual(v.get('Suspensions.Rear.SpringStiffness'), '32660')

    def test_multiword_names_recovered(self):
        # internal-space names are rejoined despite the NUL stripping
        names = {s['name'] for s in self.res['setups']}
        self.assertIn('wales down pins', names)
        self.assertIn('monte carlo up', names)

    def test_surface_recovered_where_present(self):
        # surfaces are recovered for setups that stored one (older saves don't always)
        by_name = {s['name']: s['surface'] for s in self.res['setups']}
        self.assertEqual(by_name.get('drift snow'), 'Snow')
        self.assertEqual(by_name.get('wales down pins'), 'Gravel')


if __name__ == '__main__':
    unittest.main()
