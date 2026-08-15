# CLAUDE.md — maintainer notes

This repo packages a **single self-contained Claude Skill** that builds car setups for
**Assetto Corsa Rally** and stores them in the user's **Notion**.

## Where things live
- **The product** is the skill at [.claude/skills/acr-setup-engineer/](.claude/skills/acr-setup-engineer/):
  - `SKILL.md` — entry point: core rules + the workflow routing table.
  - The workflows: `references/onboard-car.md`, `build-setup.md`, `tweak-setup.md`,
    `review-setup.md`, `ask-setups.md`, `share-setup.md`, `import-savegame.md`,
    `export-car-template.md` — plus `driving-feedback-interview.md` (below), which the
    routing table also lists as an entry point.
  - `references/notion-structure.md` — Notion layout, schemas, view + mobile conventions,
    create-if-missing rules. **The source of truth for the data model.**
  - `references/notion-rest-read.md` — the way every workflow reads a car's rows: the Notion
    connector can't list database rows, so workflows query the data source over the REST API
    (`POST /v1/data_sources/{id}/query`) using a read-only token the user sets up once (README).
  - `references/setup-tuning-principles.md` — drivetrain-tagged tuning reasoning base.
  - `references/driving-feedback-interview.md` — the shared symptom→cause question bank (beginner
    interviewing rules, pre-drive briefing, gearing sub-interview) and the **fix-order ladder**.
    Read by `build-setup.md` (baseline-first flow) and `tweak-setup.md` (vague feedback).
  - `references/tuning-guidelines-template.md` — seed for the user's editable guidelines page.
- [README.md](README.md) — end-user docs (claude.ai install + usage).
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
