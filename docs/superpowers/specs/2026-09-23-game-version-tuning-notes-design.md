# Per-game-version tuning notes

**Status:** approved in chat 2026-09-23 · **Date:** 2026-09-23

## Summary

Some tuning knowledge is true only for one version of the game. In 0.6 the tyre model changed:
tyres now heat up and wear over a run, pressure rises as they heat, and a soft tarmac tyre no
longer lasts a long stage. Today the skill carries this kind of knowledge inside the base
principles ("ACR pressure rule, early access") and in four workflow files that repeat "hold the
game's default pressures". That text is stale as of 0.6 and cannot be updated per release
without touching the reasoning base.

This design adds one bundled markdown file per game version, `game-versions/<version>.md`,
read as a guideline layer by every workflow that chooses, changes, judges or explains setup
values. The file for the current version is found from the skill's `GAME_VERSION` file. The
0.6 file carries the tyre pressure target, the tyre type rule by stage length, and the test-run
routine for finding a stage's cold pressure. The base principles go back to timeless physics.

## Goals

- One hand-written file per game version, shipped inside the skill, updated by the maintainer
  after each game release, working offline and on the Free plan.
- Build, tweak, review and ask all read it, at one fixed place in the precedence chain.
- The 0.6 tyre facts are applied: tarmac hot pressure target 28 psi, cold start below it,
  Tarmac Medium on stages of 8 km or longer, a pre-drive warning that medium tyres start cold,
  and a test-run routine using the in-game pressure gauge.
- Version-specific text leaves the base principles and the workflow files.

## Non-goals

- Structured or machine-evaluated rules. The file is prose the model follows, like
  `car-troubleshooting/`. No YAML schema, no numbers parsed by scripts.
- Gravel and snow pressure rules. No 0.6 fact is known for them; the bundled default holds.
- Generating the file from the game files. It is hand-written knowledge.
- Storing version notes in Notion.

## Decisions taken with the user (2026-09-23)

- A tarmac stage is **long** at **8 km or more**; a long stage takes Tarmac Medium, a shorter
  one Tarmac Soft. The length comes from the stage page in the catalogue; when there is no
  stage or no length, the skill asks in one short line and falls back to soft.
- Precedence: base principles → **game version notes** → car troubleshooting → global
  guidelines → surface section → per-car guidelines → driving intent. The user's own notes
  still beat the version notes.
- Version notes are the anchor for tarmac tyre pressure. They outrank the bundled default's
  pressures on tarmac. On gravel and snow the bundled default's pressures still hold.

Cold start pressure on tarmac is **27 psi** on every stage (user decision, 2026-09-23; the
gauge routine settles the rest).

## The file: `game-versions/0.6.md`

Lives at the skill root beside `car-setups/` and `car-troubleshooting/`. Frontmatter, then
sections. Every rule names the version it comes from, so a report can quote "0.6 tyre notes".

```markdown
---
game: "ACR"
version: "0.6"
---

# ACR 0.6 — tuning notes for this game version

What is true about the game in this version and not necessarily in others. Workflows read this
file as the guideline layer right after the base principles: it overrides
`setup-tuning-principles.md` where it names a rule, and the user's own guidelines (global,
surface, per-car) and the driving intent still win over it.

## What changed in 0.6

- Tyres now have a thermal model and a wear model. A tyre heats up over the run, and its
  pressure rises with its temperature. The pressure you set is the cold pressure; the pressure
  the tyre runs at is higher.
- Soft tarmac tyres wear out before the end of a long stage.

## Tyre pressure

- **Tarmac:** the optimal hot pressure is **28 psi, front and rear**. Set the cold pressure
  below it so the tyre reaches 28 during the run: start from **27 psi**, both axles, on every
  tarmac stage. Make the value legal on the car's catalog grid; if 27 is not on the grid, take
  the nearest legal value below it.
- **Gravel, snow:** no version rule. Keep the bundled default's pressures unless a symptom
  points at them.
- This replaces the base principles' "hold the default's pressures" advice on tarmac. The
  bundled default's tarmac pressures were tuned for the old model and are not the target.

## Tyre type on tarmac

- **Stage under 8 km:** `Tarmac Soft`.
- **Stage of 8 km or more:** `Tarmac Medium`. Soft does not last the whole stage.
- The stage length is on the stage's page in the catalogue. When no stage was given, or the
  page has no length, ask in one short line ("about how long is the stage?") and use
  `Tarmac Soft` if the user doesn't know.
- **Medium tyres take longer to warm up.** Tell the driver, before the run, that the first
  kilometres are on cold tyres and to be careful until the grip comes in.
- Wet, winter and snow compounds are chosen as before, from the conditions.

## Finding the right cold pressure for a stage

The best way to set a stage's pressure is a few test runs with the in-game tyre pressure gauge:

1. Run the stage on the cold pressure from *Tyre pressure* above.
2. Near the end of the run, read the gauge for each tyre.
3. Move the cold pressure by the difference: if the gauge shows 29, lower the cold pressure by
   1 psi; if it shows 27, raise it by 1. Front and rear separately if they differ.
4. Run again until the end-of-run reading sits on 28.

A driver who reports a hot reading is reporting a pressure symptom: move the cold pressure by the
difference before anything on the fix-order ladder.
```

## Resolution: `scripts/load_game_version_notes.py`

Standard library only, like the other scripts. Prints the path of the file to read.

```
python scripts/load_game_version_notes.py            # path of the notes for GAME_VERSION
python scripts/load_game_version_notes.py --version 0.6
python scripts/load_game_version_notes.py --dir DIR  # notes folder (tests)
```

- Reads `GAME_VERSION` (same file and parsing as `load_default_setup.py --game-version`).
- Lists `game-versions/*.md`, parses each filename as a version (dotted integers).
- **Exact match** → prints the path, exit 0.
- **No exact match, some file with a lower version** → prints the path of the newest lower
  version, then a second line `note: no notes for 0.6.1; using 0.6`, exit 0.
- **No file at or below the version** → prints `no version notes for <version>` to stderr, exit 1.
- Unknown flag → usage, exit 2.
- A filename that is not a version (`README.md`) is ignored.

Workflows call it once when loading guideline layers and read the file it names. Exit 1 means
"skip this layer" and say so in one line.

## Workflow changes

All four workflow files gain the layer at the same position and read it the same way.

**`SKILL.md`**
- *Layered guidelines* core rule: insert **game version notes** between base principles and
  bundled car troubleshooting, with one sentence on what the file is.
- File list: add `game-versions/` next to `car-troubleshooting/`, and the script.
- Any sentence in `SKILL.md` that says pressures are held at the default is rewritten to defer
  to the version notes.

**`references/build-setup.md`**
- Step 2 (guideline layers): new layer 2 = game version notes (`load_game_version_notes.py`),
  troubleshooting becomes 3, global 4, surface 5, per-car 6. The "more specific is the default
  lean" line lists the new order.
- Step 3 (stage facts): also read the stage's **length**; when the build surface is tarmac and
  the length is unknown, ask the one-line question here, with the conditions question.
- Step 8: tyre type on tarmac follows the version notes' stage-length rule. Tyre pressure:
  "with a baseline, hold the default's pressures" becomes "on a surface the version notes give
  a pressure rule for, start from that rule and report `default → new (0.6 tyre notes)`; on any
  other surface hold the default's pressures". The no-baseline fallback is unchanged.
- Step 12 (report) and the pre-drive briefing: one fixed line when the tyre is a medium
  compound ("the first kilometres are on cold tyres"), and one line pointing at the test-run
  routine ("read the pressure gauge near the end of the run; the target is 28").
- The rules list near the end ("Hold the default's tyre pressures…") is rewritten the same way.

**`references/tweak-setup.md`**
- Guideline layers: same insertion.
- The pressure paragraph: a reported hot reading moves the cold pressure by the difference,
  before the ladder, per the version notes. Other pressure moves stay symptom-driven.

**`references/review-setup.md`**, **`references/ask-setups.md`**
- Guideline layers: same insertion. Review judges tarmac pressures and tyre type against the
  version notes; ask explains them from it.

**`references/driving-feedback-interview.md`**
- *Tyre feel* callout and the "Tyre pressure sits outside the ladder" line: defer to the
  version notes for the target; keep "pressure is not a balance lever".

**`references/setup-tuning-principles.md`**
- Remove the "ACR pressure rule (early access)" section. Replace it with two sentences: the
  target pressure and how the game's pressure model behaves are version facts, read them from
  the current version notes; with no version rule for the surface, hold the bundled default's
  pressures, and without a default start in the upper half of the legal range.

**`references/how-to-use-template.md`**, **`references/free-plan-template.md`**
- One line: setups follow the tuning notes for game version `{game_version}` (tyre pressure
  and tyre type in 0.6).

**Guards** (`tests/test_references.py`): every workflow file that lists guideline layers
mentions `load_game_version_notes.py`; the phrase `hold the default's pressures` no longer
appears without the version-notes qualifier; the base principles no longer contain
`early access`.

## Tests

- `tests/test_game_version_notes.py`: the 0.6 file exists, its frontmatter version matches
  `GAME_VERSION`, and it has the four H2 sections named above.
- `tests/test_load_game_version_notes.py`: exact match, lower-version fallback with the note
  line, no file (exit 1), `--version`, unknown flag (exit 2), non-version filename ignored. Uses a
  temp `--dir`.
- `check_zip.py`: requires `game-versions/*.md`.

## Maintenance

- After a game release: `make extract`, then copy `game-versions/<old>.md` to
  `game-versions/<new>.md` and edit what changed. Until the copy exists the loader falls back to
  the previous file and says so.
- Written in `tools/car-catalog/README.md` (a short `## Game version notes` section) and in
  `CLAUDE.md` (file list and the release checklist line).

## Out of scope, noted for later

- Per-surface pressure rules for gravel and snow, once known.
- A pressure step that respects a car's catalog grid finer than 1 psi when moving by a gauge
  difference. Today: move by the difference, then make it legal.
