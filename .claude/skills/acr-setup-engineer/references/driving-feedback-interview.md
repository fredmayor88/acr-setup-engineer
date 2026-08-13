# Driving feedback interview (guided symptom → cause)

The shared **question bank** for turning "it felt weird" into a specific, actionable setup problem —
plus the **fix-order ladder** that decides what to change first.

Used by:
- `build-setup.md` — the **pre-drive briefing** before the user drives the game's default setup, and
  the **interview** when they report back.
- `tweak-setup.md` — whenever the user's feedback is vague, contradictory, or they say they can't
  tell what's wrong.
- Directly — the user asks for help working out what's wrong with how the car feels.

The point is that most drivers *feel* the problem correctly but don't have the words for it. Getting
the words right is worth more than any amount of clever value-picking, because a wrong diagnosis
sends the whole build in the wrong direction.

## Interviewing rules

- **Assume a beginner.** Define every term the first time it's used — never assume the user knows
  what understeer, preload, coast ramp, or brake bias mean. Definitions are one short sentence, in
  passing, not a lecture.
- **Plain words, no jargon.** Ask in everyday language — *"the back stepped out"*, *"it wouldn't
  turn"*, *"it kept bouncing"* — never in setup vocabulary. Setup terms may appear as an
  explanation the user is free to ignore, **never as the question itself**. Never ask "was that
  entry understeer or mid-corner understeer?"; ask "was it as you turned in, or once you were
  already round?"
- **Small batches.** 2–4 questions at a time, never a wall of them. Start broad, narrow only along
  the branch the answer opens.
- **"Not sure / didn't notice" is always a valid answer.** Say so, accept it, move on. Never push
  the user into guessing — a guessed symptom is worse than no symptom.
- **Ask about what they felt, not what they think is wrong.** If the user volunteers a diagnosis
  ("I think the diff is too open"), take it seriously but still check the symptom behind it.
- **Stop early.** This is triage, not a form. As soon as there's enough to act on, stop asking and
  start tuning. Two clear symptoms beat twelve vague ones.
- **The user's own words win.** If they describe something that doesn't match any family below,
  work with their description — the bank is a prompt, not a constraint.

## Corner-phase primer

Almost every balance question resolves to *where in the corner* it happened. Introduce these three
words once, in plain language, and reuse them:

- **Entry** — turning in, usually still on the brakes.
- **Mid** — off the brakes, steady through the middle of the corner.
- **Exit** — back on the throttle, straightening out.

A useful mental model to hand the user: under braking the weight moves **forward**, so the front of
the car decides what happens on **entry**; on the throttle the weight moves **back**, so the rear
decides what happens on **exit**.

## Pre-drive briefing

Delivered **before** the user drives — a driver can't report on things they didn't know to notice.

It goes with **whichever setup they're actually about to drive**, and only once that's decided:
normally the game's default, **after** it has been captured and sanity-checked (`build-setup.md`
step 5b) — never alongside the screenshot request, since a default that fails the check is never
driven. When the check rejects the default, the briefing lands before they drive the **built** setup
instead. The content below is the same either way.

Keep it to a handful of bullets:

1. The corner-phase primer above, in plain words.
2. A short **"what to pay attention to"** list, tailored to the stage's facts:
   - *bumpy / rough gravel* → harsh bangs over compressions, the car skating after bumps, deflecting
     off line on rough sections;
   - *fast tarmac* → stability under hard braking, whether it turns in cleanly, whether it feels
     twitchy at speed;
   - *tight / technical* → hairpin exits (wheelspin, the back stepping out), whether it rotates at
     all in slow corners;
   - *snow / ice* → whether it goes anywhere at all on the throttle, how catchable the slides are.
3. The gearing prompts (below) — those need to be noticed *while driving* or they're lost.
4. Reassurance: **"I didn't notice"** is a fine answer, and the run is for a reference feel, not a
   fast time. Drive it the way they normally would.

The briefing deliberately uses the same words the interview will use afterwards, so the user hears
each term twice.

## Opening triage

Start here, always:

> **"Did you like it?"**

- **Liked it** → log what worked (that's calibration data too), then ask for the *one* thing they'd
  change if they could change only one. Don't hunt for problems they didn't have.
- **Didn't like it** → "what bothered you most?" and route to the matching family below.
- **Can't tell / not sure** → the common case. Walk the guided ladder: ask the families in the order
  below, 2–4 at a time, stopping as soon as something lands. Start with the big, unmistakable ones
  (doesn't turn / back steps out / bangs over bumps / brakes wrong) before the subtle ones.

## Question bank

Each family: how to ask it, what the term means, the follow-up that pins it down, and the candidate
causes **ranked in fix-order ladder order** (see below). Candidate causes are a starting hypothesis
— confirm against `setup-tuning-principles.md`, the car's drivetrain, and any matching
`car-troubleshooting/` file before proposing values.

### Balance

**Understeer**
> "Did the car want to run wide — you turned the wheel and it kept going straight?"

*Understeer is when the front tyres give up first, so the car goes wider than you're steering.*

Follow-up: **as you turned in, once you were already round, or coming out on the throttle?**

| Phase | Ranked causes |
|---|---|
| Entry | brake bias too far forward, front ride height/spring too stiff, front ARB too stiff, not enough front toe-out, front tyre pressure too high |
| Mid | front spring/ARB too stiff, camber, front tyre pressure, rear too soft relative to front |
| Exit | too much diff lock on power (`[RWD/AWD]`), locked front diff (`[FWD]` — normal, tune for traction), rear slow bump too soft |

**Oversteer**
> "Did the back end come round / slide out more than you wanted?"

*Oversteer is the opposite — the rear tyres let go first and the back overtakes the front.*

Follow-ups: **which phase?** and **did it come on gradually, or snap suddenly?** (Gradual is a
balance problem; snappy is usually diff or damper.)

| Phase | Ranked causes |
|---|---|
| Entry | coast ramp too open, preload too low, brake bias too far rearward, rear ARB/spring too stiff, rear toe-out |
| Mid | rear ARB/spring too stiff, rear tyre pressure, rear camber |
| Exit | **check the grip regime first** (see below) — power ramp, preload, plates; then rear spring/damper on squat, rear toe-in |

> **Exit oversteer — always establish the grip regime before choosing a direction**, because the
> correct fix is *opposite* in each case (`setup-tuning-principles.md` → *Differential (LSD)*):
> ask *"did it snap suddenly when you got hard on the throttle on grippy ground, or did it wander
> and swing while you were feathering the throttle on loose stuff?"*
> Snap on grip → **less** lock. Wandering while modulating on low grip → **more** lock, preload
> first. If the answer is unclear, ask again rather than guessing.

**The car doesn't turn at all**
> "Did it feel like the steering barely did anything — like you were just a passenger?"

Follow-up: **everywhere, or only in the slow/tight corners?** (Only slow corners points at the diff;
everywhere points at the front end or the tyre.)

Ranked causes: far too much diff lock, wrong tyre for the surface, far too stiff front spring/ARB,
extreme front toe-in, ride height bottoming the front.

**Lift-off snap**
> "When you lifted off the throttle mid-corner, did the back suddenly come round?"

*Lifting off moves weight forward and unloads the rear, so the back can let go.*

Follow-up: **how violent — a nudge you could catch, or gone before you could react?**

Ranked causes: coast ramp too open, preload too low, rear spring/ARB too stiff, rear rebound too
high, rear toe-out.

### Braking

**Rear unstable under long braking**
> "Braking hard for a long time, did the rear feel like it wanted to overtake the front — the car
> squirming or trying to swap ends?"

Follow-up: **in a straight line, or only once you started turning in?** (Straight-line points at
brake bias and the diff; only on turn-in points at coast ramp and rear damping.)

Ranked causes: **preload too low** (the rear wheels can't stay tied together under decel), coast
ramp too open, brake bias too far rearward, rear rebound/slow bump, rear ride height too low.

**Braking feel / hardware**
> "Did the brakes feel weak — like you had to stand on them and nothing happened — or did they lock
> the wheels the moment you touched them?"

*Locking means the wheels stop turning and just slide; you lose steering and stopping power.*

Follow-up: **could you control it in between, or was it all-or-nothing?**

| Report | Ranked causes |
|---|---|
| Barely brakes | caliper too small (**the biggest lever** — piston count), disc too small, master cylinder too large |
| Locks instantly | caliper too big, disc too big, master cylinder too small (smaller = finer modulation), pads too aggressive; check for a matching `car-troubleshooting/` entry first |
| Can't modulate | master cylinder, pads, then ABS |

Prefer **mechanical** fixes over turning ABS up — ABS removes braking feel.

### Traction & the differential

**Hairpin exit traction**
> "Coming out of the tight hairpins, did one wheel spin up, or did the car step sideways?"

Follow-ups: **one wheel or both?** (One wheel spinning alone = not enough lock.) **Did it happen
while you were feathering the throttle, or once you were hard on it?** (Feathering = preload;
sustained = power ramp.)

Ranked causes: **preload too low** (the classic hairpin-exit loss — there's no lock at low torque,
so the inside wheel just spins), power ramp too open, too few plates, rear spring/damper letting the
car squat unevenly.

**Diff adjustments don't seem to do anything**
> "When we changed the differential last time, could you feel any difference at all?"

Ranked causes: **too few plates** (the plates scale how strong the lock is — with too few, ramp
changes barely register), or the change was too small for the surface (on gravel/snow use bigger
steps).

**Lock feels abrupt / binary**
> "Does it grip and then let go all at once, with nothing in between?"

Ranked causes: too many plates, preload too high, ramp too aggressive.

### Suspension, dampers, ride height

**Bottoming out**
> "Any harsh bangs, or a sudden loss of control, over compressions, crests, or landings?"

*Bottoming out is the suspension running out of travel — once it does, the car is effectively rigid
and skips.*

Follow-up: **where on the stage?** (Landings and compressions specifically, or everywhere?)

Ranked causes: ride height too low, springs too soft, fast bump too low.

**Floaty / skating**
> "After a bump or a crest, did the car keep moving around instead of settling straight away?"

Follow-up: **one big float, or did it keep bouncing?** (One float = rebound too high, the wheel
isn't coming back down; repeated bouncing = too little damping or springs too soft.)

Ranked causes: rebound too high (loses ground contact) or too low (oscillates), springs too soft,
ride height.

**Skipping / deflecting on rough**
> "On the rough sections, did it skip sideways or bounce off line instead of soaking it up?"

Ranked causes: springs too stiff, ARBs too stiff, fast bump too high, ride height too low. On
loose/rough surfaces keep ARBs soft so each wheel can follow the ground independently.

**Rolls over / lazy**
> "Did it lean over a lot and feel slow to change direction?"

Ranked causes: springs too soft, ARBs too soft. (Check this *against* the bumpy-stage answers —
softness that helps on rough ground costs response.)

**Darty / nervous**
> "Did it feel twitchy in a straight line, needing constant small corrections?"

Follow-up: **all the time, or mainly under braking?**

Ranked causes: too much toe (either end), ARB too stiff, tyre pressure too high, camber.

### Tyres

**Tyre feel**
> "Was the grip missing from the start, or did it fade as the stage went on?"

Ranked causes: wrong compound for the surface/conditions (missing from the start), compound too soft
/ overheating (fades), then pressure.

> **Pressure is a special case — leave it alone unless the user reports it.** ACR's tyre
> pressure model is still maturing and doesn't behave the way real-world logic suggests, so a
> captured default's pressures are a **better reference than any reasoning the skill can do**.
> Change pressure only when a symptom points directly at it or the user says the pressures felt
> wrong — never as part of routine balance tuning (`setup-tuning-principles.md` → *Tyre pressure*).

### Other

**Handbrake**
> "When you pull the handbrake, does it spin the car every single time?"

Ranked causes: handbrake force too high (especially with an on/off button and no modulation).

**Driver aids**
> "Did you feel the ABS or traction control cutting in and taking over?"

Ranked causes: aid level too high — but prefer fixing the underlying mechanical problem (diff,
gearing, engine map, brake hardware) before leaning on the aid.

## Gearing sub-interview

Gearing is a **parallel track** — it's resolved from its own questions and isn't part of the balance
ladder. These need to be noticed *while driving*, so they also go in the pre-drive briefing.

1. **"On the long straights, were you hitting the rev limiter with road still left to go?"**
   → gears too short. Lengthen the primary gear (or pick a wider set).
2. **"In the fast corners where you steer with the throttle, did the engine feel like it was pulling
   properly — or flat, or screaming?"**
   → not in the power band. Aim so that **after an upshift the revs land near the torque peak**;
   chasing the redline misses the torque.
3. **"Coming out of the slow corners, did it bog down / feel like it had nothing?"**
   → gears too long.
4. **Slippery-surface inversion — ask this separately, it's the opposite answer:**
   **"On the loose or icy bits, did the wheels spin up the moment you touched the throttle?"**
   → deliberately **longer** gears and lower revs to soften the delivery, even though that's the
   opposite of what questions 1–3 would suggest on dry tarmac. On low grip, staying *below* the
   power peak is often faster and far more controllable (pairs with a softer engine map). **Call
   this out explicitly** so it doesn't get "optimised away" by the straight-line answer.

Never reach top gear? That's fine and not a problem to fix — what matters is staying in the power
band where the driving actually happens.

## Fix-order ladder (major → fine)

Fix the big things before the fine ones. Changing alignment while the differential is wrong just
hides cause and effect.

1. **Tyre type** — the single biggest grip decision; always re-derived from the surface.
2. **Differential** — **preload** → ramp angles (power/coast) → plates.
3. **Suspension** — ride height, then spring stiffness. *Survival before balance*: first make the
   car handle the surface (no bottoming, no floating), then worry about under/oversteer.
4. **ARBs**.
5. **Dampers**.
6. **Wheel angles** — camber, toe. (A toe cause named anywhere above is a **direction** —
   "more front toe-out", "less rear toe-out". Turning it into a value uses ACR's **inverted** toe
   sign: toe-out ⇒ **positive**, toe-in ⇒ **negative** — see `SKILL.md` → *ACR's toe sign is
   inverted*.)
7. **Brake bias** — and brake hardware (calipers/discs/master cylinder) when the complaint is
   hardware-scale: *barely brakes* or *locks instantly*.

**Tyre pressure sits outside the ladder** — held at the captured default, moved only on a reported
pressure symptom (see *Tyre feel* above).

**Gearing is a parallel track** — resolved from its own sub-interview, in any order.

Two standing caveats:
- **The user's own words take priority over this order.** If they say the dampers are the problem,
  work the dampers. The ladder is the default route when nothing else decides it.
- **Change a few things at a time**, and size the step to the surface: on gravel/snow small clicks
  are barely felt (move in bigger steps); on tarmac small changes matter (move precisely).

## Recording the outcome

An interview produces a short **structured symptom list** — for each symptom: family, corner phase,
severity, and **the user's own words**. The caller persists it (`build-setup.md` step 6):

- **One-line dated verdict** into the setup row's `Notes` — readable in the table without opening
  the page.
- **The full record** into a **dated collapsed toggle** ("Driving feedback — {date}") in the setup's
  page body. Repeat interviews **stack chronologically**; never overwrite an earlier one.
- **Lasting preferences only** (things true of how this user drives *this car*, not one-off stage
  symptoms) as normal bullets in the `{Car}` page's **Guidelines** section, where they join the
  per-car guideline layer. The raw symptom log goes in a separate collapsed, dated **"Driving
  feedback log"** toggle on the same page — that log is an objective record, **not** a guideline
  layer.

Get every date from the deterministic Python one-liner in `notion-structure.md` → `Date`, never from
a guess at the wall clock.
