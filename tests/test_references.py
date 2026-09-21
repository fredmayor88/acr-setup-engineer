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


if __name__ == '__main__':
    unittest.main()
