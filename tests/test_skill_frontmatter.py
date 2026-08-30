"""Guard SKILL.md's YAML frontmatter against the claude.ai upload limits.

The uploader rejects the whole skill with "field 'description' in SKILL.md must be at most
1024 characters" — a failure that only shows up at install time, after a release is cut.
This test moves that check into `make test`, which the release runs.

Run: python -m unittest discover tests
"""
import os
import re
import unittest

SKILL_MD = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                        'acr-setup-engineer', 'SKILL.md')

# claude.ai's Upload skill limits.
MAX_DESCRIPTION = 1024
MAX_NAME = 64


def frontmatter_field(name):
    with open(SKILL_MD, encoding='utf-8') as f:
        text = f.read()
    match = re.search(r'^---\n(.*?)\n---\n', text, re.S)
    assert match, 'SKILL.md has no YAML frontmatter block'
    field = re.search(r'^%s: (.*)$' % name, match.group(1), re.M)
    assert field, 'SKILL.md frontmatter has no %r field' % name
    return field.group(1).strip()


class TestSkillFrontmatter(unittest.TestCase):
    def test_description_within_upload_limit(self):
        description = frontmatter_field('description')
        self.assertLessEqual(
            len(description), MAX_DESCRIPTION,
            'SKILL.md description is %d chars; claude.ai rejects anything over %d'
            % (len(description), MAX_DESCRIPTION))

    def test_name_within_upload_limit(self):
        name = frontmatter_field('name')
        self.assertTrue(name, 'SKILL.md frontmatter name is empty')
        self.assertLessEqual(len(name), MAX_NAME)

    def test_description_is_one_line(self):
        # A wrapped description silently truncates at the newline on upload.
        with open(SKILL_MD, encoding='utf-8') as f:
            text = f.read()
        block = re.search(r'^---\n(.*?)\n---\n', text, re.S).group(1)
        after = block.split('description: ', 1)[1].split('\n')
        self.assertTrue(after[0].strip(), 'description must be on the same line as the key')


if __name__ == '__main__':
    unittest.main()
