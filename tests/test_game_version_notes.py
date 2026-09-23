"""game-versions/<version>.md — the tuning notes for one game version.

Hand-written prose the workflows read as the guideline layer right after the base principles.
The file for the current GAME_VERSION must exist and carry the sections the workflows quote.

Run: python -m unittest discover -s tests
"""
import glob
import os
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
NOTES = os.path.join(SKILL, 'game-versions')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()

SECTIONS = [
    '## What changed in ',
    '## Tyre pressure',
    '## Tyre type on tarmac',
    '## Finding the right cold pressure for a stage',
]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class TestNotesFiles(unittest.TestCase):
    def test_current_game_version_has_notes(self):
        self.assertTrue(os.path.isfile(os.path.join(NOTES, GAME_VERSION + '.md')))

    def test_every_file_is_named_by_a_version_and_says_so_in_frontmatter(self):
        files = glob.glob(os.path.join(NOTES, '*.md'))
        self.assertTrue(files)
        for path in files:
            name = os.path.basename(path)[:-3]
            self.assertRegex(name, r'^\d+(\.\d+)+$', path)
            text = read(path)
            self.assertTrue(text.startswith('---\n'), path)
            front = text.split('---\n')[1]
            self.assertIn('game: "ACR"', front, path)
            self.assertIn(f'version: "{name}"', front, path)

    def test_current_notes_carry_the_sections_the_workflows_quote(self):
        text = read(os.path.join(NOTES, GAME_VERSION + '.md'))
        for heading in SECTIONS:
            self.assertIn(heading, text, heading)

    def test_current_notes_state_the_tyre_rules(self):
        text = read(os.path.join(NOTES, GAME_VERSION + '.md'))
        self.assertIn('28 psi', text)
        self.assertIn('8 km', text)
        self.assertIn('Tarmac Medium', text)
        self.assertIn('Tarmac Soft', text)


if __name__ == '__main__':
    unittest.main()
