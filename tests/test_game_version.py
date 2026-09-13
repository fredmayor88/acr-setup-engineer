import io
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'gearing-charts'))

from game_version import (INI_PATH, _read_file, decode_entry,  # noqa: E402
                          directory_index, display_version, find_entry, pak_footer,
                          pak_priority, project_version, read_game_version, select_source)


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


def stored_pak(files, mount='../../../'):
    """A minimal pak v11: stored (method 0), unencrypted, full directory index only.

    `files` maps 'dir/name' to bytes. Each file's data is preceded by a 53-byte FPakEntry
    header, which is where decode_entry expects it; the parser only skips over it.
    """
    body, encoded, dirs = b'', b'', {}
    for path, data in files.items():
        directory, name = path.rsplit('/', 1)
        offset = len(body)
        body += b'\0' * 53 + data
        dirs.setdefault(directory + '/', []).append((name, len(encoded)))
        encoded += struct.pack('<III', (1 << 31) | (1 << 30), offset, len(data))

    full = struct.pack('<i', len(dirs))
    for directory, names in dirs.items():
        full += fstring(directory) + struct.pack('<i', len(names))
        for name, pos in names:
            full += fstring(name) + struct.pack('<i', pos)

    index_offset = len(body)
    # mount, entry count, path hash seed, no path hash index, a full directory index at
    # offset/size, its hash, then the encoded entries
    head = (fstring(mount) + struct.pack('<iQI', len(files), 0, 0) + struct.pack('<I', 1))
    tail = b'\0' * 20 + struct.pack('<i', len(encoded)) + encoded + struct.pack('<i', 0)
    full_offset = index_offset + len(head) + 16 + len(tail)
    index = head + struct.pack('<QQ', full_offset, len(full)) + tail
    footer = (b'\0' * 16 + b'\0' + struct.pack('<IIQQ', 0x5A6F12E1, 11, index_offset,
                                                len(index))
              + b'\0' * 20 + b'\0' * 160)
    return body + index + full + footer


def ini(version):
    return (f'[/Script/EngineSettings.GeneralProjectSettings]\r\n'
            f'ProjectVersion={version}\r\n').encode('utf-8')


class SyntheticPak(unittest.TestCase):
    """The index walk, against a pak built here rather than the installed game."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name

    def write(self, name, files):
        with open(os.path.join(self.dir, name), 'wb') as fh:
            fh.write(stored_pak(files))

    def test_reads_default_game_ini_out_of_a_stored_pak(self):
        self.write('pakchunk0-Windows.pak', {
            'acr/Config/DefaultEngine.ini': b'[Core]\n',
            'acr/Config/DefaultGame.ini': ini('0.6.0.100866'),
            'acr/Content/Other.txt': b'hello',
        })
        data = _read_file(os.path.join(self.dir, 'pakchunk0-Windows.pak'), INI_PATH, self.dir)
        self.assertEqual(data, ini('0.6.0.100866'))

    def test_a_pak_without_the_file_is_none(self):
        self.write('pakchunk1-Windows.pak', {'acr/Config/DefaultEngine.ini': b'[Core]\n'})
        self.assertIsNone(_read_file(os.path.join(self.dir, 'pakchunk1-Windows.pak'),
                                     INI_PATH, self.dir))

    def test_a_file_that_is_not_a_pak_is_none(self):
        path = os.path.join(self.dir, 'junk.pak')
        with open(path, 'wb') as fh:
            fh.write(b'\0' * 400)
        self.assertIsNone(_read_file(path, INI_PATH, self.dir))

    def test_the_game_version_from_a_directory_of_paks(self):
        self.write('pakchunk0-Windows.pak', {'acr/Config/DefaultGame.ini': ini('0.6.0.100866')})
        self.write('pakchunk1-Windows.pak', {'acr/Content/Other.txt': b'x'})
        self.assertEqual(read_game_version(self.dir, self.dir), '0.6')

    def test_a_patch_pak_overrides_the_base_pak(self):
        # the patch sorts after the base, so first-sorted-wins read the stale version
        self.write('pakchunk0-Windows.pak', {'acr/Config/DefaultGame.ini': ini('0.6.0.100866')})
        self.write('pakchunk0-Windows_0_P.pak', {'acr/Config/DefaultGame.ini': ini('0.6.2.101200')})
        self.assertEqual(read_game_version(self.dir, self.dir), '0.6.2')

    def test_a_version_that_is_not_dotted_integers_names_the_value_and_the_pak(self):
        self.write('pakchunk0-Windows.pak', {'acr/Config/DefaultGame.ini': ini('0.6.0-hotfix')})
        with self.assertRaises(SystemExit) as ctx:
            read_game_version(self.dir, self.dir)
        self.assertIn("'0.6.0-hotfix'", str(ctx.exception))
        self.assertIn('pakchunk0-Windows.pak', str(ctx.exception))

    def test_equal_priority_paks_that_disagree_fail(self):
        self.write('pakchunk0-Windows_1_P.pak', {'acr/Config/DefaultGame.ini': ini('0.6.1.1')})
        self.write('pakchunk3-Windows_1_P.pak', {'acr/Config/DefaultGame.ini': ini('0.6.2.1')})
        with self.assertRaises(SystemExit) as ctx:
            read_game_version(self.dir, self.dir)
        self.assertIn('pakchunk0-Windows_1_P.pak', str(ctx.exception))
        self.assertIn('pakchunk3-Windows_1_P.pak', str(ctx.exception))

    def test_no_pak_holding_the_ini_fails(self):
        self.write('pakchunk1-Windows.pak', {'acr/Content/Other.txt': b'x'})
        with self.assertRaises(SystemExit):
            read_game_version(self.dir, self.dir)


class PakPriority(unittest.TestCase):
    """Unreal mounts *_P.pak over base paks, and a higher patch number over a lower one."""

    def test_base_paks_share_the_lowest_priority(self):
        self.assertEqual(pak_priority('pakchunk0-Windows.pak'),
                         pak_priority('pakchunk12optional-Windows.pak'))

    def test_a_patch_pak_outranks_a_base_pak(self):
        self.assertGreater(pak_priority('pakchunk0-Windows_P.pak'),
                           pak_priority('pakchunk0-Windows.pak'))
        self.assertGreater(pak_priority('pakchunk0-Windows_0_P.pak'),
                           pak_priority('pakchunk9-Windows.pak'))

    def test_a_higher_patch_number_outranks_a_lower_one(self):
        self.assertGreater(pak_priority('pakchunk0-Windows_2_P.pak'),
                           pak_priority('pakchunk0-Windows_1_P.pak'))
        # numerically, not by spelling
        self.assertGreater(pak_priority('pakchunk0-Windows_10_P.pak'),
                           pak_priority('pakchunk0-Windows_9_P.pak'))

    def test_the_suffix_is_case_insensitive(self):
        self.assertEqual(pak_priority('pakchunk0-Windows_1_p.PAK'),
                         pak_priority('pakchunk0-Windows_1_P.pak'))

    def test_select_picks_the_highest_priority_source(self):
        found = [('pakchunk0-Windows.pak', '0.6.0.1'),
                 ('pakchunk0-Windows_1_P.pak', '0.6.2.3'),
                 ('pakchunk0-Windows_0_P.pak', '0.6.1.2')]
        self.assertEqual(select_source(found), ('pakchunk0-Windows_1_P.pak', '0.6.2.3'))

    def test_select_accepts_equal_priority_sources_that_agree(self):
        found = [('a-Windows_1_P.pak', '0.6.2.3'), ('b-Windows_1_P.pak', '0.6.2.3')]
        self.assertEqual(select_source(found)[1], '0.6.2.3')

    def test_select_fails_on_equal_priority_sources_that_disagree(self):
        found = [('pakchunk0-Windows.pak', '0.6.0.1'), ('pakchunk1-Windows.pak', '0.6.1.1')]
        with self.assertRaises(SystemExit):
            select_source(found)

    def test_a_lower_priority_disagreement_does_not_matter(self):
        found = [('pakchunk0-Windows.pak', '0.6.0.1'), ('pakchunk1-Windows.pak', '0.5.0.1'),
                 ('pakchunk0-Windows_0_P.pak', '0.6.2.1')]
        self.assertEqual(select_source(found), ('pakchunk0-Windows_0_P.pak', '0.6.2.1'))


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
