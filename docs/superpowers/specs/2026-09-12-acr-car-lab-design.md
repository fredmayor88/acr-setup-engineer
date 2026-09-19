# ACR Car Lab — design

**Date:** 2026-09-12
**Status:** approved, not yet implemented

An interactive, GitHub-Pages-hosted companion to the ACR Setup Engineer. One page per car,
showing the power/torque curve plus four parametrizable gearing charts. Linked from each
car's Catalogue page in Notion.

The name is deliberately not about gearing. Gearing is the first feature, not the scope.

## Repos and the regeneration path

Two repos, one direction of travel. All pak parsing stays in `acr-setup-engineer`; the site
repo holds generated data and hand-written app code and nothing else.

**`acr-setup-engineer`** gains `tools/gearing-charts/export_car_data.py`, reusing the existing
parsers unchanged — `gear_set`, `ratio`, `tyre`, `drivetrain_chain`, `axle_final_drive`,
`pick_ratio`, `stock_final_drive`, `template_facts`. Instead of drawing PNGs it writes JSON and
page shells into a sibling `acr-car-lab` checkout.

- `--car <slug>` / `--all`, `--out ../acr-car-lab`
- A `make car-lab` target wraps it.
- The two repos are assumed to sit side by side.

**`acr-car-lab`**:

```
index.html          car picker
app.js              charts, controls, URL state, tracking (shared, cached)
app.css
data/<slug>.json    generated — every number for one car
data/index.json     generated — the car list
<slug>/index.html   generated — thin shell, title and h1 baked in for search
README.md
```

Per-car pages are real paths, not hash routes: `/lancia-stratos/`. That gives the Notion
Catalogue links clean URLs and gives each car its own indexable page.

**Updating after a game patch:** run `make car-lab`, commit in `acr-car-lab`. The app code
contains no numbers, so a patch never touches it. `acr-car-lab/README.md` must document this
procedure explicitly — the sibling-checkout assumption, the command, the post-run checks (new
cars present, tyre assets still resolving, one top speed spot-checked in-game), and the commit.

## Data model

**Export free tyre radius, not circumference.** `LOADED_RADIUS_FACTOR` ships as a default value
and the browser computes `circumference = 2*pi*r * factor`, then
`km/h = rpm * circumference * 0.06 / total_ratio`. This is what makes the editable calibration
control real: changing the factor redraws every chart from first principles. Exporting
circumference would bake the factor in and make the control a lie.

The shape below is what the exporter actually writes, verified against the generated data:

```json
{ "slug": "lancia-stratos", "name": "Lancia Stratos HF 1976", "axle": "Rear",
  "engine": { "redline": 8750, "peak_torque_rpm": 6000, "peak_power_rpm": 7750,
              "curve": [[rpm, torque_nm, power_kw]] },
  "gear_sets": [ { "label": "Gear set 1",
                   "primary": { "name": "33//31*31//30", "value": 1.1 },
                   "gears": [ { "name": "42//15", "value": 2.8 } ] } ],
  "final_drive": { "adjustment": "Differential Ratio Rear",
                   "primaries": [ { "name": "35//30*33//28", "value": 1.375 } ],
                   "options": [ { "name": "65//19", "value": 3.4211 } ],
                   "stock_option": "65//19", "rest": 1.0 },
  "fixed_final_drive": null,
  "tyres": { "Tarmac_Dry": { "asset": "PirelliT03", "free_radius": 0.296 } },
  "defaults": { "loaded_radius_factor": 0.9562 } }
```

`generated` lives in `data/index.json` only, not in each car document — stamping a date into
every file makes a no-op re-export a seventeen-file diff.

**Three car shapes, and the ratio composes differently for each.** This is the single most
error-prone part of the data model.

| Shape | Cars | `gear_sets[].primary` | `final_drive.primaries` | Below the gearbox |
| --- | --- | --- | --- | --- |
| Selectable primary | Stratos only | the stock pick, and one of the options | 8 entries | `rest × selected option` |
| Fixed primary, selectable diff | 12 cars | **varies per gear set** | `[]` — no selector, *not* no primary | `rest × selected option` |
| Nothing adjustable | i20, Fabia, Polo R5, 208 Rally4 | applies as stored | `final_drive` is `null` | `fixed_final_drive` |

```
effectivePrimary = final_drive && final_drive.primaries.length
                     ? the selected entry of final_drive.primaries
                     : gear_sets[selectedSet].primary
belowGearbox     = final_drive ? final_drive.rest * selectedOption.value
                               : fixed_final_drive
totalRatio       = gear.value * effectivePrimary.value * belowGearbox
```

On the Stratos the two primaries are **alternatives, not factors** — multiplying both
double-counts by up to 1.375×. An empty `primaries` list means the car has no primary
*selector*; its primary is the per-set one.

`rest` is everything in the driven path that is not the adjustable ratio, computed as
`stock_final_drive / ratio(stock_option)`. That matches `render_car` in
`make_gearing_chart.py`; it deliberately does **not** match `chart_final_drive`, which has a
pre-existing bug (see Known limits).

**Each gear set carries its own primary.** Four cars — Mini Cooper S, Fiat 124 Abarth, Fiat 131
Abarth, Lancia Fulvia — ship a different primary in each gear set. Publishing gear set 1's
primary for all of them overstates speeds on the other sets by up to 26%.

## Controls

One sticky control bar at the top of the car page holds only what every chart shares:

- **Surface** — five entries, labelled by condition: Dry tarmac, Wet tarmac, Gravel, Snow,
  Winter tarmac. These describe the condition rather than naming a game item, so no in-game
  verification is needed. A factual note under the dropdown that dry and wet tarmac give
  identical speeds renders ONLY on cars whose Tarmac_Dry and Tarmac_Wet free radii are equal
  (7 of 17). On the other 10 the wet tyre is a different asset with a different radius
  (e.g. Alfa GTA 0.2655 vs 0.269 m), so the note would be false there.
- **Final drive** — the selected primary × differential combination. Same state chart 2 sets
  when a row is clicked; the dropdown and the chart are two views of one value.
- **Gear set** — the selected gear set. Same state chart 3 sets when a lane name is clicked;
  again, two views of one value.

The two dropdowns are symmetrical, and so are the charts they mirror:

| State | Set where | Read by |
| --- | --- | --- |
| Surface | control bar | all five charts |
| Final drive | control bar, or clicking a row in chart 2 | chart 2 (highlighted row), charts 3, 4 and 5 (every speed) |
| Gear set | control bar, or clicking a lane in chart 3 | chart 2 (the km/h column), chart 3 (highlighted lane), chart 4 (the only set it draws) |
| Drawn gear sets | checkbox list beside chart 5 | chart 5 only |

Chart 3 still draws **every** gear set; the selection only marks one lane. Chart 5's checkbox
list is separate state and belongs to that chart alone.

## Charts

All five are hand-rolled SVG, sharing one axis/tooltip module. No charting library. Same
technique as `gremlin-curve-converter`. Brand palette and `SET_COLOURS` from
`make_gearing_chart.py`.

### 1. Power and torque

No parameters. Drawn live from the same JSON rather than reusing the existing PNG, so every
chart reads as one instrument. rpm on X, torque and power on twin Y axes, plus a redline
marker.

The two peaks are marked with their **values, not the words "peak torque" and "peak power"** —
`260 Nm · 6000 rpm` and `195 kW · 7750 rpm`. The position on the curve already says which peak
it is; the number is the part worth reading.

Hover reads out rpm, torque and power, each with **how far off peak it is as a percentage** —
`248 Nm  95% of peak`, `130 kW  67% of peak`. That is the question the chart is actually asked:
not what the engine makes here, but how much of it you are giving up.

The readout parks in the **top-left** of the plot. Bottom-left is wrong and obviously so once
stated: at low rpm both curves are near zero, and zero is at the bottom, so bottom-left is the
one corner guaranteed to be occupied — on the Stratos it hides the torque curve between roughly
778 and 1120 rpm. Top-left is clear on all seventeen cars, because reaching the top of the
torque axis requires high rpm. Tightest margin is the Citroen Xsara WRC at 47px.

### 2. Final drive grid

Parameters: gear set, surface.

One row per primary × differential combination, sorted shortest first. Each row shows percent
of the shortest combination and the resulting km/h at the top gear of the selected gear set at
the rev limit. The caption names that gear set, so the speed is never a mix-and-match of gears
no single configuration produces. Each row prints its ratio spelling, percentage and speed
permanently, so the chart has no hover.

**Clicking a row sets the final drive for charts 3, 4 and 5.** This cross-link is the main reason
the interactive version beats the static PNG.

For a car with no adjustable final drive, this chart is replaced by a single line stating that
the final drive is not adjustable on this car.

### 3. Where each gear tops out

Parameters: final drive, surface. **Every gear set is always drawn** — this chart has no
selector.

It reproduces the existing `chart_gear_ladder` layout, which is already the right answer for a
car like the 306 Maxi with ten gear sets of differing gear counts:

- One horizontal lane per gear set, labelled `Gear set 1   (5-speed)`.
- Each lane's line **starts at 0 km/h**, so first gear reads as a span like every other gear
  rather than a dot floating in space.
- A numbered dot at each gear's top speed, with the speed written above it.
- A secondary top axis giving speed relative to the slowest gear.

**Lane names are clickable, and set the gear set** — the same state as the control bar's gear
set dropdown. The selected lane is tinted and marked `selected`.

Caption, verbatim: *One lane per gear set, all of them at once. Click a lane name to select
that gear set.* It does not mention the hover — the shift comparison moved to chart 4, and
what is left is a plain readout that needs no advertising.

**Hover gives speed, gear and revs — nothing else.** One line:
`132 km/h · gear 3 · 7537 rpm`. The gear you are in is the lowest one whose top speed you have
not passed. The shift comparison lives in the Shift points chart below; carrying it here as
well earned its clutter on ten lanes and did not repay it.

The readout is a single-line tooltip placed after the lane's last dot and clamped to the chart
width, so it fits inside its own lane and never covers the next one.

### 4. Shift points

Parameters: gear set, final drive, surface. Shows **only the selected gear set** — this is the
close-up that the ladder above deliberately isn't.

One row per gear. Each bar runs from a usable-revs floor to the rev limit, so **bars overlap**:
the same road speed is reachable in more than one gear, and that overlap is the thing the chart
exists to show. Non-overlapping bars, tiled so each gear owned its own speed band, were tried
and rejected — they draw a tidy staircase that hides the choice.

The floor is currently 3000 rpm, stated in the caption. It is one constant, it sets how much
overlap the chart shows, and it is arbitrary — 3000 rpm puts the Stratos at 76% of peak torque,
which is a defensible reading of "usable". Worth eyeballing on a peaky car like the 306 Maxi
before it is settled.

Caption, verbatim: *The selected gear set, one row per gear. Each bar covers the speeds where
that gear is usable, from 3000 rpm to the rev limit. Where bars overlap you have a choice of
gear. Hover for the revs either side of a shift.*

**Shift helper.** Hovering drops a vertical line at the hovered speed. The readout above the
plot gives the gear of the row under the cursor, with its speed and revs; the hovered speed is
clamped to that gear's bar. The gear is taken from the row, not inferred as "the lowest gear
not yet topped out": inferring always picks the shortest usable gear, so every downshift would
over-rev and the warning would fire on every hover. Chips on the rows above and below give the revs you would land at in those
gears at the *same speed*. A downshift above the rev limit is called out in a warning colour,
and because the bars stop at the limiter, such a marker also sits visibly past the end of its
own bar.

Same-speed, not same-revs: you are never in two gears at once at the same revs, and on a speed
axis the comparison is a single vertical line.

### 5. Speed vs revs

Parameters: final drive, surface, and its **own vertical checkbox list of gear sets, sitting to
the right of the plot**. This list is separate from the selected gear set and belongs to this
chart alone.

**One gear set is ticked by default**, not two — a car like the 306 Maxi has ten sets of six or
seven gears each, and drawing them all at once is unreadable. The caption does not explain
this; the control is self-evident.

X is revs, Y is speed. One line per gear per ticked gear set. Hover gives gear set, gear
number, revs, speed. This is a port of the existing `chart_speed_vs_revs`, which is currently
implemented behind `--style lines` but never exported per car.

## Calibration control

Below the charts: a number input pre-filled with `0.9562`, and a reset link. Editing it redraws
everything.

The note beside it is two lines, factual, no hedging: what the number is, and that it was fitted
against measured in-game top speeds for the Stratos across 15 gears and applied to every car and
every surface.

## URL state

The full state lives in the hash, `gremlin-curve-converter` style:
`#s=Gravel&fd=3&set=1&draw=1,3&k=0.9562` — surface, final drive, the selected gear set, the
gear sets drawn in chart 5, and the rolling-radius factor. Copy link button beside the controls.
A link reproduces exactly what someone was looking at, which is what makes it postable.

Values from a URL go through the same validation as UI input.

## Tracking

GoatCounter, new site `acr-car-lab.goatcounter.com`, reusing the `track()` dedupe wrapper from
`gremlin-curve-converter`.

| Event | Question it answers |
| --- | --- |
| `car-<slug>` | Which cars people care about |
| `surface-<key>` | Whether anyone drives anything but tarmac |
| `change-final-drive`, `pick-gearset`, `toggle-drawn-set` | Whether the interactivity is used at all |
| `shift-helper` | First hover on the Shift points neighbour-gear feature |
| `edit-factor` | Whether anyone touches the calibration constant |
| `copy-link` | Whether it gets shared |

## Scope decisions

- **Studded Montecarlo is out of scope for v1.** `DA_PirelliTM00Studded` does not resolve as an
  asset. Five surfaces ship; studded is not mentioned in the UI.
- Compound (soft/medium/hard) is not a parameter. Compounds share a carcass, so compound does
  not change rolling circumference and cannot change any speed on these charts.
- Surface labels describe the condition, so the ten in-game tyre names never need mapping to the
  six DT_Wheels keys.

## Known limits

- Every speed depends on one fitted constant applied to every car and every surface.
- Dry and wet tarmac give identical speeds on 7 of the 17 cars only. Where the radii differ,
  the surface dropdown's speeds differ too, and the site says nothing general about it.
- Four of the seventeen cars have no adjustable final drive (i20, Fabia, Polo R5, 208 Rally4)
  and use the not-adjustable state.
- **Seventeen cars, not eighteen.** `peugeot-206-wrc-1999` has no engine curve in its template
  and has never had PNG charts either. Pre-existing gap, not synthesised.
- **Two pre-existing bugs in `make_gearing_chart.py`, outside this project's scope.** The
  per-gear-set primary defect above also affects the committed PNG charts for those four cars.
  Separately, `chart_final_drive` recovers `rest` by dividing a value evaluated at the shortest
  option by `ratio(stock_option)`, inflating it by `maxOption/stockOption` — 11.76% on the
  Stratos, making that chart's km/h labels about 10.5% low. Its percentage labels are unaffected
  (the factor cancels), and the gearing ladder is unaffected. Neither is inherited by the site,
  which computes `rest` directly from `stock_final_drive`.

## Tone

All on-page copy — notes, labels, the calibration explanation, the limits — is sparse and
factual. State the fact, stop.

**No defensive copy.** Never justify a default, pre-empt a criticism, or explain why something
isn't more than it is. "One is selected to start with, because a car like the 306 Maxi has ten"
is an apology for a decision that needed none; "Pick the gear sets to draw" is the whole
caption. A control that works needs no defence.

Avoid "quote" and similar jargon in UI copy. The final drive chart says *speed is top gear of
gear set 1 at the rev limit*, not *quoted at*.
