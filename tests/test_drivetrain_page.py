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
    # no-break spaces are kept: they are what holds a formula's ÷ 2 together on a line
    return re.sub(r'[ \t\r\n]+', ' ', h.unescape(re.sub(r'<[^>]+>', ' ', html)))


def section(html, cls):
    m = re.search(r'<section class="%s"[^>]*>(.*?)</section>' % cls, html, re.DOTALL)
    return m.group(1) if m else None


def note_strings(item, common=None):
    """Every piece of shown text in one workings item: a paragraph, a formula block's lines or a
    list's items. An "@name" reference is followed into common when given, else skipped."""
    if isinstance(item, str):
        if item.startswith('@'):
            if common is None or item[1:] not in common:
                return []
            ref = common[item[1:]]
            return [x for i in (ref if isinstance(ref, list) else [ref])
                    for x in note_strings(i, common)]
        return [item]
    return [x for x in item.get('formula', []) + item.get('list', []) if not x.startswith('@')]


def code_lines(html):
    import html as h
    return [h.unescape(x) for x in re.findall(r'<code>([^<]*)</code>', html)]


def numbered(html):
    """The visible text with each list item numbered, as a reader sees an <ol>."""
    def ol(m):
        items = re.findall(r'<li>(.*?)</li>', m.group(0), re.DOTALL)
        return ' ' + ' '.join(f'{i}. {x}' for i, x in enumerate(items, start=1)) + ' '
    return text_of(re.sub(r'<ol[^>]*>.*?</ol>', ol, html, flags=re.DOTALL))


DELTA = 'lancia-delta-integrale-evoluzione-1992'
P206 = 'peugeot-206-wrc-1999'
IMPREZA = 'subaru-impreza-555-s3-1993'
AUDI = 'audi-quattro-gr4-1981'
XSARA = 'citroen-xsara-wrc-2003'
STRATOS = 'lancia-stratos'
MINI = 'mini-cooper-s-1964'
FABIA = 'skoda-fabia-rs-rally2-2022'
P208 = 'peugeot-208-rally4'
LANCIA037 = 'lancia-037-evoluzione-2-1984'
P306 = 'peugeot-306-ii-maxi-1997'
ALFA = 'alfa-romeo-gta-1300-junior-1972'
STRATOS_LIMIT = 8520
SET_PRIMARY_CARS = (MINI, 'fiat-124-abarth-rally-16v-1974', 'fiat-131-abarth-1976',
                    'lancia-fulvia-coupe-hf-1970')


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
                if isinstance(item, str) and item.startswith('@'):
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
            for p in (x for item in entry['workings'] for x in note_strings(item)):
                bare = re.sub(r'\{[^{}]*\}', '', p)
                bare = re.sub(r'[\d()+]+//[\d()+]+(?:\*[\d()+]+//[\d()+]+)*', '', bare)
                bare = re.sub(r'\b(?:037|124|131|206|208|306|555|i20|S3)\b', '', bare)
                bare = re.sub(r'\b[1-7](?:st|nd|rd|th)\b', '', bare)
                bare = re.sub(r'gear sets? \d(?: and \d)?', '', bare, flags=re.I)
                bare = re.sub(r'a ratio of 1|1 everywhere', '', bare)
                # a reference to an item of the numbered list of possibilities above it
                bare = re.sub(r'possibility [1-3]\b', '', bare)
                # the formulas' own constants: (1 + rear chain) and the\u00a0÷\u00a02
                bare = re.sub(r'\(1 \+|\s÷\s2|primary = 1\.', '', bare)
                with self.subTest(car=slug, p=p[:40]):
                    self.assertNotRegex(bare, r'\d')

    def test_measurement_provenance_is_stored_with_each_rev_limiter(self):
        for slug, entry in CAL.load_calibration()['rev_limiters'].items():
            with self.subTest(car=slug):
                self.assertEqual((entry['measured'], entry['game_version']),
                                 ('2026-09-14', '0.6'))


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
        self.assertEqual(D.final_drive_lines(self.doc()),
                         ('One ratio sits below the gearbox, and setup offers it.',
                          ['final drive = Differential Ratio Rear']))

    def test_a_fixed_factor_beside_the_single_ratio_is_named(self):
        doc = self.doc(final_drive=self.fd_single(rest=0.95))
        self.assertEqual(D.final_drive_lines(doc)[1],
                         ['final drive = Differential Ratio Rear × 0.950'])

    def test_fixed_final_drive(self):
        doc = self.doc(final_drive=None, fixed_final_drive=55 / 13)
        self.assertEqual(D.final_drive_lines(doc)[1], ['final drive = 4.231 (fixed)'])
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

    def test_no_engine_curve_fact(self):
        self.assertFalse(hasattr(D, 'engine_curve_text'))


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
        codes = {s: code_lines(section(h, 'top')) for s, h in self.pages.items()}
        div2 = ')\u00a0÷\u00a02'
        self.assertEqual(codes[DELTA], [
            'front path ratio = Center Differential Ratio',
            'rear path ratio = Center Differential Ratio × Center Ratio to Rear × Differential Ratio Rear',
            'final drive = (front path ratio + rear path ratio' + div2,
            'final drive = Center Differential Ratio × (1 + Center Ratio to Rear × Differential Ratio Rear' + div2,
            "primary = the gear set's own primary"])
        self.assertEqual(codes[P206], [
            'front path ratio = Center Differential Ratio × Differential Ratio Front',
            'rear path ratio = Center Differential Ratio × Differential Ratio Rear',
            'final drive = (front path ratio + rear path ratio' + div2,
            'final drive = Center Differential Ratio × (Differential Ratio Front + Differential Ratio Rear' + div2,
            'primary = Primary Gear'])
        self.assertEqual(codes[IMPREZA][:4], [
            'front path ratio = Differential Ratio Front',
            'rear path ratio = Center Ratio to Rear × Differential Ratio Rear',
            'final drive = (front path ratio + rear path ratio' + div2,
            'final drive = (Differential Ratio Front + Center Ratio to Rear × Differential Ratio Rear' + div2])
        self.assertEqual(codes[XSARA][:4], [
            'front path ratio = Center Differential Ratio × 2.778',
            'rear path ratio = Center Differential Ratio × 2.786',
            'final drive = (front path ratio + rear path ratio' + div2,
            'final drive = Center Differential Ratio × (2.778 + 2.786' + div2])
        self.assertEqual(codes[AUDI][:4], [
            'front path ratio = Differential Ratio Front',
            'rear path ratio = Differential Ratio Rear',
            'final drive = (front path ratio + rear path ratio' + div2,
            'final drive = (Differential Ratio Front + Differential Ratio Rear' + div2])
        self.assertEqual(codes[MINI], ['final drive = Differential Ratio Front',
                                       "primary = the gear set's own primary"])
        self.assertEqual(codes[STRATOS], ['final drive = Differential Ratio Rear',
                                          'primary = Primary Gear'])
        self.assertEqual(codes[FABIA][0], 'final drive = 4.231 (fixed)')
        self.assertIn('Center Differential Ratio is applied before the centre differential.',
                      facts[DELTA])
        self.assertIn('No ratio is applied before the centre differential.', facts[IMPREZA])
        self.assertIn('Center Differential Ratio is applied before the centre differential; the front '
                      'and rear differentials are fixed in the game files.', facts[XSARA])
        self.assertIn('This formula cannot be tested on a car with no centre differential, so it is '
                      'taken from the cars where it was measured.', facts[AUDI])
        for slug, text in facts.items():
            with self.subTest(car=slug):
                self.assertNotIn(' run', text)            # no experiments in the facts
        self.assertIn('fixed at 4.231, no selectable ratio', facts[FABIA])
        self.assertIn('replaces the gear set\'s own primary (20//25). The gearing page starts on '
                      '21//24.', facts[P206])
        self.assertIn('The Primary Gear you pick replaces the gear set\'s own primary.',
                      facts[STRATOS])
        self.assertIn('No Primary Gear setting', facts[MINI])
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                self.assertNotIn('Engine curve', html)
                self.assertNotIn('Own curve', html)
                self.assertNotRegex(text_of(html), r'(?i)engine curve|borrow')
        self.assertIn('7260 rpm, measured in game with telemetry (ACR 0.6).', facts[DELTA])
        self.assertIn(f'{STRATOS_LIMIT} rpm, measured in game with telemetry (ACR 0.6).',
                      facts[STRATOS])
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
                self.assertIn('allows for a loaded tyre rolling on a slightly smaller radius; it was fitted', text)
                self.assertIn('15 runs across eight cars (Stratos, 306 Maxi, Xsara WRC, 037, 206 WRC, '
                              'Delta Integrale, Impreza and GTA Junior)', text)
                self.assertNotIn('verified', text.lower())
                self.assertNotIn('science', text.lower())
        why = ("With all four wheels turning at the same road speed, the centre differential's "
               'input turns at (front output speed + rear output speed)\u00a0÷\u00a02, so the '
               'equivalent final drive is:')
        for slug in M.CARS:
            self.assertEqual(why in work[slug], slug in (DELTA, P206, IMPREZA, XSARA), slug)
        rule = '(front path ratio + rear path ratio)\u00a0÷\u00a02'
        self.assertIn('The front drivetrain path has no additional selectable reduction', work[DELTA])
        self.assertIn('The first run could not distinguish between two possibilities: 1. The selected '
                      'Center Ratio to Rear and Differential Ratio Rear are ignored and their stock values '
                      'stay in effect: final drive = Center Differential Ratio × '
                      f'13//34 × 30//12. 2. Final drive = {rule}, with the selected rear ratios.',
                      numbered(section(self.pages[DELTA], 'workings')))
        self.assertIn('the two possibilities put 6th at about 182 and 180 km/h, only about 1% apart, too '
                      'little to distinguish reliably with the in-game speedometer. The speedometer '
                      'read 180.', work[DELTA])
        self.assertIn('Center Differential Ratio stayed on 55//12 and the rear ratios were deliberately '
                      'moved far from stock', work[DELTA])
        self.assertIn('about 182 km/h under possibility 1, or 160 km/h under possibility 2. '
                      f'The measured speed was 160 km/h, supporting final drive = '
                      f'{rule}.', work[DELTA])
        self.assertIn('On gear set 1 the predictions for 3rd were about 126 km/h with primary = '
                      'Primary Gear and 138 km/h with primary = 20//25. The speedometer read 127.',
                      work[P206])
        self.assertIn('about 9% too high on gear set 1 and 15% too high on gear set 3', work[P206])
        self.assertIn('31//21 (1.476)', work[P206])
        self.assertIn('The predictions for 5th were about 98 km/h if it multiplies and 145 km/h if it '
                      'changes nothing. The speedometer read 98', work[P206])
        self.assertIn('It was run on gear set 3 with Primary Gear 22//24, Center Differential Ratio '
                      '24//24, Differential Ratio Front', work[P206])
        self.assertIn('instead of 24//24 (a ratio of 1).', work[P206])
        self.assertIn('supporting possibility 1: Center Differential Ratio multiplies the whole final '
                      'drive.', work[P206])
        self.assertIn('The three possibilities put 4th at about 118, 175 and 141 km/h. The speedometer read '
                      f'142, supporting final drive = {rule}.', work[P206])
        self.assertIn('The three possibilities put 5th at about 128, 191 and 153 km/h. The speedometer read '
                      f'155, supporting final drive = {rule}.', work[IMPREZA])
        self.assertIn('If Center Ratio to Rear multiplies, these keep the two path ratios nearly equal.',
                      work[IMPREZA])
        self.assertIn('The three possibilities put 4th at about 162, 143 and 124 km/h. The speedometer read '
                      '164, supporting rear path ratio = Center Ratio to Rear × Differential Ratio Rear.',
                      work[IMPREZA])
        self.assertIn('the predictions for 5th were about 197 km/h if it replaces and 179 km/h if it '
                      'multiplies. The speedometer read 197', work[STRATOS])
        self.assertIn('all three put 6th at about 184 km/h', work[XSARA])
        self.assertIn('It cannot be tested here.', work[AUDI])
        self.assertIn('This car was not run.', work[MINI])
        self.assertIn('This car was not run.', work[FABIA])
        self.assertIn('A run on gear set 2 with Differential Ratio Rear 46//9 fits that formula: the '
                      'speedometer read 201 km/h in 5th, where it puts 5th at 202. That run is also '
                      'one of those the rolling factor was fitted on.', work[LANCIA037])
        self.assertIn('the speedometer read 183 km/h in 6th, where it puts 6th at 185.', work[P306])
        self.assertIn('It fits final drive = (front path ratio + rear path ratio)\u00a0÷\u00a02, the formula '
                      'measured on the Delta Integrale, 206 WRC and Impreza.', work[XSARA])
        self.assertIn('The one run could not distinguish between three possibilities:', work[XSARA])
        self.assertIn('The primary is the Primary Gear you pick. The final drive is Differential Ratio '
                      'Rear alone', work[STRATOS])
        self.assertIn('gives the same number: (4.231 + 4.231)\u00a0÷\u00a02 = 4.231. This car was not run.',
                      work[FABIA])
        per_set = ('Each gear set stores its own primary, and with no Primary Gear setting that is the '
                   'one in force: that was measured on the GTA Junior, whose gear sets all store 30//23. '
                   'Here the primary changes from set to set, and each set is taken to use its own in '
                   'the same way; primaries that change from set to set have not been run.')
        for slug in M.CARS:
            with self.subTest(car=slug):
                self.assertEqual(per_set in work[slug], slug in SET_PRIMARY_CARS)
                self.assertNotIn('has not been tested', work[slug])
                self.assertNotIn('do nothing', work[slug])
                self.assertNotIn('engine curve of its own', work[slug])
        self.assertIn('The GTA Junior has no Primary Gear setting, and every one of its gear sets stores a '
                      'primary of 30//23 (1.304). The run was chosen to distinguish between two '
                      "possibilities: 1. The gear set's stored primary applies: primary = 30//23. "
                      '2. The stored primary is ignored: primary = 1. It was run on gear set 1 with '
                      'Differential Ratio Rear 43//9. The predictions for 3rd were about 129 km/h under '
                      'possibility 1 and 168 km/h under possibility 2. The speedometer read 128, '
                      "supporting possibility 1: primary = the gear set's own primary.",
                      numbered(section(self.pages[ALFA], 'workings')))
        self.assertEqual(code_lines(section(self.pages[ALFA], 'workings'))[-1],
                         "primary = the gear set's own primary")
        self.assertNotIn('This car was not run.', work[ALFA])

    def test_measured_in_game(self):
        for slug, html in self.pages.items():
            with self.subTest(car=slug):
                m = text_of(section(html, 'measured'))
                self.assertIn('SimHub telemetry · ACR 0.6 · 2026-09-14', m)
                self.assertNotIn('%', m)
                self.assertNotIn('predict', m.lower())
                runs = [r for r in self.cal['speed_runs'] if r['car'] == slug]
                self.assertEqual(html.count('<table class="speeds">'), len(runs))
        m206 = section(self.pages[P206], 'measured')
        self.assertIn('<td>164*</td>', m206)
        self.assertEqual(m206.count('did not reach the rev limiter'), 1)
        alfa = section(self.pages[ALFA], 'measured')
        self.assertIn('<td>174*</td>', alfa)
        self.assertIn('* an approximate reading.', alfa)
        self.assertNotIn('did not reach the rev limiter', alfa)
        self.assertIn('Gear set 1 · dry tarmac · 2026-09-14', text_of(alfa))
        self.assertIn('Differential Ratio Rear 43//9', text_of(alfa))
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

    def test_the_drivetrain_pages_are_not_linked_yet(self):
        self.assertIs(E.PUBLISH_DRIVETRAIN_LINKS, False)
        for html in (E.render_index_page(self.CARS),
                     E.render_car_page('lancia-stratos', 'Lancia Stratos HF')):
            self.assertNotIn('drivetrain/', html)
            self.assertNotIn('Drivetrain notes', html)
            self.assertNotIn('dtlist', html)
        html = E.render_index_page(self.CARS)
        self.assertEqual(re.findall(r'<li><a href="([^"]+)/gears/">', html),
                         ['lancia-stratos', 'mini-cooper-s-1964'])
        self.assertLess(html.index('</ul>'), html.index('<div class="foot">'))
        row = E.render_car_page('lancia-stratos', 'Lancia Stratos HF')
        row = row[row.index('class="brandrow"'):row.index('<h1>')]
        self.assertIn('<span class="brand">ACR <b>Car Lab</b></span>\n      '
                      '<a class="crumb" href="../../">All cars', row)

    def test_the_flag_sets_both_links(self):
        from unittest import mock
        with mock.patch.object(E, 'PUBLISH_DRIVETRAIN_LINKS', True):
            self.assertEqual(E.render_index_page(self.CARS),
                             E.render_index_page(self.CARS, publish_drivetrain=True))
            self.assertEqual(E.render_car_page('lancia-stratos', 'Lancia Stratos HF'),
                             E.render_car_page('lancia-stratos', 'Lancia Stratos HF',
                                               publish_drivetrain=True))
            self.assertIn('Drivetrain notes', E.render_index_page(self.CARS))

    def test_the_drivetrain_pages_are_not_indexed(self):
        if not HAVE_SITE:
            self.skipTest('no ../acr-car-lab checkout next to this repo')
        cal, notes = CAL.load_calibration(), D.load_notes()
        for slug in M.CARS:
            html = E.render_drivetrain_page(site_doc(slug), template(slug), cal, notes)
            head = html[:html.index('</head>')]
            with self.subTest(car=slug):
                self.assertIn('<meta name="robots" content="noindex">', head)
        self.assertNotIn('noindex', E.render_car_page('lancia-stratos', 'Lancia Stratos HF'))
        self.assertNotIn('noindex', E.render_index_page(self.CARS))

    def test_the_gears_list_is_unchanged_and_a_drivetrain_list_follows(self):
        html = E.render_index_page(self.CARS, publish_drivetrain=True)
        gears = re.findall(r'<li><a href="([^"]+)/gears/">', html)
        dt = re.findall(r'<li><a href="([^"]+)/drivetrain/">', html)
        self.assertEqual(gears, ['lancia-stratos', 'mini-cooper-s-1964'])
        self.assertEqual(dt, gears)
        first_list = html[html.index('<ul class="carlist">'):html.index('</ul>')]
        self.assertNotIn('drivetrain', first_list)
        self.assertLess(html.index('</ul>'), html.index('<h2>Drivetrain notes</h2>'))
        self.assertIn('<ul class="carlist minor">', html)

    def test_the_gears_page_links_to_the_drivetrain_page(self):
        html = E.render_car_page('lancia-stratos', 'Lancia Stratos HF', publish_drivetrain=True)
        row = html[html.index('class="brandrow"'):html.index('<h1>')]
        self.assertIn('<a class="crumb" href="../drivetrain/">Drivetrain notes</a>\n      '
                      '<a class="crumb" href="../../">All cars', row)


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


def record_from(doc):
    """A car_record tuple that rebuilds `doc` through build_car_json."""
    fd = doc['final_drive']
    if fd is not None:
        fd = dict(fd, primaries=[(p['name'], p['value']) for p in fd['primaries']],
                  options=[(o['name'], o['value']) for o in fd['options']])
    e = doc['engine']
    return (doc['name'], doc['axle'],
            [([g['name'] for g in s['gears']], s['primary']['name'], '1//1')
             for s in doc['gear_sets']],
            [(rpm, nm) for rpm, nm, _kw in e['curve']], fd, doc['fixed_final_drive'],
            {k: (t['asset'], t['free_radius']) for k, t in doc['tyres'].items()},
            {'rpm': e['redline'], 'source': e['redline_source'], 'game_v4': e['game_v4'],
             'curve_source': e['curve_source'], 'curve_from': e['curve_from']})


@unittest.skipUnless(HAVE_SITE, 'no ../acr-car-lab checkout next to this repo')
class ExportRuns(unittest.TestCase):
    """main() around the drivetrain pages, with the game files stubbed by the exported data."""

    def run_main(self, argv, cars, notes=None):
        from unittest import mock
        import io
        records = {s: record_from(site_doc(s)) for s in cars}
        patches = [
            mock.patch.object(sys, 'argv', ['export_car_data.py'] + argv),
            mock.patch.object(E.M, 'CARS', {s: M.CARS[s] for s in cars}),
            mock.patch.object(E, 'car_record', lambda paks, slug, tmp: records[slug]),
            mock.patch.object(E, 'site_game_version', lambda paks, whole: '0.6' if whole else None),
            mock.patch('sys.stdout', new_callable=io.StringIO),
        ]
        if notes is not None:
            patches.append(mock.patch.object(E.DP, 'load_notes', lambda: notes))
        for p in patches:
            p.start()
        out = sys.stdout
        try:
            E.main()
            return None, out.getvalue()
        except SystemExit as e:
            return e, out.getvalue()
        finally:
            for p in reversed(patches):
                p.stop()

    def test_existing_index_facts(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(E.existing_index_facts(out), (None, None))
            os.makedirs(os.path.join(out, 'data'))
            with open(os.path.join(out, 'data', 'index.json'), 'w', encoding='utf-8') as fh:
                json.dump({'cars': [], 'generated': '2026-09-01', 'game_version': '0.5'}, fh)
            self.assertEqual(E.existing_index_facts(out), ('0.5', '2026-09-01'))

    def test_a_single_car_export_names_the_version_and_date_of_the_site_index(self):
        with tempfile.TemporaryDirectory() as out:
            os.makedirs(os.path.join(out, 'data'))
            index = {'cars': [], 'generated': '2026-09-01', 'game_version': '0.5'}
            with open(os.path.join(out, 'data', 'index.json'), 'w', encoding='utf-8') as fh:
                json.dump(index, fh)
            err, _log = self.run_main(['--car', MINI, '--out', out], [MINI])
            self.assertIsNone(err)
            with open(os.path.join(out, MINI, 'drivetrain', 'index.html'), encoding='utf-8') as fh:
                html = fh.read()
            self.assertIn('Read from the ACR 0.5 game files. Generated 2026-09-01.', html)
            self.assertIn('measured in game with telemetry (ACR 0.5).', html)
            with open(os.path.join(out, 'data', 'index.json'), encoding='utf-8') as fh:
                self.assertEqual(json.load(fh), index)          # not rewritten

    def broken_notes(self, slug):
        notes = copy.deepcopy(D.load_notes())
        notes['cars'][slug]['workings'] = ['6th reads {kmh:no_such_hypothesis:1:6} km/h.']
        return notes

    def test_a_failing_drivetrain_page_skips_that_car_and_fails_the_run_at_the_end(self):
        with tempfile.TemporaryDirectory() as out:
            os.makedirs(os.path.join(out, 'data'))
            open(os.path.join(out, 'data', 'gone.json'), 'w').close()     # a stale car
            err, log = self.run_main(['--all', '--out', out], [MINI, DELTA],
                                     notes=self.broken_notes(DELTA))
            self.assertIsInstance(err, SystemExit)
            self.assertIn('export incomplete', str(err))
            self.assertIn(DELTA, str(err))
            self.assertIn('drivetrain page failed', str(err))
            self.assertIn(f'!! {DELTA}: drivetrain page failed: ValueError', log)
            self.assertIn('no_such_hypothesis', log)
            # the other car and the site-wide steps still ran
            self.assertTrue(os.path.isfile(os.path.join(out, MINI, 'drivetrain', 'index.html')))
            with open(os.path.join(out, 'data', 'index.json'), encoding='utf-8') as fh:
                self.assertEqual([c['slug'] for c in json.load(fh)['cars']], [MINI])
            self.assertTrue(os.path.isfile(os.path.join(out, 'index.html')))
            self.assertFalse(os.path.exists(os.path.join(out, 'data', 'gone.json')))
            # nothing half-written for the failed car
            self.assertFalse(os.path.exists(os.path.join(out, 'data', DELTA + '.json')))
            self.assertFalse(os.path.exists(os.path.join(out, DELTA)))

    def test_a_single_car_failure_names_the_car_and_exits(self):
        with tempfile.TemporaryDirectory() as out:
            os.makedirs(os.path.join(out, 'data'))
            err, _log = self.run_main(['--car', DELTA, '--out', out], [DELTA],
                                      notes=self.broken_notes(DELTA))
            self.assertIsInstance(err, SystemExit)
            self.assertTrue(str(err).startswith(f'{DELTA}: drivetrain page failed'))

    def test_the_audi_final_drive_line_is_assumed_not_stated(self):
        cal, notes = CAL.load_calibration(), D.load_notes()
        for slug in M.CARS:
            top = text_of(section(E.render_drivetrain_page(site_doc(slug), template(slug), cal,
                                                           notes), 'top'))
            with self.subTest(car=slug):
                self.assertEqual('This formula cannot be tested on a car with no centre differential, '
                                 'so it is taken from the cars where it was measured.' in top,
                                 slug == AUDI)
                self.assertEqual('before the centre differential' in top,
                                 slug in (DELTA, P206, IMPREZA, XSARA))

    def test_the_torque_curve_runs_past_the_rev_limit_on_most_cars(self):
        # backs "not the limiter: on most cars here the curve runs past it". The Delta Integrale's
        # curve ends at 7250 rpm, 10 short of its 7260 limiter (measured 2026-09-14)
        short = []
        for slug in M.CARS:
            e = site_doc(slug)['engine']
            with self.subTest(car=slug):
                self.assertNotEqual(e['curve'][-1][0], e['redline'])
                if e['curve'][-1][0] < e['redline']:
                    short.append(slug)
        self.assertEqual(short, [DELTA])


@unittest.skipUnless(HAVE_SITE, 'no ../acr-car-lab checkout next to this repo')
class ReviewCopy(unittest.TestCase):
    """The copy corrections of the Job B review, word for word."""

    def work(self, slug):
        html = E.render_drivetrain_page(site_doc(slug), template(slug), CAL.load_calibration(),
                                        D.load_notes())
        return text_of(section(html, 'workings'))

    def test_corrections(self):
        self.assertIn('The same rule fits the runs on the Stratos and the 037 (Differential '
                      'Ratio Rear) and on the 306 Maxi (Differential Ratio Front).', self.work(MINI))
        self.assertIn('It was run on Center Differential Ratio 55//12 with the rear ratios close to '
                      'stock: Center Ratio to Rear 13//34 and Differential Ratio Rear 34//14.',
                      self.work(DELTA))
        self.assertIn('With the path ratios nearly equal the car drove normally, as expected.',
                      self.work(IMPREZA))
        self.assertIn('and with no centre differential they make the axles fight and the car hard to '
                      'control.', self.work(AUDI))
        for slug in M.CARS:
            text = self.work(slug)
            with self.subTest(car=slug):
                self.assertIn('The end of the torque curve in the game files is not the limiter: '
                              'on most cars here the curve runs past it.', text)
                self.assertIn('The free radius is the tyre radius stored in the game files. The rolling factor, '
                              '0.9780, allows for a loaded tyre rolling on a slightly smaller radius; '
                              'it was fitted', text)
                self.assertNotIn('undriveable', text)


@unittest.skipUnless(HAVE_SITE, 'no ../acr-car-lab checkout next to this repo')
class ImpersonalFormulaCopy(unittest.TestCase):
    """Round 4 (R56): formulas instead of the word average, and no personal name, on every page."""

    def test_no_average_and_no_name_on_any_page(self):
        cal, notes = CAL.load_calibration(), D.load_notes()
        for slug in M.CARS:
            html = E.render_drivetrain_page(site_doc(slug), template(slug), cal, notes)
            with self.subTest(car=slug):
                self.assertNotRegex(html, re.compile(r'averag', re.I))
                self.assertNotRegex(html, r'Fred\b')
                # a ÷ 2 is held together with no-break spaces, so it never starts a line
                self.assertNotRegex(html, r'[ \t\n]÷\s2|÷[ \t\n]2')
                if slug in (DELTA, P206, IMPREZA, XSARA, AUDI):
                    self.assertIn(' ÷ 2', html)

    def test_no_average_and_no_name_in_the_other_generated_pages(self):
        cars = [{'slug': s, 'name': site_doc(s)['name']} for s in M.CARS]
        pages = [E.render_index_page(cars)] + [E.render_car_page(c['slug'], c['name'])
                                               for c in cars]
        for html in pages:
            self.assertNotRegex(html, re.compile(r'averag', re.I))
            self.assertNotRegex(html, r'Fred\b')

    def test_no_name_in_any_note_a_page_can_show(self):
        notes = D.load_notes()
        common = notes['common']
        shown = [list(common['rev_limit'].values())]
        for k, v in common.items():
            if k != 'rev_limit':
                shown.append([x for i in (v if isinstance(v, list) else [v])
                              for x in note_strings(i)])
        for entry in notes['cars'].values():
            shown.append([x for i in entry['workings'] for x in note_strings(i)]
                         + [entry.get('handling', '')])
        # an "@name" item is a reference to a common item, checked above, not shown text
        # and a {placeholder} (hypothesis names are internal) is replaced before it is shown
        for text in (re.sub(r'\{[^{}]*\}', '', s) for group in shown for s in group):
            self.assertNotRegex(text, re.compile(r'averag', re.I))
            self.assertNotRegex(text, r'Fred\b')

    def test_formula_note_writes_out_a_fixed_ratio_beside_a_setting(self):
        fd = {'settings': [{'key': 'dfr', 'adjustment': 'Differential Ratio Front'},
                           {'key': 'drr', 'adjustment': 'Differential Ratio Rear'}],
              'formula': {'pre': [], 'front': ['dfr'], 'rear': ['drr'], 'fixed_pre': 1.25,
                          'fixed_front': 1.0, 'fixed_rear': 1.1}}
        self.assertEqual(D.formula_note(fd), 'Final drive = 1.250 × (Differential Ratio Front + '
                                             'Differential Ratio Rear × 1.100)\u00a0÷\u00a02')


@unittest.skipUnless(HAVE_SITE, 'no ../acr-car-lab checkout next to this repo')
class FormulaBlocks(unittest.TestCase):
    """Round 5 (R57): formulas as their own lines, the path ratios named, the intro's speed maths."""

    @classmethod
    def setUpClass(cls):
        cls.cal, cls.notes = CAL.load_calibration(), D.load_notes()
        cls.pages = {slug: E.render_drivetrain_page(site_doc(slug), template(slug), cls.cal,
                                                    cls.notes) for slug in M.CARS}

    def test_the_intro_has_the_three_formula_lines_and_where_the_point_zero_six_comes_from(self):
        for slug, html in self.pages.items():
            work = section(html, 'workings')
            with self.subTest(car=slug):
                self.assertEqual(code_lines(work)[:3], [
                    'speed (km/h) = rpm × tyre circumference (m) × 0.06 ÷ total ratio',
                    'total ratio = primary × gear × final drive',
                    'tyre circumference = 2π × free radius × 0.9780'])
                self.assertRegex(work, r'<code>speed \(km/h\)[^<]*</code></div>\s*<p>rpm × tyre circumference ÷ total '
                                       r'ratio is metres per minute; × 0\.06 \(× 60 minutes per hour ÷ '
                                       r'1000 metres per kilometre\) turns that into km/h\.</p>')
                text = text_of(work)
                self.assertIn('was fitted to the top speeds measured in game on 15 runs across eight '
                              'cars', text)
                self.assertIn('was measured in game with telemetry', text)

    def test_the_speed_formula_is_the_one_the_code_computes(self):
        import math
        rpm, r, total = 7000, 0.3, 12.5
        self.assertAlmostEqual(CAL.predicted_kmh(rpm, total, 1.0, 1.0, r, 0.9904),
                               rpm * (2 * math.pi * r * 0.9904) * 0.06 / total)

    def test_every_awd_page_names_its_path_ratios_and_the_expanded_formula_of_the_gears_note(self):
        n = 0
        for slug, html in self.pages.items():
            fd = site_doc(slug)['final_drive']
            if not fd or 'settings' not in fd:
                continue
            n += 1
            expr = D.formula_expression(fd)
            want = D.path_ratio_lines(fd) + [
                'final drive = (front path ratio + rear path ratio)\u00a0÷\u00a02',
                f'final drive = {expr}']
            with self.subTest(car=slug):
                self.assertTrue(D.formula_note(fd).startswith(f'Final drive = {expr}'))
                self.assertEqual(code_lines(section(html, 'top'))[:4], want)
                work = code_lines(section(html, 'workings'))
                for line in want:
                    self.assertIn(line, work)
                self.assertTrue(all(line.startswith(('front path ratio = ', 'rear path ratio = '))
                                    for line in want[:2]))
        self.assertEqual(n, 5)

    def test_the_xsara_predictions_really_round_to_one_number(self):
        doc = site_doc(XSARA)
        run = D.car_runs(self.cal, XSARA)[0]
        hyps = self.notes['cars'][XSARA]['hypotheses']
        got = {round(D.run_kmh(self.cal, doc, run, h, D.LOADED_RADIUS_FACTOR)[5])
               for h in ({}, hyps['front'], hyps['rear'])}
        self.assertEqual(len(got), 1)

    def test_a_rest_hypothesis_uses_one_fixed_differential(self):
        doc = site_doc(XSARA)
        run = D.car_runs(self.cal, XSARA)[0]
        f = doc['final_drive']['formula']
        _, below = D.run_ratios(doc, run, {'rest': 'fixed_front'})
        self.assertAlmostEqual(below, f['fixed_front'] * 39 / 24)

    def test_an_unknown_workings_item_raises(self):
        notes = copy.deepcopy(self.notes)
        notes['cars'][MINI]['workings'] = [{'table': []}]
        with self.assertRaises(ValueError):
            D.workings_blocks(site_doc(MINI), self.cal, notes)

    def test_hypotheses_are_numbered_lists(self):
        for slug, count in ((DELTA, 1), (P206, 3), (IMPREZA, 2), (XSARA, 1), (STRATOS, 1),
                            (ALFA, 1), (MINI, 0), (AUDI, 0)):
            with self.subTest(car=slug):
                self.assertEqual(section(self.pages[slug], 'workings').count('<ol class="hyp">'),
                                 count)

    def test_primaries_that_change_from_set_to_set_say_they_were_not_run(self):
        # the stored-primary rule was measured on the GTA Junior (30//23 on every set, no Primary
        # Gear setting); a car whose stored primary changes from set to set uses it the same way,
        # untested, and its page has to say so
        note = 'primaries that change from set to set have not been run'
        alfa_runs = D.car_runs(self.cal, ALFA)
        self.assertTrue(alfa_runs and all(abs(D.ratio(r['primary']) - 1) > 1e-9 for r in alfa_runs))
        self.assertFalse(site_doc(ALFA)['final_drive']['primaries'])
        cars = []
        for slug in M.CARS:
            doc = site_doc(slug)
            selector = bool(doc['final_drive'] and doc['final_drive']['primaries'])
            per_set = len({s['primary']['name'] for s in doc['gear_sets']}) > 1
            run_per_set = len({r['gear_set'] for r in D.car_runs(self.cal, slug)}) > 1
            with self.subTest(car=slug):
                self.assertFalse(per_set and not selector and run_per_set)  # else reword the note
                if note in text_of(section(self.pages[slug], 'workings')):
                    cars.append(slug)
                self.assertEqual(slug in cars, per_set and not selector)
        self.assertEqual(sorted(cars), sorted(SET_PRIMARY_CARS))
