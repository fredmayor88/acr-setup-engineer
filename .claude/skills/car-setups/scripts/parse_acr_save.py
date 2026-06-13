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


def body_start(d):
    """Best-effort: skip the GVAS header. On any doubt return 0 and scan the whole file
    (header text can't form param key/value pairs, so it is harmless)."""
    try:
        if d[:4] != b'GVAS':
            return 0
        off = 16 + 6 + 4           # versions + engine ver (3×u16) + changelist
        r = read_fstring(d, off)   # engine branch
        off = r[1] if r else off + 4
        off += 4                   # custom version format
        n = struct.unpack_from('<i', d, off)[0]; off += 4
        off += n * 20              # custom versions: guid(16) + int32
        r = read_fstring(d, off)   # save game class name
        return r[1] if r else off
    except Exception:
        return 0


def scan_strings(d, start):
    out, pos = [], start
    while pos < len(d):
        r = read_fstring(d, pos)
        if r:
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


def parse(path):
    """Return {ok, setup_count, recognized_fraction, notes, setups}.

    `ok=False` (low confidence) signals the workflow to fall back to AI extraction."""
    with open(path, 'rb') as fh:
        d = fh.read()
    start = body_start(d)
    setups = [build(s) for s in group_setups(scan_strings(d, start))]
    if not setups and start != 0:               # header-independent fallback
        setups = [build(s) for s in group_setups(scan_strings(d, 0))]

    notes = []
    good = [s for s in setups if s['param_count'] >= MIN_PARAMS]
    ok = bool(setups) and len(good) >= max(1, (len(setups) + 1) // 2)
    if not setups:
        notes.append('no setups found — not a recognizable ACR save')
    elif not ok:
        notes.append(f'setups have very few parameters (<{MIN_PARAMS}) — likely misparsed')
    total = sum(s['param_count'] for s in setups)
    rec = sum(s['recognized_count'] for s in setups)
    frac = round((rec / total), 2) if total else 0.0  # informational only
    for s in setups:
        notes.extend(f"{s['name']}: {w}" for w in s['warnings'])
    return {'ok': ok, 'setup_count': len(setups),
            'recognized_fraction': frac, 'notes': notes, 'setups': setups}


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
        print(f"\nCONFIDENCE: {'ok' if res['ok'] else 'LOW — consider AI fallback'} | "
              f"{res['setup_count']} setups | {res['recognized_fraction']:.0%} keys recognized")
        for n in res['notes']:
            print(f"  note: {n}")
    else:
        print(json.dumps(res, indent=2))
    sys.exit(0 if res['ok'] else 3)


if __name__ == '__main__':
    main()
