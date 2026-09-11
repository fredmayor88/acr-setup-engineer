"""Minimal UE5 IoStore (zen) package header reader: name map + export map."""
import struct

class ZenPackage:
    def __init__(self, d):
        self.d = d
        o = 0
        self.bHasVersioning = struct.unpack_from('<I', d, o)[0]; o += 4
        self.headerSize = struct.unpack_from('<I', d, o)[0]; o += 4
        self.nameMapped = struct.unpack_from('<II', d, o); o += 8
        self.packageFlags = struct.unpack_from('<I', d, o)[0]; o += 4
        self.cookedHeaderSize = struct.unpack_from('<I', d, o)[0]; o += 4
        (self.impPublicHashOff, self.importMapOff, self.exportMapOff,
         self.exportBundleEntriesOff, self.depBundleHeadersOff,
         self.depBundleEntriesOff, self.importedPkgNamesOff) = struct.unpack_from('<7i', d, o); o += 28
        # UE 5.5 added CellImportMapOffset / CellExportMapOffset here
        self.cellImportMapOff, self.cellExportMapOff = struct.unpack_from('<2i', d, o); o += 8
        self.nameMapOff = o
        self.names = self._read_name_batch(o)

    def _read_name_batch(self, o):
        d = self.d
        num, numBytes = struct.unpack_from('<II', d, o); o += 8
        if num == 0: return []
        o += 8                      # hash version
        o += 8 * num                # hashes
        hdrs = []
        for i in range(num):
            hi, lo = d[o], d[o+1]   # big-endian: bit15 = utf16, low 15 bits = len
            o += 2
            hdrs.append((bool(hi & 0x80), ((hi & 0x7f) << 8) | lo))
        names = []
        for isU16, ln in hdrs:
            if isU16:
                names.append(d[o:o+ln*2].decode('utf-16-le', 'replace')); o += ln*2
            else:
                names.append(d[o:o+ln].decode('utf-8', 'replace')); o += ln
        return names

    def name(self, idx, num=0):
        base = self.names[idx] if 0 <= idx < len(self.names) else f"<{idx}>"
        return base if num == 0 else f"{base}_{num-1}"
