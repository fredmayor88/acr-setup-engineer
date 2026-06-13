# Car Setups — your personal AI rally setup engineer for Assetto Corsa Rally

A free Claude **Skill** that crafts **personalized** car setups for **Assetto Corsa Rally** —
tuned to *your* driving style and preferences — and saves them to **your Notion**, so you can
read them on your phone while you play. It's not a one-off generator but a **complete system for
the whole life of a setup**: onboard a car, build a setup, tweak it on feedback, review it,
share it, and import what you already have. It was built for ACR but the approach is general.

> **Video walkthrough:** *(coming soon — YouTube link will go here)*

**What it does**
1. **Onboards a car** — learns a car's full parameter catalog from min/max setup screenshots (or,
   for cars that have a bundled template, instantly with no screenshots needed). Stores
   everything in your Notion `Parameters` table.
2. **Builds a setup for a stage** — describe the stage and how you like the car to feel; it
   writes a setup constrained to the car's legal values, with the justification stored on the
   Notion page.
3. **Tweaks a setup on feedback** — describe what felt wrong after a run and it proposes a
   minimal, targeted set of changes as a new setup (the original is never touched).
4. **Reviews an existing setup** — critiques a setup already in your Notion: checks for
   constraint violations, guideline alignment, and internal consistency, then appends a
   timestamped AI Review section to the setup's Notion page.
6. **Shares a setup** — produces a compact, copy-pasteable plain-text summary you can drop
   into Discord, WhatsApp, or a forum.
7. **Imports your existing setups** — from an ACR save file, so it can learn from what already
   works for you.

Together these cover the **whole lifecycle of a setup** in one place. Every value stays within
what the car actually allows, and the setups get **more personal the more you use it** — rate
your setups and tick "Learn from this" on the good ones, and future setups follow your taste.

**Other games:** this skill was built and tested exclusively for **Assetto Corsa Rally**. You
may be able to onboard cars and build setups for other rally/racing games, but this has not been
tested and is not supported. Use it for other games entirely at your own risk — no support will
be provided for non-ACR use. **Save-file import is ACR-only.**

---

## Before you start (prerequisites)

- A **Claude account** at [claude.ai](https://claude.ai). Works on the **Free** plan; for heavy
  use the **Pro** plan is smoother. *(The Skill is free — running Claude a lot may not be.)*
- A **Notion account** (free is fine). All your setups live here.

## Setup (one time, ~5 minutes)

1. **Connect Notion.** In claude.ai → **Settings → Connectors**, add **Notion** and authorize
   it. (One click; available on every plan.)
2. **Turn on code execution + Skills + network.** Settings → **Capabilities** → enable **Code
   execution** and **Skills**. Then under **Network egress** set the domain allowlist to **All
   domains** — the skill needs this to call Notion's API from the code sandbox.
3. **Add the skill.** Download **`car-setups-skill.zip`** from this project's
   [Releases](../../releases). In claude.ai → Settings → **Customize → Skills → Create skill**,
   upload the ZIP.
4. **Onboard your first car.** Start a new chat and say *"Onboard the [car name] for Assetto
   Corsa Rally."* — see [Quick start](#quick-start) for details. This creates your Notion
   structure (the Car setups page and its tables).
5. **Give the skill read access to Notion** *(takes ~3 minutes).* The skill reads your tables
   through Notion's **API** so every read is fast, exact, and cheap.

   1. **Create a read-only integration.** Go to
      [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration** →
      **Internal**, in your workspace. Under **Capabilities**, leave **only "Read content"**
      checked (uncheck Update and Insert). Copy the **Internal Integration Secret**
      (`secret_…` / `ntn_…`).
   2. **Connect it to only your data.** Open your **Car setups** page in Notion → **•••** →
      **Connections** → add your integration. Access cascades to everything under it (your
      Parameters/Setups) — **and nothing else** in your workspace. The token is read-only and
      can't see anything you didn't connect.
   3. **Give the skill the token** (pick one):
      - **Store it (recommended):** make a page named **`Config`** under **Car setups** and
        paste the token onto it. The skill reads it automatically — set once, works in every
        chat. (It's safe here: the token is read-only and only unlocks the data it sits next
        to.)
      - **Paste per chat:** don't store it; paste it when the skill asks. Nothing is saved.

   The skill detects the token and reads your setups in one exact call.

## Quick start

**Onboard your first car**

Say: *"Onboard the Lancia Stratos HF for Assetto Corsa Rally."*

- If the car has a **bundled template**, Claude will offer to auto-populate Notion from it —
  no screenshots needed.
- Otherwise, take two sets of screenshots of the car's Setup screens in ACR (everything at minimum,
  then everything at maximum), attach them, and Claude reads every setting's range from the
  images.

Either way, your Notion structure is created automatically on first use. Claude also looks up the
car's **engine layout, weight bias, and approximate weight** (facts the game doesn't show) to
personalize how it balances setups — you can edit any of these on the car's Notion page.

**Build a setup**

Tell Claude the car, the stage, and how you like to drive — e.g.:
*"Build a setup for the Lancia Stratos on a fast, bumpy tarmac stage; I like gentle
throttle-on rotation and hate a floaty car under braking."*

The new setup row appears in your Notion `Setups` database. Open it on your phone to see the
values and the reasoning behind each choice. After driving: set a **Rating**, add **Notes**,
and tick **Learn from this** if you liked it — future setups learn from the ones you've checked.

**Tweak a setup**

After driving, describe what felt wrong — e.g.: *"The Alsace setup understeers on entry —
can you soften the front ARB?"* Claude maps the feedback to specific parameters, proposes a
minimal set of changes (with a before/after diff to confirm), and creates a new setup row
based on the original. The source setup is never modified.

**Review a setup**

Say: *"Review my alsace gpt1 setup."*

Claude checks every value against the car's legal ranges and the tuning guidelines, flags
anything misaligned, and suggests specific alternatives with reasoning. The review is printed in
chat and added as a timestamped section at the bottom of the setup's Notion page.

**Import setups you already made**

Attach your `CarSetupsDataSaveSlot.sav` (Windows: `%LOCALAPPDATA%\acr\Saved\SaveGames\`) and
say *"Import my setups from this save."* Claude reads the file, shows you what it found, and
— once you confirm — adds the setups to Notion.

## Pin a setting to specific values (optional)

Onboarding records each setting's **minimum and maximum**. For a continuous setting that's all
the tool needs — it picks a value in range and tells you to dial to the nearest click in-game.

But some settings only offer a **few exact values** (e.g. spring stiffness with 4–5 steps), and
some are **named options** with no min/max (gear set, brake caliper type). These live in the
**`Discrete steps`** column — a comma-separated list, e.g. `42300, 50000, 57700, 65400, 73100`
or `Short, Medium, Long`. When filled, every setup picks **only** from those values; leave it
blank to keep the setting continuous.

For named options, onboarding **pre-seeds `Discrete steps` with whatever the screenshots show**
(usually the two endpoints) so you start from those instead of a blank cell — just open the car's
**`Parameters`** table in Notion and add any missing in-between options. On Assetto Corsa Rally,
tyre compounds and brake pads (`SOFT, MEDIUM, HARD`) come fully pre-filled and ready to use.

During onboarding, Claude flags the settings most likely to need this: spring stiffness, ARBs,
and all damper channels (these typically have just a handful of in-game click positions).

## Make it tune to your taste

The tool reasons from built-in tuning knowledge **plus your own preferences**, and **your
preferences win**. Edit those in Notion — no files, no code:

- a global **`Tuning guidelines`** page (overall style, likes/dislikes, per-surface notes)
- a **"Guidelines"** section on each car's page for car-specific quirks

Future setups follow whatever you write there.

## Car template library

The skill ships with community-contributed parameter templates in `car-templates/`. When
onboarding a car that has a template, all parameters (including pre-filled `Discrete steps`)
are loaded from the template — no screenshots needed.

To contribute your own car: once onboarded, say *"Export a template for the Lancia Stratos"*
— Claude formats the car's Notion parameters as a YAML file and optionally opens a GitHub PR
to add it to the library. (the PR functionality coming soon)

## Troubleshooting

- **Claude doesn't use the skill** → start a fresh chat; make sure **Skills** and **Code
  execution** are enabled (Settings → Capabilities) and the skill is toggled on.
- **Don't use Haiku for onboarding** → Haiku struggles to read values off the min/max setup-screen
  screenshots and will misread settings. Use **Sonnet** or **Opus** for onboarding.
- **Sonnet gets flagged for no reason** → if Sonnet trips a refusal/safety flag on a perfectly
  ordinary request, switch to **Opus** — it's confirmed to work fine.
- **It can't reach Notion** → re-check the **Notion connector** (Settings → Connectors).
- **Set up the API token but reads are still slow** → double-check that **Network egress** is set
  to **All domains** in Settings → Capabilities (see setup step 2). Without it the sandbox can't
  reach `api.notion.com` and falls back to the slower connector read.
- **Hitting limits on Free** → the workflow does several steps; the Pro plan has more headroom.
- **A value looks slightly "off"** → expected for continuous settings: dial to the nearest
  in-game position. To force exact values, fill `Discrete steps` in Notion (see above).
- **Where's my data?** → entirely in **your** Notion. Screenshots and save files you attach go
  to Claude to read; nothing is stored by this project.

## Notes

- **Assetto Corsa Rally is in early access** — tyre compounds and some settings change between
  builds. Treat the guidance as a strong starting point and verify in-game.
- Tuning advice is distilled from community guides and physics; it's not guaranteed to be the
  fastest for you — your own ratings and notes are what make it personal. Sources include (among
  others): [SETUPS para Assetto Corsa Rally (ACR) EXPLICADO](https://www.youtube.com/watch?v=0aseHRowyVs),
  [The ULTIMATE Setup Guide for EA SPORTS WRC | Every Setting Explained](https://www.youtube.com/watch?v=dIEXCHuT72U),
  [Assetto Corsa Rally SETUP GUIDE - SUSPENSIONS Explained](https://www.youtube.com/watch?v=N0W4iptyQVo).

## License

[AGPL v3](LICENSE) — free to use, modify, and share; modifications must remain open-source.

---

### For maintainers

The skill source lives in [.claude/skills/car-setups/](.claude/skills/car-setups/) — a
self-contained Claude Skill (`SKILL.md` + bundled `references/` and `car-templates/`). It also
works as a project skill in Claude Code. See [CLAUDE.md](CLAUDE.md) for the full release
procedure; the short version: `make zip` builds `dist/car-setups-skill.zip`, then
`make release TAG=vX.Y.Z` drafts the GitHub release.
