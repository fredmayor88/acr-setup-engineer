"""Measured in-game facts the game files do not give us, and what is derived from them.

calibration.json (next to this file) holds two kinds of measurement, with provenance:

- rev limiters, per car, read from telemetry. The end of a car's torque curve is not its
  limiter: on several cars it is hundreds of rpm past it.
- speed runs: per-gear top speeds on a known gearing, from the in-game speedometer. They fit
  the rolling radius factor (`fit_factor`) once the limiter they were driven against is known.

Next to each limiter it stores the game's "v4" value for that car (`rev_stages`), read when the
limiter was measured. v4 is not the limiter — it reads ~450 rpm low on the Stratos and 037 —
but a change in it means the car's engine data changed, so the measurement may be stale.
"""
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CALIBRATION = os.path.join(HERE, 'calibration.json')
sys.path.insert(0, HERE)

from gearing import ratio as _ratio             # noqa: E402

# An estimated rev limit is v4 plus this. On the 16 cars where v4 tracks the limiter it sits
# within ~200 rpm of it, mostly just under.
ESTIMATE_OVER_V4 = 100

_MARKER = struct.pack('<f', 3000.0)
# how far past the 3000.0 marker the group may start: an int and a short property header
# sit between them in every car read so far (10 bytes)
_SEARCH = 24


def load_calibration(path=CALIBRATION):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def rev_stages(blob):
    """The shift-light rev stages in a car's DA_<car> asset, as a list of rpm floats.

    Located by shape, not offset: a `3000.0` float, then within a few bytes a run of at least
    three strictly rising floats above 3000 and below 20000. Most cars store four; a stage left
    at its default is omitted from the unversioned data (the Alpine stores three). Returns
    None when no such group exists. The last value is "v4".
    """
    at = blob.find(_MARKER)
    while at >= 0:
        for start in range(at + 4, min(at + 4 + _SEARCH, len(blob) - 4)):
            group, o = [], start
            while o + 4 <= len(blob):
                v = struct.unpack_from('<f', blob, o)[0]
                if not (3000.0 < v < 20000.0) or (group and v <= group[-1]):
                    break
                group.append(v)
                o += 4
            if len(group) >= 3:
                return group
        at = blob.find(_MARKER, at + 1)
    return None


_TORQUE_REF = re.compile(rb'/Game/Data/Vehicles/(\w+)/(FC_\w+?_Torque)(?![A-Za-z0-9_])')


def torque_curve_ref(blob):
    """(vehicle folder, asset name) of the FC_*_Torque curve a DA_<car> asset points at, or
    None. The 206 WRC has no curve of its own and points at the Xsara WRC's."""
    m = _TORQUE_REF.search(blob)
    return (m.group(1).decode(), m.group(2).decode()) if m else None


def car_asset(paks, car_asset_name, tmp):
    """Unpack DA_<car_asset_name>.uasset into tmp and return its path (the exact file, not
    the longer DA_<car>_... siblings that share the prefix)."""
    import make_gearing_chart as M
    want = f'DA_{car_asset_name}.uasset'
    hits = [h for h in M.extract(paks, want, tmp) if os.path.basename(h) == want]
    if not hits:
        raise SystemExit(f'car asset {want} not found')
    return hits[0]


def resolve_rev_limit(slug, v4, calibration):
    """(rev limit rpm, source, warning or None) for one car.

    measured       — a telemetry limiter is stored and the game's v4 still matches the one it
                     was measured against.
    measured-stale — the limiter is stored but v4 has changed since: the value is still the
                     best there is, and the warning says to re-measure.
    estimated      — nothing measured: v4 + ESTIMATE_OVER_V4.
    """
    entry = calibration.get('rev_limiters', {}).get(slug)
    if entry is None:
        if v4 is None:
            raise SystemExit(f'{slug}: no measured rev limit and no rev stages in the game files')
        return int(round(v4)) + ESTIMATE_OVER_V4, 'estimated', None
    if v4 is not None and int(round(v4)) != entry['game_v4']:
        return (entry['rpm'], 'measured-stale',
                f'{slug}: game v4 changed from {entry["game_v4"]} to {int(round(v4))} since '
                f'the rev limit was measured - re-measure')
    return entry['rpm'], 'measured', None


def predicted_kmh(rpm, gear, primary, below, free_radius, factor=1.0):
    """Top speed of one gear: the same arithmetic as the site, rpm * circ * 0.06 / ratio."""
    return rpm * 2 * math.pi * free_radius * factor * 0.06 / (gear * primary * below)


def run_predictions(run, rpm, factor=1.0):
    """Predicted km/h per gear for one stored speed run at `rpm`."""
    primary = _ratio(run['primary'])
    below = run['rest'] * _ratio(run['option'])
    return [predicted_kmh(rpm, _ratio(g), primary, below, run['free_radius'], factor)
            for g in run['gears']]


# Gear 1 is left out of the fit: its top speed is the least precise reading of a run (it is
# over in a moment, so the speedometer is read at its least settled).
FIRST_FITTED_GEAR = 2


def implied_factors(calibration):
    """[(run index, gear number, measured / predicted at factor 1)] for gears 2+ of every run."""
    out = []
    limiters = calibration['rev_limiters']
    for i, run in enumerate(calibration['speed_runs']):
        pred = run_predictions(run, limiters[run['car']]['rpm'])
        for g, (measured, p) in enumerate(zip(run['kmh'], pred), start=1):
            if g >= FIRST_FITTED_GEAR:
                out.append((i, g, measured / p))
    return out


def fit_factor(calibration):
    """The rolling radius factor: the plain mean of every implied factor, gears 2+ of every
    run, each gear weighted equally. Rounded to 4 decimals."""
    values = [f for _i, _g, f in implied_factors(calibration)]
    return round(sum(values) / len(values), 4)


FORMULA = ('implied factor per gear = measured_kmh / (limiter_rpm * 2 * pi * free_radius * 0.06 '
           '/ (gear * primary * rest * option)); factor = mean over gears 2+ of every run, '
           'each gear weighted equally, rounded to 4 decimals. Gear 1 is excluded: its top '
           'speed is the least precise reading.')


def fit_report(calibration, factor=None):
    """The 'fit' block stored in calibration.json: value, formula and per-gear residuals at
    `factor` (the fitted one when not given)."""
    factor = fit_factor(calibration) if factor is None else factor
    limiters = calibration['rev_limiters']
    runs = []
    for run in calibration['speed_runs']:
        rpm = limiters[run['car']]['rpm']
        pred = run_predictions(run, rpm, factor)
        runs.append({
            'car': run['car'], 'gear_set': run['gear_set'], 'limiter_rpm': rpm,
            'gears': [{'gear': g, 'measured': m, 'predicted': round(p, 1),
                       'error_pct': round((p - m) / m * 100, 2),
                       'fitted': g >= FIRST_FITTED_GEAR}
                      for g, (m, p) in enumerate(zip(run['kmh'], pred), start=1)],
        })
    return {'loaded_radius_factor': factor, 'formula': FORMULA, 'runs': runs}


def main():
    """Refit and write the 'fit' block back into calibration.json. Prints the factor."""
    cal = load_calibration()
    cal['fit'] = fit_report(cal)
    with open(CALIBRATION, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(cal, fh, indent=1)
        fh.write('\n')
    print(f"loaded_radius_factor = {cal['fit']['loaded_radius_factor']}")
    for run in cal['fit']['runs']:
        print(f"  {run['car']} {run['gear_set']}: "
              + '  '.join(f"{g['measured']}/{g['predicted']} ({g['error_pct']:+.1f}%)"
                          for g in run['gears']))


if __name__ == '__main__':
    main()
