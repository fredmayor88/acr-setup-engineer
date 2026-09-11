"""UE5 unversioned property header decoder.

Each cooked object begins with FUnversionedHeader: uint16 fragments naming which
properties of the class schema are present, then an optional bitmask marking the
ones whose value is implicitly zero.

    SkipNum      = v & 0x007f
    bHasAnyZeroes= v & 0x0080
    bIsLast      = v & 0x0100
    ValueNum     = v >> 9
"""
import struct


def read_header(d, o):
    """-> ([(schema_index, is_zero)], offset of first stored value)."""
    frags = []
    while True:
        v = struct.unpack_from('<H', d, o)[0]; o += 2
        frags.append((v & 0x7F, bool(v & 0x80), v >> 9))
        if v & 0x100:
            break
    zeroBits = sum(n for _, hz, n in frags if hz)
    mask = 0
    if zeroBits:
        nbytes = 1 if zeroBits <= 8 else 2 if zeroBits <= 16 else ((zeroBits + 31) // 32) * 4
        mask = int.from_bytes(d[o:o + nbytes], 'little'); o += nbytes
    out, zeroIdx, schema = [], 0, 0
    for skip, hz, num in frags:
        schema += skip
        for _ in range(num):
            isZero = False
            if hz:
                isZero = bool((mask >> zeroIdx) & 1); zeroIdx += 1
            out.append((schema, isZero))
            schema += 1
    return out, o
