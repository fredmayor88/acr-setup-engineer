"""Minimal read-only reader for Unreal Engine 5 IoStore containers (.utoc/.ucas).

Parses the .utoc directory index far enough to map an asset path to a chunk, and to
work out which compressed blocks in the .ucas hold it. It deliberately does **not**
decompress: ACR's blocks are Oodle-compressed and the decompression is done by
`ooz_unpack.mjs` (see this folder's README for why).
"""

import struct


class Reader:
    def __init__(self, b, o=0):
        self.b = b
        self.o = o

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.o)[0]
        self.o += 4
        return v

    def fstring(self):
        """UE FString: positive length = UTF-8, negative = UTF-16LE. Both NUL-terminated."""
        n = struct.unpack_from("<i", self.b, self.o)[0]
        self.o += 4
        if n == 0:
            return ""
        if n > 0:
            s = self.b[self.o:self.o + n - 1].decode("utf-8", "replace")
            self.o += n
            return s
        n = -n
        s = self.b[self.o:self.o + (n - 1) * 2].decode("utf-16-le", "replace")
        self.o += n * 2
        return s


class Toc:
    """A parsed .utoc. `files()` maps asset path -> chunk index; `offlen`/`blocks`
    give the byte ranges to pull out of the sibling .ucas."""

    def __init__(self, path):
        self.path = path
        d = open(path, "rb").read()
        self.d = d
        (self.entryCount, self.blkCount, self.blkEntrySize, self.cmCount,
         self.cmLen, self.compBlockSize, self.dirIdxSize, self.partCount) = struct.unpack_from("<8I", d, 0x18)
        seeds = struct.unpack_from("<I", d, 0x54)[0]

        o = 144
        self.chunkIds = [d[o + 12 * i:o + 12 * i + 12] for i in range(self.entryCount)]
        o += 12 * self.entryCount

        # offset+length pairs: 5 bytes each, big-endian
        self.offlen = []
        for _ in range(self.entryCount):
            raw = d[o:o + 10]
            o += 10
            self.offlen.append((int.from_bytes(raw[0:5], "big"), int.from_bytes(raw[5:10], "big")))
        o += 4 * seeds

        # compression blocks: offset(5) + compressed(3) + uncompressed(3) + method(1)
        self.blocks = []
        for _ in range(self.blkCount):
            raw = d[o:o + 12]
            o += 12
            self.blocks.append((int.from_bytes(raw[0:5], "little"),
                                int.from_bytes(raw[5:8], "little"),
                                int.from_bytes(raw[8:11], "little"),
                                raw[11]))

        self.cms = ["None"] + [d[o + i * self.cmLen:o + (i + 1) * self.cmLen].rstrip(b"\0").decode()
                               for i in range(self.cmCount)]
        o += self.cmLen * self.cmCount
        self.dirIdx = d[o:o + self.dirIdxSize]

    def files(self):
        """Walk the directory index. Returns {asset path: chunk index}."""
        r = Reader(self.dirIdx)
        mount = r.fstring()
        nd = r.u32()
        dirs = [struct.unpack_from("<4I", self.dirIdx, r.o + 16 * i) for i in range(nd)]
        r.o += 16 * nd
        nf = r.u32()
        files = [struct.unpack_from("<3I", self.dirIdx, r.o + 12 * i) for i in range(nf)]
        r.o += 12 * nf
        ns = r.u32()
        strs = [r.fstring() for _ in range(ns)]

        NONE = 0xFFFFFFFF
        out = {}

        def walk(di, prefix):
            while di != NONE:
                name, firstChild, nextSib, firstFile = dirs[di]
                p = prefix if name == NONE else prefix + strs[name] + "/"
                fi = firstFile
                while fi != NONE:
                    fname, nextFile, userData = files[fi]
                    out[p + strs[fname]] = userData
                    fi = nextFile
                walk(firstChild, p)
                di = nextSib

        walk(0, mount)
        return out

    def plan(self, idx, cas_path):
        """Everything ooz_unpack.mjs needs to reconstruct chunk `idx` from the .ucas."""
        off, ln = self.offlen[idx]
        first = off // self.compBlockSize
        blocks, got, i = [], 0, first
        while got < ln:
            b = self.blocks[i]
            blocks.append(list(b))
            got += b[2]
            i += 1
        return dict(cas=cas_path, blocks=blocks, start=off - first * self.compBlockSize, len=ln)
