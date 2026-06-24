# CLAUDE.md — maintainer notes

This repo packages a **single self-contained Claude Skill** that builds car setups for racing
games (built for **Assetto Corsa Rally**) and stores them in the user's **Notion**.

## Where things live
- **The product** is the skill at [.claude/skills/car-setups/](.claude/skills/car-setups/):
  - `SKILL.md` — entry point: core rules + routing to the three workflows.
  - `references/onboard-car.md`, `build-setup.md`, `import-savegame.md` — the workflows.
  - `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions,
    create-if-missing rules. **The source of truth for the data model.**
  - `references/notion-rest-read.md` — the way every workflow reads a car's rows: the Notion
    connector can't list database rows, so workflows query the data source over the REST API
    (`POST /v1/data_sources/{id}/query`) using a read-only token the user sets up once (README).
  - `references/setup-tuning-principles.md` — drivetrain-tagged tuning reasoning base.
  - `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- [README.md](README.md) — end-user docs (claude.ai install + usage).
- `Makefile` — `make zip` builds `dist/car-setups-skill.zip`; cross-platform (Mac, Linux, WSL, Git Bash on Windows).

The skill is **self-contained** (it bundles its own references) so it works both uploaded to
claude.ai and as a project skill in Claude Code. There is **no separate Notion bootstrap** — the
skill creates its Notion structure on first use, resolving everything **by name** (no hardcoded
IDs).

## Release procedure

The skill is distributed as a ZIP release asset on
[GitHub](https://github.com/fredmayor88/car-setups). The repo remote should point there.

```bash
# One-time: switch remote from CodeCommit to GitHub
git remote set-url origin https://github.com/fredmayor88/car-setups.git
git push -u origin main
```

For each release:

1. **Commit everything** you want in the release.
2. Write `RELEASE_NOTES.md` in the repo root (not committed — gitignored). One brief paragraph
   describing what changed; it becomes the GitHub release body.
3. `make check-zip` — verify entries use forward slashes and `SKILL.md` is at the top (run after
   step 4 below produces a ZIP, or rerun once `make release` has).
4. `make release TAG=vX.Y.Z` — stamps `VERSION` to the tag and commits it (so the archived skill
   self-reports its release version — see *Skill version* in `SKILL.md`), runs `make test`,
   rebuilds `dist/car-setups-skill.zip` from that committed tree, tags, pushes, and creates a
   draft GitHub release with the ZIP attached.
5. **Manual smoke test on claude.ai**: upload the ZIP (Settings → Customize → Skills → Create
   skill), attach min/max screenshots, say "onboard my car" — confirm Notion structure is
   created; then build a setup and check the mobile checklist and that the `Setups` row's
   `Skill version` matches the tag; attach a `.sav` and import (confirm `Skill version` is set
   there too).
6. Open the draft on GitHub, verify the asset downloads cleanly, then **Publish**.

`RELEASE_NOTES.md` and `dist/` are gitignored (binary churn; notes are ephemeral).

## Conventions
- Keep the skill self-contained: bundle anything it needs under `.claude/skills/car-setups/`;
  no `../` paths escaping the skill folder.
- Ship **no private Notion IDs** or personal data in tracked files.
- Edit the data model in `references/notion-structure.md`; edit tuning knowledge in
  `references/setup-tuning-principles.md`.
- Target platform is the **claude.ai web app** (Notion connector + Skills); a later move to
  Claude Code desktop is cheap since all data lives in Notion.

## Working guidelines for Claude
- After finishing a feature or request, **do not run `make test` or build the ZIP
  (`make zip` / `make release`) by default** — only do so when explicitly instructed. These are
  part of the release procedure above, not a routine post-task check.
