import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from export_car_data import build_car_json  # noqa: E402


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


class BuildCarJson(unittest.TestCase):
    def setUp(self):
        sets, curve, fd, tyres = stratos_inputs()
        self.doc = build_car_json('lancia-stratos', 'Lancia Stratos HF', 'Rear',
                                  sets, curve, fd, tyres)

    def test_identity_fields(self):
        self.assertEqual(self.doc['slug'], 'lancia-stratos')
        self.assertEqual(self.doc['name'], 'Lancia Stratos HF')
        self.assertEqual(self.doc['axle'], 'Rear')

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
        self.assertEqual(first['primary'], {'name': '33//31*31//30', 'value': 1.100})

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
        doc = build_car_json('x', 'X', 'Front', sets, curve, None, tyres)
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
                             fixed_final_drive=4.230769)
        self.assertIsNone(doc['final_drive'])
        self.assertAlmostEqual(doc['fixed_final_drive'], 4.230769, places=6)

    def test_fixed_final_drive_is_dropped_when_the_car_is_adjustable(self):
        # the two fields are mutually exclusive whatever the caller passes
        sets, curve, fd, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres,
                             fixed_final_drive=4.230769)
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
                                  sets, curve, None, tyres, fixed_final_drive=3.7647)

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


class GeneratedDate(unittest.TestCase):
    def test_car_documents_do_not_carry_a_build_date(self):
        # stamping it into every car turned a no-op re-run into a 17-file diff
        sets, curve, fd, tyres = stratos_inputs()
        doc = build_car_json('x', 'X', 'Rear', sets, curve, fd, tyres)
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
                             render_car_page, render_index_page)


class RenderPages(unittest.TestCase):
    def test_car_page_bakes_in_name_for_search(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('<title>Lancia Stratos HF — ACR Car Lab</title>', html)
        self.assertIn('<h1>Lancia Stratos HF</h1>', html)

    def test_car_page_names_its_own_slug_for_the_app_to_read(self):
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('data-car="lancia-stratos"', html)

    def test_car_page_uses_parent_relative_asset_paths(self):
        # pages live at /<slug>/, so shared assets are one level up
        html = render_car_page('lancia-stratos', 'Lancia Stratos HF')
        self.assertIn('../app.css', html)
        self.assertIn('../js/app.js', html)

    def test_car_page_escapes_the_name(self):
        html = render_car_page('x', 'A & B <script>')
        self.assertNotIn('<script>A', html)
        self.assertIn('A &amp; B &lt;script&gt;', html)

    def test_index_json_lists_cars_sorted_by_name(self):
        doc = build_index_json([{'slug': 'b', 'name': 'Zeta'},
                                {'slug': 'a', 'name': 'Alpha'}])
        self.assertEqual([c['slug'] for c in doc['cars']], ['a', 'b'])

    def test_index_page_states_the_car_count_it_actually_lists(self):
        # the 206 WRC is not exported, so "every car in the game" would be untrue
        cars = [{'slug': f's{i}', 'name': f'Car {i}'} for i in range(3)]
        html = render_index_page(cars)
        self.assertIn('<h1>3 cars, gear by gear</h1>', html)
        self.assertIn('charts for 3 cars in', html)
        self.assertNotIn('every car', html.lower())

    def test_index_page_links_every_car(self):
        html = render_index_page([{'slug': 'lancia-stratos',
                                   'name': 'Lancia Stratos HF'}])
        self.assertIn('href="lancia-stratos/"', html)
        self.assertIn('Lancia Stratos HF', html)


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
        write('data', 'index.json')
        write('data', 'notes.txt')                 # not JSON: out of scope
        write('shared', 'extra.css')               # stale car folder with other files
        write('data', 'shared.json')
        write('shared', 'index.html')
        write('app.css')
        write('js', 'app.js')
        write('index.html')

    def exists(self, *parts):
        return os.path.exists(os.path.join(self.out, *parts))

    def test_stale_car_files_and_empty_folder_are_removed(self):
        removed = prune(self.out, {'kept'})
        self.assertFalse(self.exists('data', 'stale.json'))
        self.assertFalse(self.exists('stale', 'index.html'))
        self.assertFalse(self.exists('stale'))
        self.assertIn('data/stale.json', removed)
        self.assertIn('stale/index.html', removed)

    def test_current_cars_are_kept(self):
        prune(self.out, {'kept'})
        self.assertTrue(self.exists('data', 'kept.json'))
        self.assertTrue(self.exists('kept', 'index.html'))

    def test_nothing_else_is_touched(self):
        prune(self.out, {'kept'})
        for parts in (('data', 'index.json'), ('data', 'notes.txt'), ('app.css',),
                      ('js', 'app.js'), ('index.html',), ('shared', 'extra.css')):
            self.assertTrue(self.exists(*parts), os.path.join(*parts))

    def test_a_stale_folder_holding_other_files_keeps_them(self):
        prune(self.out, {'kept'})
        self.assertFalse(self.exists('data', 'shared.json'))
        self.assertFalse(self.exists('shared', 'index.html'))
        self.assertTrue(self.exists('shared', 'extra.css'))

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
