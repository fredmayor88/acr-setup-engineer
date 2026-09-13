import copy
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

import calibration as CAL                  # noqa: E402
import drivetrain_page as D                # noqa: E402
import export_car_data as E                # noqa: E402
import make_gearing_chart as M             # noqa: E402

SITE_DATA = os.path.join(HERE, '..', '..', 'acr-car-lab', 'data')
HAVE_SITE = os.path.isdir(SITE_DATA)


def template(slug):
    with open(os.path.join(M.TEMPLATES, slug + '.yaml'), encoding='utf-8') as fh:
        return fh.read()


def site_doc(slug):
    with open(os.path.join(SITE_DATA, slug + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def text_of(html):
    """The visible text, entities decoded, so the tests read what a reader reads."""
    import html as h
    if '<body>' in html:
        html = html[html.index('<body>'):]
    html = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL)
    return re.sub(r'\s+', ' ', h.unescape(re.sub(r'<[^>]+>', ' ', html)))


def section(html, cls):
    m = re.search(r'<section class="%s"[^>]*>(.*?)</section>' % cls, html, re.DOTALL)
    return m.group(1) if m else None


DELTA = 'lancia-delta-integrale-evoluzione-1992'
P206 = 'peugeot-206-wrc-1999'
IMPREZA = 'subaru-impreza-555-s3-1993'
AUDI = 'audi-quattro-gr4-1981'
XSARA = 'citroen-xsara-wrc-2003'
STRATOS = 'lancia-stratos'
MINI = 'mini-cooper-s-1964'
FABIA = 'skoda-fabia-rs-rally2-2022'
P208 = 'peugeot-208-rally4'


class Notes(unittest.TestCase):
    def setUp(self):
        self.notes = D.load_notes()

    def test_every_car_has_an_entry_and_no_other(self):
        self.assertEqual(sorted(self.notes['cars']), sorted(M.CARS))
        for slug, entry in self.notes['cars'].items():
            with self.subTest(car=slug):
                self.assertTrue(entry['short'])
                self.assertTrue(entry['workings'])

    def test_shared_paragraphs_exist(self):
        for slug, entry in self.notes['cars'].items():
            for item in entry['workings']:
                if item.startswith('@'):
                    self.assertIn(item[1:], self.notes['common'], slug)

    def test_the_handling_notes_are_word_for_word_and_only_where_observed(self):
        handling = {s: e['handling'] for s, e in self.notes['cars'].items() if 'handling' in e}
        self.assertEqual(handling, {
            AUDI: 'No centre differential: different front and rear ratios make the axles fight '
                  'and the car hard to control.',
            P206: 'Setting the front and rear ratios far apart can make the car handle oddly.',
            IMPREZA: 'Setting the front and rear ratios far apart can make the car handle oddly.',
        })

    def test_no_number_is_typed_into_the_prose(self):
        # tooth-count spellings (55//12, 43//13*21//13) are names; every other number is computed
        for slug, entry in self.notes['cars'].items():
            for p in entry['workings']:
                bare = re.sub(r'\{[^{}]*\}', '', p)
                bare = re.sub(r'[\d()+]+//[\d()+]+(?:\*[\d()+]+//[\d()+]+)*', '', bare)
                bare = re.sub(r'\b(?:037|124|131|206|208|306|555|i20|S3)\b', '', bare)
                bare = re.sub(r'\b[1-7](?:st|nd|rd|th)\b', '', bare)
                bare = re.sub(r'gear sets? \d(?: and \d)?', '', bare)
                bare = re.sub(r'a ratio of 1|1 everywhere', '', bare)
                with self.subTest(car=slug, p=p[:40]):
                    self.assertNotRegex(bare, r'\d')

    def test_measurement_provenance_is_stored_with_each_rev_limiter(self):
        for slug, entry in CAL.load_calibration()['rev_limiters'].items():
            with self.subTest(car=slug):
                self.assertEqual((entry['measured'], entry['game_version']),
                                 ('2026-09-13', '0.6'))


class Facts(unittest.TestCase):
    """Pure pieces of the top section, on hand-built documents."""

    def fd_single(self, **kw):
        fd = {'adjustment': 'Differential Ratio Rear', 'primaries': [],
              'options': [{'name': '43//9', 'value': 43 / 9}, {'name': '41//9', 'value': 41 / 9}],
              'stock_option': '43//9', 'rest': 1.0}
        fd.update(kw)
        return fd

    def doc(self, **kw):
        doc = {'slug': 'x', 'name': 'X', 'final_drive': self.fd_single(), 'fixed_final_drive': None,
               'gear_sets': [{'label': 'Gear set 1', 'primary': {'name': '25//25', 'value': 1.0},
                              'gears': [{}] * 5}],
               'engine': {'redline': 7000, 'redline_source': 'measured', 'curve_from': None}}
        doc.update(kw)
        return doc

    def test_layouts_come_from_the_template_and_match_the_expected_three_groups(self):
        want = {'FWD': {'lancia-fulvia-coupe-hf-1970', MINI, 'peugeot-306-ii-maxi-1997', P208},
                'RWD': {'alfa-romeo-gta-1300-junior-1972', 'alpine-a110-1-8-1973',
                        'fiat-124-abarth-rally-16v-1974', 'fiat-131-abarth-1976',
                        'lancia-037-evoluzione-2-1984', STRATOS},
                'AWD': {AUDI, XSARA, DELTA, P206, IMPREZA, 'hyundai-i20-rally2-2021', FABIA,
                        'volkswagen-polo-gti-r5-2018'}}
        got = {}
        for slug in M.CARS:
            got.setdefault(D.template_facts(template(slug))[0], set()).add(slug)
        self.assertEqual(got, want)

    def test_single_ratio_final_drive(self):
        self.assertEqual(D.final_drive_lines(self.doc())[1],
                         'Final drive = Differential Ratio Rear.')

    def test_a_fixed_factor_beside_the_single_ratio_is_named(self):
        doc = self.doc(final_drive=self.fd_single(rest=0.95))
        self.assertEqual(D.final_drive_lines(doc)[1],
                         'Final drive = Differential Ratio Rear × 0.950.')

    def test_fixed_final_drive(self):
        doc = self.doc(final_drive=None, fixed_final_drive=55 / 13)
        self.assertEqual(D.final_drive_lines(doc)[1], 'Final drive is fixed at 4.231.')
        rows = dict(D.gearing_settings(doc, True))
        self.assertEqual(rows['Final drive'], 'fixed at 4.231, no selectable ratio')

    def test_gear_sets_by_speed(self):
        doc = self.doc(gear_sets=[{'gears': [{}] * n, 'primary': {'name': '25//25'}}
                                  for n in (7, 7, 6, 6, 5)])
        self.assertEqual(D.gear_sets_text(doc, True),
                         '5 gear sets: sets 1–2 7-speed, sets 3–4 6-speed, set 5 5-speed')
        self.assertEqual(D.gear_sets_text(self.doc(), False),
                         '1 gear set, 5-speed (setup has no Gear Set setting)')

    def test_primary_of_each_set_applies_without_a_selector(self):
        doc = self.doc(gear_sets=[{'gears': [], 'primary': {'name': p}}
                                  for p in ('24//23', '23//22', '23//22')])
        self.assertEqual(D.primary_text(doc), 'No Primary Gear setting: each gear set\'s own '
                                              'primary applies (set 1 24//23, sets 2–3 23//22).')

    def test_rev_limit_sources(self):
        for source, words in (('measured', 'measured in game with telemetry'),
                              ('estimated', 'estimated from the game files'),
                              ('measured-stale', 'measured on an earlier game version')):
            doc = self.doc(engine={'redline': 7000, 'redline_source': source, 'curve_from': None})
            self.assertEqual(D.rev_limit_text(doc, {'game_version': '0.5'}, '0.6'),
                             f'7000 rpm, {words} (ACR {"0.5" if source == "measured-stale" else "0.6"}).')

    def test_engine_curve(self):
        self.assertEqual(D.engine_curve_text(self.doc()), 'Own curve.')
        doc = self.doc(engine={'curve_from': {'slug': XSARA, 'name': 'Citroen Xsara WRC 2003'}})
        self.assertEqual(D.engine_curve_text(doc),
                         'Uses the Citroen Xsara WRC 2003 engine curve in the game files.')


class Placeholders(unittest.TestCase):
    def ctx(self, workings, hypotheses=None, runs=None):
        doc = {'slug': 'x', 'name': 'X', 'engine': {'redline': 7000},
               'gear_sets': [{'label': 'Gear set 1', 'primary': {'name': '25//25', 'value': 1.0}}],
               'final_drive': {'adjustment': 'Differential Ratio Rear'}, 'fixed_final_drive': 3.5}
        run = {'car': 'x', 'gear_set': 'Gear set 1', 'primary': '25//25', 'option': '4//1',
               'rest': 1.0, 'free_radius': 0.3, 'gears': ['3//1', '2//1', '1//1'],
               'kmh': [30, 45, 90]}
        cal = {'rev_limiters': {'x': {'rpm': 7000}}, 'speed_runs': runs or [run]}
        notes = {'cars': {'x': {'short': 'Ex', 'workings': workings,
                                'hypotheses': hypotheses or {}}}}
        return D.Context(doc, cal, notes, factor=1.0)

    def test_values(self):
        c = self.ctx([], {'short': {'primary': '2//1'}})
        self.assertEqual(D.fill('{factor} {fit_runs} {fit_car_count} {fit_cars} {rev_limit}', c),
                         '1.0000 1 one Ex 7000')
        self.assertEqual(D.fill('{measured:1:2} {ratio:31//21} {fixed}', c), '45 1.476 3.500')
        import math
        raw = 7000 * 2 * math.pi * 0.3 * 0.06 / (2 * 4)
        self.assertEqual(D.fill('{kmh:formula:1:2}', c), str(round(raw)))
        self.assertEqual(D.fill('{kmh:short:1:2}', c), str(round(raw / 2)))
        self.assertEqual(D.fill('{apart:short:formula:1}', c), '100')

    def test_anything_that_does_not_resolve_raises(self):
        c = self.ctx([])
        for bad in ('{nope}', '{kmh:missing:1:2}', '{measured:2:1}', '{measured:1:9}',
                    '{kmh:formula}', 'a { b'):
            with self.subTest(bad=bad), self.assertRaises((ValueError, IndexError)):
                D.fill(bad, c)


@unittest.skipUnless(HAVE_SITE, 'no ../acr-car-lab checkout next to this repo')
class Pages(unittest.TestCase):
    """The page for each car, built from the exported documents."""

    @classmethod
    def setUpClass(cls):
        cls.cal = CAL.load_calibration()
        cls.notes = D.load_notes()
        cls.pages = {slug: E.render_drivetrain_page(site_doc(slug), template(slug), cls.cal,
                                                    cls.notes, '0.6', '2026-09-13')
                     for slug in M.CARS}

    def test_every_placeholder_resolves_on_every_car(self):
        for slug in M.CARS:
            with self.subTest(car=slug):
                paras = D.workings_paragraphs(site_doc(slug), self.cal, self.notes)
                self.assertTrue(paras)
                html = self.pages[slug]
                self.assertNotRegex(text_of(html), r'\{|\}|undefined|NaN|None|Infinity')

    def test_shared_head_toggle_and_links(self):
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                self.assertIn(f"localStorage.getItem('{E.THEME_KEY}')", html)
                self.assertIn('<button class="theme" type="button">', html)
                self.assertIn('<a class="crumb" href="../gears/">', html)
                self.assertIn('<a class="crumb" href="../../">All cars', html)
                self.assertIn('href="../../app.css"', html)
                self.assertIn('<script type="module" src="../../js/drivetrain.js"></script>', html)
                self.assertIn('gc.zgo.at/count.js', html)
                self.assertIn('Read from the ACR 0.6 game files. Generated 2026-09-13.', html)
                self.assertIn('Issues and feedback', html)
                name = site_doc(slug)['name']
                self.assertIn(f'<h1>{D.esc(name)} — drivetrain</h1>', html)

    def test_sections_in_order(self):
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                a, b = html.index('id="facts"'), html.index('id="workings"')
                c = html.index('id="measured"')
                self.assertLess(a, b)
                self.assertLess(b, c)
                self.assertIn('data-event="read-drivetrain-workings"', html)

    def test_handling_notes_only_on_the_three_cars(self):
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                has = '<dt>Handling</dt>' in html
                self.assertEqual(has, slug in (AUDI, P206, IMPREZA))
        self.assertIn('make the axles fight and the car hard to control.', self.pages[AUDI])

    def test_the_top_section_facts(self):
        facts = {s: text_of(section(h, 'top')) for s, h in self.pages.items()}
        self.assertIn('Four-wheel drive', facts[DELTA])
        self.assertIn('Front-wheel drive', facts[MINI])
        self.assertIn('Rear-wheel drive', facts[STRATOS])
        self.assertIn('Final drive = average of the front axle (Center Differential Ratio) and '
                      'the rear axle (Center Differential Ratio × Center Ratio to Rear × '
                      'Differential Ratio Rear).', facts[DELTA])
        self.assertIn('Final drive = Center Differential Ratio × average of Differential Ratio '
                      'Front and Differential Ratio Rear.', facts[P206])
        self.assertIn('Final drive = average of Differential Ratio Front and Center Ratio to Rear '
                      '× Differential Ratio Rear.', facts[IMPREZA])
        self.assertIn('Final drive = Center Differential Ratio × 2.782 (the front and rear '
                      'differentials are fixed).', facts[XSARA])
        self.assertIn('Final drive = average of Differential Ratio Front and Differential Ratio '
                      'Rear.', facts[AUDI])
        self.assertIn('Final drive = Differential Ratio Front.', facts[MINI])
        self.assertIn('Final drive is fixed at 4.231.', facts[FABIA])
        self.assertIn('fixed at 4.231, no selectable ratio', facts[FABIA])
        self.assertIn('replaces the gear set\'s own primary (20//25). The gearing page starts on '
                      '21//24.', facts[P206])
        self.assertIn('The Primary Gear you pick replaces the gear set\'s own primary.',
                      facts[STRATOS])
        self.assertIn('No Primary Gear setting', facts[MINI])
        self.assertIn('Uses the Citroen Xsara WRC 2003 engine curve in the game files.',
                      facts[P206])
        self.assertIn('Own curve.', facts[XSARA])
        self.assertIn('7200 rpm, measured in game with telemetry (ACR 0.6).', facts[DELTA])
        for name in ('Gear Set', 'Center Differential Ratio', 'Center Ratio to Rear',
                     'Differential Ratio Rear'):
            self.assertIn(name, facts[DELTA])
        self.assertIn('Primary Gear', facts[P206])
        self.assertNotIn('Primary Gear 21', facts[DELTA])

    def test_how_we_worked_it_out_per_car(self):
        work = {s: text_of(section(h, 'workings')) for s, h in self.pages.items()}
        for slug, text in work.items():
            with self.subTest(car=slug):
                self.assertIn('How we worked it out', text)
                self.assertIn('rolling factor of 0.9904', text)
                self.assertIn('14 runs across seven cars', text)
                self.assertNotIn('verified', text.lower())
                self.assertNotIn('science', text.lower())
        averaging = 'Why an average'
        for slug in M.CARS:
            self.assertEqual(averaging in work[slug], slug in (DELTA, P206, IMPREZA, XSARA, AUDI),
                             slug)
        self.assertIn('rear settings that do nothing meant about 182 km/h, the average about '
                      '161. Fred got 160.', work[DELTA])
        self.assertIn('The rear alone would have meant about 174 km/h in 4th, the front alone '
                      'about 117. Fred got 142', work[P206])
        self.assertIn('20//25 would have put them about 8% and 14% too high', work[P206])
        self.assertIn('31//21 (1.476)', work[P206])
        self.assertIn('4th tops out at about 163 km/h; if it does nothing, 143; if it divides, '
                      '124. Fred got 164', work[IMPREZA])
        self.assertIn('multiplying would have put 5th at about 180 km/h; replacing puts it at '
                      '198. Fred got 197', work[STRATOS])
        self.assertIn("can't be tested on this car", work[AUDI])
        self.assertIn('It has not been tested on this car.', work[MINI])
        self.assertIn('It has not been tested on this car.', work[FABIA])
        self.assertIn('no engine curve of its own', work[P206])

    def test_measured_in_game(self):
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                m = text_of(section(html, 'measured'))
                self.assertIn('SimHub telemetry · ACR 0.6 · 2026-09-13', m)
                self.assertNotIn('%', m)
                self.assertNotIn('predict', m.lower())
                runs = [r for r in self.cal['speed_runs'] if r['car'] == slug]
                self.assertEqual(html.count('<table class="speeds">'), len(runs))
        m206 = section(self.pages[P206], 'measured')
        self.assertIn('<td>164*</td>', m206)
        self.assertEqual(m206.count('did not reach the rev limiter'), 1)
        self.assertIn('Primary Gear <span class="mono">21//24</span> · Differential Ratio Front '
                      '<span class="mono">46//14*26//16</span> · Center Differential Ratio '
                      '<span class="mono">24//24</span> · Differential Ratio Rear', m206)
        stratos = text_of(section(self.pages[STRATOS], 'measured'))
        self.assertIn('Gear set 3 · dry tarmac · 2026-09-11', stratos)
        self.assertIn('Primary Gear 35//30*33//28 · Differential Ratio Rear 65//17', stratos)
        self.assertEqual(section(self.pages[MINI], 'measured').count('<table'), 0)

    def test_no_measured_section_without_a_measurement(self):
        doc = copy.deepcopy(site_doc(MINI))
        doc['engine']['redline_source'] = 'estimated'
        html = D.render_drivetrain_page(doc, template(MINI), self.cal, self.notes)
        self.assertIsNone(section(html, 'measured'))
        self.assertIn('is estimated from the shift-light rev stages', html)
        self.assertIn('Read from the ACR game files.', html)


class PickerAndGearsLinks(unittest.TestCase):
    CARS = [{'slug': 'lancia-stratos', 'name': 'Lancia Stratos HF'},
            {'slug': 'mini-cooper-s-1964', 'name': 'Mini Cooper S'}]

    def test_the_gears_list_is_unchanged_and_a_drivetrain_list_follows(self):
        html = E.render_index_page(self.CARS)
        gears = re.findall(r'<li><a href="([^"]+)/gears/">', html)
        dt = re.findall(r'<li><a href="([^"]+)/drivetrain/">', html)
        self.assertEqual(gears, ['lancia-stratos', 'mini-cooper-s-1964'])
        self.assertEqual(dt, gears)
        first_list = html[html.index('<ul class="carlist">'):html.index('</ul>')]
        self.assertNotIn('drivetrain', first_list)
        self.assertLess(html.index('</ul>'), html.index('<h2>Drivetrain notes</h2>'))
        self.assertIn('<ul class="carlist minor">', html)

    def test_the_gears_page_links_to_the_drivetrain_page(self):
        html = E.render_car_page('lancia-stratos', 'Lancia Stratos HF')
        row = html[html.index('class="brandrow"'):html.index('<h1>')]
        self.assertIn('<a class="crumb" href="../drivetrain/">Drivetrain notes</a>', row)


class PruneKeepsDrivetrainPages(unittest.TestCase):
    def test_kept_and_stale(self):
        with tempfile.TemporaryDirectory() as out:
            for slug in ('kept', 'stale'):
                for parts in (('data', slug + '.json'), (slug, 'index.html'),
                              (slug, 'gears', 'index.html'), (slug, 'drivetrain', 'index.html')):
                    path = os.path.join(out, *parts)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    open(path, 'w').close()
            removed = E.prune(out, {'kept'})
            self.assertTrue(os.path.isfile(os.path.join(out, 'kept', 'drivetrain', 'index.html')))
            self.assertIn('stale/drivetrain/index.html', removed)
            self.assertFalse(os.path.exists(os.path.join(out, 'stale')))

    def test_write_drivetrain_page(self):
        if not HAVE_SITE:
            self.skipTest('no ../acr-car-lab checkout next to this repo')
        with tempfile.TemporaryDirectory() as out:
            cal, notes = CAL.load_calibration(), D.load_notes()
            path = E.write_drivetrain_page(out, site_doc(MINI), template(MINI), cal, notes)
            self.assertEqual(path, 'mini-cooper-s-1964/drivetrain/index.html')
            with open(os.path.join(out, *path.split('/')), encoding='utf-8') as fh:
                self.assertEqual(fh.read(), E.render_drivetrain_page(
                    site_doc(MINI), template(MINI), cal, notes))


if __name__ == '__main__':
    unittest.main()
