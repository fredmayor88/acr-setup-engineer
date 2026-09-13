import io
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from game_version import (decode_entry, directory_index, display_version,  # noqa: E402
                          find_entry, pak_footer, project_version, read_game_version)


def fstring(s):
    b = s.encode('ascii') + b'\0'
    return struct.pack('<i', len(b)) + b


class ProjectVersion(unittest.TestCase):
    INI = ('\ufeff[/Script/EngineSettings.GeneralProjectSettings]\n'
           'ProjectID=ABC\nProjectName=acr\nProjectVersion=0.6.0.100866\n'
           '[/Script/Other]\nGameVersion=3\n')

    def test_reads_project_version_from_default_game_ini(self):
        self.assertEqual(project_version(self.INI), '0.6.0.100866')

    def test_crlf_line_endings(self):
        self.assertEqual(project_version(self.INI.replace('\n', '\r\n')), '0.6.0.100866')

    def test_no_project_version_is_none(self):
        self.assertIsNone(project_version('[/Script/Other]\nGameVersion=3\n'))

    def test_display_is_major_minor(self):
        self.assertEqual(display_version('0.6.0.100866'), '0.6')

    def test_display_keeps_a_nonzero_patch(self):
        self.assertEqual(display_version('0.6.2.101200'), '0.6.2')
        self.assertEqual(display_version('1.0'), '1.0')

    def test_display_rejects_what_is_not_a_version(self):
        for bad in ('', 'dev', '0', '0.x.1', None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                display_version(bad)


class PakFormat(unittest.TestCase):
    def test_footer(self):
        tail = (b'\0' * 16 + b'\0' + struct.pack('<IIQQ', 0x5A6F12E1, 11, 1234, 56)
                + b'\x11' * 20 + b'Oodle'.ljust(32, b'\0') + b'\0' * 128)
        self.assertEqual(len(tail), 221)
        self.assertEqual(pak_footer(tail),
                         {'version': 11, 'index_offset': 1234, 'index_size': 56,
                          'encrypted_index': False, 'methods': ['Oodle', '', '', '', '']})

    def test_footer_rejects_a_bad_magic(self):
        with self.assertRaises(ValueError):
            pak_footer(b'\0' * 221)

    def test_decode_a_single_block_compressed_entry(self):
        # 32-bit offset, uncompressed size and size; method 1; one block; block size 64K
        bits = (1 << 31) | (1 << 30) | (1 << 29) | (1 << 23) | (1 << 6) | (65536 >> 11)
        raw = struct.pack('<IIII', bits, 2932021, 15134, 4133)
        e = decode_entry(raw, 0)
        header = 53 + 4 + 16
        self.assertEqual(e['method'], 1)
        self.assertFalse(e['encrypted'])
        self.assertEqual(e['usize'], 15134)
        self.assertEqual(e['blocks'], [(2932021 + header, 4133, 15134)])

    def test_decode_an_uncompressed_entry(self):
        bits = (1 << 31) | (1 << 30)
        raw = struct.pack('<III', bits, 500, 40)
        e = decode_entry(raw, 0)
        self.assertEqual(e['method'], 0)
        self.assertEqual(e['blocks'], [(500 + 53, 40, 40)])

    def test_decode_a_multi_block_entry(self):
        bits = (1 << 31) | (1 << 30) | (1 << 29) | (1 << 23) | (2 << 6) | (65536 >> 11)
        raw = struct.pack('<IIIIII', bits, 1000, 70000, 30000, 20000, 10000)
        e = decode_entry(raw, 0)
        start = 1000 + 53 + 4 + 32
        self.assertEqual(e['blocks'], [(start, 20000, 65536), (start + 20000, 10000, 4464)])

    def test_directory_index_and_lookup(self):
        idx = (struct.pack('<i', 2)
               + fstring('/') + struct.pack('<i', 0)
               + fstring('acr/Config/') + struct.pack('<i', 1)
               + fstring('DefaultGame.ini') + struct.pack('<i', 42))
        files = directory_index(io.BytesIO(idx), '../../../')
        self.assertEqual(files, {'../../../acr/Config/DefaultGame.ini': 42})
        self.assertEqual(find_entry(files, 'acr/Config/DefaultGame.ini'), 42)
        self.assertIsNone(find_entry(files, 'acr/Config/DefaultEngine.ini'))


@unittest.skipUnless(os.path.isdir(
    'C:/Program Files (x86)/Steam/steamapps/common/Assetto Corsa Rally/acr/Content/Paks'),
    'needs the game installed')
class InstalledGame(unittest.TestCase):
    def test_reads_a_version_from_the_install(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            v = read_game_version(
                'C:/Program Files (x86)/Steam/steamapps/common/Assetto Corsa Rally/acr/Content/Paks',
                tmp)
        self.assertRegex(v, r'^\d+\.\d+(\.\d+)?$')


if __name__ == '__main__':
    unittest.main()
