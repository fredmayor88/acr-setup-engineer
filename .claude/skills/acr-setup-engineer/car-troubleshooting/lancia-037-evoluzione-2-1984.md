---
car: "Lancia 037 Evoluzione 2 1984"
game: "ACR"
save_ids: ["LanciaRally037Evo2"]
---

# Lancia 037 Evoluzione 2 1984 — troubleshooting

Curated, car-specific symptom→fix knowledge for this car. These entries **take precedence over the
general base** (`setup-tuning-principles.md`) where they address a concrete symptom; the user's own
authored guidelines (global / surface / per-car) still win over this file.

Match this file to the car the same way `onboard-car.md` step 1 matches a bundled template:
`car:` field, case-insensitive, ignoring punctuation.

## Brakes lock very easily as soon as braking starts / poor brake modulation

**Symptom:** the brakes snatch into a lock almost the instant you touch the pedal — there's very
little usable travel between "braking" and "locked," so trail-braking and threshold braking feel
impossible.

**Fix:** step **both** `Front Cylinder` and `Rear Cylinder` to a **smaller** diameter — move down the
discrete list (`15.88, 17.46, 17.78, 19.05, 22.23`) toward `15.88`. Change **both by the same number
of steps** so the front/rear balance (`Front Bias`) stays where it was; you're softening the *overall*
brake response, not shifting bias. If one step isn't enough, keep stepping both down together.

**Why:** a smaller brake cylinder does two things at once —
- **More leverage** — it can build higher line pressure for a given pedal force, and
- **More travel per unit pressure** — a given rise in pressure now takes more pedal movement.

The second effect is what fixes the symptom: with more pedal travel mapped to the same pressure
range, the brakes ramp up **progressively** and give you far finer modulation, instead of jumping
from nothing to locked in a sliver of travel. Larger cylinders do the opposite — they pack the whole
pressure range into a short, twitchy bit of travel, which is what makes the 037 so easy to lock early.

Keep every value within the car's discrete steps.
