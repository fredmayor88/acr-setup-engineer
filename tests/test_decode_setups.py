"""The game's default setups, decoded out of a car's presets asset.

`tools/car-catalog/decode_setups.py` pins the schema of `PhysicsCarSetup`, a nested
unversioned struct that carries no setting ids at all - the meaning of a value is its
slot position. That makes it exactly the kind of thing a game update can move silently,
so these tests pin the numbers the Lancia Stratos's setup screen shows on game 0.6 and
assert the decoder still produces them.

Two fixtures, both checked in under `tests/fixtures/paks/`: the Stratos (RWD, one
differential, no master cylinders) and the Lancia 037 Evo 2 (master cylinders, no rear
anti-roll bar), plus the `DT_*Lists` tables the display strings are resolved through.

Run: python -m unittest discover -s tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'car-catalog'))

from acrpkg import Package                                    # noqa: E402
from datatable import rows as dt_rows                         # noqa: E402
import decode_setups as D                                     # noqa: E402
from extract_car_catalog import read_old                      # noqa: E402

PAKS = os.path.join(HERE, 'fixtures', 'paks')
TEMPLATES = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer', 'car-templates')

STRATOS = 'DA_LanciaStratosHFPresets'
EVO2 = 'DA_LanciaRally037Evo2Presets'


def package(basename):
    with open(os.path.join(PAKS, basename + '.uasset'), 'rb') as fh:
        return Package(fh.read())


def tables():
    out = {}
    for entry in sorted(os.listdir(PAKS)):
        if entry.startswith('DT_') and entry.endswith('.uasset'):
            out[entry[:-7]] = dt_rows(package(entry[:-7]))
    return out


def template(slug):
    return read_old(os.path.join(TEMPLATES, slug + '.yaml'))[1]


def setup_of(basename, slug, surface, preset='Balanced', tabs=None):
    """({adjustment: value}, [unfilled]) for one car, surface and preset."""
    tabs = tabs if tabs is not None else tables()
    pkg = package(basename)
    decoded = D.decode_car(pkg, tabs)
    values = D.compose(decoded, surface, preset)
    return D.to_adjustments(values, template(slug), tabs, D.car_keys_from(pkg))


def off_grid(slug, surface, adjustments):
    """Every (adjustment, value) the car's template wouldn't accept for that surface."""
    rows, bad = {}, []
    for r in template(slug):
        if r.get('surface') in ('', None) and r['adjustment'] not in rows:
            rows[r['adjustment']] = r
        elif r.get('surface') == surface:
            rows[r['adjustment']] = r               # a surface row narrows the base one
    for name, value in adjustments.items():
        row = rows.get(name)
        if row is None:
            bad.append((name, value, 'no template row'))
            continue
        steps = [s.strip() for s in (row['discrete_steps'] or '').split(',') if s.strip()]
        if steps:
            if str(value) not in steps:
                bad.append((name, value, f'not one of {row["discrete_steps"][:60]}'))
            continue
        try:
            low, high = float(row['min']), float(row['max'])
        except ValueError:
            continue                                # an em-dash row: nothing to check
        if not low - 1e-9 <= float(value) <= high + 1e-9:
            bad.append((name, value, f'outside {row["min"]}..{row["max"]}'))
    return bad


# The Stratos's tarmac Balanced setup as game 0.6 ships it. Every number here was read
# out of the fixture and cross-checked against the user's capture of the in-game setup
# screen; see the two notes below for the two places they disagree.
STRATOS_TARMAC = {
    'Gear Set': '1',
    'Primary Gear': '33//31*31//30',
    'Differential Ratio Rear': '65//19',
    'LSD Power/Coast Ramp Rear': '50/65',
    'LSD Preload Rear': 100,
    'Plates Number Rear': 4,
    'Spring Stiffness Front': 65000,
    'Spring Stiffness Rear': 42500,
    'Adjuster Ring Front': 0.048,
    'Slow Bump Front': 6250,
    'Slow Rebound Front': 7250,
    'Fast Bump Front': 4750,
    'Fast Rebound Front': 6250,
    'Slow Bump Rear': 4250,
    'Slow Rebound Rear': 5750,
    'Fast Bump Rear': 3750,
    'Fast Rebound Rear': 5250,
    'Anti-roll Bar Stiffness Front': 3250,
    'Anti-roll Bar Stiffness Rear': 2500,
    'Front Bias': 0.57,
    'Camber Front': -2.4,
    # The capture reads -2. The asset stores -1.9 (float 0xbff33333) in the two rear
    # corners of PhysicsCarSetup's wheel array and nothing overrides it: the tarmac
    # surface's 19 overrides carry no camber, and Balanced is empty. -1.9 is on the
    # template's grid, so it is a real value, not a rounding artefact of the decode.
    'Camber Rear': -1.9,
    'Pressure Front': 27,
    'Pressure Rear': 26,
    'Brake Pads Front': 'MEDIUM',
    'Brake Discs Front': '267/156X28 B TYPE1',
    'Brake Calipers Rear': '4X38.1 TYPE1',
}

STRATOS_GRAVEL = {
    'Spring Stiffness Front': 35000,
    'Spring Stiffness Rear': 20000,
    'Adjuster Ring Front': 0.115,
    'Slow Bump Front': 5000,
    'Fast Bump Rear': 1750,
    'Front Bias': 0.53,
    'Camber Front': -2,
    'Camber Rear': -3,
    'Pressure Front': 30,
    'LSD Preload Rear': 90,
    'LSD Power/Coast Ramp Rear': '45/50',
    'Gear Set': '2',
    'Brake Discs Front': '271/160X22 P TYPE1',
    'Anti-roll Bar Stiffness Front': 4250,
    'Anti-roll Bar Stiffness Rear': 0,
}

# The 037's tarmac Balanced setup as the user captured it on game 0.5. This is a sanity
# check, not a contract: the car was retuned between 0.5 and 0.6, so the test reports the
# differences instead of asserting them. See test_evo2_tarmac_matches_the_0_5_capture.
EVO2_TARMAC_0_5 = {
    'Gear Set': '2',
    'LSD Power/Coast Ramp Rear': '45/55',
    'LSD Preload Rear': 120,
    'Plates Number Rear': 6,
    'Spring Stiffness Front': 50000,
    'Spring Stiffness Rear': 35000,
    'Slow Bump Front': 3750,
    'Fast Bump Front': 3250,
    'Camber Front': -1.4,
    'Camber Rear': -1.5,
    'Pressure Front': 32,
    'Front Bias': 0.5,
}


class StratosTarmac(unittest.TestCase):
    def test_every_value(self):
        adjustments, _ = setup_of(STRATOS, 'lancia-stratos', 'Tarmac')
        for name, want in sorted(STRATOS_TARMAC.items()):
            with self.subTest(name):
                self.assertIn(name, adjustments)
                self.assertEqual(want, adjustments[name])

    def test_tyre_type_is_unfilled(self):
        """The presets asset has no tyre setting at all - not even a name for one."""
        adjustments, unfilled = setup_of(STRATOS, 'lancia-stratos', 'Tarmac')
        self.assertNotIn('Tyre Type', adjustments)
        self.assertIn('Tyre Type', unfilled)
        names = package(STRATOS).names
        self.assertFalse([n for n in names if 'Tyre' in n and 'Pressure' not in n])


class StratosGravel(unittest.TestCase):
    def test_every_value(self):
        adjustments, _ = setup_of(STRATOS, 'lancia-stratos', 'Gravel')
        for name, want in sorted(STRATOS_GRAVEL.items()):
            with self.subTest(name):
                self.assertIn(name, adjustments)
                self.assertEqual(want, adjustments[name])

    def test_an_override_with_no_stored_value_is_zero(self):
        """Gravel's rear anti-roll bar is an empty override export, and that means 0.

        "A property equal to its default is not written" applies to the override object
        too, so reading a missing slot as "no value" instead of 0 would silently leave
        the tarmac bar fitted on gravel.
        """
        decoded = D.decode_car(package(STRATOS), tables())
        self.assertEqual(2500, decoded['base']['Axles.Rear.ARBStiffness'])
        self.assertEqual(0, decoded['surfaces']['Gravel']['overrides']
                            ['Axles.Rear.ARBStiffness'])


class Evo2(unittest.TestCase):
    def test_tarmac_matches_the_0_5_capture(self):
        """Report every difference from the 0.5 capture; assert only what 0.6 still has.

        The 037's 0.6 tarmac defaults are far stiffer than the 0.5 capture, and six of
        the captured values turn up on 0.6's *gravel* preset instead - so the capture is
        not a usable contract for 0.6. What is asserted is that the four list-valued
        settings the brief names are decoded at all and land on the template's grid.
        """
        tarmac, _ = setup_of(EVO2, 'lancia-037-evoluzione-2-1984', 'Tarmac')
        gravel, _ = setup_of(EVO2, 'lancia-037-evoluzione-2-1984', 'Gravel')
        report = []
        for name, captured in sorted(EVO2_TARMAC_0_5.items()):
            if tarmac.get(name) != captured:
                report.append(f'    {name:28} 0.5 capture {captured!r:16} '
                              f'0.6 tarmac {tarmac.get(name)!r:16} '
                              f'0.6 gravel {gravel.get(name)!r}')
        if report:
            print('\n  037 Evo 2 tarmac Balanced vs the 0.5 capture:\n' + '\n'.join(report))
        for name in ('Gear Set', 'LSD Power/Coast Ramp Rear', 'LSD Preload Rear',
                     'Plates Number Rear'):
            with self.subTest(name):
                self.assertIn(name, tarmac)
        self.assertEqual(6, tarmac['Plates Number Rear'])
        self.assertEqual([], off_grid('lancia-037-evoluzione-2-1984', 'Tarmac', tarmac))

    def test_the_bore_fallback_fills_one_rear_caliper_and_refuses_the_other(self):
        """The 037's rear axle is where position-for-position mapping runs out.

        Three calipers fit its rear discs and the screenshot-era template lists two, so the
        fallback matches the part's bore instead. Tarmac fits the `4x42`, which is the only
        `4x42` on either side - filled. Gravel fits `Brembo_2Pot_Type4_2x48`, and the axle
        also takes an `ATE_Porsche_911_S-Type_2x48`; the `TYPE<n>` in the template's strings
        is a UI number that is in no game file, so nothing can say which of the two the
        single `2x48 Type3` step means - refused and reported, not guessed.
        """
        tarmac, tarmac_gaps = setup_of(EVO2, 'lancia-037-evoluzione-2-1984', 'Tarmac')
        gravel, gravel_gaps = setup_of(EVO2, 'lancia-037-evoluzione-2-1984', 'Gravel')
        self.assertEqual('4x42 Type1', tarmac['Brake Calipers Rear'])
        self.assertNotIn('Brake Calipers Rear', tarmac_gaps)
        self.assertNotIn('Brake Calipers Rear', gravel)
        self.assertIn('Brake Calipers Rear', gravel_gaps)

    def test_master_cylinders_come_out_of_the_base_struct(self):
        """The 037 has the two brake slots the Stratos doesn't - slots 8 and 9."""
        base = D.decode_car(package(EVO2), tables())['base']
        self.assertEqual(('db', 'MasterCylinders', '19.05'),
                         base['Brakes.BrakesMain.MasterCylinderFront'])
        self.assertEqual(('db', 'MasterCylinders', '19.05'),
                         base['Brakes.BrakesMain.MasterCylinderRear'])


class Structure(unittest.TestCase):
    def test_surfaces_and_presets(self):
        decoded = D.decode_car(package(STRATOS), tables())
        self.assertEqual([('Tarmac', 'Balanced'), ('Gravel', 'Balanced')],
                         D.surfaces_and_presets(decoded))

    def test_balanced_is_the_surface_layer(self):
        """Every car ships an empty `Balanced` variant, so it must change nothing."""
        decoded = D.decode_car(package(STRATOS), tables())
        self.assertEqual({}, decoded['surfaces']['Tarmac']['presets']['Balanced'])
        self.assertEqual(D.compose(decoded, 'Tarmac'),
                         D.compose(decoded, 'Tarmac', 'Balanced'))

    def test_compose_layers_base_then_surface(self):
        decoded = D.decode_car(package(STRATOS), tables())
        self.assertEqual(28, decoded['base']['Wheels.FrontLeft.TyrePressure'])
        self.assertEqual(27, D.compose(decoded, 'Tarmac')['Wheels.FrontLeft.TyrePressure'])
        self.assertEqual(30, D.compose(decoded, 'Gravel')['Wheels.FrontLeft.TyrePressure'])

    def test_an_unknown_surface_or_preset_raises(self):
        decoded = D.decode_car(package(STRATOS), tables())
        with self.assertRaises(KeyError):
            D.compose(decoded, 'Snow')
        with self.assertRaises(KeyError):
            D.compose(decoded, 'Tarmac', 'Aggressive')

    def test_left_that_disagrees_with_right_raises(self):
        """A corner that differs side to side means the walk slipped - never average it."""
        tabs = tables()
        pkg = package(STRATOS)
        decoded = D.decode_car(pkg, tabs)
        values = D.compose(decoded, 'Tarmac', 'Balanced')
        values['Wheels.RearLeft.Camber'] = -1.2
        with self.assertRaises(AssertionError):
            D.to_adjustments(values, template('lancia-stratos'), tabs,
                             D.car_keys_from(pkg))

    def test_every_composed_value_is_on_the_template_grid(self):
        for basename, slug in ((STRATOS, 'lancia-stratos'),
                               (EVO2, 'lancia-037-evoluzione-2-1984')):
            decoded = D.decode_car(package(basename), tables())
            for surface, preset in D.surfaces_and_presets(decoded):
                with self.subTest(slug=slug, surface=surface):
                    adjustments, _ = setup_of(basename, slug, surface, preset)
                    self.assertEqual([], off_grid(slug, surface, adjustments))

    def test_the_schema_accounts_for_every_byte(self):
        """The walk must land exactly on the export's 4-byte trailer, or it isn't pinned."""
        for basename in (STRATOS, EVO2):
            with self.subTest(basename):
                self.assertTrue(D.decode_base(package(basename)))

    def test_a_db_row_the_car_cannot_take_is_reported(self):
        """The DB-row check has to look in the list the value is actually resolved from.

        A bare `Discs` hint is not a table name, so checking `DT_Discs` finds nothing and
        the check passes on anything. Here a disc the Stratos does not fit is planted in a
        decoded car and the note has to name it.
        """
        tabs = tables()
        keys = D.car_keys_from(package(STRATOS))
        decoded = D.decode_car(package(STRATOS), tabs)
        self.assertNotIn('Brakes.FrontLeft.Disc', [n.split(':')[0] for n in decoded['notes']])
        decoded['surfaces']['Tarmac']['overrides']['Brakes.FrontLeft.Disc'] = (
            'db', 'Discs', 'Brembo_332mm_Type1_332x30_Baffled&Drilled_4x98')
        notes = D.db_row_notes(decoded, tabs, keys)
        self.assertIn('Brakes.FrontLeft.Disc: Brembo_332mm_Type1_332x30_Baffled&Drilled_4x98'
                      ' is in no Discs list for LanciaStratosHF', notes)

    def test_the_only_note_on_the_fixtures_is_the_primary_gear_filler(self):
        """The check is live, not vacuous - and what it finds on 0.6 is real.

        The Stratos's `PhysicsCarSetup` leaves `25//25` in the primary-gear slot and its
        `DT_PrimaryGearsLists` row has no such entry, so the base carries no usable primary
        gear; both of its surfaces override it, which is why the composed setups are fine.
        """
        self.assertEqual(['Gearbox.GearboxMain.GearPrimary: 25//25 is in no Gears list '
                          'for LanciaStratosHF'],
                         D.decode_car(package(STRATOS), tables())['notes'])
        self.assertEqual([], D.decode_car(package(EVO2), tables())['notes'])

    def test_an_unset_db_row_is_unfilled_not_a_crash(self):
        """A zero-masked FName decodes as None; `resolve` must not try to spell it."""
        tabs = tables()
        pkg = package(STRATOS)
        values = D.compose(D.decode_car(pkg, tabs), 'Tarmac', 'Balanced')
        values['Brakes.FrontLeft.PadCompound'] = ('db', 'Pads', None)
        values['Brakes.FrontRight.PadCompound'] = ('db', 'Pads', None)
        adjustments, unfilled = D.to_adjustments(values, template('lancia-stratos'), tabs,
                                                 D.car_keys_from(pkg))
        self.assertNotIn('Brake Pads Front', adjustments)
        self.assertIn('Brake Pads Front', unfilled)

    def test_per_surface_disc_lists_are_prefixes_of_the_union(self):
        """What makes one union stand in for four per-surface lists - and its guard.

        The rows are not identical (the Delta fits 9 front discs on tarmac and 5 on
        gravel), but each is a prefix of the union on all 18 cars, so a disc's index is the
        same whichever surface asks. `_disc_options` raises the moment that stops holding.
        """
        tabs = tables()
        for wheels, axle in (('LanciaStratosHF', 'Front'), ('LanciaStratosHF', 'Rear'),
                             ('LanciaRally037Evoluzione2', 'Front'),
                             ('LanciaRally037Evoluzione2', 'Rear')):
            with self.subTest(wheels=wheels, axle=axle):
                union = D._disc_options(tabs, wheels, axle)
                rows = [v for r, v in tabs['DT_DiscsLists'].items()
                        if r.startswith(wheels + '_') and r.endswith('_' + axle)]
                self.assertEqual(4, len(rows))
                for row in rows:
                    self.assertEqual(list(row), union[:len(row)])
        broken = {'DT_DiscsLists': {'X_Tarmac_Front': ['a', 'b'], 'X_Gravel_Front': ['b']}}
        with self.assertRaises(AssertionError):
            D._disc_options(broken, 'X', 'Front')

    def test_a_per_corner_array_that_is_not_four_long_raises(self):
        with self.assertRaises(AssertionError):
            D._by_corner([{}, {}, {}], 'Dampers')
        self.assertEqual([], D._by_corner([], 'Dampers'))
        self.assertEqual(4, len(D._by_corner([{}] * 4, 'Dampers')))

    def test_car_keys_come_out_of_the_asset(self):
        self.assertEqual({'wheels': 'LanciaStratosHF', 'gears_sets': 'LanciaStratos'},
                         D.car_keys_from(package(STRATOS)))
        self.assertEqual({'wheels': 'LanciaRally037Evoluzione2',
                          'gears_sets': 'LanciaRally037Evo2'},
                         D.car_keys_from(package(EVO2)))


if __name__ == '__main__':
    unittest.main()
