"""Game setting id -> car-template parameter, and the shape of the emitted YAML.

The game names every setting per corner (`Dampers.FrontLeft.SlowBump`); templates
carry one row per axle. Corners are collapsed here, and left/right are asserted
equal by the extractor before collapsing.
"""

# in-game suffix -> (template adjustment, order, unit)
GEARBOX = {
    'GearsSet':    ('Gear Set', 1010, ''),
    'GearPrimary': ('Primary Gear', 1020, ''),
}

SUSPENSION = {                     # (adjustment stem, front order, rear order, unit)
    'AdjusterRing':    ('Adjuster Ring', 2010, 2030, 'm'),
    'SpringStiffness': ('Spring Stiffness', 2020, 2040, 'N/m'),
}

DAMPERS = {
    'SlowBump':          ('Slow Bump', 3010, 3050, 'Ns/m'),
    'SlowRebound':       ('Slow Rebound', 3020, 3060, 'Ns/m'),
    'FastBump':          ('Fast Bump', 3030, 3070, 'Ns/m'),
    'FastRebound':       ('Fast Rebound', 3040, 3080, 'Ns/m'),
    'BumpTransition':    ('Bump Transition', 3045, 3085, 'm/s'),
    'ReboundTransition': ('Rebound Transition', 3046, 3086, 'm/s'),
}

AXLES = {'ARBStiffness': ('Anti-roll Bar Stiffness', 4010, 4020, 'N/m')}

# differential suffix -> (adjustment stem, unit, {axle: order})
DIFFS = {
    'DifferentialRatio':       ('Differential Ratio', '', {'Front': 5005, 'Rear': 5035}),
    'LSDRamps':                ('LSD Power/Coast Ramp', '', {'Front': 5010, 'Centre': 5036, 'Rear': 5040}),
    'LSDPreload':              ('LSD Preload', 'Nm', {'Front': 5020, 'Centre': 5037, 'Rear': 5050}),
    'LSDFrictionPlates':       ('Plates Number', '', {'Front': 5030, 'Centre': 5038, 'Rear': 5060}),
    'CentreDifferentialRatio': ('Center Differential Ratio', '', {'Centre': 5032}),
    'CentreRatioToRear':       ('Center Ratio to Rear', '', {'Centre': 5034}),
}

WHEELS = {
    'TyrePressure': ('Pressure', 6020, 6050, 'psi'),
    'Camber':       ('Camber', 6030, 6060, '°'),
    'Toe':          ('Toe', 6040, 6070, 'm'),
}

BRAKE_PARTS = {                      # carried over from the previous template
    'Disc':        ('Brake Discs', 7010, 7080, ''),
    'Caliper':     ('Brake Calipers', 7020, 7090, ''),
    'PadCompound': ('Brake Pads', 7030, 7100, ''),
}

BRAKES_MAIN = {
    'FrontBias':             ('Front Bias', 7040, ''),
    'ProportioningRatio':    ('Proportioning Ratio', 7040, ''),
    'ProportioningPreload':  ('Proportioning Preload', 7045, 'MPa'),
    'MasterCylinderFront':   ('Front Cylinder', 7050, 'mm'),
    'MasterCylinderRear':    ('Rear Cylinder', 7060, 'mm'),
    'MasterCylinder':        ('Master Cylinder', 7050, ''),
    'HandbrakeForce':        ('Handbrake Force', 7070, ''),
}

ELECTRONICS = {
    'AdditionalLights': ('Additional Lights', 8005, ''),
    'ABS':              ('ABS Map', 8010, ''),
    'TCS':              ('TCS Map', 8020, ''),
    'EngineMap':        ('Engine Map', 8030, ''),
    'ThrottleMap':      ('Throttle Map', 8040, ''),
}

SECTIONS = {
    'Gearbox': 'Gearbox', 'Suspensions': 'Suspensions', 'Dampers': 'Dampers',
    'Axles': 'Axles', 'Differentials': 'Differentials', 'Wheels': 'Wheels',
    'Brakes': 'Brakes', 'Other': 'Electronics',
}

# Settings the game exposes that templates deliberately don't carry.
IGNORED = {'Wheels.Steering.FFBPlayerMultiplier', 'Other.Lights'}

# Definition-level ranges: the per-car assets override only the step, so min/max
# come from the shared setting definition rather than from any car's asset.
DEFINITION_RANGES = {
    'Front Bias':          (0.25, 0.75),
    'Proportioning Ratio': (0.0, 1.0),
    'ABS Map':             (1, 3),
    'TCS Map':             (1, 3),
}

# Parameters whose legal values are DB part records whose *display* strings the UI
# synthesises from part specs; the previous template's wording is kept for these.
CARRIED_OVER = {'Tyre Type', 'Brake Discs Front', 'Brake Discs Rear',
                'Brake Calipers Front', 'Brake Calipers Rear',
                'Brake Pads Front', 'Brake Pads Rear',
                'Front Cylinder', 'Rear Cylinder', 'Master Cylinder'}

MAX_DISCRETE = 64          # longer than this and a min/max line says it better
