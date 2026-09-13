"""The installed game's version, read from its own config.

ACR packs its config into the legacy .pak files next to the IoStore containers.
acr/Config/DefaultGame.ini carries the project version the studio stamps on each build
(`ProjectVersion=0.6.0.100866` in the 0.6 release). The .exe's version resource says only
`UE5-CL-0`, and Steam's build id is not a game version, so this ini is the one place
the number people call the game by is actually written down.

Only what reading one small file needs: pak format 11 (UE 5.x) with an unencrypted index,
the encoded entry table and the full directory index. Oodle blocks go through the same
ooz-wasm helper the gear-set extraction uses.
"""

import io
import os
import re
import struct

PAK_MAGIC = 0x5A6F12E1
FOOTER_SIZE = 221            # guid 16, encrypted flag 1, magic 4, version 4, offset 8,
                             # size 8, hash 20, five 32-byte compression method names
INI_PATH = 'acr/Config/DefaultGame.ini'

# FPakEntry as written in front of each file's data: offset, size, uncompressed size
# (8 each), compression method (4), hash (20), encrypted flag (1), block size (4); plus a
# block count and 16 bytes per block when the file is compressed.
ENTRY_HEADER = 53


def project_version(ini_text):
    m = re.search(r'^ProjectVersion=([^\r\n]+)', ini_text, re.MULTILINE)
    return m.group(1).strip() if m else None


def display_version(version):
    """'0.6.0.100866' -> '0.6'. The build number is dropped; a patch is kept when set."""
    parts = (version or '').split('.')
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f'not a version: {version!r}')
    shown = parts[:2]
    if len(parts) > 2 and int(parts[2]):
        shown.append(parts[2])
    return '.'.join(shown)


def pak_footer(tail):
    magic, version, offset, size = struct.unpack_from('<IIQQ', tail, 17)
    if magic != PAK_MAGIC:
        raise ValueError('not a pak footer')
    methods = [tail[61 + i * 32:93 + i * 32].split(b'\0')[0].decode('ascii')
               for i in range(5)]
    return {'version': version, 'index_offset': offset, 'index_size': size,
            'encrypted_index': bool(tail[16]), 'methods': methods}


def _u32(buf):
    return struct.unpack('<I', buf.read(4))[0]


def _i32(buf):
    return struct.unpack('<i', buf.read(4))[0]


def _u64(buf):
    return struct.unpack('<Q', buf.read(8))[0]


def _fstring(buf):
    n = _i32(buf)
    if n == 0:
        return ''
    if n > 0:
        return buf.read(n)[:-1].decode('latin-1')
    return buf.read(-n * 2)[:-2].decode('utf-16-le')


def decode_entry(encoded, pos):
    """One bit-packed entry from the index's encoded table.

    Returns the method index (0 = stored), whether it is encrypted, the uncompressed size,
    and the blocks as (file offset, stored size, uncompressed size).
    """
    buf = io.BytesIO(encoded[pos:])
    bits = _u32(buf)
    block_size = _u32(buf) if (bits & 0x3f) == 0x3f else (bits & 0x3f) << 11
    count = (bits >> 6) & 0xffff
    encrypted = bool((bits >> 22) & 1)
    method = (bits >> 23) & 0x3f
    offset = _u32(buf) if (bits >> 31) & 1 else _u64(buf)
    usize = _u32(buf) if (bits >> 30) & 1 else _u64(buf)
    size = (_u32(buf) if (bits >> 29) & 1 else _u64(buf)) if method else usize

    start = offset + ENTRY_HEADER + ((4 + 16 * count) if method else 0)
    if not method:
        blocks = [(start, usize, usize)]
    elif count == 1 and not encrypted:
        blocks = [(start, size, usize)]
    else:
        blocks, left = [], usize
        for _ in range(count):
            stored = _u32(buf)
            blocks.append((start, stored, min(block_size, left)))
            start += stored
            left -= block_size
    return {'method': method, 'encrypted': encrypted, 'usize': usize, 'blocks': blocks}


def directory_index(buf, mount):
    """Full path -> position in the encoded entry table."""
    files = {}
    for _ in range(_i32(buf)):
        directory = _fstring(buf)
        for _ in range(_i32(buf)):
            name = _fstring(buf)
            files[mount + directory.lstrip('/') + name] = _i32(buf)
    return files


def find_entry(files, path):
    for full, pos in files.items():
        if full.replace('\\', '/').endswith('/' + path):
            return pos
    return None


def _read_file(pak, path, tmp):
    """The bytes of `path` inside one .pak, or None when this pak does not hold it."""
    with open(pak, 'rb') as fh:
        fh.seek(0, os.SEEK_END)
        if fh.tell() < FOOTER_SIZE:
            return None
        fh.seek(-FOOTER_SIZE, os.SEEK_END)
        try:
            footer = pak_footer(fh.read(FOOTER_SIZE))
        except ValueError:
            return None
        if footer['version'] < 10 or footer['encrypted_index']:
            return None
        fh.seek(footer['index_offset'])
        index = io.BytesIO(fh.read(footer['index_size']))
        mount = _fstring(index)
        _i32(index)                                  # entry count
        _u64(index)                                  # path hash seed
        if _u32(index):                              # path hash index: not needed
            index.read(8 + 8 + 20)
        if not _u32(index):
            return None
        full_offset, full_size = _u64(index), _u64(index)
        index.read(20)
        encoded = index.read(_i32(index))
        fh.seek(full_offset)
        files = directory_index(io.BytesIO(fh.read(full_size)), mount)
        pos = find_entry(files, path)
        if pos is None or pos < 0:
            return None
        entry = decode_entry(encoded, pos)
        if entry['encrypted']:
            return None
        if entry['method'] == 0:
            offset, stored, _u = entry['blocks'][0]
            fh.seek(offset)
            return fh.read(stored)
        method = footer['methods'][entry['method'] - 1]
    if method != 'Oodle':
        raise SystemExit(f'{os.path.basename(pak)}: {path} uses {method}, not Oodle')

    import make_gearing_chart as M                 # the ooz-wasm helper lives there
    out = os.path.join(tmp, 'DefaultGame.ini')
    # the helper takes IoStore-style blocks: [offset, stored, uncompressed, method],
    # where any non-zero method means Oodle
    M.unpack([{'cas': pak, 'blocks': [[o, s, u, 1] for o, s, u in entry['blocks']],
               'start': 0, 'len': entry['usize'], 'out': out}])
    with open(out, 'rb') as fh:
        return fh.read()


_PATCH = re.compile(r'_(?:(\d+)_)?P\.pak$', re.IGNORECASE)


def pak_priority(name):
    """How Unreal ranks a .pak when two hold the same file; higher wins.

    Patch paks (`*_P.pak`, `*_<n>_P.pak`) mount over base paks, and a higher patch number
    over a lower one. All base paks rank the same.
    """
    m = _PATCH.search(name)
    if not m:
        return (0, 0)
    return (1, int(m.group(1) or 0))


def select_source(found):
    """The `(pak, value)` that wins out of every pak holding the file.

    Only the highest-priority paks count. If more than one of those holds the file and
    they disagree, there is no telling which the game loads, so this refuses to guess.
    """
    if not found:
        return None
    top = max(pak_priority(pak) for pak, _v in found)
    winners = [(pak, v) for pak, v in found if pak_priority(pak) == top]
    if len({v for _p, v in winners}) > 1:
        raise SystemExit('paks of equal priority disagree on ProjectVersion: '
                         + ', '.join(f'{pak} = {v!r}' for pak, v in sorted(winners)))
    return sorted(winners)[0]


def read_game_version(paks, tmp):
    """The display version ('0.6') of the game whose paks are in `paks`.

    Paks are read from the highest priority down, and the first priority level holding
    the ini decides: a patch pak's copy replaces the base pak's in game.
    """
    names = [e for e in os.listdir(paks) if e.lower().endswith('.pak')]
    for level in sorted({pak_priority(n) for n in names}, reverse=True):
        found = []
        for entry in sorted(n for n in names if pak_priority(n) == level):
            data = _read_file(os.path.join(paks, entry), INI_PATH, tmp)
            if data is not None:
                found.append((entry, project_version(
                    data.decode('utf-8-sig', errors='replace'))))
        if not found:
            continue
        pak, version = select_source(found)
        if not version:
            raise SystemExit(f'{pak}: no ProjectVersion in {INI_PATH}')
        try:
            return display_version(version)
        except ValueError:
            raise SystemExit(f'{pak}: ProjectVersion {version!r} in {INI_PATH} is not '
                             'dotted integers') from None
    raise SystemExit(f'no {INI_PATH} in any .pak under {paks}')
