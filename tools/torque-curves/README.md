# torque-curves — engine curves out of the ACR game files

Maintainer tooling. Reads every car's engine torque curve straight out of Assetto Corsa
Rally's pak files, renders a power/torque chart per car into [`car-charts/`](../../car-charts),
and writes the curve back into each bundled template in
[`.claude/skills/acr-setup-engineer/car-templates/`](../../.claude/skills/acr-setup-engineer/car-templates).

**Nothing here ships inside the skill.** It needs a local game install, so it can't run on
claude.ai. The skill consumes only the committed outputs: the PNGs (by public URL) and the
`engine_curve:` block in each template.

## Running it

```bash
npm install                                  # once — pulls ooz-wasm
pip install matplotlib                       # once
python extract_torque_curves.py --dry-run    # report only, writes nothing
python extract_torque_curves.py              # regenerate charts + templates
```

`--paks` overrides the game path if ACR isn't at the default Steam location. Re-running is
idempotent: charts are overwritten and the template stanza is delimited by
`# --- engine curve … ---` markers, so it's replaced in place and hand-written fields around it
are left alone.

Run it after a game update that touches car physics, and whenever a new car is onboarded —
add the car to `CAR_MAP` (in-game folder name → template slug) first, or the tool will say it
doesn't recognise it.

## Where the data comes from

Each car has an `FC_<Car>_Torque` asset under `acr/Content/Data/Vehicles/<Car>/` — a UE
`FRichCurve` mapping engine speed to crank torque in Nm, sampled every 250 rpm from 0 to just past
the redline. That curve is the game's engine output; power is derived from it
(`kW = Nm × rpm / 9549`, then metric hp), never stored separately.

Two things make reading it awkward, and both are handled here:

- **Oodle compression.** ACR is UE 5.x, and the oo2core DLLs shipped with older games reject its
  blocks. `ooz_unpack.mjs` uses the [ooz-wasm](https://www.npmjs.com/package/ooz-wasm)
  reimplementation instead, which is why there's a node dependency in a Python tool.
- **Unversioned property serialisation.** There are no name tags in the asset to anchor a parser
  on, so `parse_rich_curve` scans for an int32 key count followed by that many 27-byte
  `FRichCurveKey` structs with strictly increasing, in-range times, and keeps the longest match.
  It's a heuristic, but a well-constrained one — see the sanity check below.

**Sanity check.** Derived peak power lands within a few percent of the figure the game quotes for
every naturally aspirated car (Alfa GTA 163 hp vs 163, Fulvia 165 vs 165, Mini 115 vs 115, Xsara
311 vs 310, Impreza 301 vs 300). If a game update ever breaks the parser, that agreement is the
first thing to lose — check it before trusting a regenerated batch.

**Peak torque is a different story on forced-induction cars.** The curve is what the game
simulates; the `max_torque:` line in a template is a real-world spec resolved by a different
ladder, and on the turbo/supercharged cars the two genuinely disagree (Fabia 310 Nm vs 430,
i20 320 vs 420, Delta Evo 417 vs 535, 037 348 vs 320). That's expected. The tool doesn't touch
`max_power:` / `max_torque:`, and the skill is told to keep both and explain the difference rather
than reconcile them.

## Sibling curves, deliberately ignored

Each car also has `FC_<Car>_Density` — charge air density in kg/m³. Naturally aspirated cars top
out at exactly 1.204 (sea-level ambient) and fall away with rpm; turbo cars run well above it
(the Xsara reaches 2.63). It's informative about boost, but it is **not** a multiplier on the
torque curve: applying it puts the Xsara at 654 hp. The torque curve already reflects final
output, so density is left alone. `FC_AutoBlip` / `FC_<Car>_BlipProfile` are throttle-blip
shapes, not engine output.
