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


def struct_rows(pkg, tags):
    """{row name: {tag: value}} for a table whose rows carry several named
    FName fields plus unrelated untagged names (asset paths, localization keys,
    livery lists, ...) that `tagged_rows`'s cur-tracking would misattribute.

    Used for DT_Cars: each row lists Manufacturers/EngineTypes/EnginePositions/
    Inductions/WheelDrives/GearsTypes/CarsClasses side by side, interleaved with
    plenty of other names tagged_rows would trip over. Row boundaries are found
    by anchoring on `tags[0]`, which the game always writes immediately after
    the row's own key with nothing between them — verified against every row in
    DT_Cars (see tools/car-catalog/README.md - Car identity facts). A row with
    no other known tags before the next anchor still comes back with whatever
    subset it has; missing tags are simply absent from its dict.
    """
    _, blob = pkg.export_bytes(0)
    seq = _fnames(pkg, blob)
    names = [pkg.name(idx, num) for (_, idx, num) in seq]
    tagset, anchor = set(tags), tags[0]
    starts = [i - 1 for i, n in enumerate(names) if n == anchor and i > 0]
    bounds = starts + [len(names)]
    out = {}
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        key = names[s]
        window = names[s:e]
        facts, j = {}, 0
        while j < len(window) - 1:
            if window[j] in tagset and window[j] not in facts:
                facts[window[j]] = window[j + 1]
                j += 2
            else:
                j += 1
        out[key] = facts
    return out
