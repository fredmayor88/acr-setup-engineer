"""Guard the bundled VERSION file: it must exist and be non-empty so it can't silently
go missing from the packaged skill tree (the release process stamps it to the tag).

Run: python -m unittest discover tests
"""
import os
import unittest

VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills',
                             'car-setups', 'VERSION')


class TestSkillVersion(unittest.TestCase):
    def test_version_file_exists_and_nonempty(self):
        self.assertTrue(os.path.isfile(VERSION_FILE), f'missing {VERSION_FILE}')
        with open(VERSION_FILE, encoding='utf-8') as f:
            content = f.read().strip()
        self.assertTrue(content, 'VERSION file is empty')


if __name__ == '__main__':
    unittest.main()
