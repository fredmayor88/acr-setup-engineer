# Per-game-version tuning notes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one hand-written tuning-notes file per game version inside the skill (`game-versions/0.6.md` first), a stdlib script that finds the file for the current `GAME_VERSION`, and make build, tweak, review and ask read it as the guideline layer right after the base principles, so the 0.6 tyre facts (28 psi hot target on tarmac, Tarmac Medium on stages of 8 km or more, gauge test runs) drive setups and version-specific text leaves the base principles.

**Architecture:** A markdown file per version, same shape as `car-troubleshooting/` (frontmatter + prose the model follows). `scripts/load_game_version_notes.py` resolves `GAME_VERSION` → file path (exact match, else newest lower version with a note, else exit 1). Every workflow that lists guideline layers gets the new layer at position 2; the base principles and the interview lose their version-specific pressure text and point at the notes instead.

**Tech Stack:** Python 3 stdlib in the skill; `unittest` (`python -m unittest discover -s tests`, run from the repo root; 467 tests green at start); markdown references executed by an LLM.

**Spec:** `docs/superpowers/specs/2026-09-23-game-version-tuning-notes-design.md`

## Global Constraints

- Skill scripts are **stdlib only**; unknown flags **exit 2**; nothing found **exit 1** with a clear message on stderr.
- The notes file is prose. No numbers are parsed by any script.
- Precedence (lowest → highest), spelled the same everywhere: base principles → **game version notes** → bundled car troubleshooting → global `Tuning guidelines` → surface section → per-car `Guidelines` → driving intent.
- Long tarmac stage = **8 km or more** → `Tarmac Medium`; under 8 km → `Tarmac Soft`. Tarmac cold pressure: **27 psi** under 8 km, **26 psi** at 8 km or more, both axles; hot target **28 psi**. Gravel and snow: bundled default's pressures hold.
- The sentence `ACR's pressure model isn't physically sensible` and the phrase `early access` are version claims and must not survive anywhere in `SKILL.md` or `references/`.
- Writing rule (CLAUDE.md): every workflow step followable by a less capable model — exact commands, exact phrases, and every guarded phrase kept on **one physical line** (hard-wrapping breaks the substring guards in `tests/test_references.py`).
- Work on branch `game-version-notes` off `main`. Commit after each task, short factual message, end with a blank line and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Never push. Full suite green before each commit: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`.
- Do not run `make zip` (it overwrites the released zip in `dist/`).

---

### Task 1: The 0.6 notes file, its test, and the zip check

**Files:**
- Create: `.claude/skills/acr-setup-engineer/game-versions/0.6.md`
- Create: `tests/test_game_version_notes.py`
- Modify: `check_zip.py` (after the `GAME_VERSION` check, around line 40)

**Interfaces:**
- Produces: the folder `game-versions/` with `<version>.md` files whose frontmatter has `game: "ACR"` and `version: "<version>"`, and four H2 sections: `## What changed in 0.6`, `## Tyre pressure`, `## Tyre type on tarmac`, `## Finding the right cold pressure for a stage`. Task 2's script lists this folder; Tasks 3–5 quote these section names.

- [ ] **Step 1: Write the failing test**

`tests/test_game_version_notes.py`:

```python
"""game-versions/<version>.md — the tuning notes for one game version.

Hand-written prose the workflows read as the guideline layer right after the base principles.
The file for the current GAME_VERSION must exist and carry the sections the workflows quote.

Run: python -m unittest discover -s tests
"""
import glob
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
NOTES = os.path.join(SKILL, 'game-versions')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()

SECTIONS = [
    '## What changed in ',
    '## Tyre pressure',
    '## Tyre type on tarmac',
    '## Finding the right cold pressure for a stage',
]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class TestNotesFiles(unittest.TestCase):
    def test_current_game_version_has_notes(self):
        self.assertTrue(os.path.isfile(os.path.join(NOTES, GAME_VERSION + '.md')))

    def test_every_file_is_named_by_a_version_and_says_so_in_frontmatter(self):
        files = glob.glob(os.path.join(NOTES, '*.md'))
        self.assertTrue(files)
        for path in files:
            name = os.path.basename(path)[:-3]
            self.assertRegex(name, r'^\d+(\.\d+)+$', path)
            text = read(path)
            self.assertTrue(text.startswith('---\n'), path)
            front = text.split('---\n')[1]
            self.assertIn('game: "ACR"', front, path)
            self.assertIn(f'version: "{name}"', front, path)

    def test_current_notes_carry_the_sections_the_workflows_quote(self):
        text = read(os.path.join(NOTES, GAME_VERSION + '.md'))
        for heading in SECTIONS:
            self.assertIn(heading, text, heading)

    def test_current_notes_state_the_tyre_rules(self):
        text = read(os.path.join(NOTES, GAME_VERSION + '.md'))
        self.assertIn('28 psi', text)
        self.assertIn('8 km', text)
        self.assertIn('Tarmac Medium', text)
        self.assertIn('Tarmac Soft', text)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest tests.test_game_version_notes -v`
Expected: FAIL — `test_current_game_version_has_notes` (no folder yet).

- [ ] **Step 3: Write the notes file**

`.claude/skills/acr-setup-engineer/game-versions/0.6.md`, exactly:

````markdown
---
game: "ACR"
version: "0.6"
---

# ACR 0.6 — tuning notes for this game version

What is true about the game in this version and not necessarily in others. Workflows read this
file as the guideline layer right after the base principles: it overrides
`setup-tuning-principles.md` where it names a rule, and the user's own guidelines (global,
surface, per-car) and the driving intent still win over it. Quote it as "0.6 tyre notes" when a
value comes from here.

## What changed in 0.6

- Tyres now have a thermal model and a wear model. A tyre heats up over the run, and its
  pressure rises with its temperature. The pressure you set is the cold pressure; the pressure
  the tyre runs at is higher.
- Soft tarmac tyres wear out before the end of a long stage.

## Tyre pressure

- **Tarmac:** the optimal hot pressure is **28 psi, front and rear**. Set the cold pressure
  below it so the tyre reaches 28 during the run: **27 psi** on a stage under 8 km,
  **26 psi** on a stage of 8 km or more. Both axles the same. Make the value legal on the
  car's catalog grid; if 27 or 26 is not on the grid, take the nearest legal value below it.
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
````

- [ ] **Step 4: Add the zip check**

In `check_zip.py`, after the `GAME_VERSION missing` block:

```python
# The tuning notes for the current game version ship with the skill: every workflow reads
# game-versions/<version>.md as a guideline layer, so a ZIP without them tunes on stale rules.
if not any(n.startswith("acr-setup-engineer/game-versions/") and n.endswith(".md") for n in names):
    errors.append("no game-versions/*.md found")
```

- [ ] **Step 5: Run the tests**

Run: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`
Expected: `OK`, 471 tests.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/acr-setup-engineer/game-versions/0.6.md tests/test_game_version_notes.py check_zip.py
git commit -m "game-versions: 0.6 tuning notes (tyre pressure, tyre type by stage length, gauge test runs)"
```

---

### Task 2: `scripts/load_game_version_notes.py`

**Files:**
- Create: `.claude/skills/acr-setup-engineer/scripts/load_game_version_notes.py`
- Create: `tests/test_load_game_version_notes.py`

**Interfaces:**
- Consumes: `game-versions/<version>.md` (Task 1); `GAME_VERSION` at the skill root.
- Produces: the command `python scripts/load_game_version_notes.py [--version V] [--dir DIR]`. stdout line 1 = path of the notes file; optional line 2 = `note: no notes for <V>; using <U>`. Exit 0 found, 1 nothing at or below V, 2 usage. Module functions `parse_version(text) -> tuple|None`, `available(directory) -> [(tuple, str, path)]`, `resolve(version, directory) -> (tuple, str, path)|None`.

- [ ] **Step 1: Write the failing tests**

`tests/test_load_game_version_notes.py`:

```python
"""scripts/load_game_version_notes.py — which game-versions/<version>.md applies.

Exact match on GAME_VERSION, else the newest lower version with a note line, else exit 1.
Stdlib only: it runs in the user's code sandbox.

Run: python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SKILL = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer')
SCRIPT = os.path.join(SKILL, 'scripts', 'load_game_version_notes.py')
GAME_VERSION = open(os.path.join(SKILL, 'GAME_VERSION'), encoding='utf-8').read().strip()
sys.path.insert(0, os.path.join(SKILL, 'scripts'))

import load_game_version_notes as lgn  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class TestFunctions(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(lgn.parse_version('0.6'), (0, 6))
        self.assertEqual(lgn.parse_version('0.6.1'), (0, 6, 1))
        self.assertIsNone(lgn.parse_version('README'))
        self.assertIsNone(lgn.parse_version('0.6a'))

    def test_available_ignores_non_version_files(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('0.5.md', '0.6.md', 'README.md', 'notes.txt'):
                open(os.path.join(d, name), 'w').close()
            self.assertEqual([v for v, _, _ in lgn.available(d)], [(0, 5), (0, 6)])

    def test_resolve_exact_lower_and_none(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('0.5.md', '0.6.md'):
                open(os.path.join(d, name), 'w').close()
            self.assertEqual(lgn.resolve('0.6', d)[1], '0.6')
            self.assertEqual(lgn.resolve('0.6.1', d)[1], '0.6')
            self.assertEqual(lgn.resolve('0.5.9', d)[1], '0.5')
            self.assertIsNone(lgn.resolve('0.4', d))


class TestCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        for name in ('0.5.md', '0.6.md', 'README.md'):
            open(os.path.join(self.tmp.name, name), 'w').close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_match_prints_the_path_only(self):
        r = run('--version', '0.6', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines(), [os.path.join(self.tmp.name, '0.6.md')])

    def test_lower_version_fallback_adds_a_note(self):
        r = run('--version', '0.6.1', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(lines[0], os.path.join(self.tmp.name, '0.6.md'))
        self.assertEqual(lines[1], 'note: no notes for 0.6.1; using 0.6')

    def test_nothing_at_or_below_exits_1(self):
        r = run('--version', '0.4', '--dir', self.tmp.name)
        self.assertEqual(r.returncode, 1)
        self.assertIn('no version notes for 0.4', r.stderr)

    def test_unknown_flag_exits_2(self):
        r = run('--bogus')
        self.assertEqual(r.returncode, 2)
        self.assertIn('Usage', r.stderr)

    def test_default_resolves_the_skills_game_version_exactly(self):
        r = run()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(os.path.basename(lines[0]), GAME_VERSION + '.md')
        self.assertEqual(len(lines), 1, 'the current version must have its own file')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m unittest tests.test_load_game_version_notes -v`
Expected: import error (`No module named load_game_version_notes`).

- [ ] **Step 3: Write the script**

`.claude/skills/acr-setup-engineer/scripts/load_game_version_notes.py`:

```python
#!/usr/bin/env python3
"""Find the tuning notes for the current game version.

Some tuning knowledge is true for one game version only (tyre pressure targets, which compound
lasts a stage). It ships as `game-versions/<version>.md`, hand-written, one file per version.
Every workflow that loads guideline layers runs this once and reads the file it names.

Usage:
  python scripts/load_game_version_notes.py                 # notes for the skill's GAME_VERSION
  python scripts/load_game_version_notes.py --version 0.6
  python scripts/load_game_version_notes.py --dir DIR       # notes folder (tests)

Output (stdout):
  line 1: the path of the notes file to read
  line 2 (only when the version has no file of its own): note: no notes for 0.6.1; using 0.6

Exit codes:
  0  a file was found (exact version, or the newest lower version)
  1  no file at or below the version — skip the layer and say so in one line
  2  usage error
"""
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(SKILL_DIR, 'game-versions')
GAME_VERSION_FILE = os.path.join(SKILL_DIR, 'GAME_VERSION')

USAGE = ('Usage: load_game_version_notes.py [--version V] [--dir DIR]')


class NotesError(Exception):
    pass


def parse_version(text):
    """'0.6.1' -> (0, 6, 1); anything that is not dotted integers -> None."""
    parts = text.strip().split('.')
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def available(directory):
    """Every <version>.md in directory, as (version tuple, version text, path), ascending."""
    found = []
    try:
        names = os.listdir(directory)
    except OSError as exc:
        raise NotesError(f'cannot read notes folder: {exc}')
    for name in names:
        if not name.endswith('.md'):
            continue
        version = parse_version(name[:-3])
        if version is not None:
            found.append((version, name[:-3], os.path.join(directory, name)))
    return sorted(found)


def resolve(version, directory):
    """The file for `version`: exact, else the newest lower one; None if nothing qualifies."""
    target = parse_version(version)
    if target is None:
        raise NotesError(f'not a version: {version!r}')
    candidates = [entry for entry in available(directory) if entry[0] <= target]
    return candidates[-1] if candidates else None


def read_game_version(path=GAME_VERSION_FILE):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read().strip()
    except OSError as exc:
        raise NotesError(f'cannot read GAME_VERSION: {exc}')


def main():
    args = sys.argv[1:]
    version = None
    directory = NOTES_DIR
    i = 0
    while i < len(args):
        if args[i] == '--version' and i + 1 < len(args):
            version = args[i + 1]
            i += 2
        elif args[i] == '--dir' and i + 1 < len(args):
            directory = args[i + 1]
            i += 2
        else:
            print(f'unknown or incomplete option: {args[i]}\n{USAGE}', file=sys.stderr)
            return 2
    try:
        if version is None:
            version = read_game_version()
        entry = resolve(version, directory)
    except NotesError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if entry is None:
        print(f'no version notes for {version}', file=sys.stderr)
        return 1
    _, used, path = entry
    print(path)
    if parse_version(used) != parse_version(version):
        print(f'note: no notes for {version}; using {used}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`
Expected: `OK`, 479 tests.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/scripts/load_game_version_notes.py tests/test_load_game_version_notes.py
git commit -m "scripts: load_game_version_notes.py resolves GAME_VERSION to game-versions/<version>.md"
```

---

### Task 3: Base principles, interview and SKILL.md lose the version claims and gain the layer

**Files:**
- Modify: `.claude/skills/acr-setup-engineer/references/setup-tuning-principles.md` (the `ACR pressure rule (early access)` paragraph, lines ~171–184)
- Modify: `.claude/skills/acr-setup-engineer/references/driving-feedback-interview.md` (the *Tyre feel* callout ~255–259; the "Tyre pressure sits outside the ladder" line ~328; the *Pre-drive briefing* list ~61–70)
- Modify: `.claude/skills/acr-setup-engineer/SKILL.md` (*Layered guidelines* core rule ~358; fix-order ladder bullet ~194–196; file list after `car-troubleshooting/` ~87–93; script list after `load_default_setup.py` ~120–127)
- Modify: `tests/test_references.py` (new class)

**Interfaces:**
- Consumes: `game-versions/0.6.md` section names (Task 1); the script command (Task 2).
- Produces: the exact layer sentence other workflows copy in Tasks 4–5:
  `**Game version notes** — run `python scripts/load_game_version_notes.py` and read the file it prints (the tuning notes for the current game version, `game-versions/<version>.md`); when it prints a second `note:` line, say it in one line. **They override the base principles** for the rules they name (in 0.6: tarmac tyre pressure and tyre type by stage length). If it exits 1, skip this layer and say so in one line.`

- [ ] **Step 1: Write the failing guards**

Append to `tests/test_references.py` before `if __name__ == '__main__':`:

```python
class TestGameVersionNotes(unittest.TestCase):
    """The per-version tuning notes are a guideline layer every value-choosing workflow reads."""
    WORKFLOWS = ('build-setup.md', 'tweak-setup.md', 'review-setup.md', 'ask-setups.md')

    def ref(self, name):
        return read(os.path.join(SKILL, 'references', name))

    def test_every_workflow_runs_the_notes_loader(self):
        for name in self.WORKFLOWS:
            self.assertIn('python scripts/load_game_version_notes.py', self.ref(name), name)

    def test_skill_md_names_the_folder_the_script_and_the_layer(self):
        text = read(os.path.join(SKILL, 'SKILL.md'))
        self.assertIn('game-versions/', text)
        self.assertIn('scripts/load_game_version_notes.py', text)
        self.assertIn('game version notes', text.lower())

    def test_version_claims_left_the_base_and_the_workflows(self):
        for path in FILES:
            text = read(path).lower()
            self.assertNotIn("pressure model isn't physically sensible", text, path)
            self.assertNotIn('early access', text, path)
            self.assertNotIn('still maturing', text, path)

    def test_principles_point_at_the_notes_for_pressure(self):
        text = self.ref('setup-tuning-principles.md')
        self.assertIn('load_game_version_notes.py', text)

    def test_interview_points_at_the_notes_for_pressure_and_cold_tyres(self):
        text = self.ref('driving-feedback-interview.md')
        self.assertIn('game version notes', text.lower())
        self.assertIn('cold tyres', text)

    def test_build_uses_stage_length_and_the_pressure_target(self):
        text = self.ref('build-setup.md')
        self.assertIn('8 km', text)
        self.assertIn('0.6 tyre notes', text)
        self.assertIn('about how long is the stage?', text)
        self.assertIn('cold tyres', text)

    def test_tweak_moves_cold_pressure_by_the_gauge_difference(self):
        self.assertIn('by the difference', self.ref('tweak-setup.md'))

    def test_docs_pages_say_setups_follow_the_version_notes(self):
        for name in ('how-to-use-template.md', 'free-plan-template.md'):
            body = self.ref(name).partition('\n---\n')[2]
            self.assertIn('tuning notes for game version {game_version}', body, name)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m unittest tests.test_references -v 2>&1 | grep -E "FAIL|ERROR|^OK"`
Expected: every `TestGameVersionNotes` test fails except none. (Tasks 4 and 5 turn the build, tweak and docs-page guards green; this task turns the rest green.)

- [ ] **Step 3: Rewrite the pressure rule in the base principles**

In `setup-tuning-principles.md`, replace the whole block from the line starting `**ACR pressure rule (early access).**` through the line `Revisit this rule as game builds update.` with:

```markdown
**Target pressure is a game-version fact, not physics.** How the game's tyre model heats, wears
and reads pressure changes between releases, so the pressure to aim at and how to reach it come
from the **game version notes** (`python scripts/load_game_version_notes.py`, the layer right
above this file). When the notes give a rule for the build surface, that rule is the anchor for
`Pressure Front` and `Pressure Rear`. When they give none for the surface: with a bundled or
captured default, **hold the default's pressures** and move them only on a reported pressure
symptom; with no default, start in the upper half of the surface's legal range and adjust from
feedback. Never adjust pressure as part of routine balance tuning — use the balance levers.
```

Check: `grep -n -i "early access\|still maturing\|physically sensible" .claude/skills/acr-setup-engineer/references/setup-tuning-principles.md` prints nothing.

- [ ] **Step 4: Rewrite the interview's two pressure passages and add the cold-tyre briefing line**

In `driving-feedback-interview.md`, replace the blockquote under *Tyre feel* (the five lines starting `> **Pressure is a special case`) with:

```markdown
> **Pressure is a special case — its target comes from the game version notes, not from feel.**
> The notes (`python scripts/load_game_version_notes.py`) say what hot pressure the current
> version rewards and how to read it off the in-game gauge. A driver who reports a gauge reading
> is reporting a pressure symptom: move the cold pressure by the difference to the target. Change
> pressure only on such a report or a symptom that points directly at it — never as part of
> routine balance tuning (`setup-tuning-principles.md` → *Tyre pressure*).
```

Replace the line `**Tyre pressure sits outside the ladder** — held at the captured default, moved only on a reported` and its continuation `pressure symptom (see *Tyre feel* above).` with:

```markdown
**Tyre pressure sits outside the ladder** — set from the game version notes' target (or held at
the default where the notes give no rule), moved only on a gauge reading or a reported pressure
symptom (see *Tyre feel* above).
```

In the *Pre-drive briefing* numbered list, add after item 2 (the "what to pay attention to" list) a new item, renumbering the ones after it:

```markdown
3. **When the tyre is a medium compound**, one line: the first kilometres are on cold tyres — grip
   comes in after a few corners, so be careful until it does. And for tarmac in the current
   version: **read the tyre pressure gauge near the end of the run** and report the numbers — the
   game version notes say what they should be.
```

- [ ] **Step 5: SKILL.md — precedence, ladder bullet, file and script lists**

In the *Layered guidelines — the user wins* bullet, change `base principles →` followed by `bundled car troubleshooting` so the chain reads:

```
base principles → game version notes (`game-versions/<version>.md` for the current `GAME_VERSION`, found with `scripts/load_game_version_notes.py` — overrides the base for the rules it names) → bundled car troubleshooting (the matching file in `car-troubleshooting/`, if one exists — overrides the base for the symptoms it names) → global `Tuning guidelines` → …
```
Keep the rest of the bullet as it is.

In the fix-order ladder bullet, replace `**tyre pressure sits outside the ladder** and is held at the anchor unless a symptom points at it (ACR's pressure model isn't physically sensible).` with:

```
**tyre pressure sits outside the ladder** — its target comes from the game version notes (held at the anchor where the notes give no rule) and it moves only on a gauge reading or a pressure symptom.
```

In the file list, after the `car-troubleshooting/` bullet add:

```markdown
- `game-versions/` — bundled **per-game-version tuning notes**, one markdown file per version
  (`game-versions/0.6.md`), hand-written by the maintainer after each game release. Found with
  `scripts/load_game_version_notes.py` (exact `GAME_VERSION`, else the newest lower version, said
  in one line). Whenever a workflow loads its guideline layers it reads this file as the layer
  **right after the base principles**: it overrides them for the rules it names (in 0.6: tarmac
  tyre pressure target and cold start, tyre type by stage length, the gauge test-run routine).
```

In the script list, after the `load_default_setup.py` bullet add:

```markdown
- `scripts/load_game_version_notes.py` — prints the path of the `game-versions/` file for the
  skill's `GAME_VERSION` (`--version V` to ask for another; exit 1 = no notes, skip the layer).
```

- [ ] **Step 6: Run the tests**

Run: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`
Expected: `FAILED` with exactly these three still red: `test_build_uses_stage_length_and_the_pressure_target`, `test_tweak_moves_cold_pressure_by_the_gauge_difference`, `test_docs_pages_say_setups_follow_the_version_notes`, and `test_every_workflow_runs_the_notes_loader`. Everything else green. (If `test_banned_phrases` fails, a rewritten line contains `paste the` or another banned phrase — reword.)

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/acr-setup-engineer/SKILL.md .claude/skills/acr-setup-engineer/references/setup-tuning-principles.md .claude/skills/acr-setup-engineer/references/driving-feedback-interview.md tests/test_references.py
git commit -m "principles, interview, SKILL.md: game version notes layer; pressure target is a version fact"
```

---

### Task 4: build-setup.md reads the notes: layer, stage length, tyre type, pressure, report

**Files:**
- Modify: `.claude/skills/acr-setup-engineer/references/build-setup.md` — step 2 (~147–168), step 3 (~178–192), step 8 (~420–458), step 12 (~599–615), the rules list near the end (~658–659)

**Interfaces:**
- Consumes: the layer sentence from Task 3; `game-versions/0.6.md` section names (Task 1).

- [ ] **Step 1: Step 2 — insert the layer and renumber**

Replace the numbered list under `2. **Load the guideline layers**` so it reads:

```markdown
   1. **Base** — `setup-tuning-principles.md`.
   2. **Game version notes** — run `python scripts/load_game_version_notes.py` and read the file it prints (the tuning notes for the current game version, `game-versions/<version>.md`); when it prints a second `note:` line, say it in one line. **They override the base principles** for the rules they name (in 0.6: tarmac tyre pressure and tyre type by stage length). If it exits 1, skip this layer and say so in one line.
   3. **Bundled car troubleshooting** — check the `car-troubleshooting/` folder for a file whose
      name matches this car (same match rule as a bundled template — `onboard-car.md` step 1 →
      *Matching a car name* — e.g. `car-troubleshooting/lancia-037-evoluzione-2-1984.md`). **If one
      exists, read it and apply its symptom→fix entries — they override the base principles** for the
      symptoms they name. If no file matches, skip this layer.
   4. **Global user guidelines** — the Notion `Tuning guidelines` page (under `ACR Setup Engineer`).
   5. **Surface section** of those guidelines — the page's "Per surface" subsection matching the
      build surface (step 3 fixes the surface; this is not a separate page).
   6. **Per-car guidelines** — the car's `Guidelines` page.
```

Change `(base < troubleshooting < global < surface < per-car < intent)` to `(base < version notes < troubleshooting < global < surface < per-car < intent)`.

- [ ] **Step 2: Step 3 — read the stage length; ask when missing on tarmac**

In step 3, after the sentence ending `…they feed reasoning the same way the car's identity facts do.` insert:

```markdown
   **Read the stage's length too.** The game version notes pick the tarmac tyre type by it (in 0.6:
   under 8 km `Tarmac Soft`, 8 km or more `Tarmac Medium`) and the cold pressure with it. When the
   build surface is tarmac and no stage was given, or the stage page has no length, ask in one short
   line — "about how long is the stage?" — together with the conditions question below; if the user
   doesn't know, treat the stage as under 8 km and say so.
```

- [ ] **Step 3: Step 8 — tyre type by stage length; pressure from the notes**

In step 8's opening sentence, after `First pick the **tyre type** for the surface/conditions (biggest grip decision)` insert ` — **on tarmac, by stage length per the game version notes** (`game-versions/<version>.md` → *Tyre type on tarmac*; in 0.6 a stage of 8 km or more takes `Tarmac Medium`)`.

Replace the bullet starting `- **Tyre pressure is always two values**` (through `…(start in the upper half of the legal range).`) with:

```markdown
   - **Tyre pressure is always two values** — choose `Pressure Front` and `Pressure Rear` separately,
     never a single combined pressure. **The target comes from the game version notes**
     (`game-versions/<version>.md` → *Tyre pressure*): when the notes give a rule for the build
     surface, start from it — in 0.6, tarmac cold pressure 27 psi under 8 km and 26 psi at 8 km or
     more, both axles, hot target 28 — make it legal on the catalog grid (nearest legal value below
     when off it) and report it as `default → new (0.6 tyre notes)`. When the notes give no rule for
     the surface (gravel, snow in 0.6), **hold the default's pressures** and move them only on a
     reported pressure symptom. Without a baseline and without a notes rule, start in the upper
     half of the legal range (`setup-tuning-principles.md` → *Tyre pressure*).
```

- [ ] **Step 4: Step 12 — the two report lines**

In step 12 (*Report*), after `Summarise the setup (incl. tyre type), assumptions, which user guidelines were applied, and whether any checked prior setups were learned from.` insert:

```markdown
   **Two fixed lines from the game version notes:** when the tyre type is a medium compound, "the
   first kilometres are on cold tyres — be careful until the grip comes in"; and on tarmac, "read
   the tyre pressure gauge near the end of the run and tell me the numbers — the target is 28 psi
   hot; I'll move the cold pressure by the difference" (`game-versions/<version>.md` → *Finding the
   right cold pressure for a stage*).
```

- [ ] **Step 5: The rules list near the end**

Replace the bullet `- **Hold the default's tyre pressures** unless a symptom points at them; ACR's pressure model isn't` / `physically sensible, so the game's numbers beat the skill's reasoning.` with:

```markdown
- **Tyre pressure follows the game version notes.** Where the notes give a rule for the surface,
  it is the anchor (0.6: tarmac 28 psi hot, cold start below it); where they don't, hold the
  default's pressures unless a symptom or a gauge reading points at them.
```

- [ ] **Step 6: Check for other stale pressure sentences in the file**

Run: `grep -n -i "physically sensible\|hold the default's pressures\|hold its pressures" .claude/skills/acr-setup-engineer/references/build-setup.md`
Expected: only lines that carry the "where the notes give no rule" qualifier. Rewrite any other hit to the same shape as Step 5.

- [ ] **Step 7: Run the tests**

Run: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`
Expected: `FAILED` with only `test_tweak_moves_cold_pressure_by_the_gauge_difference`, `test_docs_pages_say_setups_follow_the_version_notes` and `test_every_workflow_runs_the_notes_loader` red.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/build-setup.md
git commit -m "build-setup: game version notes layer; tyre type by stage length; pressure target from the notes"
```

---

### Task 5: tweak, review, ask, the two Notion doc pages, tooling README and CLAUDE.md

**Files:**
- Modify: `.claude/skills/acr-setup-engineer/references/tweak-setup.md` (layer list ~70–80; pressure sentence ~147–149)
- Modify: `.claude/skills/acr-setup-engineer/references/review-setup.md` (layer list ~62–72)
- Modify: `.claude/skills/acr-setup-engineer/references/ask-setups.md` (layer list ~114–125; conceptual path ~41)
- Modify: `.claude/skills/acr-setup-engineer/references/how-to-use-template.md` (~40–43)
- Modify: `.claude/skills/acr-setup-engineer/references/free-plan-template.md` (~34–36)
- Modify: `tools/car-catalog/README.md` (new `## Game version notes` after `## Default setups`' *Running it*)
- Modify: `CLAUDE.md` (file list after the `GAME_VERSION` bullet ~55–58; the "After a game update" paragraph ~181)

**Interfaces:**
- Consumes: the layer sentence from Task 3.

- [ ] **Step 1: tweak, review, ask — the layer**

In each of `tweak-setup.md`, `review-setup.md`, `ask-setups.md`, in the guideline-layer list, insert as item 2 (renumbering 2–5 to 3–6):

```markdown
2. **Game version notes** — run `python scripts/load_game_version_notes.py` and read the file it prints (the tuning notes for the current game version, `game-versions/<version>.md`); when it prints a second `note:` line, say it in one line. **They override the base principles** for the rules they name (in 0.6: tarmac tyre pressure and tyre type by stage length). If it exits 1, skip this layer and say so in one line.
```

- [ ] **Step 2: tweak — pressure by the gauge difference**

In `tweak-setup.md`, replace `**Tyre pressure sits outside it**: leave it alone unless a symptom` / `points directly at it (ACR's pressure model isn't physically sensible — see` / `` `setup-tuning-principles.md` → *Tyre pressure*).`` with:

```markdown
**Tyre pressure sits outside it**: when the user reports an in-game gauge reading, move the cold
  pressure **by the difference** to the game version notes' target (0.6 tarmac: 28 psi hot), front
  and rear separately, **before** anything on the ladder; otherwise leave it alone unless a symptom
  points directly at it (`setup-tuning-principles.md` → *Tyre pressure*).
```

- [ ] **Step 3: ask — the conceptual path names the notes**

In `ask-setups.md` section `## 2. Conceptual path (no Notion)`, change `Answer from `setup-tuning-principles.md`:` to:

```markdown
Answer from `setup-tuning-principles.md`, and for anything the current game version changes (tyre
pressure target, which compound lasts a stage) from the game version notes —
`python scripts/load_game_version_notes.py` and read the file it prints:
```

- [ ] **Step 4: the two doc pages**

`how-to-use-template.md`: in the *Build a setup* bullet, after `(game version {game_version}).` insert ` They also follow the skill's tuning notes for game version {game_version} — in 0.6 that is the tyre pressure target and the tyre type for long stages.`

`free-plan-template.md`: after the bullet ending `…or asks for its screenshots.` add a new bullet:

```markdown
- **Setups follow the tuning notes for game version {game_version}**, built into the skill (in 0.6:
  tarmac tyre pressure aims at 28 psi hot, and a stage of 8 km or more gets medium tyres).
```

Check both placeholders stay `{game_version}` (not `{version}`).

- [ ] **Step 5: tooling README and CLAUDE.md**

`tools/car-catalog/README.md`, after the *Running it* subsection of `## Default setups` (before `## What it doesn't touch`), add:

```markdown
## Game version notes

`game-versions/<version>.md` in the skill is **hand-written**, never extracted: the tuning rules
that are true for one game version (0.6: tarmac hot pressure target 28 psi, cold start 27/26 by
stage length, `Tarmac Medium` on stages of 8 km or more, the gauge test-run routine). After a game
release, once `make extract` has bumped `GAME_VERSION`, copy the previous file to the new version
number, edit what changed, and run `make test` — `tests/test_game_version_notes.py` fails until the
current version has its own file. Until then `scripts/load_game_version_notes.py` falls back to the
newest lower version and says so.
```

`CLAUDE.md`: after the `GAME_VERSION` bullet in the file list add:

```markdown
  - `game-versions/<version>.md` — hand-written tuning notes for one game version (0.6: tyre
    pressure target and cold start, tyre type by stage length, gauge test runs). The guideline layer
    right after the base principles in every value-choosing workflow; found with
    `scripts/load_game_version_notes.py`. Copied and edited by hand after each game release —
    never generated.
```

And change the paragraph `After a game update, run `make extract` once; it refreshes …. Read the diff, run `make test`, commit.` to end with: `Then copy `game-versions/<old>.md` to `game-versions/<new>.md` and edit what changed — the notes are the one bundled file `make extract` does not write. Read the diff, run `make test`, commit.`

- [ ] **Step 6: Run the full suite**

Run: `python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran )"`
Expected: `OK`, 487 tests.

- [ ] **Step 7: Verify the zip check on a HEAD-built archive in a temp dir (not `dist/`)**

```bash
cd /c/Users/fred/w/acr-setup-engineer && T=$(mktemp -d) && git archive --format=zip --prefix=acr-setup-engineer/ HEAD:.claude/skills/acr-setup-engineer -o "$T/acr-setup-engineer-skill-dev.zip" && python check_zip.py "$T/acr-setup-engineer-skill-dev.zip"
```
Expected: `OK` (run after the commit in Step 8 if the archive must include this task's files; `git archive HEAD` reads the last commit).

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/tweak-setup.md .claude/skills/acr-setup-engineer/references/review-setup.md .claude/skills/acr-setup-engineer/references/ask-setups.md .claude/skills/acr-setup-engineer/references/how-to-use-template.md .claude/skills/acr-setup-engineer/references/free-plan-template.md tools/car-catalog/README.md CLAUDE.md
git commit -m "tweak, review, ask, doc pages, README, CLAUDE.md: game version notes layer and maintenance"
```

---

## Self-review against the spec

- File `game-versions/0.6.md` with four sections → Task 1. Resolution script with exact/lower/none/usage → Task 2. Precedence slot in SKILL.md, build, tweak, review, ask → Tasks 3–5. Stage length read and one-line question → Task 4 step 2. Tyre type by length, pressure from notes, `default → new (0.6 tyre notes)` → Task 4 step 3. Pre-drive cold-tyre line and gauge line → Task 3 step 4 and Task 4 step 4. Tweak by gauge difference → Task 5 step 2. Interview and principles rewritten → Task 3. Doc pages → Task 5 step 4. check_zip → Task 1. Maintenance in README and CLAUDE.md → Task 5 step 5. Guards → Task 3 step 1.
- Names used across tasks: `load_game_version_notes.py`, `game-versions/`, section headings, `0.6 tyre notes`, `about how long is the stage?`, `cold tyres`, `by the difference`, `tuning notes for game version {game_version}` — each appears verbatim in the task that writes it and in the guard that checks it.
- Test counts (467 → 471 → 479 → 487) assume 4, 8 and 8 new tests; if a count differs by the number of tests actually added, that is fine — the requirement is `OK`.
