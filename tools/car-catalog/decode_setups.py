"""The game's own default setups, straight out of a car's presets asset.

Maintainer tooling, same family as `extract_car_catalog.py`: it needs the cooked
game files and never ships inside the skill. Where the catalog extractor reads the
*ranges* a parameter may take, this reads the *values* the game ships as that car's
default setup, per surface and per named preset.

    from acrpkg import Package
    from datatable import rows as dt_rows
    import decode_setups as D

    pkg = Package(open('DA_LanciaStratosHFPresets.uasset', 'rb').read())
    decoded = D.decode_car(pkg, tables)
    keys = D.car_keys_from(pkg)
    for surface, preset in D.surfaces_and_presets(decoded):
        values = D.compose(decoded, surface, preset)
        adjustments, unfilled = D.to_adjustments(values, template_rows, tables, keys)

Three layers, applied in this order (spec: *What the game files hold*):

1. `PhysicsCarSetup` - one export, the car's base setup. Positional, not keyed by
   setting id: the schema below is what turns its slots into setting ids.
2. `CarSetupVariantsSurface` - one export per surface, a `TMap<FName setting id,
   UCarSettingOverride*>`. Value overrides only; range overrides in the same map are
   the catalog extractor's business and are skipped here.
3. `CarSetupVariant` - the named presets, held in a second `TMap<FName, obj>` at the
   end of the surface export. `Balanced` is empty on every car seen so far.

=============================================================================
The pinned schema
=============================================================================

Everything below was read off the Lancia Stratos fixture
(`tests/fixtures/paks/DA_LanciaStratosHFPresets.uasset`, game 0.6) and cross-checked
against the Lancia 037 Evo 2 and the Lancia Delta HF Integrale Evo, which between them
cover RWD, a front/centre/rear drivetrain, and master cylinders. Offsets are relative
to the start of the export's bytes (`Package.export_bytes`).

**Nothing here is 4-byte aligned.** Every struct - including every element of an array
of structs - starts with its own `FUnversionedHeader` (`unversioned.read_header`), which
is 2 bytes plus an optional zero-mask byte. A property whose value equals its default is
not written at all; a property flagged in the zero mask is present but stored as zero.
So the *slot index* is the only stable key, and the walk has to be type-driven, which is
what `_SCHEMA` below is. The validation that the schema is right is that the walk lands
exactly on the 4-byte trailer: `_read_struct` asserts it.

`PhysicsCarSetup` (Stratos export 171, 516 bytes, header `00 08 02 03` -> slots
0,1,2,3,6, first value at +4):

    slot 0  Drivetrain struct                              +4   (see below)
    slot 1  Axles struct                                   +146
    slot 2  array[4] of Damper struct                      +242  (FL, FR, RL, RR)
    slot 3  array[4] of Wheel struct                       +398  (FL, FR, RL, RR)
    slot 6  Brakes struct                                  +446
            4-byte trailer                                 +512

Drivetrain (Stratos +4, header `02 02 01 02 01 0b` -> slots 2,4,6,7,8,9,10):

    slot 0  Differential struct   Differentials.Front.*
    slot 1  Differential struct   Differentials.Centre.*
    slot 2  Differential struct   Differentials.Rear.*     +10 on the Stratos
    slot 3  float                 centre torque split (0.4717 on the Delta - no setting id)
    slot 4  DB ref                Gearbox.GearboxMain.GearsSet    +38 `GearsSets/…Set0`
    slot 5  DB ref                Differentials.Centre.CentreRatioToFront (unseen on any
                                  bundled car - DT_CentreToFrontGearsLists is empty for all
                                  of them; typed as a DB ref so the walk stays aligned)
    slot 6  DB ref                Differentials.Centre.CentreDifferentialRatio (Delta `51//13`)
    slot 7  DB ref                Gearbox.GearboxMain.GearPrimary +74 `Gears/25//25`
    slot 8  DB ref                Differentials.Centre.CentreRatioToRear  (Delta `13//34`)
    slot 9  DB ref                Differentials.Front.DifferentialRatio   (Delta `25//25`)
    slot 10 DB ref                Differentials.Rear.DifferentialRatio +128 `Gears/65//19`

    Pinned by list membership, which is unambiguous: the Delta's slot 6 `51//13` is in
    DT_CentreGearsLists and not in its one-entry DT_PrimaryGearsLists, its slot 8 `13//34`
    is in DT_CentreToRearGearsLists, its slot 10 `30//12` is in DT_RearGearsLists.

    Differential struct (Stratos rear at +10, header `00 07` -> 3 slots):
        slot 0  DB ref   LSDRamps            +12 `LSDRampAngles/50_65`
        slot 1  int32    LSDFrictionPlates   +30 `4`
        slot 2  float    LSDPreload          +34 `100.0`
        (slots 3-5 typed as floats; none of the three reference cars writes them)

    DB ref struct (header `00 05` -> 2 slots, 2 FNames, 18 bytes in all):
        slot 0  FName    the DataTable hint (`GearsSets`, `Gears`, `LSDRampAngles`, ...)
        slot 1  FName    the row name (`LanciaStratosSet0`, `65//19`, `50_65`, ...)

Axles (Stratos +146, header `00 06 01 03` -> slots 0,1,2,4):

    slot 0  float                       Axles.Front.ARBStiffness   +150 `3250.0`
    slot 1  float                       Axles.Rear.ARBStiffness    +154 `2500.0`
    slot 2  float                       unmapped (0.04 Stratos, 0.039 037, 0.042 Delta)
    slot 3  float                       unmapped
    slot 4  array[4] Suspension corner  +162
    slot 5  float                       unmapped

    Suspension corner (Stratos +166, header `80 0b` + zero-mask `08` -> 5 slots, slot 3 zero):
        slot 0  float  unmapped                    +169 `0.015`
        slot 1  float  unmapped                    +173 `0.05`
        slot 2  float  SpringStiffness             +177 `65000.0`  (rear corners `42500.0`)
        slot 3  float  unmapped (zero on all three cars)
        slot 4  float  AdjusterRing                +181 `0.048`    (rear `0.067`)

Damper (Stratos front corner +246, header `00 0d` -> 6 slots):

    slot 0  pair struct  slow   +248 -> SlowBump `6250.0`, SlowRebound `7250.0`
    slot 1  pair struct  fast   +258 -> FastBump `4750.0`, FastRebound `6250.0`
    slot 2  float        BumpTransition     +268 `0.1`
    slot 3  float        ReboundTransition  +272 `0.1`
    slot 4  float        unmapped `1.0`
    slot 5  float        unmapped `1.0`
    (element is 38 bytes; rear corners read 4250/5750, 3750/5250, 0.15, 0.15)

Wheel (Stratos front corner +402, header `80 09` + zero-mask `0c` -> 4 slots, 2 and 3 zero):

    slot 0  float  TyrePressure  +405 `28.0`
    slot 1  float  Camber        +409 `-2.4`   (rear corners `-1.9`)
    slot 2  float  Toe           (zero here; the Delta's front corners store `0.0001`)
    slot 3  float  unmapped

Brakes (Stratos +446, header `00 0f` -> 7 slots):

    slot 0  float                  Brakes.BrakesMain.FrontBias       +448 `0.57`
    slot 1  float                  unmapped (2.75 Stratos, 3.0 on the 037 and the Delta)
    slot 2  float                  Brakes.BrakesMain.ProportioningRatio  +456 `0.5`
    slot 3  float                  Brakes.BrakesMain.HandbrakeForce      +460 `1.0`
    slot 4  array[4] part struct   discs    +464  (all-zero on all three cars)
    slot 5  array[4] part struct   calipers +480
    slot 6  array[4] part struct   pads     +496
    slot 7  float                  unmapped
    slot 8  DB ref                 Brakes.BrakesMain.MasterCylinderFront
                                   (037: `MasterCylinders/19.05`)
    slot 9  DB ref                 Brakes.BrakesMain.MasterCylinderRear
    slot 10 DB ref                 unmapped

    The three part arrays are all-zero on every car checked, which is consistent with
    every surface overriding discs, calipers and pads explicitly - so the per-corner
    brake parts always come from layer 2, never from the base.

`CarSetupVariantsSurface` (Stratos Tarmac export 169, 272 bytes, header `00 02 01 05`
-> slots 0,2,3, first value at +4):

    slot 0  FName                       the default preset's name (`Balanced`)  +4
    slot 2  TMap<FName, obj>            the surface's overrides   +12 (19 entries)
    slot 3  TMap<FName, obj>            name -> CarSetupVariant   +248 (1 entry)

    A TMap serialises as int32 `NumRemoved` (always 0 here), int32 `Num`, then `Num`
    entries of 12 bytes: FName index, FName number, FPackageIndex. **The package index
    is one more than the export index**, exactly as in `acrpkg.setting_pairs`.

`CarSetupVariant` (Stratos `Balanced` export 167, 6 bytes: a bare header `01 01` and the
trailer - no properties at all, so Balanced == the surface layer). The Delta's
`Aggressive` (export 189, 62 bytes) has slot 0 = the same kind of override TMap, 4 entries.

An override export carries the chosen value:

    CarSettingOverrideFloat / Integer / Bool   schema slot 0, read with
                                               `Package.floats`/`ints`; a slot that is
                                               absent means the value equals its default,
                                               which for these is 0 (the gravel
                                               `Axles.Rear.ARBStiffness` override is
                                               exactly this: an empty export meaning 0).
    CarSettingOverrideValueSetDBReference      24 bytes: FName (table hint) at +4,
                                               FName (row) at +12.

=============================================================================
From setting ids to what the setup screen shows
=============================================================================

`to_adjustments` collapses corners to axles (left and right asserted equal, as the
catalog extractor does for ranges), maps setting ids to template `Adjustment` names
through `mapping.py`, and resolves DB references through the `DT_*Lists` tables:

| gear set          | position in DT_GearsSetsLists[car] + 1 -> `1`               |
| primary, ratios   | the row name as is (`33//31*31//30`, `65//19`)              |
| LSD ramps         | `45_50` -> `45/50`                                          |
| pads              | the suffix, upper-cased (`Type13_Medium` -> `MEDIUM`)       |
| master cylinders  | the row name as is (`19.05`)                                |
| discs             | position in the car's disc list for that axle, taken as the |
|                   | same position in the template's `Discrete steps`            |
| calipers          | same, over the calipers the axle's discs can take; a car    |
|                   | whose list is longer than the template's falls back to the  |
|                   | caliper's bore (`4x42` -> `4x42 Type1`), and only when that |
|                   | bore is unique among both the options and the steps         |

The option lists are the union of the car's four per-surface `DT_DiscsLists` rows for that
axle, which works because every one of those rows is a *prefix* of the union on all 18 cars
- so a part's position is the same whatever surface is asking, and `to_adjustments` needs no
surface. `_disc_options` asserts that prefix property rather than trusting it.

`decode_car` also returns `notes`: every DB reference whose row is not in the car's own list
for that setting (`db_row_notes`). On 0.6 that finds ten cars whose base primary gear is the
struct's filler, the Alpine A110's gravel rear caliper, and the Audi Quattro's master
cylinder - all real, all worth reading after an extraction.

A resolved list value the template doesn't list is dropped and named as unfilled rather
than written: the Peugeot 206 WRC's base primary gear is the struct's `25//25` filler and
neither of its surfaces overrides it, so that car has no default primary gear in the
files at all, and writing `25//25` would just put an illegal value in the bundled file.

Validated on game 0.6 against all 18 cars in `extract_car_catalog.CAR_MAP`: every one
walks to its trailer, no car disagrees left to right, and every composed value lands on
its template's grid except three the game itself ships off it (the Peugeot 208's
`Slow Bump Front 4285`, the VW Polo's `Anti-roll Bar Stiffness Front 19500`, the Mini's
gravel `Proportioning Preload 3.5` - all template-range questions, not decode errors).

=============================================================================
What the presets asset does not hold
=============================================================================

- **Tyre type.** No `Wheels.*.TyreCompound` setting, and no `TireCompounds` name in the
  Stratos or 037 presets asset at all. The car asset `DA_LanciaStratosHF` names
  `TarmacSoft`, but that is the physics tyre, not a setup value layered per surface.
  `Tyre Type` therefore comes back unfilled.
- **ABS / TCS map, additional lights.** Declared as settings, never given a base value.
- **Brake discs, calipers and pads at the base level** - see above; they always come
  from the surface layer.
"""

import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mapping as M                          # noqa: E402
from unversioned import read_header          # noqa: E402

TRAILER = 4

# ------------------------------------------------------------------ the schema
#
# A type is 'f' (float32), 'i' (int32), 'n' (FName, 8 bytes), ('S', {slot: type})
# for a nested struct, or ('A', type) for int32 count + that many elements.

DBREF = ('S', {0: 'n', 1: 'n'})
DIFF = ('S', {0: DBREF, 1: 'i', 2: 'f', 3: 'f', 4: 'f', 5: 'f'})
DRIVETRAIN = ('S', {0: DIFF, 1: DIFF, 2: DIFF, 3: 'f',
                    **{k: DBREF for k in range(4, 16)}})
SUSPENSION = ('S', {k: 'f' for k in range(8)})
AXLES = ('S', {0: 'f', 1: 'f', 2: 'f', 3: 'f', 4: ('A', SUSPENSION), 5: 'f', 6: 'f'})
DAMPER_PAIR = ('S', {0: 'f', 1: 'f'})
DAMPER = ('S', {0: DAMPER_PAIR, 1: DAMPER_PAIR, 2: 'f', 3: 'f', 4: 'f', 5: 'f', 6: 'f'})
WHEEL = ('S', {k: 'f' for k in range(6)})
BRAKE_PART = ('S', {0: DBREF, 1: DBREF})
BRAKES = ('S', {0: 'f', 1: 'f', 2: 'f', 3: 'f',
                4: ('A', BRAKE_PART), 5: ('A', BRAKE_PART), 6: ('A', BRAKE_PART), 7: 'f',
                **{k: DBREF for k in range(8, 12)}})
PHYSICS_CAR_SETUP = ('S', {0: DRIVETRAIN, 1: AXLES, 2: ('A', DAMPER), 3: ('A', WHEEL),
                           4: 'f', 5: 'f', 6: BRAKES, 7: 'f'})

CORNERS = ('FrontLeft', 'FrontRight', 'RearLeft', 'RearRight')

# drivetrain slot -> setting id
DRIVETRAIN_IDS = {
    4:  'Gearbox.GearboxMain.GearsSet',
    5:  'Differentials.Centre.CentreRatioToFront',
    6:  'Differentials.Centre.CentreDifferentialRatio',
    7:  'Gearbox.GearboxMain.GearPrimary',
    8:  'Differentials.Centre.CentreRatioToRear',
    9:  'Differentials.Front.DifferentialRatio',
    10: 'Differentials.Rear.DifferentialRatio',
}
DIFF_AXLES = {0: 'Front', 1: 'Centre', 2: 'Rear'}
DIFF_IDS = {0: 'LSDRamps', 1: 'LSDFrictionPlates', 2: 'LSDPreload'}
AXLE_IDS = {0: 'Axles.Front.ARBStiffness', 1: 'Axles.Rear.ARBStiffness'}
SUSPENSION_IDS = {2: 'SpringStiffness', 4: 'AdjusterRing'}
DAMPER_PAIR_IDS = {0: ('SlowBump', 'SlowRebound'), 1: ('FastBump', 'FastRebound')}
DAMPER_IDS = {2: 'BumpTransition', 3: 'ReboundTransition'}
WHEEL_IDS = {0: 'TyrePressure', 1: 'Camber', 2: 'Toe'}
BRAKE_IDS = {
    0: 'Brakes.BrakesMain.FrontBias',
    2: 'Brakes.BrakesMain.ProportioningRatio',
    3: 'Brakes.BrakesMain.HandbrakeForce',
    8: 'Brakes.BrakesMain.MasterCylinderFront',
    9: 'Brakes.BrakesMain.MasterCylinderRear',
}

# A `Gears` DB reference names no table of its own - which gear list it has to come from
# is decided by the setting it belongs to.
GEAR_TABLES = {
    'Gearbox.GearboxMain.GearPrimary':              'DT_PrimaryGearsLists',
    'Differentials.Front.DifferentialRatio':        'DT_FrontGearsLists',
    'Differentials.Rear.DifferentialRatio':         'DT_RearGearsLists',
    'Differentials.Centre.CentreDifferentialRatio': 'DT_CentreGearsLists',
    'Differentials.Centre.CentreRatioToFront':      'DT_CentreToFrontGearsLists',
    'Differentials.Centre.CentreRatioToRear':       'DT_CentreToRearGearsLists',
}


# -------------------------------------------------------------- the struct walk

class _Reader:
    def __init__(self, pkg, start, end):
        self.pkg, self.d, self.o, self.end = pkg, pkg.d, start, end

    def _take(self, n):
        if self.o + n > self.end:
            raise AssertionError(f'PhysicsCarSetup walk ran past the export at {self.o}')
        o = self.o
        self.o += n
        return o

    def read(self, t, path):
        if t == 'f':
            return struct.unpack_from('<f', self.d, self._take(4))[0]
        if t == 'i':
            return struct.unpack_from('<i', self.d, self._take(4))[0]
        if t == 'n':
            idx, num = struct.unpack_from('<II', self.d, self._take(8))
            if idx >= len(self.pkg.names) or num > 4096:
                raise AssertionError(f'{path}: {idx},{num} is not an FName')
            return self.pkg.name(idx, num)
        if t[0] == 'S':
            return self.struct(t[1], path)
        if t[0] == 'A':
            n = struct.unpack_from('<i', self.d, self._take(4))[0]
            if not 0 <= n <= 16:
                raise AssertionError(f'{path}: implausible array count {n}')
            return [self.read(t[1], f'{path}[{k}]') for k in range(n)]
        raise ValueError(t)

    def struct(self, schema, path):
        present, o = read_header(self.d, self.o)
        if o > self.end:
            raise AssertionError(f'{path}: header runs past the export')
        self.o = o
        out = {}
        for idx, is_zero in present:
            t = schema.get(idx)
            if t is None:
                raise AssertionError(
                    f'{path}: slot {idx} is not in the pinned schema - the game files '
                    f'changed, re-read the module docstring and re-pin it')
            out[idx] = _zero_of(t) if is_zero else self.read(t, f'{path}.{idx}')
        return out


def _zero_of(t):
    """The value of a property the zero mask flags as present-but-zero."""
    if t == 'f':
        return 0.0
    if t == 'i':
        return 0
    if t == 'n':
        return None
    return {}                       # a struct or array whose whole value is zero


def snap(v):
    """Drop float32 storage noise: 9.999999747e-05 is the game's 0.0001."""
    return float(f'{v:.7g}')


def _num(v):
    """A float the templates would write bare: 65000.0 -> 65000, 0.048 stays 0.048."""
    v = snap(v)
    return int(round(v)) if abs(v - round(v)) < 1e-9 else v


def _dbref(ref):
    """('db', table hint, row name) for a DB-reference struct, or None when unset."""
    if not ref or 0 not in ref or 1 not in ref:
        return None
    return ('db', ref[0], ref[1])


# --------------------------------------------------------------- layer 1: base

def _by_corner(array, what):
    """[(corner, element)] for a per-corner array, which is four long or absent.

    Zipping against `CORNERS` would quietly drop a fifth element or leave a corner
    undecoded; a per-corner array that isn't four long means the schema moved.
    """
    if not array:
        return []
    if len(array) != len(CORNERS):
        raise AssertionError(f'{what}: {len(array)} corners, expected {len(CORNERS)} '
                             f'- the pinned schema no longer matches the game files')
    return list(zip(CORNERS, array))


def decode_base(pkg):
    """{setting id: value} for the car's `PhysicsCarSetup` export.

    A value is a float, an int, a bool, or a `('db', table hint, row name)` tuple.
    Slots the schema leaves unmapped are read (so the walk stays aligned) and dropped.
    """
    idx = [i for i, e in enumerate(pkg.exports) if e[2] == 'PhysicsCarSetup']
    if len(idx) != 1:
        raise AssertionError(f'expected one PhysicsCarSetup export, found {len(idx)}')
    start, blob = pkg.export_bytes(idx[0])
    end = start + len(blob)
    r = _Reader(pkg, start, end)
    root = r.struct(PHYSICS_CAR_SETUP[1], 'PhysicsCarSetup')
    if r.o != end - TRAILER:
        raise AssertionError(
            f'PhysicsCarSetup walk consumed {r.o - start} of {len(blob) - TRAILER} bytes '
            f'- the pinned schema no longer matches the game files')

    out = {}
    drivetrain = root.get(0) or {}
    for slot, axle in DIFF_AXLES.items():
        diff = drivetrain.get(slot)
        if not isinstance(diff, dict) or not diff:
            continue                       # this car has no differential on that axle
        for k, suffix in DIFF_IDS.items():
            if suffix == 'LSDRamps':
                ref = _dbref(diff.get(k))
                if ref is not None:
                    out[f'Differentials.{axle}.{suffix}'] = ref
            else:
                out[f'Differentials.{axle}.{suffix}'] = _value(diff.get(k, 0))
    for slot, sid in DRIVETRAIN_IDS.items():
        ref = _dbref(drivetrain.get(slot))
        if ref is not None:
            out[sid] = ref

    axles = root.get(1) or {}
    if axles:
        for slot, sid in AXLE_IDS.items():
            out[sid] = _value(axles.get(slot, 0.0))
    for corner, susp in _by_corner(axles.get(4), 'Suspensions'):
        for slot, suffix in SUSPENSION_IDS.items():
            out[f'Suspensions.{corner}.{suffix}'] = _value(susp.get(slot, 0.0))

    for corner, damper in _by_corner(root.get(2), 'Dampers'):
        for slot, names in DAMPER_PAIR_IDS.items():
            pair = damper.get(slot) or {}
            for k, suffix in enumerate(names):
                out[f'Dampers.{corner}.{suffix}'] = _value(pair.get(k, 0.0))
        for slot, suffix in DAMPER_IDS.items():
            out[f'Dampers.{corner}.{suffix}'] = _value(damper.get(slot, 0.0))

    for corner, wheel in _by_corner(root.get(3), 'Wheels'):
        for slot, suffix in WHEEL_IDS.items():
            out[f'Wheels.{corner}.{suffix}'] = _value(wheel.get(slot, 0.0))

    brakes = root.get(6) or {}
    for slot, sid in BRAKE_IDS.items():
        t = BRAKES[1][slot]
        if t is DBREF:
            ref = _dbref(brakes.get(slot))
            if ref is not None:
                out[sid] = ref
        elif brakes:
            out[sid] = _value(brakes.get(slot, 0.0))
    return out


def _value(v):
    """A property's value the way a template writes it; `None` (an unset FName) is 0."""
    if v is None:
        return 0
    return _num(v) if isinstance(v, float) else v


# ------------------------------------------------- layers 2 and 3: the overrides

def _entries(pkg, exp):
    """Every (FName, export index) of every `TMap<FName, object>` in one export.

    A TMap serialises as int32 NumRemoved (0), int32 Num, then Num 12-byte entries of
    (FName index, FName number, FPackageIndex). Entries are validated against the name
    map and the export map, so a run of bytes that only looks like a map is rejected.
    """
    start, blob = pkg.export_bytes(exp)
    d, end, o, out = pkg.d, start + len(blob), start, []
    while o <= end - 8:
        removed, n = struct.unpack_from('<ii', d, o)
        if removed == 0 and 1 <= n <= 512 and o + 8 + 12 * n <= end:
            pairs, p, ok = [], o + 8, True
            for _ in range(n):
                ni, nn, ref = struct.unpack_from('<IIi', d, p)
                if ni >= len(pkg.names) or nn > 4096 or not 0 < ref <= len(pkg.exports):
                    ok = False
                    break
                pairs.append((pkg.name(ni, nn), ref - 1))
                p += 12
            if ok:
                out += pairs
                o = p
                continue
        o += 1
    return out


def override_value(pkg, exp):
    """The value one `CarSettingOverride*` export carries, or None if it isn't one.

    A float/integer/bool override whose slot 0 is absent means "equal to the default",
    which for these overrides is zero - the gravel `Axles.Rear.ARBStiffness` override is
    an empty export and the game reads it as 0.
    """
    cls = pkg.exports[exp][2]
    if cls.endswith('ValueSetDBReference'):
        a, _ = pkg.export_bytes(exp)
        return ('db', pkg.name(*struct.unpack_from('<II', pkg.d, a + 4)),
                pkg.name(*struct.unpack_from('<II', pkg.d, a + 12)))
    if cls.endswith('OverrideFloat'):
        return _num(pkg.floats(exp).get(0, 0.0))
    if cls.endswith('OverrideInteger'):
        return pkg.ints(exp).get(0, 0)
    if cls.endswith('OverrideBool'):
        return bool(pkg.ints(exp).get(0, 0))
    return None


def variant_values(pkg, exp):
    """{setting id: value} for one surface or one named preset export.

    The complement of `acrpkg.variant_ranges`, which keeps the range overrides and skips
    these. Range overrides (`CarSettingOverrideRange*`, `RangeOverride*`) are the catalog
    extractor's business.
    """
    out = {}
    for sid, ref in _entries(pkg, exp):
        if '.' not in sid or sid in M.IGNORED:
            continue
        cls = pkg.exports[ref][2]
        if 'Range' in cls or not cls.startswith('CarSettingOverride'):
            continue
        v = override_value(pkg, ref)
        if v is not None:
            out[sid] = v
    return out


def variant_presets(pkg, exp):
    """{preset name: CarSetupVariant export} held at the end of a surface export."""
    return {name: ref for name, ref in _entries(pkg, exp)
            if '.' not in name and pkg.exports[ref][2] == 'CarSetupVariant'}


# ------------------------------------------------------------------- public API

def decode_car(pkg, tables=None):
    """The whole car: base setup, per-surface overrides, per-preset overrides.

        {'base': {setting id: value},
         'surfaces': {surface: {'overrides': {setting id: value},
                                'presets': {name: {setting id: value}}}},
         'notes': [str]}

    A value is a float, an int, a bool, or `('db', table hint, row name)`. `tables`
    ({table name: {row: [values]}}, as `extract_car_catalog` builds them) is optional and
    used only to note DB references whose row is missing from the tables - the decode
    itself never needs them.
    """
    main = pkg.main_export()
    out = {'base': decode_base(pkg), 'surfaces': {}, 'notes': []}
    for surface, exp in pkg.surface_variants(main).items():
        presets = {name: variant_values(pkg, ref)
                   for name, ref in variant_presets(pkg, exp).items()}
        out['surfaces'][surface] = {'overrides': variant_values(pkg, exp),
                                    'presets': presets}
    if tables:
        out['notes'] = db_row_notes(out, tables, car_keys_from(pkg))
    return out


def db_options(setting_id, value, tables, car_keys):
    """The car's legal rows for one DB-referenced setting, or None when there are none.

    None means "nothing to check this against" - the table isn't loaded, or the car has no
    list for that setting (a rear-drive car has no centre-differential list, and no `Pads`
    list ships in the game files at all). It is the same lookup `resolve` does, so the two
    can't drift: a row this returns nothing for is a row `resolve` can't spell either.
    """
    _, hint, row = value
    wheels = car_keys.get('wheels')
    axle = setting_id.split('.')[1].replace('Left', '').replace('Right', '')
    if hint == 'GearsSets':
        sets = tables.get('DT_GearsSetsLists') or {}
        return sets.get(car_keys.get('gears_sets')) or sets.get(wheels)
    if hint == 'Gears':
        table = tables.get(GEAR_TABLES.get(setting_id, ''))
        return (table or {}).get(wheels)
    if hint == 'LSDRampAngles':
        return (tables.get('DT_DiffRampsLists') or {}).get(f'{wheels}_{axle}')
    if hint == 'MasterCylinders':
        return (tables.get('DT_MasterCylindersLists') or {}).get(wheels)
    if hint == 'Discs' and tables.get('DT_DiscsLists'):
        return _disc_options(tables, wheels, axle) or None
    if hint == 'Calipers' and tables.get('DT_CalipersLists'):
        return _caliper_options(tables, wheels, axle) or None
    return None


def db_row_notes(decoded, tables, car_keys):
    """Every DB reference in a decoded car whose row is not in the car's own list.

    Worth reading after an extraction: it is how a game update that renames a part, or a
    slot that has quietly moved, shows up as words rather than as a wrong value in a
    bundled file. The `25//25` filler the drivetrain struct leaves in the gear-ratio slots
    it doesn't use is the common honest hit - see the Peugeot 206 WRC in the docstring.
    """
    notes, seen = [], set()
    layers = [decoded['base']]
    for layer in decoded['surfaces'].values():
        layers.append(layer['overrides'])
        layers += list(layer['presets'].values())
    for values in layers:
        for sid in sorted(values):
            v = values[sid]
            if not (isinstance(v, tuple) and v and v[0] == 'db') or (sid, v) in seen:
                continue
            seen.add((sid, v))
            if v[2] is None:
                notes.append(f'{sid}: the {v[1]} row is unset')
                continue
            options = db_options(sid, v, tables, car_keys)
            if options and v[2] not in options:
                notes.append(f'{sid}: {v[2]} is in no {v[1]} list for '
                             f'{car_keys.get("wheels")}')
    return notes


def compose(decoded, surface, preset=None):
    """base + the surface's overrides + the preset's overrides, in that order."""
    if surface not in decoded['surfaces']:
        raise KeyError(f'no {surface} surface: {sorted(decoded["surfaces"])}')
    layer = decoded['surfaces'][surface]
    values = dict(decoded['base'])
    values.update(layer['overrides'])
    if preset is not None:
        if preset not in layer['presets']:
            raise KeyError(f'no {preset} preset on {surface}: {sorted(layer["presets"])}')
        values.update(layer['presets'][preset])
    return values


def surfaces_and_presets(decoded):
    """[(surface, preset)] in the order the asset lists them."""
    return [(surface, name)
            for surface, layer in decoded['surfaces'].items()
            for name in layer['presets']]


# --------------------------------------------------- setting ids -> the template

def car_keys_from(pkg):
    """The car's DataTable row keys, read off its own range overrides.

        {'wheels': 'LanciaStratosHF',      # DT_Wheels prefix: discs, gears, cylinders
         'gears_sets': 'LanciaStratos'}    # the DT_GearsSetsLists row

    `Differentials.*.DifferentialRatio` names `('RearGearsLists', <wheels prefix>)` and
    `Gearbox.GearboxMain.GearsSet` names `('GearsSetsLists', <gear-set key>)`, so both
    come out of the asset with no per-car table to maintain. `LSDRamps` is the fallback
    for the wheels prefix (its row is `<prefix>_Rear`).
    """
    keys = {}
    for sid, exp in pkg.setting_pairs(pkg.main_export()):
        if 'DBReferenceSetFromDB' not in pkg.exports[exp][2]:
            continue
        got = _range_list_row(pkg, exp)
        if not got:
            continue
        hint, row = got
        if hint == 'GearsSetsLists':
            keys['gears_sets'] = row
        elif hint in ('RearGearsLists', 'FrontGearsLists', 'PrimaryGearsLists',
                      'MasterCylindersLists'):
            keys.setdefault('wheels', row)
        elif hint == 'LSDRampAnglesLists':
            keys.setdefault('wheels', re.sub(r'_(Front|Centre|Rear)$', '', row))
    return keys


def _range_list_row(pkg, exp):
    """('<Thing>Lists', row) named by a range override, or None when it names none."""
    _, blob = pkg.export_bytes(exp)
    i = blob.find(b'Values\x00')
    if i < 0:
        return None
    p = i + 7 + 2                                   # past the FString and the 2-byte header
    if p + 16 > len(blob):
        return None
    return (pkg.name(*struct.unpack_from('<II', blob, p)),
            pkg.name(*struct.unpack_from('<II', blob, p + 8)))


def adjustment_of(setting_id):
    """The template `Adjustment` name for one game setting id, or None.

    Corners collapse to axles, exactly as `extract_car_catalog.collapse` does for ranges.
    """
    if setting_id in M.IGNORED or setting_id.count('.') != 2:
        return None
    group, where, suffix = setting_id.split('.', 2)
    axle = where.replace('Left', '').replace('Right', '')
    if group == 'Gearbox' and suffix in M.GEARBOX:
        return M.GEARBOX[suffix][0]
    for table in (M.SUSPENSION, M.DAMPERS, M.WHEELS):
        if suffix in table and group in ('Suspensions', 'Dampers', 'Wheels'):
            return f'{table[suffix][0]} {axle}'
    if group == 'Axles' and suffix in M.AXLES:
        return f'{M.AXLES[suffix][0]} {axle}'
    if group == 'Differentials' and suffix in M.DIFFS:
        stem, _, orders = M.DIFFS[suffix]
        if axle not in orders:
            return None
        # always axle-qualified, the way the rebuilt templates spell it
        return stem if stem.startswith('Center') else \
            f'{stem} {"Center" if axle == "Centre" else axle}'
    if group == 'Brakes' and suffix in M.BRAKES_MAIN:
        return M.BRAKES_MAIN[suffix][0]
    if group == 'Brakes' and suffix in M.BRAKE_PARTS:
        return f'{M.BRAKE_PARTS[suffix][0]} {axle}'
    if group == 'Other' and suffix in M.ELECTRONICS:
        return M.ELECTRONICS[suffix][0]
    return None


def collapse(values):
    """{adjustment: value} with left and right corners merged.

    Raises if a car ever disagrees side to side - as in the catalog extractor, that
    would mean the walk had slipped, and averaging it would hide the bug.
    """
    out = {}
    for sid in sorted(values):
        name = adjustment_of(sid)
        if name is None:
            continue
        v = values[sid]
        if name in out and out[name] != v:
            raise AssertionError(f'left/right mismatch for {name} ({sid}): '
                                 f'{out[name]!r} vs {v!r}')
        out[name] = v
    return out


def _steps(template_rows, adjustment):
    """A template row's `discrete_steps`, split; surface-specific rows are ignored."""
    for r in template_rows:
        if r.get('adjustment') == adjustment and not r.get('surface'):
            return [s.strip() for s in (r.get('discrete_steps') or '').split(',') if s.strip()]
    return []


def _disc_options(tables, wheels_key, axle):
    """Every disc this car can fit on one axle, in DT_DiscsLists order, deduplicated.

    A car has four `DT_DiscsLists` rows per axle - `<prefix>_Tarmac_Front`, `_Gravel_Front`,
    `_Montecarlo_Front`, `_Sweden_Front` - and they are **not** all the same: on 14 of the
    36 car/axle groups in `CAR_MAP` they differ, the Lancia Delta's front axle listing 9
    discs on tarmac and 5 on gravel. What *is* true on all 18 cars is that every per-surface
    row is a **prefix** of the union in table order, and that is the whole reason a single
    union can stand in for the per-surface list: a disc has the same index in both, so
    "position in the option list" is surface-independent and the caller needs no surface.

    That prefix property is asserted here, because the day it stops holding is the day the
    union silently starts naming the wrong disc.
    """
    out, rows = [], []
    for row, discs in (tables.get('DT_DiscsLists') or {}).items():
        if not (row.startswith(wheels_key + '_') and row.endswith('_' + axle)):
            continue
        rows.append((row, list(discs)))
        for d in discs:
            if d not in out:
                out.append(d)
    for row, discs in rows:
        if discs != out[:len(discs)]:
            raise AssertionError(
                f'{wheels_key} {axle}: {row} is not a prefix of the union of that axle\'s '
                f'disc lists, so a disc\'s position is no longer surface-independent - '
                f'resolve discs and calipers per surface instead')
    return out


def _caliper_key(disc_row):
    """The DT_CalipersLists row that lists the calipers fitting one disc.

    `APLockheed_CP4448-81_267x28_Baffled_5x108_APLockheedDisc00_LanciaStratosHF_Rear`
    -> `APLockheed_CP4448-81_267x28_Baffled_5x108_Calipers_LanciaStratosHF_Rear`: the
    `_<Maker>Disc<n>` asset segment is dropped and `_Calipers` takes its place, keeping
    whatever per-car, per-axle suffix followed it.
    """
    m = re.search(r'_[A-Za-z]+Disc\d+', disc_row)
    if m:
        return disc_row[:m.start()] + '_Calipers' + disc_row[m.end():]
    return disc_row + '_Calipers'


def _caliper_options(tables, wheels_key, axle):
    """Every caliper this car can fit on one axle, in disc order, deduplicated.

    Surface-independent for the same reason the disc list is: a first-appearance union over
    a prefix of the discs is a prefix of the union over all of them.
    """
    calipers = tables.get('DT_CalipersLists') or {}
    out = []
    for disc in _disc_options(tables, wheels_key, axle):
        for c in calipers.get(_caliper_key(disc), ()):
            if c not in out:
                out.append(c)
    return out


BORE = re.compile(r'\d+x[\d.]+(?:/[\d.]+)?', re.I)


def _bore(part):
    """`Brembo_4Pot_Type6_4x42_BremboCaliper02` -> `4x42`, or None."""
    found = BORE.findall(part)
    return found[-1].lower() if found else None


def _by_bore(part, steps, options):
    """The one template step this caliper's bore names, or None when it isn't the one.

    The fallback for a car whose caliper option list is longer than the template's - the
    037's rear axle lists three calipers where the screenshot-era template kept two, so
    position-for-position mapping is off the table. A part id spells its bore, and the
    template's strings start with it (`4x42 Type1`).

    It refuses unless the bore identifies the caliper on **both** sides: exactly one
    template step may start with it, and exactly one of the car's options for that axle may
    carry it. The `TYPE<n>` index in the template's strings is a UI number that is in no
    game file (see README.md - *What it doesn't touch*), so with two same-bore options
    there is nothing left to tell them apart - the 037's rear axle fits both a
    `Brembo_2Pot_Type4_2x48` and an `ATE_Porsche_911_S-Type_2x48`, and guessing between
    them would put a wrong part in a bundled setup. Unfilled and reported is the honest
    answer; the Stratos's front axle is the same story.
    """
    bore = _bore(part)
    if bore is None:
        return None
    if len([o for o in options if _bore(o) == bore]) != 1:
        return None
    hits = [s for s in steps if s.lower().replace(' ', '').startswith(bore)]
    return hits[0] if len(hits) == 1 else None


def resolve(value, adjustment, template_rows, tables, car_keys):
    """One DB reference as the setup screen spells it, or None when it can't be resolved.

    The rules are the spec's *Global Constraints* table:

    | gear set          | position in DT_GearsSetsLists[car] + 1                  |
    | primary, ratios   | the row name as is (`33//31*31//30`, `65//19`)          |
    | LSD ramps         | `45_50` -> `45/50`                                      |
    | pads              | the suffix, upper-cased (`Type13_Medium` -> `MEDIUM`)   |
    | master cylinders  | the row name as is (`19.05`)                            |
    | discs, calipers   | position in the car's option list for that axle, taken  |
    |                   | as the same position in the template's Discrete steps   |
    """
    _, hint, row = value
    if row is None:
        return None            # a zero-masked FName: the row was never set
    if hint == 'GearsSets':
        sets = tables.get('DT_GearsSetsLists') or {}
        # the Peugeot 208 declares no gear-set range override, so its asset names no
        # DT_GearsSetsLists row - its list is keyed by the DT_Wheels prefix instead
        rows = sets.get(car_keys.get('gears_sets')) or sets.get(car_keys.get('wheels')) or []
        return str(rows.index(row) + 1) if row in rows else None
    if hint == 'Gears':
        return row
    if hint == 'LSDRampAngles':
        return row.replace('_', '/')
    if hint == 'Pads':
        return row.rsplit('_', 1)[-1].upper()
    if hint == 'MasterCylinders':
        return row
    if hint in ('Discs', 'Calipers'):
        axle = adjustment.rsplit(' ', 1)[-1]
        options = (_disc_options if hint == 'Discs' else _caliper_options)(
            tables, car_keys.get('wheels'), axle)
        steps = _steps(template_rows, adjustment)
        if row in options and len(options) == len(steps):
            return steps[options.index(row)]
        return _by_bore(row, steps, options) if hint == 'Calipers' else None
    return None


def to_adjustments(values, template_rows, tables, car_keys):
    """({template adjustment: display value}, [template adjustments left unfilled]).

    `values` is one composed setup (`compose`); `template_rows` the car template's
    parameter rows as `extract_car_catalog.read_old` returns them; `tables` the DataTables
    `extract_car_catalog` already loads; `car_keys` the car's DataTable row keys, exactly
    `car_keys_from(pkg)` - **no surface**, because a disc's and a caliper's position in the
    car's option list is the same on every surface (see `_disc_options`).

    Corner values are collapsed to axles and left is asserted equal to right. A value the
    game data has no source for - `Tyre Type`, `ABS Map`, `TCS Map` - is left out and
    named in the second return value, so the caller can report it rather than guess.
    """
    merged = collapse(values)
    out, notes = {}, []
    for name, v in merged.items():
        if isinstance(v, tuple) and v and v[0] == 'db':
            display = resolve(v, name, template_rows, tables, car_keys)
            steps = _steps(template_rows, name)
            # A list value the template doesn't list is not a value, it's a gap. The
            # Peugeot 206 WRC's base primary gear is the struct's `25//25` placeholder
            # and neither surface overrides it, so the car genuinely has no default
            # primary gear in the files - say so rather than write an illegal one.
            if display is None or (steps and display not in steps):
                notes.append(name)
                continue
            out[name] = display
        else:
            out[name] = v
    wanted = [r['adjustment'] for r in template_rows if not r.get('surface')]
    unfilled = sorted(set(notes) | {n for n in wanted if n not in out})
    return {k: out[k] for k in sorted(out) if k in set(wanted)}, unfilled
