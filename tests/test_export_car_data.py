import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from export_car_data import build_car_json  # noqa: E402
import make_gearing_chart as _M  # noqa: E402


def stratos_inputs():
    """A trimmed but real Lancia Stratos, read from the game files on 2026-09-12."""
    sets = [
        ([('42//15', 2.800), ('40//19', 2.053), ('37//23', 1.619),
          ('33//25', 1.320), ('30//26', 1.154)], ('33//31*31//30', 1.100)),
        ([('44//14', 3.143), ('38//17', 2.235), ('37//21', 1.762),
          ('34//24', 1.417), ('30//26', 1.154)], ('33//31*31//30', 1.100)),
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


# The Stratos's resolved rev limit: measured, and well short of its curve's 8750 end.
RL = {'rpm': 8450, 'source': 'measured', 'game_v4': 8000,
      'curve_source': 'LanciaStratosHF', 'curve_from': None}


class BuildCarJson(unittest.TestCase):
    def setUp(self):
        sets, curve, fd, tyres = stratos_inputs()
        self.doc = build_car_json('lancia-stratos', 'Lancia Stratos HF', 'Rear',
                                  sets, curve, fd, tyres, rev_limit=RL)

    def test_identity_fields(self):
        self.assertEqual(self.doc['slug'], 'lancia-stratos')
        self.assertEqual(self.doc['name'], 'Lancia Stratos HF')
        self.assertEqual(self.doc['axle'], 'Rear')

    def test_redline_is_the_resolved_rev_limit_not_the_curve_end(self):
        self.assertEqual(self.doc['engine']['redline'], 8450)
        self.assertEqual(self.doc['engine']['redline_source'], 'measured')
        self.assertEqual(self.doc['engine']['game_v4'], 8000)

    def test_the_curve_keeps_its_full_extent(self):
        self.assertEqual(self.doc['engine']['curve'][-1][0], 8750)

    def test_a_rev_limit_is_required(self):
        sets, curve, fd, tyres = stratos_inputs()
        with self.assertRaises(ValueError):
            build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres)

    def test_an_own_curve_has_no_borrowed_owner(self):
        self.assertEqual(self.doc['engine']['curve_source'], 'LanciaStratosHF')
        self.assertIsNone(self.doc['engine']['curve_from'])

    def test_a_borrowed_curve_names_its_owner(self):
        sets, curve, fd, tyres = stratos_inputs()
        borrowed = dict(RL, curve_source='CitroenXsaraWRC',
                        curve_from={'slug': 'citroen-xsara-wrc-2003',
                                    'name': 'Citroen Xsara WRC 2003'})
        doc = build_car_json('peugeot-206-wrc-1999', 'Peugeot 206 WRC 1999', 'Rear',
                             sets, curve, fd, tyres, rev_limit=borrowed)
        self.assertEqual(doc['engine']['curve_source'], 'CitroenXsaraWRC')
        self.assertEqual(doc['engine']['curve_from']['name'], 'Citroen Xsara WRC 2003')

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
        self.assertEqual(first['primary'], {'name': '33//31*31//30', 'value': 1.100})

    def test_tyres_carry_free_radius_not_circumference(self):
        # the browser applies the loaded-radius factor, so the stored value is the
        # free radius and nothing else
        self.assertEqual(self.doc['tyres']['Tarmac_Dry'],
                         {'asset': 'PirelliT03', 'free_radius': 0.2960})

    def test_default_factor_is_exported(self):
        import gearing
        self.assertEqual(self.doc['defaults']['loaded_radius_factor'], 0.9904)
        self.assertEqual(self.doc['defaults']['loaded_radius_factor'],
                         gearing.LOADED_RADIUS_FACTOR)

    def test_final_drive_options_carry_spelling_and_value(self):
        fd = self.doc['final_drive']
        self.assertEqual(fd['adjustment'], 'Differential Ratio Rear')
        self.assertEqual(fd['stock_option'], '65//19')
        self.assertEqual(fd['rest'], 1.0)
        self.assertEqual(fd['options'][0], {'name': '65//17', 'value': 3.8235})
        self.assertEqual(len(fd['primaries']), 2)

    def test_non_adjustable_final_drive_is_null(self):
        sets, curve, _, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Front', sets, curve, None, tyres, rev_limit=RL)
        self.assertIsNone(doc['final_drive'])

    def test_adjustable_car_has_no_fixed_final_drive(self):
        # the primary x option combinations already carry the ratio; a second copy
        # could drift out of step with them
        self.assertIsNone(self.doc['fixed_final_drive'])

    def test_non_adjustable_car_carries_its_fixed_final_drive(self):
        # without this the document has nothing below the gearbox at all, and no
        # absolute km/h is reachable for the car
        sets, curve, _, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Front', sets, curve, None, tyres,
                             fixed_final_drive=4.230769, rev_limit=RL)
        self.assertIsNone(doc['final_drive'])
        self.assertAlmostEqual(doc['fixed_final_drive'], 4.230769, places=6)

    def test_fixed_final_drive_is_dropped_when_the_car_is_adjustable(self):
        # the two fields are mutually exclusive whatever the caller passes
        sets, curve, fd, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres,
                             fixed_final_drive=4.230769, rev_limit=RL)
        self.assertIsNotNone(doc['final_drive'])
        self.assertIsNone(doc['fixed_final_drive'])

    def test_fixed_final_drive_key_is_always_present(self):
        # the browser reads the key unconditionally, so it must exist on every car
        self.assertIn('fixed_final_drive', self.doc)


def mini_inputs():
    """The Mini Cooper S, whose four gear sets each ship a different primary.

    Read from DA_MiniCooperS1275_Gearset_0..3 on 2026-09-12. First gear is 32//13 in
    every set, so the primary is the only thing distinguishing them — publish one
    car-level primary and all four sets collapse onto the same speeds.
    """
    sets = [
        ([('32//13', 2.4615), ('29//17', 1.7059), ('25//21', 1.1905),
          ('23//24', 0.9583)], ('24//23', 1.043478)),
        ([('32//13', 2.4615), ('28//17', 1.6471), ('24//20', 1.2000),
          ('22//23', 0.9565)], ('23//22', 1.045455)),
        ([('32//13', 2.4615), ('27//18', 1.5000), ('23//22', 1.0455),
          ('20//25', 0.8000)], ('25//20', 1.250000)),
        ([('32//13', 2.4615), ('28//19', 1.4737), ('24//23', 1.0435),
          ('20//26', 0.7692)], ('26//20', 1.300000)),
    ]
    curve = [(3000, 90.0), (6000, 110.0)]
    tyres = {'Tarmac_Dry': ('DunlopT00', 0.2600)}
    return sets, curve, tyres


class PerGearSetPrimary(unittest.TestCase):
    """The primary belongs to the gear set, not to the car."""

    def setUp(self):
        sets, curve, tyres = mini_inputs()
        self.doc = build_car_json('mini-cooper-s-1964', 'Mini Cooper S 1964', 'Front',
                                  sets, curve, None, tyres, fixed_final_drive=3.7647,
                                  rev_limit=dict(RL, rpm=7400))

    def test_each_gear_set_carries_its_own_primary(self):
        got = [(gs['primary']['name'], gs['primary']['value'])
               for gs in self.doc['gear_sets']]
        self.assertEqual(got, [('24//23', 1.043478), ('23//22', 1.045455),
                               ('25//20', 1.250000), ('26//20', 1.300000)])

    def test_the_primaries_are_not_all_the_same(self):
        # the regression this guards: publishing set 1's primary for every set
        values = {gs['primary']['value'] for gs in self.doc['gear_sets']}
        self.assertEqual(len(values), 4)

    def test_a_car_level_primary_would_overstate_the_last_set(self):
        # set 4's primary is 24.6% taller than set 1's, so reusing set 1's would put
        # set 4's speeds 24.6% high
        first = self.doc['gear_sets'][0]['primary']['value']
        last = self.doc['gear_sets'][3]['primary']['value']
        self.assertAlmostEqual(last / first, 1.24583, places=4)

    def test_no_selectable_primaries_means_an_empty_list_not_a_fake_one(self):
        # this car has no adjustable Primary Gear; the gear set's own primary stands
        self.assertIsNone(self.doc['final_drive'])

    def test_speed_composes_from_the_set_primary(self):
        # gear * set primary * fixed_final_drive, per the documented formula
        import math
        d = self.doc
        circ = 2 * math.pi * d['tyres']['Tarmac_Dry']['free_radius'] * \
            d['defaults']['loaded_radius_factor']
        rl = d['engine']['redline']

        def speed(i, gear_index):
            gs = d['gear_sets'][i]
            g = gs['gears'][gear_index]['value']
            return rl * circ * 0.06 / (g * gs['primary']['value']
                                       * d['fixed_final_drive'])

        # First gear is the identical 32//13 in all four sets, so the primary is the
        # only thing that can separate them. Set 4's is 24.6% taller, so its first gear
        # must top out 24.6% slower — under the old car-level primary all four sets
        # reported exactly the same first-gear speed, which is the visible symptom.
        self.assertAlmostEqual(speed(0, 0) / speed(3, 0), 1.24583, places=4)
        self.assertNotAlmostEqual(speed(0, 0), speed(3, 0), places=1)


def template(*blocks):
    """A car template's adjustment list: (adjustment, discrete_steps) in setup-screen order."""
    head = 'car: "Test"\ndrivetrain: "AWD"\nparameters:\n'
    return head + ''.join(
        f'  - section: "Differentials"\n    adjustment: "{name}"\n    order: {5000 + i}\n'
        f'    min: "\u2014"\n    max: "\u2014"\n    unit: ""\n    discrete_steps: "{steps}"\n'
        for i, (name, steps) in enumerate(blocks))


# Stock drivetrain chains as DA_<car> stores them (centre diff, centre->front, centre->rear,
# front diff, rear diff), read from the ACR 0.6 game files on 2026-09-13.
DELTA_CHAIN = ['51//13', '25//25', '13//34', '25//25', '30//12']
XSARA_CHAIN = ['37//26', '(27+48)//27', '26//28', '25//25', '27//9']
P206_CHAIN = ['24//24', '25//25', '25//25', '46//14*26//16', '46//14*26//16']
IMPREZA_CHAIN = ['25//25', '25//25', '31//31', '35//9', '35//9']

DELTA_TEMPLATE = template(
    ('Plates Number Front', ''),
    ('Center Differential Ratio', '55//12, 51//13, 53//18'),
    ('Center Ratio to Rear', '13//34, 17//38'),
    ('Differential Ratio Rear', '34//13, 30//12, 34//14'),
    ('LSD Power/Coast Ramp Rear', '30//50, 45//60'))
P206_TEMPLATE = template(
    ('Primary Gear', '21//24, 22//24, 21//25'),
    ('Differential Ratio Front', '43//13*21//13, 46//14*26//16, 40//18*26//16'),
    ('Center Differential Ratio', '31//21, 24//24'),
    ('Differential Ratio Rear', '46//14*26//16, 40//18*26//16'))


class AveragedAxles(unittest.TestCase):
    """Ruling R51: the ratio below the gearbox is the mean of the front and rear chains."""

    def test_only_the_five_measured_or_assumed_cars(self):
        import export_car_data as E
        self.assertEqual(E.AVERAGED_AXLE_CARS, {
            'lancia-delta-integrale-evoluzione-1992', 'peugeot-206-wrc-1999',
            'subaru-impreza-555-s3-1993', 'citroen-xsara-wrc-2003', 'audi-quattro-gr4-1981'})

    def test_the_template_settings_are_the_chain_ratios_in_screen_order(self):
        import export_car_data as E
        self.assertEqual([n for n, _ in E.template_ratio_settings(P206_TEMPLATE)],
                         ['Differential Ratio Front', 'Center Differential Ratio',
                          'Differential Ratio Rear'])
        self.assertEqual(E.template_ratio_settings(DELTA_TEMPLATE)[1],
                         ('Center Ratio to Rear', ['13//34', '17//38']))

    def test_the_delta_puts_the_centre_diff_before_the_split(self):
        import export_car_data as E
        fd = E.averaged_final_drive(DELTA_TEMPLATE, DELTA_CHAIN, [])
        self.assertEqual([(s['key'], s['adjustment'], s['stock']) for s in fd['settings']], [
            ('cdr', 'Center Differential Ratio', '51//13'),
            ('ctr', 'Center Ratio to Rear', '13//34'),
            ('drr', 'Differential Ratio Rear', '30//12')])
        self.assertEqual(fd['settings'][0]['steps'][0], {'name': '55//12', 'value': 55 / 12})
        self.assertEqual(fd['formula'], {'pre': ['cdr'], 'front': [], 'rear': ['ctr', 'drr'],
                                         'fixed_pre': 1.0, 'fixed_front': 1.0,
                                         'fixed_rear': 1.0, 'centre_differential': True,
                                         'measured': True})
        self.assertEqual(fd['rows'], ['cdr'])
        self.assertEqual([o for o, _v in fd['options']], ['55//12', '51//13', '53//18'])

    def test_stock_below_is_the_mean_of_the_two_chains(self):
        import export_car_data as E
        from gearing import averaged_final_drive
        fd = E.averaged_final_drive(DELTA_TEMPLATE, DELTA_CHAIN, [])
        want = 51 / 13 * (1 + 13 / 34 * 30 / 12) / 2
        self.assertAlmostEqual(averaged_final_drive(DELTA_CHAIN), want, places=12)
        # rest * option keeps its meaning with every other setting at stock
        self.assertAlmostEqual(fd['rest'] * 51 / 13, want, places=12)

    def test_the_formula_follows_any_setting(self):
        import export_car_data as E
        fd = E.averaged_final_drive(DELTA_TEMPLATE, DELTA_CHAIN, [])
        values = {'cdr': 55 / 12, 'ctr': 17 / 38, 'drr': 34 / 13}
        self.assertAlmostEqual(E.averaged_below(fd['formula'], values),
                               55 / 12 * (1 + 17 / 38 * 34 / 13) / 2, places=12)

    def test_the_xsara_keeps_its_fixed_front_and_rear_chains_apart(self):
        import export_car_data as E
        fd = E.averaged_final_drive(template(('Center Differential Ratio', '39//24, 37//26')),
                                    XSARA_CHAIN, [])
        f = fd['formula']
        self.assertEqual((f['pre'], f['front'], f['rear']), (['cdr'], [], []))
        self.assertAlmostEqual(f['fixed_front'], 75 / 27, places=12)
        self.assertAlmostEqual(f['fixed_rear'], 26 / 28 * 27 / 9, places=12)
        self.assertAlmostEqual(fd['rest'], (75 / 27 + 26 / 28 * 3) / 2, places=12)

    def test_the_206_rows_set_both_differentials_over_the_steps_they_share(self):
        import export_car_data as E
        fd = E.averaged_final_drive(P206_TEMPLATE, P206_CHAIN, ['21//24', '22//24', '21//25'])
        self.assertEqual(fd['rows'], ['dfr', 'drr'])
        self.assertEqual([o for o, _v in fd['options']], ['46//14*26//16', '40//18*26//16'])
        self.assertEqual(fd['stock_option'], '46//14*26//16')
        self.assertEqual(fd['formula']['pre'], ['cdr'])
        self.assertEqual(fd['adjustment'], 'Differential Ratio Front + Differential Ratio Rear')
        self.assertEqual([p for p, _v in fd['primaries']], ['21//24', '22//24', '21//25'])
        self.assertAlmostEqual(fd['rest'], 1.0, places=12)

    def test_the_audi_alone_has_no_centre_differential_and_is_not_measured(self):
        import export_car_data as E
        import calibration as CAL
        self.assertEqual(E.NO_CENTRE_DIFFERENTIAL, {'audi-quattro-gr4-1981'})
        with open(os.path.join(_M.TEMPLATES, 'audi-quattro-gr4-1981.yaml'),
                  encoding='utf-8') as fh:
            self.assertNotIn('adjustment: "Center', fh.read())
        measured = {r['car'] for r in CAL.load_calibration()['speed_runs']}
        self.assertEqual(sorted(E.AVERAGED_AXLE_CARS - measured), ['audi-quattro-gr4-1981'])
        audi = template(('Differential Ratio Front', '39//8, 37//10'),
                        ('Differential Ratio Rear', '39//8, 37//10'))
        fd = E.averaged_final_drive(audi, ['25//25', '25//25', '25//25', '37//10', '37//10'], [],
                                    centre_differential=False, measured=False)
        self.assertEqual((fd['formula']['centre_differential'], fd['formula']['measured']),
                         (False, False))

    def test_a_fixed_ratio_on_a_path_with_settings_fails_the_car(self):
        import export_car_data as E
        # a fixed 27//25 centre-to-rear transfer on a path whose rear diff is a setting
        rear_only = template(('Differential Ratio Rear', '34//13, 30//12'))
        with self.assertRaises(SystemExit) as caught:
            E.averaged_final_drive(rear_only, ['51//13', '25//25', '27//25', '25//25', '30//12'], [])
        self.assertIn('rear', str(caught.exception))
        # a fixed ratio before the split with no centre setting is fine, as on the Xsara
        E.averaged_final_drive(template(('Center Differential Ratio', '39//24, 37//26')),
                               XSARA_CHAIN, [])

    def test_a_stock_ratio_that_is_not_a_step_fails_the_car(self):
        import export_car_data as E
        with self.assertRaises(SystemExit):
            E.averaged_final_drive(DELTA_TEMPLATE, ['59//14'] + DELTA_CHAIN[1:], [])

    def test_the_new_fields_reach_the_document_and_no_other_car_gains_them(self):
        import export_car_data as E
        sets, curve, fd, tyres = stratos_inputs()
        plain = build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres, rev_limit=RL)
        self.assertEqual(sorted(plain['final_drive']), sorted(
            ['adjustment', 'primaries', 'options', 'stock_option', 'rest']))
        averaged = E.averaged_final_drive(DELTA_TEMPLATE, DELTA_CHAIN, [])
        doc = build_car_json('x', 'X', 'Rear', sets, curve, averaged, tyres, rev_limit=RL)
        self.assertEqual(doc['final_drive']['rows'], ['cdr'])
        self.assertEqual(doc['final_drive']['formula'], averaged['formula'])
        self.assertEqual(len(doc['final_drive']['settings']), 3)


GAME_PAKS = _M.DEFAULT_PAKS if os.path.isdir(_M.DEFAULT_PAKS) else None


@unittest.skipUnless(GAME_PAKS, 'Assetto Corsa Rally is not installed')
class AveragedAxlesInTheGame(unittest.TestCase):
    def test_each_cars_chain_and_template_agree(self):
        import tempfile
        import export_car_data as E
        import calibration as CAL
        from acrpkg import Package
        from gearing import averaged_final_drive, drivetrain_chain
        chains = {}
        with tempfile.TemporaryDirectory() as tmp:
            for slug in sorted(E.AVERAGED_AXLE_CARS):
                with self.subTest(car=slug):
                    with open(CAL.car_asset(GAME_PAKS, _M.CARS[slug][2], tmp), 'rb') as fh:
                        chain = drivetrain_chain(Package(fh.read()))
                    chains[slug] = chain
                    with open(os.path.join(_M.TEMPLATES, slug + '.yaml'),
                              encoding='utf-8') as fh:
                        text = fh.read()
                    # raises when a stock ratio is not one of its setting's steps
                    fd = E.averaged_final_drive(text, chain, [])
                    stock = {s['key']: E.ratio(s['stock']) for s in fd['settings']}
                    self.assertAlmostEqual(E.averaged_below(fd['formula'], stock),
                                           averaged_final_drive(chain), places=12)
        # the fixtures above are what the game files hold
        self.assertEqual(chains['lancia-delta-integrale-evoluzione-1992'], DELTA_CHAIN)
        self.assertEqual(chains['citroen-xsara-wrc-2003'], XSARA_CHAIN)
        self.assertEqual(chains['peugeot-206-wrc-1999'], P206_CHAIN)
        self.assertEqual(chains['subaru-impreza-555-s3-1993'], IMPREZA_CHAIN)


class GeneratedDate(unittest.TestCase):
    def test_car_documents_do_not_carry_a_build_date(self):
        # stamping it into every car turned a no-op re-run into an 18-file diff
        sets, curve, fd, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres, rev_limit=RL)
        self.assertNotIn('generated', doc)

    def test_the_index_carries_the_build_date(self):
        doc = build_index_json([{'slug': 'a', 'name': 'A'}], '2026-09-12')
        self.assertEqual(doc['generated'], '2026-09-12')

    def test_the_index_omits_it_when_not_given(self):
        self.assertNotIn('generated', build_index_json([{'slug': 'a', 'name': 'A'}]))


class GameVersion(unittest.TestCase):
    def test_the_index_carries_the_game_version_next_to_the_date(self):
        doc = build_index_json([{'slug': 'a', 'name': 'A'}], '2026-09-12', '0.6')
        self.assertEqual(doc['game_version'], '0.6')
        self.assertEqual(doc['generated'], '2026-09-12')

    def test_the_index_omits_it_when_not_given(self):
        self.assertNotIn('game_version',
                         build_index_json([{'slug': 'a', 'name': 'A'}], '2026-09-12'))

    def test_a_site_export_reads_the_version_from_the_paks(self):
        from unittest import mock
        import export_car_data as E
        calls = []
        with mock.patch.object(E, 'read_game_version',
                               side_effect=lambda paks, tmp: calls.append(paks) or '0.6'):
            self.assertEqual(E.site_game_version('/paks', True), '0.6')
            self.assertIsNone(E.site_game_version('/paks', False))
        self.assertEqual(calls, ['/paks'])

    def test_an_unreadable_version_fails_the_site_export(self):
        from unittest import mock
        import export_car_data as E
        with mock.patch.object(E, 'read_game_version', side_effect=SystemExit('no version')):
            with self.assertRaises(SystemExit):
                E.site_game_version('/paks', True)


from export_car_data import (THEME_KEY, build_index_json, prune,  # noqa: E402
                             render_car_page, render_index_page, render_redirect_page,
                             write_car_pages)


class RenderPages(unittest.TestCase):
    def test_car_page_bakes_in_name_for_search(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('<title>Lancia Stratos HF — ACR Car Lab</title>', html)
        self.assertIn('<h1>Lancia Stratos HF</h1>', html)

    def test_car_page_names_its_own_slug_for_the_app_to_read(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('data-car="lancia-stratos"', html)

    def test_car_page_reaches_the_site_root_from_two_levels_down(self):
        # pages live at /<slug>/gears/, so shared assets and the picker are two levels up
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('href="../../app.css"', html)
        self.assertIn('src="../../js/app.js"', html)
        self.assertIn('<a class="crumb" href="../../">All cars', html)
        # nothing left pointing one level up only
        self.assertNotRegex(html, r'(?:href|src)="\.\./(?!\.\./)')

    def test_car_page_escapes_the_name(self):
        html = render_car_page('x', 'A & B <script>')
        self.assertNotIn('<script>A', html)
        self.assertIn('A &amp; B &lt;script&gt;', html)

    def test_index_json_lists_cars_sorted_by_name(self):
        doc = build_index_json([{'slug': 'b', 'name': 'Zeta'},
                                {'slug': 'a', 'name': 'Alpha'}])
        self.assertEqual([c['slug'] for c in doc['cars']], ['a', 'b'])

    def test_index_page_states_the_car_count_it_actually_lists(self):
        # the count is whatever was exported, never a claim about the whole game
        cars = [{'slug': f's{i}', 'name': f'Car {i}'} for i in range(3)]
        html = render_index_page(cars)
        self.assertIn('<h1>3 cars, gear by gear</h1>', html)
        self.assertIn('charts for 3 cars in', html)
        self.assertNotIn('every car', html.lower())

    def test_index_page_links_every_car(self):
        html = render_index_page([{'slug': 'lancia-stratos',
                                   'name': 'Lancia Stratos HF'}])
        self.assertIn('href="lancia-stratos/gears/"', html)
        self.assertNotIn('href="lancia-stratos/"', html)
        self.assertIn('Lancia Stratos HF', html)


class RedirectStub(unittest.TestCase):
    """<slug>/ used to be the car page; links already shared must land on <slug>/gears/."""

    def setUp(self):
        self.html = render_redirect_page('lancia-stratos', 'Lancia Stratos HF 1976')

    def test_the_script_keeps_query_and_hash(self):
        self.assertIn("<script>location.replace('gears/'+location.search+location.hash)"
                      '</script>', self.html)

    def test_it_paints_in_the_readers_theme_while_it_forwards(self):
        # without it a dark-theme reader sees a white flash before gears/ loads
        head = self.html[:self.html.index('</head>')]
        self.assertIn('<meta name="color-scheme" content="light dark">', head)

    def test_it_redirects_without_script_too(self):
        self.assertIn('<meta http-equiv="refresh" content="0; url=gears/">', self.html)

    def test_the_script_runs_before_the_refresh_can_drop_the_hash(self):
        self.assertLess(self.html.index('location.replace'),
                        self.html.index('http-equiv="refresh"'))

    def test_it_names_the_real_page_as_canonical(self):
        self.assertIn('<link rel="canonical" href="gears/">', self.html)

    def test_it_has_a_title_and_a_link_to_follow(self):
        self.assertIn('<title>Lancia Stratos HF 1976 — ACR Car Lab</title>', self.html)
        self.assertIn('<a href="gears/">', self.html)

    def test_it_is_not_counted(self):
        # the page it forwards to counts the visit; counting here would count it twice
        self.assertNotIn('goatcounter', self.html)
        self.assertNotIn('gc.zgo.at', self.html)

    def test_it_escapes_the_name(self):
        html = render_redirect_page('x', 'A & B <script>')
        self.assertIn('A &amp; B &lt;script&gt;', html)


class WriteCarPages(unittest.TestCase):
    def test_the_page_goes_under_gears_and_the_old_path_forwards(self):
        import tempfile
        with tempfile.TemporaryDirectory() as out:
            written = write_car_pages(out, 'lancia-stratos', 'Lancia Stratos HF')
            self.assertEqual(written, ['lancia-stratos/gears/index.html',
                                       'lancia-stratos/index.html'])
            with open(os.path.join(out, 'lancia-stratos', 'gears', 'index.html'),
                      encoding='utf-8') as fh:
                self.assertEqual(fh.read(),
                                 render_car_page('lancia-stratos', 'Lancia Stratos HF'))
            with open(os.path.join(out, 'lancia-stratos', 'index.html'),
                      encoding='utf-8') as fh:
                self.assertEqual(fh.read(),
                                 render_redirect_page('lancia-stratos', 'Lancia Stratos HF'))


class PickerPromo(unittest.TestCase):
    COPY = ('Want a setup, not just the numbers? '
            '<a href="https://github.com/fredmayor88/acr-setup-engineer">ACR Setup Engineer</a>'
            ' — a free Claude skill that tunes a car to how you drive and saves it to your '
            'Notion.')

    def page(self):
        return render_index_page([{'slug': 'lancia-stratos', 'name': 'Lancia Stratos HF'}])

    def test_the_picker_ends_with_the_approved_line(self):
        html = self.page()
        self.assertIn(f'<p class="promo">{self.COPY}', html)
        self.assertGreater(html.index('class="promo"'), html.index('</ul>'))

    def test_it_opens_in_the_same_tab(self):
        self.assertNotIn('target=', self.page())

    ISSUES = ' · <a href="https://github.com/fredmayor88/acr-car-lab/issues">Issues and feedback</a>'

    def test_the_issues_link_follows_the_promo_on_the_same_line(self):
        # the promo copy stays word for word; the issues link closes the same paragraph
        self.assertIn(f'<p class="promo">{self.COPY}{self.ISSUES}</p>', self.page())

    def test_the_issues_link_is_untracked_like_the_promo(self):
        html = self.page()
        line = html[html.index('<p class="promo">'):]
        line = line[:line.index('</p>')]
        self.assertNotIn('data-goatcounter-click', line)
        self.assertNotIn('onclick', line)


class ThemeInPages(unittest.TestCase):
    """Dark mode: the stored choice must be on <html> before the stylesheet paints."""

    def pages(self):
        return {'car': render_car_page('lancia-stratos', 'Lancia Stratos HF'),
                'index': render_index_page([{'slug': 'lancia-stratos',
                                             'name': 'Lancia Stratos HF'}])}

    def test_the_key_matches_the_site(self):
        # js/theme.js in acr-car-lab writes this key; its tests read it back from the pages
        self.assertEqual(THEME_KEY, 'acr-car-lab-theme')

    def test_head_script_reads_the_stored_theme_before_the_stylesheet(self):
        for kind, html in self.pages().items():
            head = html[:html.index('</head>')]
            script = head.index(f"localStorage.getItem('{THEME_KEY}')")
            self.assertLess(script, head.index('rel="stylesheet"'), kind)
            self.assertIn('document.documentElement.dataset.theme=t', head, kind)
            # storage can throw (blocked cookies); the page must still render
            self.assertIn('try{', head, kind)
            self.assertIn('catch(e){}', head, kind)

    def test_head_script_leaks_no_global(self):
        # a bare `var t` at the top level of a classic script becomes window.t
        for kind, html in self.pages().items():
            script = html[html.index('<script>'):html.index('</script>')]
            self.assertTrue(script.startswith('<script>(function(){'), kind)
            self.assertTrue(script.endswith('})()'), kind)
            self.assertEqual(script.count('var '), 1, kind)

    def test_head_script_only_accepts_the_two_themes(self):
        for kind, html in self.pages().items():
            self.assertIn("if(t==='dark'||t==='light')", html, kind)

    def test_native_controls_are_told_both_schemes_exist(self):
        for kind, html in self.pages().items():
            self.assertIn('<meta name="color-scheme" content="light dark">', html, kind)

    def test_both_pages_carry_a_labelled_toggle_in_the_brandrow(self):
        for kind, html in self.pages().items():
            row = html[html.index('class="brandrow"'):html.index('<h1>')]
            self.assertIn('<button class="theme" type="button">', row, kind)
            self.assertIn('>Dark</span>', row, kind)
            self.assertIn('>Light</span>', row, kind)

    def test_both_toggle_labels_carry_their_icon(self):
        # a moon beside "Dark", a sun beside "Light": the icon lives inside the label's span,
        # so the CSS that picks the label picks the icon too, before any script runs
        for kind, html in self.pages().items():
            button = html[html.index('<button class="theme"'):html.index('</button>')]
            dark = button[button.index('class="to-dark"'):button.index('>Dark</span>')]
            light = button[button.index('class="to-light"'):button.index('>Light</span>')]
            self.assertIn('class="icon moon"', dark, kind)
            self.assertIn('class="icon sun"', light, kind)
            self.assertEqual(button.count('<svg'), 2, kind)

    def test_toggle_icons_are_decorative_and_follow_the_text_colour(self):
        for kind, html in self.pages().items():
            button = html[html.index('<button class="theme"'):html.index('</button>')]
            svgs = re.findall(r'<svg[^>]*>', button)
            self.assertEqual(len(svgs), 2, kind)
            for svg in svgs:
                self.assertIn('aria-hidden="true"', svg, kind)
                self.assertIn('focusable="false"', svg, kind)
                self.assertIn('stroke="currentColor"', svg, kind)
            # no colour of its own, no emoji
            self.assertNotRegex(button, r'#[0-9a-fA-F]{3,6}\b|rgba?\(', kind)
            self.assertTrue(all(ord(ch) < 0x2000 for ch in button), kind)

    def test_car_toggle_sits_after_the_all_cars_link(self):
        html = self.pages()['car']
        self.assertLess(html.index('All cars'), html.index('class="theme"'))

    def test_index_page_loads_the_theme_module(self):
        # car pages get it through js/app.js; the picker has no other script
        self.assertIn('<script type="module" src="js/theme.js"></script>',
                      self.pages()['index'])


class Prune(unittest.TestCase):
    """prune() deletes files, so what it may touch is pinned down exactly."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

        def write(*parts):
            path = os.path.join(self.out, *parts)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('x')

        for slug in ('kept', 'stale'):
            write('data', slug + '.json')
            write(slug, 'index.html')
            write(slug, 'gears', 'index.html')
        write('data', 'index.json')
        write('data', 'notes.txt')                 # not JSON: out of scope
        write('shared', 'extra.css')               # stale car folder with other files
        write('shared', 'gears', 'extra.css')      # ...and a gears folder with other files
        write('data', 'shared.json')
        write('shared', 'index.html')
        write('shared', 'gears', 'index.html')
        write('data', 'old.json')                  # a car from before the gears move
        write('old', 'index.html')
        write('app.css')
        write('js', 'app.js')
        write('index.html')

    def exists(self, *parts):
        return os.path.exists(os.path.join(self.out, *parts))

    def test_stale_car_files_and_empty_folder_are_removed(self):
        removed = prune(self.out, {'kept'})
        self.assertFalse(self.exists('data', 'stale.json'))
        self.assertFalse(self.exists('stale', 'index.html'))
        self.assertFalse(self.exists('stale', 'gears', 'index.html'))
        self.assertFalse(self.exists('stale', 'gears'))
        self.assertFalse(self.exists('stale'))
        self.assertIn('data/stale.json', removed)
        self.assertIn('stale/gears/index.html', removed)
        self.assertIn('stale/index.html', removed)

    def test_a_car_with_only_the_old_single_page_is_removed_too(self):
        removed = prune(self.out, {'kept'})
        self.assertFalse(self.exists('old'))
        self.assertIn('old/index.html', removed)
        self.assertNotIn('old/gears/index.html', removed)

    def test_current_cars_are_kept(self):
        prune(self.out, {'kept'})
        self.assertTrue(self.exists('data', 'kept.json'))
        self.assertTrue(self.exists('kept', 'index.html'))
        self.assertTrue(self.exists('kept', 'gears', 'index.html'))

    def test_nothing_else_is_touched(self):
        prune(self.out, {'kept'})
        for parts in (('data', 'index.json'), ('data', 'notes.txt'), ('app.css',),
                      ('js', 'app.js'), ('index.html',), ('shared', 'extra.css')):
            self.assertTrue(self.exists(*parts), os.path.join(*parts))

    def test_a_stale_folder_holding_other_files_keeps_them(self):
        prune(self.out, {'kept'})
        self.assertFalse(self.exists('data', 'shared.json'))
        self.assertFalse(self.exists('shared', 'index.html'))
        self.assertFalse(self.exists('shared', 'gears', 'index.html'))
        self.assertTrue(self.exists('shared', 'extra.css'))
        self.assertTrue(self.exists('shared', 'gears', 'extra.css'))

    def test_the_parent_of_the_target_is_not_touched(self):
        sibling = os.path.join(os.path.dirname(self.out),
                               os.path.basename(self.out) + '-sibling.json')
        with open(sibling, 'w') as fh:
            fh.write('x')
        self.addCleanup(os.remove, sibling)
        prune(self.out, set())
        self.assertTrue(os.path.exists(sibling))
        self.assertTrue(self.exists('data', 'index.json'))


if __name__ == '__main__':
    unittest.main()


class EngineSources(unittest.TestCase):
    def test_template_curve_reads_points_and_folder(self):
        from export_car_data import template_curve
        text = ('engine_curve:\n  source: "ACR game files - FC_LanciaStratosHF_Torque"\n'
                '  torque_points: [\n    [0, 0], [250, 12.5], [8750, 192]\n  ]\n')
        curve, folder = template_curve(text)
        self.assertEqual(curve, [(0, 0.0), (250, 12.5), (8750, 192.0)])
        self.assertEqual(folder, 'LanciaStratosHF')

    def test_template_without_a_curve(self):
        from export_car_data import template_curve
        self.assertEqual(template_curve('car: "Peugeot 206 WRC 1999"\n'), ([], None))

    def test_curve_from_is_none_for_the_cars_own_curve(self):
        from export_car_data import curve_from
        self.assertIsNone(curve_from('CitroenXsaraWRC', 'citroen-xsara-wrc-2003'))

    def test_curve_from_names_the_owner_of_a_borrowed_curve(self):
        from export_car_data import curve_from
        self.assertEqual(curve_from('CitroenXsaraWRC', 'peugeot-206-wrc-1999'),
                         {'slug': 'citroen-xsara-wrc-2003', 'name': 'Citroen Xsara WRC 2003'})

    def test_no_car_is_known_missing_any_more(self):
        from export_car_data import KNOWN_MISSING
        self.assertNotIn('peugeot-206-wrc-1999', KNOWN_MISSING)
