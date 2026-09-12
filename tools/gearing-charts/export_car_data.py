"""Export one JSON document per car for the ACR Car Lab site.

Where make_gearing_chart.py draws PNGs, this writes the same facts as data and lets the
browser do the arithmetic. The split matters for one reason: the site exposes an editable
rolling-radius factor, so the stored tyre figure has to be the free radius with no factor
baked into it.

    python export_car_data.py --all --out ../acr-car-lab
"""

LOADED_RADIUS_FACTOR = 0.9562


def _kw(torque_nm, rpm):
    """Engine power in kW from torque in Nm at a given engine speed."""
    return torque_nm * rpm / 9549


def build_car_json(slug, name, axle, gear_sets, engine_curve, final_drive, tyres,
                   generated):
    """One car's complete published record.

    Every downstream number on the site is derived from this document, so anything the
    browser cannot recompute has to be in here.
    """
    curve = [[rpm, torque, _kw(torque, rpm)] for rpm, torque in engine_curve]
    peak_torque = max(curve, key=lambda r: r[1])
    peak_power = max(curve, key=lambda r: r[2])

    doc = {
        'slug': slug,
        'name': name,
        'axle': axle,
        'engine': {
            'redline': max(r[0] for r in curve),
            'peak_torque_rpm': peak_torque[0],
            'peak_power_rpm': peak_power[0],
            'curve': curve,
        },
        'gear_sets': [
            {'label': f'Gear set {i + 1}',
             'gears': [{'name': n, 'value': v} for n, v in gears]}
            for i, gears in enumerate(gear_sets)
        ],
        'final_drive': None,
        'tyres': {key: {'asset': asset, 'free_radius': radius}
                  for key, (asset, radius) in tyres.items()},
        'defaults': {'loaded_radius_factor': LOADED_RADIUS_FACTOR},
        'generated': generated,
    }

    if final_drive is not None:
        doc['final_drive'] = {
            'adjustment': final_drive['adjustment'],
            'primaries': [{'name': n, 'value': v}
                          for n, v in final_drive['primaries']],
            'options': [{'name': n, 'value': v} for n, v in final_drive['options']],
            'stock_option': final_drive['stock_option'],
            'rest': final_drive['rest'],
        }
    return doc
