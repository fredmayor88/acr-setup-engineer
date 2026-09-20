"""The DataTable FName scanner must read the value that ends the blob.

ACR's cooked tables end exactly on an FName: the last row's last value is the final
eight bytes of the export, with nothing after it. A scanner that stops short of them
silently drops one value from the table's last row — for the gears lists that is the
206 WRC, which loses a primary gear and one ratio from each differential list.

Run: python -m unittest discover tests
"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'car-catalog'))

from datatable import rows, tagged_rows      # noqa: E402


class FakePackage:
    """The two things the readers use: a name table and one export's bytes.

    `name()` mirrors zen.Package: FName number 0 is the bare name, and number N is
    the name suffixed with N-1.
    """

    def __init__(self, names, blob):
        self.names = names
        self._blob = blob

    def name(self, idx, num=0):
        base = self.names[idx] if 0 <= idx < len(self.names) else f'<{idx}>'
        return base if num == 0 else f'{base}_{num - 1}'

    def export_bytes(self, i):
        return None, self._blob


def table(names, entries):
    """A blob of FNames, `(name index, number)` pairs, ending flush with the last one."""
    return b''.join(struct.pack('<II', idx, num) for idx, num in entries)


class ScannerReachesTheEnd(unittest.TestCase):
    # 0 row key, 1 the tag every value follows, 2..4 values
    NAMES = ['Peugeot206WRC', 'Gears', '21//24', '22//24', '20//25']

    def test_rows_keeps_the_value_that_ends_the_blob(self):
        blob = table(self.NAMES, [(0, 0), (1, 0), (2, 0), (1, 0), (3, 0), (1, 0), (4, 0)])
        pkg = FakePackage(self.NAMES, blob)
        self.assertEqual(rows(pkg), {'Peugeot206WRC': ['21//24', '22//24', '20//25']})

    def test_the_last_value_is_the_final_eight_bytes(self):
        """Guards the boundary itself: the case only breaks when nothing follows."""
        blob = table(self.NAMES, [(0, 0), (1, 0), (2, 0), (1, 0), (4, 0)])
        self.assertEqual(len(blob) % 8, 0)
        pkg = FakePackage(self.NAMES, blob)
        self.assertEqual(rows(pkg)['Peugeot206WRC'][-1], '20//25')

    def test_trailing_padding_after_the_last_value_still_reads(self):
        """The common case, and the one that already worked: it must keep working."""
        blob = table(self.NAMES, [(0, 0), (1, 0), (2, 0), (1, 0), (4, 0)]) + b'\x00\x00'
        pkg = FakePackage(self.NAMES, blob)
        self.assertEqual(rows(pkg)['Peugeot206WRC'], ['21//24', '20//25'])

    def test_tagged_rows_keeps_the_value_that_ends_the_blob(self):
        names = ['VolkswagenPoloGTIR5', 'Tires', 'MichelinT00']
        blob = table(names, [(0, 0), (1, 0), (2, 0)])
        pkg = FakePackage(names, blob)
        self.assertEqual(tagged_rows(pkg, 'Tires'), {'VolkswagenPoloGTIR5': 'MichelinT00'})


if __name__ == '__main__':
    unittest.main()
