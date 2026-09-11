"""Read the row -> value lists out of ACR's cooked UDataTable assets.

Every table this tool needs has the same shape: a row key FName, then an array of
entries in which a constant tag FName alternates with the value FName. The value
may carry an FName *number*, which is how the game spells compound values -
`60` with number 71 is the ramp pair `60/70`.
"""
import struct
from collections import Counter


def _fnames(pkg, blob):
    """Every (offset, name index, number) that parses as an FName, in file order."""
    out, o = [], 0
    while o < len(blob) - 8:
        idx, num = struct.unpack_from('<II', blob, o)
        if idx < len(pkg.names) and num < 4096:
            out.append((o, idx, num)); o += 8
        else:
            o += 1
    return out


def rows(pkg):
    """{row name: [value, ...]} for the table's single export."""
    _, blob = pkg.export_bytes(0)
    seq = _fnames(pkg, blob)
    if not seq:
        return {}
    tag = Counter(i for _, i, _ in seq).most_common(1)[0][0]
    out, cur, expect_value = {}, None, False
    for _, idx, num in seq:
        if idx == tag and num == 0:
            expect_value = True
            continue
        if expect_value:
            if cur is not None:
                out[cur].append(pkg.name(idx, num))
            expect_value = False
        else:
            cur = pkg.name(idx, num)
            out.setdefault(cur, [])
    return out


def tagged_rows(pkg, tag):
    """{row name: value} for one tag in a table whose rows carry several.

    DT_Wheels rows list Tires / Rims / Calipers / Discs side by side, so the
    single-tag heuristic in rows() would keep whichever tag happened to be the
    most common. Naming the tag removes the guess.
    """
    _, blob = pkg.export_bytes(0)
    seq = _fnames(pkg, blob)
    tags = {'Tires', 'Rims', 'Calipers', 'Discs', 'Pads', 'Gears', 'Values', 'Name'}
    out, cur, pending = {}, None, None
    for _, idx, num in seq:
        name = pkg.name(idx, num)
        if pending is not None:
            if pending == tag and cur is not None:
                out[cur] = name
            pending = None
            continue
        if name in tags:
            pending = name
            continue
        cur = name
    return out
