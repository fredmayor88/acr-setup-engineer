# How to use template (seed for the Notion page)

This is the seed for the **`How to use`** page directly under the `ACR Setup Engineer` root: a short,
phone-readable list of what the user can ask for, the one command to run after updating the skill,
and who owns which page. It is **skill-owned and auto-maintained**, exactly like `Parameter
reference` (`notion-structure.md` → *`How to use` and `Claude Free plan` pages*): rewritten in full
whenever the skill version changes, and by *"refresh my ACR Notion"*.

> When writing the Notion page, copy everything below the line. Replace `{version}` with the skill
> version (`SKILL.md` → *Skill version*). Replace `{game_version}` with the content of the skill's
> `GAME_VERSION` file (`python scripts/load_default_setup.py --game-version`). Write **`After you
> update the skill`** as a normal heading and each other `##` section as a **collapsed toggle
> heading**, so the page opens short on a phone. Keep the prompts exactly as written — the user
> copies them.

Covers: onboard-car.md, build-setup.md, tweak-setup.md, driving-feedback-interview.md, review-setup.md, ask-setups.md, share-setup.md, capture-setup.md, import-savegame.md, export-car-template.md, edit-catalog.md, refresh-notion.md, setups-list-read.md

---

# How to use

> *Maintained by the skill ({version}). Don't write here: updates replace this page.*

**On Claude's Free plan?** Read the **`Claude Free plan`** page next to this one first.

## After you update the skill

Say **"refresh my ACR Notion"**. It updates this page, `Claude Free plan`, `Parameter reference`
and every car's pages. It never changes your setups, your `Guidelines`, your `Tuning guidelines`
or your notes on a car's `Log`.

To update one car only: **"refresh the Lancia Stratos in my Notion"**.

## What you can ask

Swap in your own car, stage and setup names.

- **Add a car** — "onboard the Lancia Stratos". Bundled cars are ready at once. For other cars,
  attach screenshots of the setup screens with everything at minimum, then at maximum.
- **Build a setup** — "build a setup for Col de Turini with the Lancia Stratos". Say how you like
  the car to feel, and it builds for you. Setups start from the game's own default for the car and
  surface (game version {game_version}). They also follow the skill's
  tuning notes for game version {game_version} — in 0.6 that is the tyre pressure target and the
  tyre type for long stages. Say "start from the Aggressive preset" for a car that has one on
  tarmac (Lancia Delta, Peugeot 208 Rally4).
- **Change a setup after driving** — "stratos turini understeers on corner entry". It suggests
  changes in the chat and saves a new setup only when you ask.
- **Not sure what's wrong** — "I drove stratos turini, it felt off". It asks a few simple
  questions to find the problem.
- **Review a setup** — "review stratos turini". A rally mechanic's verdict: is it right for this
  stage and for you, and what to change before the start.
- **Ask a question** — "why is the rear anti-roll bar so soft in stratos turini?", or "what does
  diff preload do?".
- **Share a setup** — "share stratos turini". Plain text to paste anywhere.
- **Index your older setups** — "index these setups:" followed by the Notion links of the setups
  you want the skill to know about (open a setup in Notion and copy its link). Do this once after
  you install a new version. Setups the skill saves are listed by itself on the car's `Setups`
  page under `Setup index`; add ` - learn: yes` to the end of a line to always learn from that
  setup, or ` - learn: no` to never read it.
- **Save your own setup** — "store these screens as my tarmac for the Lancia Stratos", with photos
  of the setup screens.
- **Import a save file** — "import my setups from this save file", with the game's `.sav` file
  attached.
- **Use your own ranges for a car** — "onboard the Lancia Stratos from my screenshots". For when
  the game changed and the bundled list is behind.
- **Change a car's parameter list** — "the Lancia Stratos' front anti-roll bar goes 1 to 6 in
  steps of 1". It checks the change and updates the car's list.
- **Share a car you onboarded** — "export the Lancia Stratos as a template", so other drivers get
  it too.

## Which page is whose

- **`Tuning guidelines`** and each car's **`Guidelines`** — yours. The skill reads them and never
  writes to them.
- Each car's **`Log`** — shared. Write your own notes anywhere; the skill adds a dated entry each
  time you tell it how a drive felt, and never changes anything already there.
- Each car's **`Setups`** — the skill adds setups and keeps the `Setup index` list under the
  table; your own edits to setups are never overwritten, and the only part of the list you edit
  is a ` - learn: yes` / ` - learn: no` at the end of a line.
- **`How to use`**, **`Claude Free plan`**, **`Parameter reference`** and each car's **`Catalog`**
  — the skill's. Updates replace them, so don't write there.
- **`Config`** — holds your read-only Notion token, if you set one up.
