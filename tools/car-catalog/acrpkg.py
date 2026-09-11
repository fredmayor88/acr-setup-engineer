"""Read a cooked ACR .uasset: name map, export map, and the car-setting overrides."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zen import ZenPackage
from unversioned import read_header

EXPORT_ENTRY = 72
TRAILER = 4


class Package(ZenPackage):
    def __init__(self, d):
        super().__init__(d)
        self.exports = []
        n = (self.exportBundleEntriesOff - self.exportMapOff) // EXPORT_ENTRY
        for i in range(n):
            o = self.exportMapOff + i * EXPORT_ENTRY
            so, ss = struct.unpack_from('<QQ', d, o)
            nameIdx = struct.unpack_from('<I', d, o + 16)[0]
            self.exports.append((so, ss, self.name(nameIdx)))

    def main_export(self):
        for i, (_, _, c) in enumerate(self.exports):
            if c.startswith('DA_'):
                return i
        raise LookupError('no DA_ export')

    def export_bytes(self, i):
        so, ss, _ = self.exports[i]
        a = self.headerSize + so
        return a, self.d[a:a + ss]

    def values(self, i):
        """Decoded 4-byte property slots of export i, keyed by schema index."""
        a, blob = self.export_bytes(i)
        pres, o = read_header(self.d, a)
        out = {}
        for idx, isZero in pres:
            if isZero:
                out[idx] = b'\0\0\0\0'
            else:
                out[idx] = self.d[o:o + 4]; o += 4
        return out

    def floats(self, i):
        return {k: struct.unpack('<f', b)[0] for k, b in self.values(i).items()}

    def ints(self, i):
        return {k: struct.unpack('<i', b)[0] for k, b in self.values(i).items()}

    def setting_pairs(self, main_idx):
        """Every (setting id, export index) in the presets DataAsset's TMaps.

        The asset holds two maps keyed the same way - constraints and range
        overrides - so pairs come back as a list and are classified by the
        referenced export's class rather than collapsed into one dict.
        """
        a, blob = self.export_bytes(main_idx)
        out, o, end = [], a, a + len(blob)
        while o < end - 12:
            idx, num, ref = struct.unpack_from('<IIi', self.d, o)
            if num == 0 and 0 < idx < len(self.names) and '.' in self.names[idx] \
               and 0 < ref <= len(self.exports):
                out.append((self.names[idx], ref - 1))   # FPackageIndex -> export
                o += 12
                continue
            o += 1
        return out

    def overrides(self, main_idx):
        return {n: i for n, i in self.setting_pairs(main_idx)
                if 'Override' in self.exports[i][2] or self.exports[i][2].startswith('RangeOverride')}

    def constraints(self, main_idx):
        return {n: i for n, i in self.setting_pairs(main_idx)
                if self.exports[i][2].startswith('CarSettingConstraint')}

    def surface_variants(self, main_idx):
        """{surface name: variant export index}.

        The presets asset maps each surface to a CarSetupVariantsSurface object,
        which may narrow a parameter's range for that surface - gravel springs are
        usually much softer than the tarmac ones the base asset declares.
        """
        a, blob = self.export_bytes(main_idx)
        try:
            tag = self.names.index('SurfaceTypes')
        except ValueError:
            return {}
        out, o = {}, 0
        while o < len(blob) - 20:
            idx, num = struct.unpack_from('<II', blob, o)
            if idx == tag and num == 0:
                surface = self.name(*struct.unpack_from('<II', blob, o + 8))
                ref = struct.unpack_from('<i', blob, o + 16)[0]
                if 0 < ref <= len(self.exports):
                    out[surface] = ref - 1
                o += 20
                continue
            o += 1
        return out

    def variant_ranges(self, variant_idx):
        """{setting id -> export index} for range overrides inside one variant.

        A variant also carries plain CarSettingOverrideFloat entries - those are the
        preset's chosen *values*, not bounds, so they are skipped here.
        """
        a, blob = self.export_bytes(variant_idx)
        out, o = {}, 0
        while o < len(blob) - 12:
            idx, num, ref = struct.unpack_from('<IIi', blob, o)
            if num == 0 and 0 < idx < len(self.names) and '.' in self.names[idx] \
               and 0 < ref <= len(self.exports):
                cls = self.exports[ref - 1][2]
                if 'Range' in cls:
                    out[self.names[idx]] = ref - 1
                o += 12
                continue
            o += 1
        return out
