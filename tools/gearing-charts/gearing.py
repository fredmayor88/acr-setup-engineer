"""Gear ratios for one car, straight out of the ACR game files.

A gear set asset stores its ratios as FNames spelling the tooth counts - `42//15` is
a 42/15 pair, `33//31*31//30` a two-stage primary. The array is laid out
[gear 1 .. gear N, primary, reverse], which holds for 5- and 6-speed cars alike.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'car-catalog'))

from acrpkg import Package                  # noqa: E402
from datatable import rows as dt_rows       # noqa: E402


def ratio(name):
    """`42//15` -> 2.8; `33//31*31//30` -> 1.1 (stages multiply).

    An epicyclic set is spelled with a sum: `(27+48)//27` is 75/27.
    """
    def teeth(part):
        return sum(float(x) for x in part.strip('()').split('+'))

    total = 1.0
    for stage in name.split('*'):
        a, b = stage.split('//')
        total *= teeth(a) / teeth(b)
    return total


def drivetrain_chain(pkg):
    """The car's five default drivetrain ratios, in the order the game stores them:
    centre diff, centre->front, centre->rear, front diff, rear diff."""
    _, blob = pkg.export_bytes(0)
    seq, o = [], 0
    while o < len(blob) - 8:
        idx, num = struct.unpack_from('<II', blob, o)
        if num == 0 and 0 <= idx < len(pkg.names):
            seq.append(pkg.name(idx, num)); o += 8
        else:
            o += 1
    out, expect = [], False
    for n in seq:
        if n == 'Gears':
            expect = True
            continue
        if expect:
            out.append(n); expect = False
    return out


def axle_final_drive(chain, axle):
    """Engine-to-wheel ratio for the driven axle, excluding the gearbox.

    Only the driven axle's branch counts: on a rear-drive car the front entries are
    all 1:1 placeholders, and using the whole chain would multiply in the branch the
    car never drives.
    """
    r = [ratio(c) for c in chain]
    if len(r) != 5:
        raise ValueError(f'expected 5 drivetrain ratios, got {len(r)}')
    return r[0] * (r[1] * r[3] if axle == 'Front' else r[2] * r[4])


# Which slot of drivetrain_chain each ratio adjustment on the setup screen replaces.
CHAIN_SLOTS = {
    'Center Differential Ratio': 0,
    'Center Ratio to Front': 1,
    'Center Ratio to Rear': 2,
    'Differential Ratio Front': 3,
    'Differential Ratio Rear': 4,
}


def with_settings(chain, settings):
    """The chain with each named ratio setting (`{adjustment: spelling}`) put in its slot.
    Names that are not chain ratios (Primary Gear) are ignored."""
    out = list(chain)
    for name, spelling in settings.items():
        if name in CHAIN_SLOTS:
            out[CHAIN_SLOTS[name]] = spelling
    return out


def averaged_final_drive(chain):
    """Engine-to-wheel ratio below the gearbox on a car whose centre differential averages its
    two outputs (ruling R51, measured in game on the Delta, 206 WRC, Impreza and Xsara WRC):
    with every wheel at the same road speed the gearbox output turns at the mean of the front
    and rear chains.

        centre diff * (centre->front * front diff + centre->rear * rear diff) / 2
    """
    r = [ratio(c) if isinstance(c, str) else c for c in chain]
    if len(r) != 5:
        raise ValueError(f'expected 5 drivetrain ratios, got {len(r)}')
    return r[0] * (r[1] * r[3] + r[2] * r[4]) / 2


def gear_set(path):
    """-> (forward gear ratio names, primary name, reverse name)."""
    pkg = Package(open(path, 'rb').read())
    _, blob = pkg.export_bytes(0)
    seq, o = [], 0
    while o < len(blob) - 8:
        idx, num = struct.unpack_from('<II', blob, o)
        if num == 0 and 0 <= idx < len(pkg.names):
            seq.append(pkg.names[idx]); o += 8
        else:
            o += 1
    vals = [n for n in seq if '//' in n]
    if len(vals) < 3:
        raise ValueError(f'{os.path.basename(path)}: only {len(vals)} ratios')
    return vals[:-2], vals[-2], vals[-1]


# The stored radius is the free (unloaded) one. A loaded tyre rolls on a slightly
# smaller effective radius, so speed per rev is lower than the geometry suggests.
# Fitted against measured in-game top speeds on seven cars (Stratos, 306 Maxi, Xsara WRC, 037,
# 206 WRC, Delta Integrale, Impreza) at their measured rev limiters: see calibration.py and
# calibration.json. export_car_data imports this one, so there is a single copy; a test asserts
# it equals the refit.
LOADED_RADIUS_FACTOR = 0.9904


def tyre_geometry(blob):
    """(section width, free radius) in metres.

    Found by shape rather than a fixed offset: the property header in front of them
    varies in length, and a tyre that leaves a value at its default omits it entirely.
    """
    for o in range(2, 26):
        try:
            w, r, x = struct.unpack_from('<fff', blob, o)
        except struct.error:
            return None
        if 0.05 < w < 0.5 and 0.15 < r < 0.5 and 3 < x < 40:
            return w, r
    return None


def rolling_circumference(radius):
    """Effective rolling circumference in metres for a free radius."""
    import math
    return 2 * math.pi * radius * LOADED_RADIUS_FACTOR
