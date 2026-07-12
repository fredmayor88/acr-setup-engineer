# Car setup tuning principles (base layer)

The reasoning base for `build-setup`. These are **physics effects and consensus heuristics**
for Assetto Corsa Rally (ACR), independent of any specific car — only the legal *ranges*
differ per car (those come from the `Parameters` catalog). Synthesised from the in-game
descriptions and several community tuning guides, critically filtered for physical soundness.

## How this fits together (layers & precedence)

This file is the **shipped base**. The user's own preferences live in **Notion** and
**override** this file. When `build-setup` reasons about a setup, it combines four **authored**
layers, in increasing priority:

1. **Base principles** (this file)
2. **Global user guidelines** (Notion: `Car setups / {Game} / Tuning guidelines`)
3. **Surface section** of that same page (its "Per surface" subsection matching the build
   surface) — not a separate page
4. **Per-car guidelines** (the car page's "Guidelines" section)

The **setup's own driving intent** (what the driver wants from *this* build — rotation,
stability, braking, bumps, conditions) is the most specific layer of all, supplied with the build
request and recorded only in the setup's page body — see `build-setup.md`.

**Location/stage facts (surface, corners, length, character) are not a guideline layer** — they
are objective inputs read from the shared `Locations` catalogue (`notion-structure.md`), the same
way a car's identity facts (drivetrain, weight) are objective inputs. They never carry tuning
advice.

More specific is the **default lean**, not an automatic override: when two authored layers
**materially contradict** on the same parameter, `build-setup` does not silently pick one — it
**surfaces the conflict and asks the user** which to follow before choosing a value.

### Drivetrain tags
Every guideline below is tagged with the drivetrain(s) it applies to. `build-setup` must know
the car's drivetrain and apply only matching lines.

- `[All]` — universal physics, applies to every car.
- `[FWD]` — front-wheel drive.
- `[RWD]` — rear-wheel drive.
- `[AWD]` — all-wheel drive.
- Combos like `[RWD/AWD]` apply to both.

A tagged line never contradicts an `[All]` line; where drivetrains diverge there are separate
tagged lines.

## Workflow / methodology

1. `[All]` **Pick the tyre first** — match it to the surface/conditions (see *Tyres*). This is
   the single biggest grip decision; everything else fine-tunes around it.
2. `[All]` **Read the car** — note engine position and weight bias. The heavier axle can take
   more brake bias and wants slightly more spring/damper support.
3. `[All]` **Set up for *survival* before *balance*** — first make the car safely handle the
   surface (no bottoming out, no floatiness over bumps), *then* tune the under/oversteer balance.
4. `[All]` **Start soft** — a softer car is more predictable; stiffen toward responsiveness.
5. `[All]` **Change a few things at a time** — differential + brake bias give the most change
   for the least effort; get those right, then suspension (height → springs → dampers), then
   alignment. Tuning everything at once hides cause and effect.
6. `[All]` **Step size by surface** — on gravel/snow (soft setups) small clicks are barely
   felt, so move in bigger steps; on tarmac, small changes matter, so move precisely.
7. `[All]` **Learn by repetition** — running the same stretch repeatedly teaches how each
   change feels far better than chasing a single stage.

## Balance cheat-sheet (which way to push)

| Want | Front | Rear |
|---|---|---|
| Less understeer / more rotation | softer spring, softer ARB, slight toe-out, lower tyre pressure | stiffer spring, stiffer ARB |
| More stability / less oversteer | stiffer spring, stiffer ARB | softer spring, softer ARB, more toe-in |
| More braking rotation | — | shift brake bias rearward |
| More braking stability | shift brake bias forward | — |
| More on-power traction, on grip `[RWD/AWD]` | — | more LSD lock (lower power-ramp angle / more plates / more preload) |
| More on-power rotation, on grip `[RWD/AWD]` | — | less LSD lock (higher power-ramp angle) |
| Rear feels loose/wandering through throttle modulation at/over the limit (e.g. drifting on low grip) `[RWD/AWD]` | — | more LSD lock — **preload first** (raise preload), then more power-ramp lock if still loose. Do not reduce lock — see *Differential (LSD)* below |
| More corner-entry rotation | — | higher coast-ramp angle / less preload |

General rule `[All]`: **stiffer where you want less grip/more response; softer where you want
more grip/compliance.** Front and rear changes push the balance in opposite directions.

Two mental models worth keeping:
- **Spring vs. damper** `[All]`: a *spring* reacts to **position** (how compressed it is), a
  *damper* reacts to **speed** (how fast it's compressing). So tune steady-state roll/dive with
  **springs/ARBs**, and the *speed* at which the car rolls/pitches with **dampers**.
- **"Weight = responsibility"** `[All]`: under braking, weight shifts to the **front**, so the
  front governs corner **entry**; on power, weight shifts **rear**, so the rear governs **exit**.
  Tune the loaded end for the phase you want to fix.

## Weight bias (engine layout)

The car's **engine layout** and **weight bias** are recorded as identity facts on its Notion page
(`Engine layout`, `Weight bias`, `Weight` — see `onboard-car.md`). Read them before balancing; they
set the car's *natural* tendency, which the rest of the setup works with or against. If a field is
blank or `couldn't determine`, infer the bias from drivetrain + engine layout, or proceed
drivetrain-only.

- `[All]` **Rear-biased / mid- or rear-engine** (e.g. the heavier axle is the rear): expect easy
  **throttle-on oversteer** and **lift-off rotation**. Lean the setup toward **rear stability** —
  the rear can take more spring/ARB/damper support and the heavier rear axle tolerates **more rear
  brake bias** than a front-heavy car. Don't over-soften the rear chasing rotation it already has.
- `[All]` **Front-biased / front-engine** (typical FWD, and front-engined RWD/AWD): expect
  **understeer** (power understeer on FWD). **Free the front** (softer front ARB/spring, a touch
  more front brake, slight front toe-out); watch for **lift-off snap** if the rear is left too
  stiff. The heavier front axle can carry **more front brake bias**.
- `[All]` **Balanced / ~50/50** (often mid-engine): a **neutral baseline** — smaller corrections
  needed in either direction; trust the symmetric defaults and tune to the stage.
- `[All]` **Weight magnitude is a secondary cue**: a **heavier** car wants slightly **more
  spring/damper support** (to avoid bottoming and floatiness); a **lighter** car can run softer and
  reacts faster to small clicks. Treat this as a tiebreaker, not a primary lever.

## Tuning by drivetrain

### `[FWD]`
The driven wheels both steer and pull, so FWD naturally **understeers** (engine/gearbox mass
over the front). To add rotation: **softer front / stiffer rear** springs and ARBs; some
**rear toe-out** and lift-off help rotate the car; the handbrake is a key rotation tool. The
**front diff** is safe to lock for traction (a heavily locked front mainly adds understeer).
Keep the **driven (front) axle softer** than the rear.

### `[RWD]`
Prone to **power-oversteer / snap**. A safe base is **stiffer front / softer rear** to maximise
traction on the driven rear and calm the snap. Main rotation levers are the **LSD power ramp /
preload** and throttle discipline; rear **toe-in** stabilises the exit. On low grip, **longer
gears** and a **softer engine map** tame the snap. Keep the **driven (rear) axle softer**.

### `[AWD]`
Both pushes and pulls, so **front/rear spring balance matters less** — you steer with throttle
and tune the **differentials**. The **centre diff** sets the front/rear torque split: bias it
**rearward for more rotation / less understeer**, forward for stability. Keep the **front diff
fairly open** so the nose rotates under power; tune the **rear ramp/preload** for the amount of
kick-out you want. Deliberately unbalancing F/R springs is a *fine-tuning* move, not the base.

## Parameters

### Tyres `[All]`

**Tyre type — choose first.** Match the tyre to the surface and conditions; it dominates grip.
ACR offers 10 compounds (see the verbatim in-game text under *Wheels → Tyre Type* in
[parameter-reference-template.md](parameter-reference-template.md)). Pick the **surface** first
(Tarmac vs Gravel vs Snow), then the **compound/condition**:

- **Compound — Soft / Medium / Hard** (same trade-off on both Tarmac and Gravel): **Soft** gives
  the most grip and shortest braking but overheats and wears fastest → short/technical stages,
  cool conditions, or when you can change tyres often. **Medium** is the all-rounder → moderate
  or fast-flowing stages and multi-stage legs. **Hard** has the lowest grip but best durability
  and likes heat → long/abrasive/hot stages or long legs between tyre changes. In cold temps Hard
  struggles to switch on.
- **Tarmac Wet (Rain)** — wet tarmac; soft rain compound, **overheats fast on dry/abrasive**
  surface. Use only when wet is forecast or wet stages outnumber dry in the leg.
- **Tarmac Winter** — Monte-Carlo-type variable conditions; very soft, spans cold-dry → wet →
  light snow. Wears quickly if the stage is mostly dry tarmac.
- **Tarmac Snow** — 2 mm metal studs; compact snow/ice with **little exposed tarmac** (studs
  grind away on bare tarmac).
- **Snow (Studs)** — 7 mm studs, narrow; full snow stages (e.g. Sweden). Carves through snow but
  overheats/wears very fast above freezing. Snow-stage only.

You can **mix tyres per corner** (e.g. a diagonal Winter / Tarmac-Snow split) for mixed loops.
**Width/construction**: narrow/studded tyres **cut into** snow/ice to reach grip beneath and
reduce float; wider tyres give more contact on firm ground and better straight-line traction.

**Tyre pressure.** Lower pressure → bigger contact patch → more grip, and on gravel it lets the
tyre absorb rocks rather than skip; too low → excessive deformation/slip-angle (especially
rear). Higher pressure → smaller contact patch (front high pressure adds understeer) but a more
precise, stable response. Pick per surface and per axle from these trade-offs, then balance by
feel — there is no default direction. **Do not default to low pressures.**

**ACR pressure rule (early access).** Current ACR builds do not appear to reward low pressures
the way real-world logic suggests (the tyre heating/pressure model is still maturing, so tyres
may never reach their optimal hot pressure). **For ACR: when unsure, start in the upper half of
the surface's legal range and adjust from feedback.** Revisit this rule as game builds update.

### Gearbox

**Gear set** `[All]` — selects a ratio family: lower/closer ratios for high-traction surfaces,
higher/wider lower ratios for loose terrain (more wheel torque/control). Sets may differ in
gear count.

**Primary gear** `[All]` — the final-drive pair. Shorter (more reduction) = quicker
acceleration and keeps the engine **in its torque band**, but lower top speed and more
wheelspin risk; longer = higher top speed, gentler delivery. Aim so that **after an upshift the
revs land near the car's torque peak** — chasing redline misses the torque. It doesn't matter
if you never reach top gear; what matters is staying in the power band. Make gears long enough
not to sit on the limiter down long straights.

Drivetrain notes: `[RWD]` on low grip, **longer gears** soften torque delivery and tame
snap-oversteer for less countersteering. `[FWD]` the extra front pull just adds mild,
controllable understeer.

### Suspension

**Adjuster ring (ride height)** `[All]` — raises/lowers the chassis by moving the spring perch;
it mostly changes the **damper's working length / suspension travel**, not spring force. Higher
= more clearance and travel (prevents bottoming on rough ground) but higher CoG, more roll, a
softer/less-responsive feel. Lower = lower CoG, less roll, sharper response, but more bottoming
risk. **Never bottom out** — once the suspension is fully compressed it's rigid and the car
skips. After a height change, re-check travel.

**Spring stiffness** `[All]` — sets suspension frequency and bump absorption. Softer = more
absorption, predictability, and grip on rough ground, but more body movement/oscillation and
bottoming risk; stiffer = responsive, less roll, but on rough terrain it skips and loses
contact. Stiffer **front** → understeer; stiffer **rear** → oversteer (and vice-versa). A
slightly higher rear frequency helps the rear track the front over bumps.
- `[FWD/RWD]` keep the **driven axle softer** than the other.
- `[All]` the **heavier (engine) axle** wants slightly more stiffness as a helper to damping.
- `[All]` pair height with stiffness: "raise + soften" for rough/cut stages, "lower + stiffen"
  for smooth tarmac.

### Dampers

Four settings = compression (**bump**) and extension (**rebound**), each **slow** and **fast**.
`[All]` **Slow** = chassis movements from driver inputs (braking dive, cornering, gentle
surface changes); **fast** = wheel movements from terrain (bumps, kerbs, jumps, vibration).
Bump is usually set lower than rebound (the spring already resists compression).

- **Slow bump** ↑ → slows body movement for control; too high feels unresponsive and "pumps".
- **Slow rebound** ↑ → controls body motion/stability after inputs; too high stops the
  suspension extending fast enough to keep grip.
- **Fast bump** ↑ → calms compression over bumps; too high makes hits harsh and the car skip.
- **Fast rebound** ↑ → controls wheel oscillation after bumps; firmer on smooth ground but
  reduces ground-contact time on rough surfaces.

`[All]` **Bump/Rebound transition** — the blend point (in m/s of *suspension* speed, not car
speed) between slow and fast damping; it's a gradient, not an on/off switch. Higher transition
keeps more high-speed damping engaged → more stability but **more tyre-contact loss** on rough
ground.

Practical:
- `[All]` Exit understeer → stiffen **rear slow bump** (slows the rearward weight transfer so
  the nose doesn't lift/unload). Exit oversteer → soften **rear slow bump** (let the rear squat
  and load up). (Diff lock and throttle also drive exit balance — account for them.)
- `[All]` Floaty car / tyre-contact loss on bumpy stages → **reduce rebound** (and overall
  damping) so the wheel snaps back onto the surface. Remember: every stability gain costs some
  ground contact.

### Axles — anti-roll bars (ARB) `[All]`

An ARB ties the two wheels on an axle and twists to resist body roll. Stiffer reduces roll and
keeps camber but increases lateral load transfer (less grip on that axle). Stiffer **front** →
understeer; stiffer **rear** → oversteer. On loose/rough surfaces keep ARBs **soft** so each
wheel can follow the terrain independently (more contact, more traction); too stiff there makes
the car skippy. Tune ARBs **last**, for fine rotation, after springs/dampers are settled.

### Differential (LSD)

ACR uses a **ramp** system. `[All]` **Lower ramp angle = more lock** — so a **30°** ramp locks
more than a **45°** ramp; the lower number is the more aggressive/locked setting. The **power
ramp** acts under acceleration (exit), the **coast ramp** under deceleration/lift (entry). More
lock = more traction and stability but less turn-in (it forces both wheels toward the same
speed); more open = better cornering but less drive on low grip. **Preload** = a baseline lock
present before any wheel-speed difference (proactive traction on loose patches). **Plates** scale
the locking strength (more plates = stronger lock).

`[RWD/AWD]` **On-power lock vs. rotation flips with grip regime — don't apply one rule blind.**
- **On grip (tarmac, good traction):** more rear power lock ties the wheels into one unit and
  raises total rear thrust, so it's easier to break the whole rear loose → **more lock = more
  power-oversteer / snap**; less lock = calmer, more controllable power delivery. This is the
  regime the in-game **Plates** description and the RWD note below speak to.
- **At or beyond the limit (low grip — snow/ice, drifting, throttle modulation past peak grip):**
  the wheels are already slipping, so locking them ties them into one **predictable, catchable**
  slide; an **open** diff lets one rear wheel spin/grip independently of the other, which is what
  makes the rear feel loose and prone to swinging past the front. Here → **more lock = more
  stability**, less lock = more freedom/unpredictability. Don't reach for "less lock" just because
  the rear feels too free — check which regime you're in first.

**Preload vs. power ramp — match the lever to the throttle regime.** Preload is the lock present
at **low/zero torque**, so it governs **throttle transitions, on/off modulation, trailing
throttle, and proactive traction on loose patches**; the power ramp governs **sustained
acceleration**. A rear that wanders or steps out **during drift-style throttle modulation on loose
surfaces** is a **preload** problem first — raise preload before touching the power ramp. A rear
that only breaks loose under **hard, sustained** power is a power-ramp problem. If it's unclear
from the driver's description which regime applies, **ask** (modulating through a slide on snow,
or a sudden snap when the throttle is pinned on grippy tarmac?) rather than guessing a lock
direction — the correct move is opposite in each case.

**Diagnostic — "rear swings around / overtakes the front on throttle":**
- Drift-style / low grip, happens while **modulating** throttle → **raise preload** first; if
  still loose under power, **add lock** (lower the power-ramp angle). Do **not** reduce lock —
  that adds the freedom that caused the swing.
- High grip, the rear **snaps** when it suddenly bites under **hard** power → **reduce lock**
  (raise the power-ramp angle) — the opposite move.
- If the report doesn't make the regime clear, ask before recommending a direction.

Drivetrain:
- `[RWD]` a locked rear on power, **on grip** → spin/oversteer; tune power ramp/preload for
  traction vs snap. **On low grip**, more lock instead steadies a loose/wandering rear — see the
  grip-regime note above.
- `[FWD]` a heavily locked **front** diff → understeer, but it's safe to lock for traction.
- `[AWD]` the **centre diff** splits torque front/rear: rearward bias → more rotation / less
  understeer, forward → stability. Keep the **front diff** freer for rotation; tune the **rear**
  ramp/preload for desired kick-out. (Differential ratio, where adjustable, shifts torque bias
  and final drive — compensate top speed via the gearbox.)

### Wheels — alignment `[All]`

**Camber** (negative) — compensates tyre deformation so the loaded **outer** tyre keeps a full
contact patch mid-corner. Run **more camber at the front** than the rear (the front also steers,
and carries the engine on front-engined cars); too much hurts straight-line and braking grip and
overheats the inner edge. Use **more camber on twisty stages**, less on fast/straight ones.

**Toe** — front **toe-out** sharpens turn-in and helps the fronts roll into the corner when
sideways; front toe-in adds straight-line stability but resists turning (understeer). Rear
**toe-in** stabilises the exit and stops the rear getting squirrelly under power (especially
`[RWD]`); rear toe-out adds rotation/oversteer. **Don't overdo toe** — it scrubs and slows the
car. Rally default: **front toe-out + rear toe-in**.

### Brakes `[All]`

**Front bias** — forward bias makes the front lock first → understeer (predictable, planted
under braking); rearward bias makes the rear lock → rotation/oversteer (and a spin if too far).
Keep front bias **≥ ~55%** so the rear doesn't step out under braking; a front-heavy car can
take more front bias. Trail-braking naturally migrates the balance rearward through the corner.

**Hardware** (where adjustable) — softer **pads** bite more; the **master-cylinder** value is
*inverse* to braking power (higher value → less line pressure → less power). If the car locks
too easily even at the right bias, fit **smaller discs / weaker pads** (front and rear equally)
to cut total braking force rather than relying on ABS — you keep more feel and control.

**Handbrake force** — rear wheels only; used to rotate the car (hairpins, tight turns). If it's
an on/off button with no modulation, **lower the force** so it doesn't spin you on every pull.

### Electronics & engine

`[All]` **ABS / TCS** — driver aids that prevent lockup / wheelspin. They reduce feel and
control, so prefer mechanical fixes (diff, toe, brake hardware) first; using them is fine if the
car came with them. **ABS** especially removes braking feel.

**Engine map** — a more aggressive map raises revs and delivers torque sooner: `[RWD]` more
nervous, `[FWD]` more stable. `[RWD]` on very low grip, a **softer map + longer gears** keeps
the rear from spinning up and constantly triggering TCS.

**Throttle map** — shapes pedal response (direct vs progressive); mostly a feel/comfort aid,
and interacts with your pedal hardware curves. Don't over-tune it.

## Surface guidance (starting bias)

- **Tarmac** `[All]`: **low and stiff**, roll-controlled; higher tyre pressure; more camber;
  brake bias forward; more power-lock for drive; minimise unnecessary sliding. Precision pays —
  small changes are felt.
- **Gravel** `[All]`: **high ride height**, soft springs/ARBs (soft front, medium-stiff rear is
  a common base), front toe-out, lower pressure, lots of travel; an **active rear diff** (more
  power lock, medium coast) with a freer front. The car should "breathe" over the surface.
- **Snow / ice** `[All]`: **very high ride height**, **very soft** ARBs both ends, soft
  dampers, lowest grip — set the car up to *survive*: more **coast lock + preload**, near-neutral
  brake bias, gentle inputs; more camber for corner traction. Studded/winter tyres are essential.
- **Bumpy surfaces (any)** `[All]`: prioritise compliance and ground contact — softer springs,
  less rebound, softer ARBs, enough ride height not to bottom — to avoid a floaty car.

> **Aero note** `[All]`: aerodynamic downforce is **negligible** in ACR at rally speeds. Set
> ride height and rake for **mechanical** reasons (CoG, weight transfer, travel, clearance), not
> for downforce.

## In-game parameter definitions (authoritative game text)

The authoritative, **verbatim** in-game descriptions of **every tunable parameter** now live in
[parameter-reference-template.md](parameter-reference-template.md) — a single source of truth that
also **seeds the user's Notion `Parameter reference` page** (see `notion-structure.md`). When you
need the exact game wording for a parameter (e.g. to quote or paraphrase what a setting does, or to
check a direction / sign convention such as toe or LSD ramp), read that file.

The notes below are **skill reasoning that extends the game text**; they stay here in the reasoning
base (the verbatim page above is user-facing and deliberately omits them).

### Master Cylinder
Cylinder diameter has **two combined effects**, so treat it as a modulation/feel lever, not a
one-way "power" knob. A **smaller** cylinder gains more leverage (it can build higher line pressure
for a given pedal force) **and** spreads a given pressure rise over **more pedal travel** — which
gives **finer modulation** and a more progressive ramp, so the brakes are less likely to snatch into
an early lock. A **larger** cylinder does the opposite: it packs the pressure range into a shorter,
twitchier bit of travel. So on loose / low-grip surfaces where locking early is the problem, the
usual answer is a **smaller** cylinder for controllable, progressive braking; a larger cylinder can
suit high-grip tarmac where you want a shorter, firmer pedal. Move front and rear together to keep
brake bias put. **A car-specific troubleshooting file, where one exists, takes precedence over this
general guidance** for the concrete symptom it names (see `car-troubleshooting/`).

### Discs / Calipers
**Caliper is the higher-impact lever — choose it first.** Piston area has a large effect on brake
force (e.g. a 4-piston vs a 2-piston caliper changes the achievable braking sharply), so pick the
caliper that best suits the braking demand for the surface and intent, then choose the disc size for
brake torque / cooling / modulation. Because the game gates the **available** calipers by the
**selected disc**, the disc+caliper pair you recommend may not be co-selectable in-game. When that
happens, **keep the recommended caliper and use the closest available disc size** — the caliper
carries the bigger braking effect, so it's the one to preserve.

## Sources & version caveats

Synthesised from the in-game setup descriptions and community guides (several YouTube tuning
tutorials covering springs/dampers/ARBs, differentials, and full-car ACR/WRC walkthroughs) plus
written guides: Sportskeeda (tyre-choice and per-stage setups), OverTake (Monte-Carlo snow
tips), and BoxThisLap (v0.4 Impreza setup). Advice was filtered for physical soundness;
single-creator opinions and non-handling tips were dropped.

**Build-dependent — re-confirm after ACR updates:** compound **behaviour**, the tyre
**heating/pressure** model, and **bump/rebound transition** behaviour. ACR is in early access and
its tyre/physics model is still changing.
