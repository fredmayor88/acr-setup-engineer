# Parameter reference template (seed for the Notion page)

This is the seed used to create the **global** `Parameter reference` page in Notion
(`Car setups / {Game} / Parameter reference`). It lists and describes **every tunable parameter
available in the game**, using the authoritative in-game text, so the user can read what each
setting does on their phone without opening the game or returning to the tuning menu.

Unlike the `Tuning guidelines` page (which is the user's own editable preferences), this page is
**auto-maintained**: the skill re-seeds it from this file on updates, so its game text stays
current. It is therefore **read-only** for the user — see the banner in the body.

> When seeding the Notion page, copy everything below the line. It's the authoritative game text
> plus a short read-only banner; keep both. On a refresh, replace the page body with the current
> version of everything below the line.

---

# 🔧 Parameter reference

> **Read-only — auto-maintained by the car-setups skill.** This page lists every tunable
> parameter in the game with its authoritative in-game description. The skill **refreshes this
> page on updates**, so **don't add personal notes here — they will be overwritten**. Put your own
> tuning preferences on the **`Tuning guidelines`** page instead (that one is yours to edit).

The following descriptions are copied verbatim from the ACR in-game setup UI. They are the
authoritative definitions of what each parameter does in the game engine.

## Gearbox

### Gear Set

Each gearset consists of a pair of gearbox shafts (and, if available, a drop gear) equipped with fixed gears.

When selecting the ideal gearset for a rally stage, consider that closer lower ratios can provide better acceleration on high-traction surfaces, while wider lower ratios may be preferable on loose or slippery terrain to increase wheel torque and maintain control.

Increasing the gear set value selects wider lower ratios. Decreasing the value selects closer lower ratios.

Choose the configuration that best matches the stage conditions to optimize performance.

Different Gear set may have a different number of Gears.

### Primary Gear

Higher gear ratios in a car are designed to improve acceleration, allowing the vehicle to reach top speeds more quickly from a standstill. By favoring quicker engine revving and faster power delivery, these ratios provide an advantage during rapid changes in pace, such as tight corners or technical sections.

However, this comes with trade-offs. While acceleration is enhanced, the car's top speed is reduced, limiting its maximum velocity on straights. Moreover, higher ratios can negatively affect traction, as increased torque at the wheels may lead to wheel spin, especially on loose or slippery surfaces.

## Suspension

### Adjuster Ring

The ride height is adjusted using an adjuster ring that shifts the spring perch up or down, raising or lowering the car. Changing the spring seat alters the chassis height and static corner weights, but it also affects the damper's working point.

Increasing the Adjuster Ring value will raise the ride height of the car up, helping to prevent the car from bottoming out but can make the car feel softer and less responsive in turns. Decreasing the value will drop the ride height, making the cars handling feel more responsive to driver inputs, but increasing the chance of bottoming out on rougher terrain.

After changing ride height you must check damper travel and spring compression to ensure there's still sufficient bump and rebound range and no bottoming or topping out. Re-verify bump stops, ride frequency and alignment settings, and make further adjustments to spring preload or damping as needed so the suspension operates safely and effectively across rally terrain.

### Spring Stiffness

The Main Spring determines the natural frequency of a car's suspension system, impacting how the car responds to driver input and absorbtion of bumps from the terrain. It also affects wheel droop, reducing rebound if too stiff, causing frequent loss of wheel contact and spring oscillations that may damage the suspension.

This is where Helper Springs and Rebound Stops become crucial, preventing damage by managing suspension travel.

Generally, a higher rear spring frequency is preferred to help the rear wheels better synchronize with the front wheels over bumps, improving stability.

Increasing front spring stiffness tends to increase understeer, while softer front springs promote oversteer. The opposite happens for the rear, where increasing rear springs tends to increase oversteer, while softer rear springs brings the rears balance back towards understeer. Tune the two to find yours and the car's ideal handling balance.

## Dampers

### Slow Bump

Slow bump damping controls the low-speed resistance of the damper shaft during suspension compression, in response to driver inputs.

Increasing slow bump damping strengthens the force opposing wheel bump, helping to slow down body movements for better control.

However, too high a setting can make the car feel less responsive to input, slowing the rate at which tyres load up in grip. It can also cause a pumping effect, where the suspension appears underdamped but is actually overdamped, relying mainly on tyre sidewall flex with minimal damping.

Typically, bump damping is set lower than rebound damping since the spring also resists compression. In softer springs, slightly higher bump damping can help reduce load transfer.

### Slow Rebound

Slow rebound damping regulates the low-speed resistance of the damper shaft against the wheel's downward movement, extension, or droop, caused by driver inputs.

Increasing this setting raises the force opposing suspension extension, which helps control body movements by slowing them down, resulting in improved stability and handling.

However, higher slow rebound damping can also prevent the suspension from extending quickly enough to maintain tyre grip in response to driver input.

### Fast Bump

Fast bump damping controls the resistance force on the damper shaft during rapid suspension compression, in response to suspension movement caused by the terrain.

Increasing this setting slows down the suspensions compression by adding more resistance, reducing oscillations and improving control.

However, too high a fast bump setting can cause a pumping effect, where the suspension feels underdamped despite being overdamped, resulting in most compression being absorbed by the tyre sidewall, which offers minimal damping. It can also amplify the feeling of larger bumps on rougher terrain, by not allowing the suspension to compress quickly enough to absorb the impact.

Typically, bump damping is set lower than rebound damping because the spring force also opposes compression.

### Fast Rebound

Fast rebound damping controls the high-speed resistance of the damper shaft during extension and wheel droop, in response to suspension movement caused by the terrain.

Increasing this setting raises the force opposing suspension extension, which helps to slow down and better control wheel oscillations. This creates a firmer response, improving stability on smoother terrain, but can in turn reduce the wheel's contact time with the ground, potentially impacting grip on rougher surfaces.

### Bump Transition

The Bump Threshold Speed in a car's suspension is adjusted using the Fast Bump preload via a simple screw. This adjustment controls when the piston holes fully open, transitioning the damper to its softer setting.

Increasing the Bump Transition delays the opening, making the suspension maintain higher damping during rapid vibrations, improving stability but potentially increasing tyre contact losses.

Decreasing the Bump Transition value allows the opening to free up sooner, causing the softer damping phase to activate sooner, reducing the force applied during normal body movements.
While this can enhance comfort, it may also lead to unwanted vehicle oscillations, affecting overall handling and control.

### Rebound Transition

The Rebound Transition in a car suspension is adjusted using the Fast Rebound preload, controlled by a simple screw.

This mechanism either anticipates or delays the full opening of the piston holes, which sets the damper to its soft rebound rate.

Increasing the Rebound Transition value will delay the opening, maintaining higher damping during fast vibrations, improving stability but potentially increasing tyre contact losses.

Lowering the Rebound Transition value will anticipate the opening, reducing damping force earlier during rebound, which can lead to less control over body movements through unwanted oscillations, but is better suited to rougher and bumpier surfaces.

## Axles

### Anti-Roll Bar Stiffness

Anti-roll bars connect the wheels on the same axle to reduce body roll during cornering.

While this decreases roll and helps maintain better camber angles, it also increases load transfer between the tyres, which can reduce the overall grip of that axle.

Raising the anti-roll bar stiffness at the front generally moves the bias towards understeer. Increasing it at the rear tends to cause oversteer by allowing the rear to rotate more in the mid corner.

In rally cars, especially on loose surfaces with long suspension travel, it's important to balance anti-roll bar settings. Too much stiffness causes excessive load transfer and tyre grip saturation, while too little roll can lead to poor camber control.

## Wheels

### Pressure

Adjust tyre pressures to maintain the optimal contact patch and working temperature of the tyres.

Increasing tyre pressures increases the stiffness of the tyres sidewall, decreasing the amount of heat produced in the tyre preventing and/or reducing overheating. It does, however, also reduce the tyres contact patch with the road surface, which can decrease grip.

Reducing tyre pressure increases the tyres contact patch and improves grip, but it does also increase rolling resistance. Lower tyre pressures also allow the tyre to move around and flex more, raising tyre temperatures, but it can increase the risk of the tyre coming off the rim.

Try balancing tyre pressure to keep, for as long as possible, the tyres in their ideal temperature window for maximum grip and durability.

### Camber

When viewed from the front, wheels have negative camber if the tops of the tyre tilt inward toward the centre of the car, and positive camber if they tilt outward.

Negative camber improves grip and tyre responsiveness, allowing the outer wheel during a corner maintain a better tyre contact patch.

However, too much negative camber reduces the contact patch on straights and concentrates stress on the inner edge, which can decrease acceleration and braking performance. It can also lead to situations, especially when the car is stiffer and has less roll, where the full width of the tyre isn't used in a corner leading to a reduction in peak cornering grip.

It's important to monitor tyre temperatures, ensuring the difference between the inner and outer edges doesn't exceed 20°C to maintain balanced grip and tyre life.

### Toe

In the top-down/birds-eye view, car wheels are Toe In if angled inward towards the centre of the car and Toe Out if angled outward.

Front Toe In boosts straight-line stability by keeping the car steady, while Front Toe Out reduces Camber Thrust effects, sharpening turn-in and responsiveness of the car.

Rear Toe In enhances cornering stability by creating lateral force and improving grip, whereas Rear Toe Out reduces stability, allowing more rotation leading to an increase in oversteer.

Rally setups often use slight Front Toe Out for better responsiveness and Rear Toe In for balanced cornering stability. Toe settings balance stability and agility based on driving needs.

**Sign convention in ACR:** negative values = toe-out; positive values = toe-in.

### Tyre Type

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

## Brakes

### Front Bias

In a car equipped with two master cylinders, the brake pressure distribution can be adjusted by manipulating a lever that controls the pressure bias ratio between the front and rear brakes.

This system allows for fine-tuning the braking performance based on driving conditions and surface grip.

Shifting the Brake Bias forwards can make the car behave more predictably, biasing the car towards understeer during braking. Shifting the bias rearwards will allow for more rotation and oversteer during braking, but can make the car more difficult to control.

Find the right balance for your own driving preference and surface type you're driving on.

It's important to note that this pressure bias setting does not directly translate to the final brake torque at each wheel. Variations such as brake caliper efficiency, brake disc size, and tyre grip can all influence the actual torque applied. Therefore, always verify the final brake torque distribution on the wheels to ensure optimal balance and performance.

### Master Cylinder (templates also call it "Front Cylinder" / "Rear Cylinder")

The Master Cylinder converts the driver's foot force into hydraulic pressure for the braking system.

In rally cars, it can come as a single unit with two internal cylinders for the front and rear axles. This design limits direct adjustment of brake bias, but bias can be indirectly influenced by altering the diameters of these cylinders.

Alternatively, some setups use two separate Master Cylinders, one for each axle. This allows for direct brake bias control through a lever mechanism, which adjusts how much the brake pedal pushes on each cylinder, giving the driver fine-tuned braking balance between front and rear wheels.

### Proportioning Preload

Basic or stock brake systems typically offer limited adjustability, but they often include an adjustable Proportioning Valve to enhance brake balance. As the car decelerates, it requires increasing front brake bias for stability and control.
The Proportioning Valve achieves this by reducing the rear brake line pressure once a certain Preload pressure is reached. This reduction occurs according to a set Ratio, allowing fine-tuning of brake performance.

Adjusting the Preload pressure changes the point of the rear pressure cut. A higher Preload delays the cut, making rear braking more aggressive, while a lower Preload causes earlier cut, favoring front brake dominance.

### Proportioning Ratio

Basic or stock brake systems typically offer limited adjustability, but they can include an adjustable Proportioning Valve to enhance brake balance. As the car decelerates, it requires increasing front brake bias for stability and control.
The Proportioning Valve achieves this by reducing the rear brake line pressure once a certain Preload pressure is reached. This reduction occurs according to a set Ratio, allowing fine-tuning of brake performance.

Adjusting the ratio changes how much pressure is cut from the rear brakes: higher ratios decrease the pressure reduction, making the rear brakes more aggressive, while lower ratios increase pressure reduction for a more stable rear braking feel.

### Handbrake Force

The handbrake system can be finely tuned by adjusting or replacing components such as the handbrake calipers, brake pads, or the master cylinder pressure. With Handbrake Force, you are adjusting the whole system to increase or reduce its effect.

Increasing the Handbrake Force requires less pull on the handbrake to lock the wheels, even on smoother and grippier surfaces, making it easier to rotate the car with less modulation required.

Decreasing the Handbrake Force will require more pull on the handbrake to lock the wheels, reducing the cars desire to rotate as quickly or sharply when trying to engage or modulate the handbrake.

Tune based on the your preference and the amount of available grip.

### Discs (templates also call it "Brake Discs")

Modulating brake power becomes more difficult on low-grip surfaces, so choosing smaller brake discs can help by directly reducing the brake torque applied.

Brake discs are sorted by diameter and cooling efficiency, the larger the disc, the greater the potential brake torque and better cooling.

Smaller, non-vented discs tend to heat up more quickly than larger, highly vented ones, which is important to consider in your strategy.

Keep in mind that changing the discs will likely affect your brake bias as well.

### Calipers (templates also call it "Brake Calipers")

If a disc is compatible with multiple calipers, you'll see the available options sorted by piston area size.

A larger piston area generally means greater braking force and better cooling efficiency.

However, keep in mind that each caliper uses its own set of brake pad compounds, so the actual wheel torque may vary depending on the caliper chosen.

### Pads/Shoe (templates also call it "Brake Pads")

You can select from various compounds for your brake pads or shoes, each suited to different driving conditions.

For shorter rally stages, you might prefer softer pads with a strong initial bite and better stopping power. This does come at a cost though, with faster wear and increased chance of locking on loose surfaces.
For longer or low-grip stages, more highly durable compounds are generally better, as they last longer and maintain a more consistent performance.

Keep in mind that different pads or shoes can affect the brake bias at each wheel, so always check and adjust the bias accordingly to ensure optimal handling and safety.

## Differentials

### Differential Ratio

You may adjust one or both axle differential ratios; even differently one from the other. Setting a higher ratio at the front shifts more torque to the front wheels, enhancing front torque bias and vice versa.

However, this also raises the overall final drive ratio, which reduces top speed but improves acceleration. To maintain the original final drive effect, you can compensate by adjusting the gearbox final ratio in the opposite direction.

This asymmetric setup not only changes torque distribution but also preloads the center differential, allowing it to respond more quickly to differences in wheel slip between axles, improving traction and handling in rally conditions.

### Center Differential Ratio

In-game this field shows the generic gear-ratio text below (it reuses the *Primary Gear*
description). For the actual centre-diff torque-split behaviour, see *Center Ratio to Rear* below.
The in-game text reads:

Higher gear ratios in a car are designed to improve acceleration, allowing the vehicle to reach top speeds more quickly from a standstill. By favoring quicker engine revving and faster power delivery, these ratios provide an advantage during rapid changes in pace, such as tight corners or technical sections.

However, this comes with trade-offs. While acceleration is enhanced, the car's top speed is reduced, limiting its maximum velocity on straights. Moreover, higher ratios can negatively affect traction, as increased torque at the wheels may lead to wheel spin, especially on loose or slippery surfaces.

### Center Ratio to Rear

You can adjust the torque distribution to the rear differential by altering its ratio relative to the front differential.

Setting a higher ratio than the front shifts more torque to the rear, increasing rear bias.
However, this also raises the overall final drive ratio, which reduces top speed but improves acceleration. To maintain the original final drive ratio, you can compensate by adjusting the gearbox final ratio in the opposite direction.

This asymmetric setup not only changes the front-to-rear torque balance but can also preload the center differential, allowing it to respond quicker to differences in axle slip, enhancing traction and handling in rally conditions.

### LSD Power/Coast Ramp

The Ramp Angle of a Limited Slip Differential (LSD) controls how much input torque clamps the two output shafts together. The Power side angle (left value) affects clamping under acceleration, while the Coast side angle (right value) affects it under deceleration.

Lower angles increase clamping force and traction but reduce speed difference and steering agility.

Higher angles improve steering but allow more slippage or less stability. The Locking Effect (LE) shows the percentage of torque clamping the shafts, higher LE means stronger lock. Front LSDs typically have higher angles for better steering.

Remember that brakes don't influence Coast side locking since LSD responds to engine torque.

### LSD Preload

The Limited Slip Differential (LSD) preload is the initial torque resistance that must be overcome for any speed difference to occur between the two driven wheels on the same axle.

Until this torque threshold is exceeded, both wheels rotate at the same speed, similar to a locked axle. At low lateral accelerations, this preload causes slower corner entry, reduced steering response, and some understeer. However, under high lateral load transfer, it improves traction and stability.

Preload is especially important on loose surfaces, providing needed traction before the differential fully locks. Front differentials typically require less preload to preserve steering feel.

### Plates Number

A limited-slip differential (LSD) in a rally car uses friction plates to control torque distribution between the wheels. The number of friction plates in contact directly affects the locking force of the differential, influencing wheel slip in both coast and on-power situations.

Increasing the number of plates amplifies the locking effect, making the LSD more aggressive by transmitting more torque to the wheel with better traction. This can shift the bias towards more stability through more understeer when coasting, but more oversteer when on power.

Reducing the number of plates reduces the locking effect, allowing for freer wheel rotation. This shifts the bias towards more freer rotation and better cornering during coast, but more understeer when on power.

This adjustability enables fine-tuning of the LSD to match driving style and conditions, enhancing traction and vehicle control within various scenarios.

## Electronics & Aerodynamics

### ABS Map

The ABS (Anti-lock Braking System) is an active safety system that prevents the wheels from locking during sudden braking, thus avoiding skidding and loss of grip.

When the ABS detects locking, it acts cyclically (hundreds of times per second) temporarily reducing the brake pressure on the wheel about to lock. Once the wheel starts to rotate again, the brake pressure is restored.

When the ABS is deactivated (OFF) the control of the brake pressure is completely in the hands of the driver. As the ABS values increase, the system becomes more sensitive to the pressure, anticipating the wheel lock and optimizing the response.

The braking distance with the ABS active may be slightly longer than with a driver-controlled braking without locking the wheels. However, in the event of a wheel lock, stopping times are significantly longer without ABS.
On slippery surfaces, such as dirt and snow, the ABS may be too intrusive due to the ease with which the wheels lock.

### TCS Map

The TCS (Traction Control System) is a traction control system that prevents the drive wheels from slipping during acceleration by reducing engine power or intervening on the brakes when it detects that one wheel is spinning faster than the others.

The system optimizes the performance and stability of the vehicle, especially during acceleration in difficult conditions such as rain, snow or slippery surfaces. Furthermore, by reducing wheel slippage during extreme acceleration, it improves traction and ensures more efficient power transfer.

With the TCS deactivated (OFF) the driver has full control over acceleration. Greater experience is required in dosing the pressure, preventing loss of grip and thus obtaining superior performance.

By increasing the intensity of the system, the TCS becomes more sensitive to wheel slippage, intervening to reduce it and ensuring adequate performance even for those with less experience, reducing the need to carefully control the accelerator.

### Additional Lights

Additional lights are powerful light components used to improve visibility during night stages and low visibility conditions in rally racing. While they can significantly enhance a driver's ability to see the road ahead, many cars only have them as optional equipment, and regulations often enforce their installation for night events.

These lights are delicate and positioned on the car's front, making them vulnerable to damage from collisions. Because of their fragility, installing additional lights requires the car's bodywork to be in good condition. If the front bodywork is heavily damaged, it must be repaired before the lights can be securely fitted, ensuring both safety and functionality.
