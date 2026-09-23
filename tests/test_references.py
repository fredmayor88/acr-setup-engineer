"""Guard the skill references against the machinery this design removed.

Run: python -m unittest discover -s tests
"""
import glob
import os
import re
import unittest

SKILL = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'acr-setup-engineer')
FILES = [os.path.join(SKILL, 'SKILL.md')] + sorted(glob.glob(os.path.join(SKILL, 'references', '*.md')))

# A phrase that must not appear anywhere (case-insensitive), except in the one file allowed.
BANNED = [
    ('catalog snapshot', {'notion-structure.md', 'onboard-car.md', 'catalog-read.md'}),  # legacy + migration
    ('refresh-catalog-snapshot', set()),
    ('paste the', {'config-page-template.md'}),  # pasting the API token is legitimate
    ('--snapshot', set()),
    ('--all', set()),
    ('params_data_source_id', set()),
    ('`parameters` rows', {'notion-structure.md', 'onboard-car.md'}),   # legacy note + migration only
    ('`parameters` db', {'notion-structure.md', 'onboard-car.md'}),
]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class TestNoRemovedMachinery(unittest.TestCase):
    def test_catalog_read_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(SKILL, 'references', 'catalog-read.md')))

    def test_snapshot_workflow_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(SKILL, 'references', 'refresh-catalog-snapshot.md')))

    def test_banned_phrases(self):
        problems = []
        for path in FILES:
            name = os.path.basename(path)
            text = read(path).lower()
            for phrase, allowed in BANNED:
                if name in allowed:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if phrase in line:
                        problems.append(f'{name}:{i}: {phrase!r}')
        self.assertFalse(problems, '\n'.join(problems))

    def test_every_catalog_loading_workflow_points_at_catalog_read(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md', 'share-setup.md',
                     'review-setup.md', 'ask-setups.md', 'import-savegame.md',
                     'export-car-template.md', 'edit-catalog.md'):
            self.assertIn('catalog-read.md', read(os.path.join(SKILL, 'references', name)), name)


class TestSetupIndex(unittest.TestCase):
    def ref(self, name):
        return read(os.path.join(SKILL, 'references', name))

    def test_data_model_has_the_section(self):
        text = self.ref('notion-structure.md')
        self.assertIn('### Adding a line to `Setup index`', text)
        self.assertIn('setups_list.py --line', text)

    def test_refresh_docs_never_write_the_index(self):
        for name in ('onboard-car.md', 'refresh-notion.md'):
            self.assertIn('`Setup index`', self.ref(name), name)
            self.assertRegex(self.ref(name), r'`Setup index`[^\n]*never', name)

    def test_every_saver_adds_an_index_line(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md', 'import-savegame.md'):
            text = self.ref(name)
            self.assertIn('Adding a line to `Setup index`', text, name)

    def test_build_indexes_the_default_too(self):
        text = self.ref('build-setup.md')
        self.assertEqual(text.count('Adding a line to `Setup index`'), 2,
                         'build-setup must add a line for the built setup AND for a captured default')

    def test_free_read_path_exists_and_never_searches(self):
        path = os.path.join(SKILL, 'references', 'setups-list-read.md')
        self.assertTrue(os.path.isfile(path))
        text = read(path)
        for section in ('## Reading a car\'s setups on Free', '## Load more',
                        '## Finding one setup by name', '## Adding setups by link'):
            self.assertIn(section, text, section)
        self.assertNotIn('notion-search', text.replace('never `notion-search`', ''))

    def test_offline_mode_routes_to_the_list(self):
        text = self.ref('notion-rest-read.md')
        self.assertIn('setups-list-read.md', text)
        self.assertNotIn("can't read your saved setups", text)
        self.assertIn('--overrides', text)

    def test_build_names_the_free_path(self):
        self.assertIn('setups-list-read.md', self.ref('build-setup.md'))

    def test_skill_md_lists_the_script_and_the_reference(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('scripts/setups_list.py', text)
        self.assertIn('references/setups-list-read.md', text)

    def test_index_by_links_is_named_everywhere(self):
        self.assertIn('index these setups:', read(os.path.join(SKILL, 'SKILL.md')))
        self.assertIn('index these setups:', self.ref('how-to-use-template.md'))
        self.assertIn('One insert per car', self.ref('setups-list-read.md'))
        self.assertNotIn('Adding a setup by link', self.ref('setups-list-read.md'))

    def test_named_setup_workflows_use_the_index_on_free(self):
        for name in ('review-setup.md', 'ask-setups.md', 'share-setup.md', 'tweak-setup.md'):
            self.assertIn('Finding one setup by name', self.ref(name), name)

    def test_readme_no_longer_says_no_setup_history(self):
        text = read(os.path.join(SKILL, '..', '..', '..', 'README.md'))
        self.assertNotIn('**No setup history.**', text)
        self.assertIn('Setup index', text)


class TestBundledDefaults(unittest.TestCase):
    def ref(self, name):
        return read(os.path.join(SKILL, 'references', name))

    def test_build_anchors_on_the_bundled_setup(self):
        text = self.ref('build-setup.md')
        self.assertIn('load_default_setup.py --car', text)
        self.assertIn('car-setups/', text)

    def test_skill_md_names_the_loader_and_game_version(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('scripts/load_default_setup.py', text)
        self.assertIn('GAME_VERSION', text)

    def test_game_version_fills_the_column(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md'):
            self.assertIn('GAME_VERSION', self.ref(name), name)

    def test_free_read_path_defers_to_bundled_defaults(self):
        self.assertIn('car-setups/', self.ref('setups-list-read.md'))

    def test_the_notion_read_path_defers_to_bundled_defaults(self):
        """The `--source default` query is for screenshot cars only.

        Every place notion-rest-read.md mentions the stored-default slice has to say so, or a
        template car's build spends a read on rows it must not use.
        """
        self.assertIn('car-setups/', self.ref('notion-rest-read.md'))

    def test_off_grid_bundled_values_are_kept_not_clamped(self):
        self.assertIn('kept as the game ships it', self.ref('build-setup.md'))

    def test_free_plan_page_promises_the_bundled_default_and_its_version(self):
        """The page body has to state where the default comes from, with the game version.

        The old test asserted the *absence* of a sentence nobody had written, so it passed on
        an empty page. This one fails if the promise or the version placeholder goes away.
        """
        body = self.ref('free-plan-template.md').partition('\n---\n')[2]
        self.assertIn('built into the skill', body)
        self.assertIn('{game_version}', body)

    def test_how_to_use_page_carries_the_game_version(self):
        body = self.ref('how-to-use-template.md').partition('\n---\n')[2]
        self.assertIn('{game_version}', body)


class TestGameVersionNotes(unittest.TestCase):
    """The per-version tuning notes are a guideline layer every value-choosing workflow reads."""
    WORKFLOWS = ('build-setup.md', 'tweak-setup.md', 'review-setup.md', 'ask-setups.md')

    def ref(self, name):
        return read(os.path.join(SKILL, 'references', name))

    def test_skill_md_names_the_folder_the_script_and_the_layer(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('game-versions/', text)
        self.assertIn('scripts/load_game_version_notes.py', text)
        self.assertIn('game version notes', text.lower())

    def test_version_claims_left_the_base_and_the_workflows(self):
        for path in FILES:
            text = read(path).lower()
            self.assertNotIn("pressure model isn't physically sensible", text, path)
            self.assertNotIn('early access', text, path)
            self.assertNotIn('still maturing', text, path)

    def test_principles_point_at_the_notes_for_pressure(self):
        text = self.ref('setup-tuning-principles.md')
        self.assertIn('load_game_version_notes.py', text)

    def test_interview_points_at_the_notes_for_pressure_and_cold_tyres(self):
        text = self.ref('driving-feedback-interview.md')
        self.assertIn('game version notes', text.lower())
        self.assertIn('cold tyres', text)

    def test_build_uses_stage_length_and_the_pressure_target(self):
        text = self.ref('build-setup.md')
        self.assertIn('8 km', text)
        self.assertIn('0.6 tyre notes', text)
        self.assertIn('about how long is the stage?', text)
        self.assertIn('cold tyres', text)

    def test_every_workflow_runs_the_notes_loader(self):
        for name in self.WORKFLOWS:
            self.assertIn('python scripts/load_game_version_notes.py', self.ref(name), name)

    def test_tweak_moves_cold_pressure_by_the_gauge_difference(self):
        self.assertIn('by the difference', self.ref('tweak-setup.md'))

    def test_docs_pages_say_setups_follow_the_version_notes(self):
        for name in ('how-to-use-template.md', 'free-plan-template.md'):
            body = self.ref(name).partition('\n---\n')[2]
            self.assertIn('tuning notes for game version {game_version}', body, name)


if __name__ == '__main__':
    unittest.main()
