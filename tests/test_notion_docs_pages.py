"""Guard the two skill-owned documentation pages the skill writes into the user's Notion.

`How to use` and `Claude Free plan` are seeded from templates in `references/` and rewritten on
every skill update. The page body is everything below the template's `---` line. These tests keep
the pages from falling behind the skill: every workflow in SKILL.md's routing table must be named
in the `How to use` template's `Covers:` list, so adding a workflow fails here until the page
gets a line for it.

Run: python -m unittest discover -s tests
"""
import os
import re
import unittest

SKILL = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'acr-setup-engineer')
REFS = os.path.join(SKILL, 'references')
HOW_TO = os.path.join(REFS, 'how-to-use-template.md')
FREE = os.path.join(REFS, 'free-plan-template.md')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def split(path):
    """(header, body) — the body is what gets written to Notion."""
    header, sep, body = read(path).partition('\n---\n')
    assert sep, f'{path} has no --- line separating the notes from the page body'
    return header, body


def routed_workflows():
    """Every references/*.md named in the SKILL.md routing table."""
    table = [line for line in read(os.path.join(SKILL, 'SKILL.md')).splitlines()
             if line.startswith('|')]
    return sorted({m for line in table for m in re.findall(r'references/([\w-]+\.md)', line)})


class TestHowToUsePage(unittest.TestCase):
    def test_covers_every_routed_workflow(self):
        header, _ = split(HOW_TO)
        covers = re.search(r'^Covers:(.*)$', header, re.M)
        self.assertIsNotNone(covers, 'no "Covers:" line above the --- line')
        covered = set(re.findall(r'[\w-]+\.md', covers.group(1)))
        missing = [w for w in routed_workflows() if w not in covered]
        self.assertFalse(missing, f'How to use has no line for: {missing}')
        self.assertIn('onboard-car.md', routed_workflows())  # the table parse still works

    def test_banner_carries_the_version(self):
        _, body = split(HOW_TO)
        self.assertIn('{version}', body.strip().splitlines()[2])

    def test_names_the_update_command(self):
        _, body = split(HOW_TO)
        self.assertIn('refresh my ACR Notion', body)

    def test_points_free_users_to_their_page(self):
        _, body = split(HOW_TO)
        self.assertIn('Claude Free plan', body)

    def test_mentions_the_setup_index_override(self):
        _, body = split(HOW_TO)
        self.assertIn('learn: yes', body)
        self.assertIn('paste', body.lower())


class TestFreePlanPage(unittest.TestCase):
    def test_banner_carries_the_version(self):
        _, body = split(FREE)
        self.assertIn('{version}', body.strip().splitlines()[2])

    def test_names_learn_from_this(self):
        _, body = split(FREE)
        self.assertIn('Learn from this', body)

    def test_no_longer_claims_setups_cannot_be_read(self):
        _, body = split(FREE)
        self.assertNotIn("can't be read back", body)
        self.assertIn('Setup index', body)
        self.assertIn('up to 6', body)
        self.assertIn('learn: yes', body)


class TestNoRemovedCommands(unittest.TestCase):
    def test_no_snapshot_command(self):
        for path in (HOW_TO, FREE):
            _, body = split(path)
            self.assertNotIn('catalog snapshot for', body.lower(), path)


if __name__ == '__main__':
    unittest.main()
