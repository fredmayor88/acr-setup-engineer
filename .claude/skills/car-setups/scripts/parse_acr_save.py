#!/usr/bin/env python3
"""Parse an Assetto Corsa Rally CarSetupsDataSaveSlot.sav (UE5 GVAS) into JSON.

The save is a GVAS container whose body is a custom serialization:
  per setup: name, version, car, track, surface (FStrings, separated by small binary
  fields), then a count and that many (key, value) FString pairs. Values are stored as
  strings, e.g. "(Gears:65//19)", "(LSDRampAngles:60_70)", "75.000000".

This parser is **schema-agnostic**: it does not hard-code a parameter vocabulary. It reads
the FString stream (length-prefixed, null-terminated) and groups it by the unambiguous
parameter key/value runs, so it works for any car — including ones it has never seen.
Unknown keys pass through; the per-car Notion catalog is the source of truth for canonical
names (the import workflow maps these raw keys onto it). Confidence is judged structurally
(did we find real setups), not by recognising names. stdlib only.

**Version-aware dispatch.** Save formats can vary between ACR builds. The parser detects the
save-format fingerprint (GVAS engine/custom versions) and the per-setup game version(s), then
picks a handler from a small registry. Today there are two handlers, both schema-agnostic:
`parse_structural` (strict FString reads — v0.4 and any same-format build) and
`parse_nul_tolerant` (for saves whose NUL terminators are gone — every `0x00` is `0x20` —
seen on v0.2/v0.3 samples). When a future build genuinely re-serializes the body, add a new
handler keyed on its fingerprint; until then an unrecognised format yields low confidence and
the caller falls back to AI extraction.

Usage:
  python parse_acr_save.py CarSetupsDataSaveSlot.sav            # JSON to stdout
  python parse_acr_save.py CarSetupsDataSaveSlot.sav --pretty   # human summary
Exit code is 0 when confident, 3 when low-confidence (caller may fall back to AI parsing).
"""
import sys, struct, json, re

KEY_RE = re.compile(r'^[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+$')
VERSION_RE = re.compile(r'^\d+(?:\.\d+){2,3}$')
SURFACES = {'tarmac', 'asphalt', 'gravel', 'snow', 'dirt', 'wet', 'ice', 'mud'}
IGNORE_META = {'None', 'CarSetupsSaveGameData', ''}
MIN_PARAMS = 6  # a real setup has many params; fewer ⇒ probably misparsed
# major.minor game-version families this parser has been validated against (informational).
TESTED_VERSIONS = {'0.2', '0.3', '0.4'}

# Optional nice labels (hints only — never used to judge success or drop data).
LEAF_LABEL = {
    'DifferentialRatio': 'Differential ratio', 'LSDRamps': 'LSD Power/Coast Ramp',
    'LSDPreload': 'LSD Preload', 'LSDFrictionPlates': 'Plates number',
    'GearsSet': 'Gear set', 'GearPrimary': 'Primary Gear',
    'Disc': 'Disc', 'Caliper': 'Caliper', 'PadCompound': 'Pad',
    'HandbrakeForce': 'Handbrake force', 'FrontBias': 'Front Bias',
    'MasterCylinderFront': 'Master cylinder front', 'MasterCylinderRear': 'Master cylinder rear',
    'ProportioningPreload': 'Proportioning preload', 'ProportioningRatio': 'Proportioning ratio',
    'CentreRatioToRear': 'Centre diff ratio (to rear)',
    'TyrePressure': 'Pressure', 'Camber': 'Camber', 'Toe': 'Toe',
    'TyreType': 'Tyre type', 'FFBPlayerMultiplier': 'FFB multiplier',
    'ABS': 'ABS', 'TCS': 'TCS', 'AdditionalLights': 'Additional lights',
    'AdjusterRing': 'Adjuster ring', 'SpringStiffness': 'Spring Stiffness',
    'ARBStiffness': 'Anti-roll Bar',
    'SlowBump': 'Slow Bump', 'SlowRebound': 'Slow Rebound',
    'FastBump': 'Fast Bump', 'FastRebound': 'Fast Rebound',
    'BumpTransition': 'Bump transition', 'ReboundTransition': 'Rebound transition',
}


def read_fstring(d, off):
    """Return (string, new_off) if a valid FString starts at off, else None."""
    if off + 4 > len(d):
        return None
    n = struct.unpack_from('<i', d, off)[0]
    if n > 0:
        if n <= 4000 and off + 4 + n <= len(d):
            s = d[off + 4:off + 4 + n]
            if s[-1:] == b'\x00' and all(0x20 <= b < 0x7f for b in s[:-1]):
                return s[:-1].decode('utf-8', 'replace'), off + 4 + n
    elif n < 0:
        m = -n
        if m <= 4000 and off + 4 + m * 2 <= len(d):
            s = d[off + 4:off + 4 + m * 2]
            if s[-2:] == b'\x00\x00':
                try:
                    return s[:-2].decode('utf-16-le'), off + 4 + m * 2
                except UnicodeDecodeError:
                    return None
    return None


def read_fstring_tolerant(d, off):
    """Like read_fstring but for saves whose NUL bytes were turned into spaces (0x20).

    The strict reader fails on such files: the FString length prefix `len 00 00 00` arrives as
    `len 20 20 20` and the terminating `0x00` is now `0x20`. We can't even trust the length
    byte itself — in observed v0.2/v0.3 samples a value whose real length is `0x0d` is mangled
    to `0x0a`, which would truncate it. But because every NUL became a space, the *content* of
    a key/value (dotted identifiers, numbers, `(Type:Value)` wrappers) never contains a `0x20`,
    so each string is delimited by spaces. We therefore require the would-be-NUL high length
    bytes (`off+1..off+3 == 20 20 20`) and read the content as the printable run up to the next
    `0x20`.

    Free-text metadata (a setup name like "drift snow") legitimately contains a space, so a
    printable-run-only read would split it. We don't trust the length byte to fix this — the same
    corruption that mangles values also hits length bytes (a `0x0d` → `0x0a`). Instead we resolve
    each `0x20` by look-ahead: it's an *internal* space if the next byte is printable and is **not**
    the start of the next FString's `[len][20][20][20]` prefix; otherwise it's the was-NUL
    terminator. Parameter keys/values never contain spaces, so the very next `0x20` ends them — they
    are unaffected; only multi-word free text is rejoined."""
    if off + 4 > len(d) or d[off + 1:off + 4] != b'\x20\x20\x20':
        return None
    i = off + 4
    end = i
    while end < len(d):
        b = d[end]
        if 0x21 <= b < 0x7f:                              # printable content byte
            end += 1
        elif b == 0x20 and end > i and end + 4 < len(d) and 0x21 <= d[end + 1] < 0x7f \
                and d[end + 2:end + 5] != b'\x20\x20\x20':  # internal space, not a leading/next one
            end += 1
        else:
            break                                         # was-NUL terminator (or padding/binary)
    if end == i or end >= len(d) or d[end] != 0x20:       # non-empty, space-terminated
        return None
    return d[i:end].decode('utf-8', 'replace'), end + 1


def read_header(d):
    """Skip the GVAS header and fingerprint the save format. Returns (body_start, save_format).

    `save_format` is the dispatch key for format changes: ACR bumps these when the body
    serialization changes. On any doubt body_start is 0 (scan the whole file — header text
    can't form param key/value pairs, so it is harmless)."""
    if d[:4] != b'GVAS':
        return 0, {'gvas': False}
    fmt = {'gvas': True}
    try:
        engine = struct.unpack_from('<3H', d, 16 + 6)  # 3×u16 engine version (major,minor,patch)
        fmt['engine_version'] = '.'.join(str(x) for x in engine)
        off = 16 + 6 + 4           # versions + engine ver (3×u16) + changelist
        r = read_fstring(d, off)   # engine branch
        off = r[1] if r else off + 4
        off += 4                   # custom version format
        n = struct.unpack_from('<i', d, off)[0]; off += 4
        fmt['custom_version_count'] = n if 0 <= n <= 1000 else None
        off += n * 20              # custom versions: guid(16) + int32
        r = read_fstring(d, off)   # save game class name
        return (r[1] if r else off), fmt
    except Exception:
        return 0, fmt


def scan_strings(d, start, reader=read_fstring):
    out, pos = [], start
    while pos < len(d):
        r = reader(d, pos)
        if r and r[0] != '':
            out.append(r[0]); pos = r[1]
        else:
            pos += 1
    return out


def clean_value(v):
    m = re.match(r'^\((?:[^:]*):(.*)\)$', v)   # strip (Key:Value) wrapper
    if m:
        return m.group(1)
    if re.match(r'^-?\d+\.\d+$', v):           # trim trailing zeros on decimals
        return v.rstrip('0').rstrip('.')
    return v


def collapse_mid(mid):
    """FrontLeft/FrontRight → Front, RearLeft/RearRight → Rear (generic, no fixed list)."""
    for suf in ('Left', 'Right'):
        if mid.endswith(suf) and len(mid) > len(suf):
            return mid[:-len(suf)]
    return 'Centre' if mid == 'Center' else mid


def decamel(s):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', s)


def detect_drivetrain(params):
    """Deterministic from the differential sections present:
    front+rear (or any centre diff) ⇒ AWD; front-only ⇒ FWD; rear-only ⇒ RWD."""
    keys = [k for k, _ in params]
    front = any(k.startswith('Differentials.Front') for k in keys)
    rear = any(k.startswith('Differentials.Rear') for k in keys)
    centre = any(k.startswith(('Differentials.Centre', 'Differentials.Center')) for k in keys)
    if centre or (front and rear):
        return 'AWD'
    if front:
        return 'FWD'
    if rear:
        return 'RWD'
    return None


def group_setups(strings):
    setups, cur = [], None
    i = 0
    while i < len(strings):
        s = strings[i]
        if KEY_RE.match(s) and i + 1 < len(strings):
            if cur is None:
                cur = {'meta': [], 'params': [], 'in_params': False}
            cur['params'].append((s, strings[i + 1]))
            cur['in_params'] = True
            i += 2
        else:
            if cur is not None and cur['in_params']:
                setups.append(cur); cur = None
            if cur is None:
                cur = {'meta': [], 'params': [], 'in_params': False}
            if s not in IGNORE_META:
                cur['meta'].append(s)
            i += 1
    if cur and cur['params']:
        setups.append(cur)
    return setups


def classify_meta(meta):
    out = {'name': None, 'version': None, 'car': None, 'track': None, 'surface': None}
    vi = next((k for k, m in enumerate(meta) if VERSION_RE.match(m)), None)
    if vi is not None:
        out['version'] = meta[vi]
        if vi - 1 >= 0:
            out['name'] = meta[vi - 1]
        if vi + 1 < len(meta):
            out['car'] = meta[vi + 1]
        if vi + 2 < len(meta):
            out['track'] = meta[vi + 2]
    for m in meta:
        if m.lower() in SURFACES:
            out['surface'] = m
    if out['track'] and out['track'].lower() in SURFACES:
        out['track'] = None
    return out


def build(setup):
    meta = classify_meta(setup['meta'])
    groups, warnings = {}, []
    for raw, val in setup['params']:
        parts = raw.split('.')
        cmid = collapse_mid(parts[1]) if len(parts) >= 2 else ''
        ckey = '.'.join([parts[0], cmid] + parts[2:]) if len(parts) >= 2 else raw
        groups.setdefault(ckey, []).append(clean_value(val))
    params = []
    for ckey, vals in groups.items():
        if len(set(vals)) > 1:                  # symmetric corners disagree
            warnings.append(f'{ckey}: differing values {sorted(set(vals))}')
        parts = ckey.split('.')
        leaf = parts[-1]
        cmid = parts[1] if len(parts) >= 2 else ''
        side = cmid if cmid in ('Front', 'Rear', 'Centre') else ''
        label = f"{side} {LEAF_LABEL.get(leaf) or decamel(leaf)}".strip()
        params.append({'key': ckey, 'label': label, 'value': vals[0]})
    recognized = sum(1 for p in params if p['key'].split('.')[-1] in LEAF_LABEL)
    return {
        'name': meta['name'], 'car': meta['car'], 'track': meta['track'],
        'surface': meta['surface'], 'game_version': meta['version'],
        'drivetrain': detect_drivetrain(setup['params']),
        'params': params, 'warnings': warnings,
        'param_count': len(params), 'recognized_count': recognized,
    }


def _scan_to_setups(d, start, reader):
    """Run one reader over the body; header-independent retry from offset 0."""
    setups = [build(s) for s in group_setups(scan_strings(d, start, reader))]
    if not setups and start != 0:
        setups = [build(s) for s in group_setups(scan_strings(d, 0, reader))]
    return setups


def parse_structural(d, start):
    """Strict FString reads — v0.4 and any same-format build."""
    return _scan_to_setups(d, start, read_fstring)


def parse_nul_tolerant(d, start):
    """For saves whose NUL terminators are gone (every 0x00 is 0x20) — seen on v0.2/v0.3."""
    return _scan_to_setups(d, start, read_fstring_tolerant)


# Dispatch registry: first handler whose predicate(save_format, nul_count) matches is tried first;
# if it is low-confidence the others are tried as a fallback and the best result is kept. Add a new
# (predicate, handler) entry — keyed on the save_format fingerprint — when a future build genuinely
# re-serializes the body. The structural handler is the universal default.
HANDLERS = [
    (lambda fmt, nuls: nuls == 0, parse_nul_tolerant),   # NUL-stripped saves
    (lambda fmt, nuls: True,      parse_structural),     # default
]


def _confidence(setups):
    """(ok, num_good): a real setup has many params; few ⇒ probably misparsed."""
    good = [s for s in setups if s['param_count'] >= MIN_PARAMS]
    ok = bool(setups) and len(good) >= max(1, (len(setups) + 1) // 2)
    return ok, len(good)


def parse(path):
    """Return {ok, setup_count, recognized_fraction, game_versions, save_format, nul_count,
    handler_used, notes, setups}.

    `ok=False` (low confidence after every handler) signals the workflow to fall back to AI
    extraction."""
    with open(path, 'rb') as fh:
        d = fh.read()
    start, save_format = read_header(d)
    nul_count = d.count(0)

    # Try predicate-matching handlers first (registry order), then the rest as a fallback. Stop at
    # the first confident result; otherwise keep the best (most-confident, then most setups).
    matching = [fn for pred, fn in HANDLERS if pred(save_format, nul_count)]
    rest = [fn for pred, fn in HANDLERS if not pred(save_format, nul_count)]
    setups, handler_used, best = [], None, None
    for fn in matching + rest:
        cand = fn(d, start)
        ok, num_good = _confidence(cand)
        score = (ok, num_good, len(cand))
        if best is None or score > best[0]:
            best = (score, cand, fn.__name__)
        if ok:
            setups, handler_used = cand, fn.__name__
            break
    else:
        _, setups, handler_used = best

    notes = []
    ok, _ = _confidence(setups)
    if not setups:
        notes.append('no setups found — not a recognizable ACR save')
    elif not ok:
        notes.append(f'setups have very few parameters (<{MIN_PARAMS}) — likely misparsed')
    game_versions = sorted({s['game_version'] for s in setups if s['game_version']})
    # flag any version whose major.minor family (e.g. '0.5' from '0.5.1.123') isn't tested
    untested = [v for v in game_versions
                if '.'.join(v.split('.')[:2]) not in TESTED_VERSIONS]
    for v in untested:
        notes.append(f"game version {v} not in the tested set — parsed structurally, verify values")
    total = sum(s['param_count'] for s in setups)
    rec = sum(s['recognized_count'] for s in setups)
    frac = round((rec / total), 2) if total else 0.0  # informational only
    for s in setups:
        notes.extend(f"{s['name']}: {w}" for w in s['warnings'])
    return {'ok': ok, 'setup_count': len(setups), 'recognized_fraction': frac,
            'game_versions': game_versions, 'save_format': save_format, 'nul_count': nul_count,
            'handler_used': handler_used, 'notes': notes, 'setups': setups}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    pretty = '--pretty' in sys.argv
    if not args:
        print('usage: parse_acr_save.py <CarSetupsDataSaveSlot.sav> [--pretty]', file=sys.stderr)
        sys.exit(2)
    res = parse(args[0])
    if pretty:
        for s in res['setups']:
            print(f"\n=== {s['name']} | {s['car']} ({s['drivetrain']}) | {s['track']} | "
                  f"{s['surface']} | {s['game_version']}")
            for p in s['params']:
                print(f"  {p['label']}  [{p['key']}]: {p['value']}")
            for w in s['warnings']:
                print(f"  ! {w}")
        fmt = res['save_format']
        fmt_str = (f"GVAS engine {fmt.get('engine_version', '?')} · "
                   f"{fmt.get('custom_version_count', '?')} custom versions"
                   if fmt.get('gvas') else 'not GVAS')
        print(f"\nFORMAT: {fmt_str} | game versions {res['game_versions'] or '—'} | "
              f"handler {res['handler_used']}"
              f"{' (NUL-recovered)' if res['handler_used'] == 'parse_nul_tolerant' else ''}")
        print(f"CONFIDENCE: {'ok' if res['ok'] else 'LOW — consider AI fallback'} | "
              f"{res['setup_count']} setups")
        for n in res['notes']:
            print(f"  note: {n}")
    else:
        print(json.dumps(res, indent=2))
    sys.exit(0 if res['ok'] else 3)


if __name__ == '__main__':
    main()
