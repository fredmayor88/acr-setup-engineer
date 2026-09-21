# CLAUDE.md — maintainer notes

This repo packages a **single self-contained Claude Skill** that builds car setups for
**Assetto Corsa Rally** and stores them in the user's **Notion**.

## Where things live
- **The product** is the skill at [.claude/skills/acr-setup-engineer/](.claude/skills/acr-setup-engineer/):
  - `SKILL.md` — entry point: core rules + the workflow routing table.
  - The workflows: `references/onboard-car.md`, `build-setup.md`, `tweak-setup.md`,
    `review-setup.md`, `ask-setups.md`, `share-setup.md`, `capture-setup.md`,
    `import-savegame.md`, `export-car-template.md`, `edit-catalog.md` (change a car's parameter
    list in chat), `refresh-notion.md` (every car at once) — plus
    `driving-feedback-interview.md` (below), which the routing table also lists as an entry point.
  - `references/how-to-use-template.md` and `free-plan-template.md` — the two skill-owned Notion
    documentation pages. `tests/test_notion_docs_pages.py` fails when a routed workflow is missing
    from the `How to use` template's `Covers:` line — give the page a line for it, then add it.
    `tests/test_references.py` guards the references against the machinery this design removed —
    catalog snapshots, `Parameters` DB reads, paste routes — and checks that every
    catalog-loading workflow points at `catalog-read.md`.
  - `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions,
    create-if-missing rules. **The source of truth for the data model.**
  - `references/notion-rest-read.md` — the way every workflow reads **rows in Notion**: the
    connector can't list database rows, so `Setups` slices are queried over REST with a read-only
    token. **Catalogs are never read that way**: every car's catalog is a template file — bundled,
    or the `yaml` block on the car's `Parameters` page — read by `scripts/load_catalog.py` via
    `references/catalog-read.md`.
  - `references/catalog-read.md` — the **one** path that loads a car's catalog, for every
    workflow that needs legal values. The two kinds of car are defined in
    `references/notion-structure.md` → *Where a car's catalog lives*.
  - `scripts/` — the stdlib-only Python the skill runs in the user's code sandbox (no PyYAML
    there): `parse_acr_save.py` (save-file import), `load_catalog.py` (a template file read as a
    catalog — rows in the REST read's shape, surface resolution, `--check` validation,
    `--to-template`) and `query_notion_parameters.py` (`Setups` reads and
    `--show-order --from-template`).
  - `references/setup-tuning-principles.md` — drivetrain-tagged tuning reasoning base.
  - `references/driving-feedback-interview.md` — the shared symptom→cause question bank (beginner
    interviewing rules, pre-drive briefing, gearing sub-interview) and the **fix-order ladder**.
    Read by `build-setup.md` (baseline-first flow) and `tweak-setup.md` (vague feedback).
  - `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- [README.md](README.md) — end-user docs (claude.ai install + usage).
- `car-charts/` — the power/torque chart PNG per car, generated from the ACR game files.
  **Committed and served by public raw URL**, not bundled in the skill ZIP: a skill on claude.ai
  has no way to push a local file into Notion, so the car page attaches the chart from its URL
  (which is also why the template stores a URL, not a path). Regenerate with `make charts`
  (`tools/torque-curves`); never hand-edit.
- `tools/torque-curves/` — maintainer-only extractor (needs a local ACR install, node + python).
  Reads each car's `FC_<Car>_Torque` curve out of the pak files, renders `car-charts/`, and rewrites
  the delimited `# --- engine curve … ---` stanza in each bundled template. Its README documents the
  IoStore/Oodle handling, the parser heuristic, and the sanity check that catches a game update
  breaking it. Re-run after a physics-touching patch or when a car is onboarded (add it to
  `CAR_MAP` first).
- `tools/gearing-charts/` — maintainer-only, same requirements. Holds the shared game-file
  readers (gear sets, tyres, final drives, template facts) other tools import, the rev-limit
  calibration (`calibration.py`), and the ACR Car Lab exporter (`export_car_data.py`, run with
  `make car-lab`, which writes into the sibling `acr-car-lab` checkout). The per-car gearing and
  final drive PNG charts this directory used to render were replaced by the ACR Car Lab web tool;
  each template links to its page there through its `gearing_tool:` field. Add new cars to `CARS`
  first.
- `tools/car-catalog/` — maintainer-only. Rebuilds every template's `parameters:` block (Min/Max/
  Discrete steps) straight from the game's setup-preset assets, so a game update is a re-run instead
  of a fresh round of screenshots. See its README.
- `Makefile` — `make zip` builds `dist/acr-setup-engineer-skill-<version>.zip`, where `<version>` is
  read from **HEAD's** `VERSION` file so the filename always matches the `VERSION` inside the
  archive (`make check-zip` enforces that). On an unstamped checkout that's the previous release's
  tag, so build the ZIP *after* `stamp-version` — which `make release` already does. `make clean`
  removes `dist/`. Cross-platform (Mac, Linux, WSL, and Windows from **both** Git Bash and
  PowerShell/cmd). **Keep recipes free of shell-specific syntax** — make uses cmd.exe when invoked
  from PowerShell, where `2>/dev/null`, `||`, `rm -rf` and `echo > file` all misbehave; do that work
  in `python -c` instead. Assume GNU Make 3.81 (no `$(file <...)`).

The skill is **self-contained** (it bundles its own references) so it works both uploaded to
claude.ai and as a project skill in Claude Code. There is **no separate Notion bootstrap** — the
skill creates its Notion structure on first use, resolving everything **by name** (no hardcoded
IDs).

## Writing rule — every workflow must work on a less capable model

The references are executed by whatever model the user runs, often Sonnet. Write them so that
model gets it right without judgement calls:

- Short numbered steps. One decision per step, stated as a question with its answers.
- The exact wording to say to the user, in quotes, wherever a line is required.
- A script does anything deterministic: parsing, YAML, validation, ordering, dates. The model
  never hand-formats YAML, never computes a `SHOW` list, never guesses a date.
- Say which file to read *before* the step that needs it, not after.
- One place per rule. Other files point at it; they don't restate it.

## Release procedure

The skill is distributed as a ZIP release asset on
[GitHub](https://github.com/fredmayor88/acr-setup-engineer). The repo remote should point there.

```bash
# One-time: switch remote from CodeCommit to GitHub
git remote set-url origin https://github.com/fredmayor88/acr-setup-engineer.git
git push -u origin main
```

For each release:

1. **Commit everything** you want in the release.
2. Write `RELEASE_NOTES.md` in the repo root (not committed — gitignored); it becomes the GitHub
   release body. **Always format it as a bullet-point list of the user-facing changes** (one
   bullet per change, optionally under a `What's new in vX.Y.Z:` line) — first review the full
   `git log`/`git diff` since the previous tag so no change is missed. Exclude maintainer-only
   churn (e.g. CLAUDE.md working notes, the VERSION stamp).
3. `make check-zip` — verify entries use forward slashes, `SKILL.md` is at the top, and the
   version in the ZIP filename matches the `VERSION` file inside it (run after
   step 4 below produces a ZIP, or rerun once `make release` has).
4. `make release TAG=vX.Y.Z` — stamps `VERSION` to the tag and commits it (so the archived skill
   self-reports its release version — see *Skill version* in `SKILL.md`), runs `make test`,
   rebuilds `dist/acr-setup-engineer-skill-vX.Y.Z.zip` from that committed tree, tags, pushes, and creates a
   draft GitHub release with the ZIP attached.
5. **Manual smoke test on claude.ai**: upload the ZIP (Settings → Customize → Skills → Create
   skill), attach min/max screenshots, say "onboard my car" — confirm Notion structure is
   created; then build a setup and check the mobile checklist and that the `Setups` row's
   `Skill version` matches the tag; attach a `.sav` and import (confirm `Skill version` is set
   there too).
6. Open the draft on GitHub, verify the asset downloads cleanly, then **Publish**.

`RELEASE_NOTES.md` and `dist/` are gitignored (binary churn; notes are ephemeral).

## Conventions
- Keep the skill self-contained: bundle anything it needs under `.claude/skills/acr-setup-engineer/`;
  no `../` paths escaping the skill folder.
- Ship **no private Notion IDs** or personal data in tracked files.
- Edit the data model in `references/notion-structure.md`; edit tuning knowledge in
  `references/setup-tuning-principles.md`; edit the diagnostic questions and the fix-order ladder in
  `references/driving-feedback-interview.md` (the ladder is authored there and *referenced* from
  `setup-tuning-principles.md`, `build-setup.md`, `tweak-setup.md` and `SKILL.md` — keep those
  pointers, don't restate the order in several places).
- **Flow diagrams live in the README as Mermaid**, not as images — they diff in review and can't
  go stale silently the way a PNG does. The hand-drawn `docs/*_flow.png` / `docs/knowledgeFlow.png`
  files are **superseded and no longer referenced**; don't re-add them. When a workflow changes,
  update the matching Mermaid block under *Flows*.
- `docs/notionConnectionSetup{,2,3}.png` are referenced from the token-setup steps. `…Setup3.png`
  **had** the author's email visible in a Notion tooltip; it is now redacted with an opaque fill,
  and the pre-redaction blobs were purged from git history (`git filter-repo`, force-pushed).
  Before adding any new screenshot, check it for personal data — and make redactions **opaque**,
  never a translucent brush stroke (the first attempt was recoverable by raising the contrast).
- Target platform is the **claude.ai web app** (Notion connector + Skills); a later move to
  Claude Code desktop is cheap since all data lives in Notion.

## Working guidelines for Claude
- After finishing a feature or request, **do not run `make test` or build the ZIP
  (`make zip` / `make release`) by default** — only do so when explicitly instructed. These are
  part of the release procedure above, not a routine post-task check.

### Car templates and charts: get it from the game files

Whenever asked to **create or update a car template or its charts**, the default is to extract
**everything you can** from the ACR game files with the `tools/` extractors. Don't ask for
screenshots of anything the files already hold — the parameter catalogue in particular is fully
extractable, and asking for min/max setup screens for it is redoing solved work.

- **Ask for one thing: the in-game car-info screen.** It carries the display name, year, engine,
  max power, max torque, weight and steering lock in a single capture. Two known traps (both hit
  on real cars) are written up in `bootstrap_header()` in `tools/car-catalog/extract_car_catalog.py`:
  the steering-lock figure is sometimes the per-side angle, and the engine description can be
  wrong. Read them before transcribing.
- **The one capture the files genuinely can't replace** is the brake setup screen — brake discs
  and calipers, plus `Engine Map` / `Throttle Map` / `Proportioning Preload` on the rare car that
  has them. Everything else in the catalogue comes from the files.
- **Before concluding anything "isn't in the game files", read
  [tools/car-catalog/README.md](tools/car-catalog/README.md).** It records what has been ruled out
  *with the evidence*, and the naming pattern that usually cracks a new field: `DT_<Thing>Lists`
  holds per-car option lists and parses with the plain `datatable.rows()` reader, while
  `DT_<Thing>` holds part records needing struct-level parsing. Wiring a new one up is usually a
  `WANTED_TABLES` entry plus a lookup. A previous session wrote off tyres, pads and master
  cylinders as screenshot-only; all three turned out to be extractable.
- **Validate every new extraction against the screenshot-onboarded templates before trusting it.**
  There are 14 of them and they are ground truth. Every extractor in `tools/` was confirmed this
  way (identity facts matched all 14; master-cylinder bores matched every car that has them), and
  the exercise also surfaced typos in the hand-entered values — so when derived and hand-entered
  values disagree, suspect the hand-entered one.
- **Keep the blast radius to the car you were asked about.** All four extractors take `--car`;
  use it. Re-running a tool across every car rewrites templates you weren't asked to touch, and
  on Windows (`core.autocrlf=true`) that also sprays line-ending-only "modified" flags with no
  content change.
