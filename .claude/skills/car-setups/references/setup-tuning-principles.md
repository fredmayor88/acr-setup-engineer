# Car setup tuning principles (base layer)

The reasoning base for `build-setup`. These are **physics effects and consensus heuristics**
for Assetto Corsa Rally (ACR), independent of any specific car — only the legal *ranges*
differ per car (those come from the `Parameters` catalog). Synthesised from the in-game
descriptions and several community tuning guides, critically filtered for physical soundness.

## How this fits together (layers & precedence)

This file is the **shipped base**. The user's own preferences live in **Notion** and
**override** this file. When `build-setup` reasons about a setup, it combines, in increasing
priority (later wins on conflict):

1. **Base principles** (this file)
2. **Global user guidelines** (Notion: `Car setups / {Game} / Tuning guidelines`)
3. **Surface section** of those guidelines matching the stage's surface
4. **Per-car guidelines** (the car page's "Guidelines" section)
5. **Stage description / driving style** (most specific — the actual stage)

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
| More on-power traction `[RWD/AWD]` | — | more LSD lock (lower power-ramp angle / more plates / more preload) |
| More on-power rotation `[RWD/AWD]` | — | less LSD lock |
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
ACR offers 10 compounds (see the verbatim in-game text under *In-game parameter definitions →
Tyres*). Pick the **surface** first (Tarmac vs Gravel vs Snow), then the **compound/condition**:

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
rear). Higher pressure → smaller contact patch (front high pressure adds understeer). Run low
in general, balance by feel. *(Build caveat: if a build doesn't model tyre heating, the tyre
won't reach its optimal hot pressure — start a few psi higher and revisit after updates.)*

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

ACR uses a **ramp** system. `[All]` **Lower ramp angle = more lock.** The **power ramp** acts
under acceleration (exit), the **coast ramp** under deceleration/lift (entry). More lock = more
traction and stability but less turn-in (it forces both wheels toward the same speed); more
open = better cornering but less drive on low grip. **Preload** = a baseline lock present before
any wheel-speed difference (proactive traction on loose patches). **Plates** scale the locking
strength (more plates = stronger lock).

Drivetrain:
- `[RWD]` a locked rear on power → spin/oversteer; tune power ramp/preload for traction vs snap.
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

The following descriptions are copied verbatim from the ACR in-game setup UI. They are the
authoritative definitions of what each parameter does in the game engine.

### Gearbox

#### Gear Set

Each gearset consists of a pair of gearbox shafts (and, if available, a drop gear) equipped with fixed gears.

When selecting the ideal gearset for a rally stage, consider that closer lower ratios can provide better acceleration on high-traction surfaces, while wider lower ratios may be preferable on loose or slippery terrain to increase wheel torque and maintain control.

Increasing the gear set value selects wider lower ratios. Decreasing the value selects closer lower ratios.

Choose the configuration that best matches the stage conditions to optimize performance.

Different Gear set may have a different number of Gears.

#### Primary Gear

Higher gear ratios in a car are designed to improve acceleration, allowing the vehicle to reach top speeds more quickly from a standstill. By favoring quicker engine revving and faster power delivery, these ratios provide an advantage during rapid changes in pace, such as tight corners or technical sections.

However, this comes with trade-offs. While acceleration is enhanced, the car's top speed is reduced, limiting its maximum velocity on straights. Moreover, higher ratios can negatively affect traction, as increased torque at the wheels may lead to wheel spin, especially on loose or slippery surfaces.

### Suspension

#### Adjuster Ring

The ride height is adjusted using an adjuster ring that shifts the spring perch up or down, raising or lowering the car. Changing the spring seat alters the chassis height and static corner weights, but it also affects the damper's working point.

Increasing the Adjuster Ring value will raise the ride height of the car up, helping to prevent the car from bottoming out but can make the car feel softer and less responsive in turns. Decreasing the value will drop the ride height, making the cars handling feel more responsive to driver inputs, but increasing the chance of bottoming out on rougher terrain.

After changing ride height you must check damper travel and spring compression to ensure there's still sufficient bump and rebound range and no bottoming or topping out. Re-verify bump stops, ride frequency and alignment settings, and make further adjustments to spring preload or damping as needed so the suspension operates safely and effectively across rally terrain.

#### Spring Stiffness

The Main Spring determines the natural frequency of a car's suspension system, impacting how the car responds to driver input and absorbtion of bumps from the terrain. It also affects wheel droop, reducing rebound if too stiff, causing frequent loss of wheel contact and spring oscillations that may damage the suspension.

This is where Helper Springs and Rebound Stops become crucial, preventing damage by managing suspension travel.

Generally, a higher rear spring frequency is preferred to help the rear wheels better synchronize with the front wheels over bumps, improving stability.

Increasing front spring stiffness tends to increase understeer, while softer front springs promote oversteer. The opposite happens for the rear, where increasing rear springs tends to increase oversteer, while softer rear springs brings the rears balance back towards understeer. Tune the two to find yours and the car's ideal handling balance.

### Dampers

#### Slow Bump

Slow bump damping controls the low-speed resistance of the damper shaft during suspension compression, in response to driver inputs.

Increasing slow bump damping strengthens the force opposing wheel bump, helping to slow down body movements for better control.

However, too high a setting can make the car feel less responsive to input, slowing the rate at which tyres load up in grip. It can also cause a pumping effect, where the suspension appears underdamped but is actually overdamped, relying mainly on tyre sidewall flex with minimal damping.

Typically, bump damping is set lower than rebound damping since the spring also resists compression. In softer springs, slightly higher bump damping can help reduce load transfer.

#### Slow Rebound

Slow rebound damping regulates the low-speed resistance of the damper shaft against the wheel's downward movement, extension, or droop, caused by driver inputs.

Increasing this setting raises the force opposing suspension extension, which helps control body movements by slowing them down, resulting in improved stability and handling.

However, higher slow rebound damping can also prevent the suspension from extending quickly enough to maintain tyre grip in response to driver input.

#### Fast Bump

Fast bump damping controls the resistance force on the damper shaft during rapid suspension compression, in response to suspension movement caused by the terrain.

Increasing this setting slows down the suspensions compression by adding more resistance, reducing oscillations and improving control.

However, too high a fast bump setting can cause a pumping effect, where the suspension feels underdamped despite being overdamped, resulting in most compression being absorbed by the tyre sidewall, which offers minimal damping. It can also amplify the feeling of larger bumps on rougher terrain, by not allowing the suspension to compress quickly enough to absorb the impact.

Typically, bump damping is set lower than rebound damping because the spring force also opposes compression.

#### Fast Rebound

Fast rebound damping controls the high-speed resistance of the damper shaft during extension and wheel droop, in response to suspension movement caused by the terrain.

Increasing this setting raises the force opposing suspension extension, which helps to slow down and better control wheel oscillations. This creates a firmer response, improving stability on smoother terrain, but can in turn reduce the wheel's contact time with the ground, potentially impacting grip on rougher surfaces.

### Axles

#### Anti-Roll Bar Stiffness

Anti-roll bars connect the wheels on the same axle to reduce body roll during cornering.

While this decreases roll and helps maintain better camber angles, it also increases load transfer between the tyres, which can reduce the overall grip of that axle.

Raising the anti-roll bar stiffness at the front generally moves the bias towards understeer. Increasing it at the rear tends to cause oversteer by allowing the rear to rotate more in the mid corner.

In rally cars, especially on loose surfaces with long suspension travel, it's important to balance anti-roll bar settings. Too much stiffness causes excessive load transfer and tyre grip saturation, while too little roll can lead to poor camber control.

### Wheels

#### Pressure

Adjust tyre pressures to maintain the optimal contact patch and working temperature of the tyres.

Increasing tyre pressures increases the stiffness of the tyres sidewall, decreasing the amount of heat produced in the tyre preventing and/or reducing overheating. It does, however, also reduce the tyres contact patch with the road surface, which can decrease grip.

Reducing tyre pressure increases the tyres contact patch and improves grip, but it does also increase rolling resistance. Lower tyre pressures also allow the tyre to move around and flex more, raising tyre temperatures, but it can increase the risk of the tyre coming off the rim.

Try balancing tyre pressure to keep, for as long as possible, the tyres in their ideal temperature window for maximum grip and durability.

#### Camber

When viewed from the front, wheels have negative camber if the tops of the tyre tilt inward toward the centre of the car, and positive camber if they tilt outward.

Negative camber improves grip and tyre responsiveness, allowing the outer wheel during a corner maintain a better tyre contact patch.

However, too much negative camber reduces the contact patch on straights and concentrates stress on the inner edge, which can decrease acceleration and braking performance. It can also lead to situations, especially when the car is stiffer and has less roll, where the full width of the tyre isn't used in a corner leading to a reduction in peak cornering grip.

It's important to monitor tyre temperatures, ensuring the difference between the inner and outer edges doesn't exceed 20°C to maintain balanced grip and tyre life.

#### Toe

In the top-down/birds-eye view, car wheels are Toe In if angled inward towards the centre of the car and Toe Out if angled outward.

Front Toe In boosts straight-line stability by keeping the car steady, while Front Toe Out reduces Camber Thrust effects, sharpening turn-in and responsiveness of the car.

Rear Toe In enhances cornering stability by creating lateral force and improving grip, whereas Rear Toe Out reduces stability, allowing more rotation leading to an increase in oversteer.

Rally setups often use slight Front Toe Out for better responsiveness and Rear Toe In for balanced cornering stability. Toe settings balance stability and agility based on driving needs.

#### Tyre Type

The compound descriptions below are copied verbatim from the ACR SELECT TYRE screens. **Soft / Medium / Hard describe the rubber compound and the text is identical for the Tarmac and Gravel variants** (e.g. "Tarmac Soft" and "Gravel Soft" share the Soft text); the remaining tyres are condition-specific.

**Soft** (Tarmac Soft / Gravel Soft):

SOFT tyres offer superior grip due to their more pliable rubber, making it suitable for loose surfaces, gravel or cold/mild tarmac.

In these conditions, the SOFT compound provides better cornering grip, shorter braking zones, and better traction off corners compared to harder compounds.

However, they wear out faster than the harder compounds and are easier to overheat, especially on hot or abrasive roads.

SOFT tyres are best for short, technical stages or cooler conditions where grip is prioritized over durability.

**Medium** (Tarmac Medium / Gravel Medium):

MEDIUM tyres are a jack of all trades, capable of performing across a wide range of scenarios. The medium compound provides good amounts of cornering grip and traction off corners, and has a moderate amount of durability.

They won't have quite as much bite as a soft tyre but will provide more grip than a hard. They perform better over longer distances than a soft, but wear out faster than a hard compound.

MEDIUM tyres are best for moderate length stages, fast flowing sections, and rally legs where you'll tackle multiple stages before being able to change tyres.

**Hard** (Tarmac Hard / Gravel Hard):

HARD tyres are the ultimate durability tyre compound, ideal for longer and multiple stages in a row.

Grip levels are lower than the two softer compounds, however it is better suited for hotter conditions and faster or more abrasive surfaces.

This tyre will struggle for grip in lower and cooler temperatures.

HARD tyres are best for long stages, hot conditions, or rally legs featuring multiple moderate to long length stages before being able to change tyres.

**Tarmac Wet (Rain):**

RAIN tyres are the choice to go for in wet conditions.

They feature more heavily tread blocks to disperse water from underneath the tyre, better maintaining contact between the tyre and road surface when it is wet providing more grip.

The compound is generally very soft, allowing it to generate heat quicker than a dry tyre and maintain grip in the cooler wet conditions.

This does however mean that a rain tyre will overheat easily if the surface is dry or abrasive, causing grip levels to drop sharply and rapidly increase tyre wear.

RAIN tyres should only be used when wet conditions are forecasted, or there are more wet stages than dry in the next rally leg.

**Tarmac Winter:**

TARMAC WINTER tyres are a bespoke tyre compound suited for the variable conditions that the rallies like Monte-Carlo can produce.

Its foundation is a very soft compound, that is designed to work across conditions from very cold but dry, through to wet and into snowy conditions. Due to it's soft compound, it may start to overheat and wear quicker if the majority of the stage is dry tarmac.

The TARMAC WINTER tyres are therefore best used when conditions are wet, or there is significant sections of the road covered in snow at some of the higher elevations on the Monte-Carlo stages.

**Tarmac Snow:**

TARMAC SNOW tyres are a more extreme version of the winter tyre, featuring 2 millimeters metal studs protruding from the rubber.

These provide great traction in very snowy and icey conditions, with the metal studs digging into the surface to provide more grip.

They however wear extremely quickly on exposed tarmac, as the studs grind down and break away on the solid surface.

The TARMAC SNOW tyres is therefore only to be used on stages that are covered in compact snow and ice, with little exposed tarmac.

**Snow (Studs):**

SNOW tyres are specific tyres designed for snowy stages, such as those of the Swedish rally.

Their narrow design and 7 millimeters studs allow the tyre to carve through the snow at higher speeds, whilst providing good amounts of grip whilst braking and cornering.

Their built to work in extremely cold temperatures, and will therefore overheat and wear very quickly on tarmac and conditions above freezing.

SNOW tyres are only available on full snow rally stages.

### Brakes

#### Front Bias

In a car equipped with two master cylinders, the brake pressure distribution can be adjusted by manipulating a lever that controls the pressure bias ratio between the front and rear brakes.

This system allows for fine-tuning the braking performance based on driving conditions and surface grip.

Shifting the Brake Bias forwards can make the car behave more predictably, biasing the car towards understeer during braking. Shifting the bias rearwards will allow for more rotation and oversteer during braking, but can make the car more difficult to control.

Find the right balance for your own driving preference and surface type you're driving on.

It's important to note that this pressure bias setting does not directly translate to the final brake torque at each wheel. Variations such as brake caliper efficiency, brake disc size, and tyre grip can all influence the actual torque applied. Therefore, always verify the final brake torque distribution on the wheels to ensure optimal balance and performance.

### Differentials

#### Differential Ratio

You may adjust one or both axle differential ratios; even differently one from the other. Setting a higher ratio at the front shifts more torque to the front wheels, enhancing front torque bias and vice versa.

However, this also raises the overall final drive ratio, which reduces top speed but improves acceleration. To maintain the original final drive effect, you can compensate by adjusting the gearbox final ratio in the opposite direction.

This asymmetric setup not only changes torque distribution but also preloads the center differential, allowing it to respond more quickly to differences in wheel slip between axles, improving traction and handling in rally conditions.

#### LSD Power/Coast Ramp

The Ramp Angle of a Limited Slip Differential (LSD) controls how much input torque clamps the two output shafts together. The Power side angle (left value) affects clamping under acceleration, while the Coast side angle (right value) affects it under deceleration.

Lower angles increase clamping force and traction but reduce speed difference and steering agility.

Higher angles improve steering but allow more slippage or less stability. The Locking Effect (LE) shows the percentage of torque clamping the shafts, higher LE means stronger lock. Front LSDs typically have higher angles for better steering.

Remember that brakes don't influence Coast side locking since LSD responds to engine torque.

#### LSD Preload

The Limited Slip Differential (LSD) preload is the initial torque resistance that must be overcome for any speed difference to occur between the two driven wheels on the same axle.

Until this torque threshold is exceeded, both wheels rotate at the same speed, similar to a locked axle. At low lateral accelerations, this preload causes slower corner entry, reduced steering response, and some understeer. However, under high lateral load transfer, it improves traction and stability.

Preload is especially important on loose surfaces, providing needed traction before the differential fully locks. Front differentials typically require less preload to preserve steering feel.

#### Plates Number

A limited-slip differential (LSD) in a rally car uses friction plates to control torque distribution between the wheels. The number of friction plates in contact directly affects the locking force of the differential, influencing wheel slip in both coast and on-power situations.

Increasing the number of plates amplifies the locking effect, making the LSD more aggressive by transmitting more torque to the wheel with better traction. This can shift the bias towards more stability through more understeer when coasting, but more oversteer when on power.

Reducing the number of plates reduces the locking effect, allowing for freer wheel rotation. This shifts the bias towards more freer rotation and better cornering during coast, but more understeer when on power.

This adjustability enables fine-tuning of the LSD to match driving style and conditions, enhancing traction and vehicle control within various scenarios.

## Sources & version caveats

Synthesised from the in-game setup descriptions and community guides (several YouTube tuning
tutorials covering springs/dampers/ARBs, differentials, and full-car ACR/WRC walkthroughs) plus
written guides: Sportskeeda (tyre-choice and per-stage setups), OverTake (Monte-Carlo snow
tips), and BoxThisLap (v0.4 Impreza setup). Advice was filtered for physical soundness;
single-creator opinions and non-handling tips were dropped.

**Build-dependent — re-confirm after ACR updates:** compound **behaviour**, the tyre
**heating/pressure** model, and **bump/rebound transition** behaviour. ACR is in early access and
its tyre/physics model is still changing.
