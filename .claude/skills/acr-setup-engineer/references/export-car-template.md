# Workflow: export a car parameter template

Hand over a screenshot car's catalog file as a shareable community template. The catalog is
already a template-format YAML file on the car's `Parameters` page; export loads it, normalises
its header, and gives the user the result. Once added to the skill's
`.claude/skills/acr-setup-engineer/car-templates/` folder (the same one the bundled templates live in),
lets future users onboard the same car without screenshots.

## Trigger phrases
"export template", "export car template", "create bundle file", "share my parameters",
"contribute my car", "submit my car setup parameters", or any request to produce a shareable
parameter file for a car.

**Also entered from onboarding.** `onboard-car.md` step 10 offers this at the end of a
**screenshot** onboarding — the case where the user has just hand-built a catalog for a car with no
bundled template, and is therefore the only person who can contribute it. That path is
screenshot-only by definition, so step 0 below never applies to it; the car's file is
**already in hand**, so see the note in step 1.

## Inputs
- **Car name** — ask if not provided or ambiguous (must match a car already onboarded in Notion).
- **Game version** — the version the parameters were captured in (e.g. `0.4`), since tunable
  ranges can shift between versions. **Step 0 already reads it**: a screenshot car's
  `Catalog source:` line carries the version the user gave when they uploaded the screenshots
  (or the literal `unknown`). Take it from there and **don't ask again**. Only ask when that line
  is missing entirely — a car onboarded before the line existed — and write `"unknown"` if the
  user doesn't know. (No other Notion lookup — never infer it from existing setups.) The file's
  own `version:` header line normally already carries it.

## Procedure

### 0. Is there anything to export?
Read the car's `Catalog source:` line (`notion-structure.md` → *Where a car's catalog lives*).
**A template car has nothing to export** — its catalog is already a bundled file. Say so in one
line and stop:

> "The {Car} already uses the bundled template `car-templates/{slug}.yaml` (game version
> {version}, from {game files | a community export}) — that file *is* its catalog, so there's
> nothing in your Notion to export."

The rest is for **screenshot cars** (including a bundled car the user edited in chat).

### 1. Get the file
Load the catalog per [catalog-read.md](catalog-read.md): the car's `Parameters` page, saved as
`parameters/<slug>.yaml`. **That file is the export.** Arriving from `onboard-car.md` step 10,
you already hold the `--to-template` output from the write — save it as `parameters/<slug>.yaml`
and use it, don't re-fetch. **Unless the user has changed the list since** (an `edit-catalog.md`
run, typically filling in the `Discrete steps` the onboarding report asked for): then load the
car's catalog again per `catalog-read.md`, because those edits live only on the page.

Also read the car's `Drivetrain` and its identity facts (`Engine layout`, `Weight bias`, `Weight`,
`Max power`, `Max torque`, `Class`, `Gearbox`, `Steering lock`) from its `Catalog` page **only if
the file's header is missing them** — the header normally already carries them.

### 2. Completeness check
Before formatting, scan for gaps and warn (but do NOT block the export):

- **Unnamed enumeration params** (`min: "—"` and `max: "—"`) with a blank `discrete_steps`:
  list them explicitly — these entries export with an empty `discrete_steps`, making
  them unusable to anyone who imports the template without first filling it in.
- **Flagged numeric params** (any entry where `min` or `max` is unexpectedly `"—"`): note them.

Show the warning as a numbered list of parameter names and what's missing. Then make one offer:
> "Say 'the {Car}'s {parameter} steps are …' and I'll add them, then export again."

Proceed on either answer; if the user wants to fill the gaps first, stop here.

### 3. Normalise the header
Rewrite the file's header for sharing, with Python (**never by hand**):
- `source: "community"`;
- delete `written_at`, `skill_version`, `parameter_count`, `forked_from`;
- keep everything else (`car`, `game`, `save_ids` if present, `drivetrain`, the identity facts,
  `version`).

The `parameters:` list is already in `Order` (`--to-template` sorted it; baseline before surface).
**Don't touch it** — don't reorder, reformat or "clean" a single entry.

Run this, with `SLUG` set to the car's slug:

```python
import pathlib

SLUG = '<slug>'                        # e.g. fiat-131-abarth-1976
DROP = ('written_at', 'skill_version', 'parameter_count', 'forked_from')

lines = pathlib.Path(f'parameters/{SLUG}.yaml').read_text(encoding='utf-8').split('\n')
out, in_header, seen_source = [], True, False
for line in lines:
    if in_header and line.startswith('parameters:'):
        if not seen_source:
            out.append('source: "community"')
        in_header = False
    if in_header and not line.startswith((' ', '\t', '#')) and ':' in line:
        key = line.split(':', 1)[0]
        if key in DROP:
            continue
        if key == 'source':
            line, seen_source = 'source: "community"', True
    out.append(line)

pathlib.Path('exports').mkdir(exist_ok=True)
pathlib.Path(f'exports/{SLUG}.yaml').write_text('\n'.join(out), encoding='utf-8')
print(f'exports/{SLUG}.yaml written')
```

It edits whole lines and only top-level (column-0) keys above `parameters:`, so every entry in the
list passes through byte-for-byte.

**What the header means** (for reading the result, not for retyping it):
- `source` — where the values came from: `"game-files"` for a maintainer's template extracted from
  the ACR game files, `"community"` for one a user exported. Always `"community"` here. It is read
  back into the car's catalog source line on import (`notion-structure.md` → *Car page*). A
  template with no `source:` line at all is treated as `community`.
- `version` — the game version the parameters were captured in, from the **Game version** input;
  `unknown` when it isn't known.
- `save_ids` — the exact in-save car string(s) ACR writes for this car, used by save-file import
  (`import-savegame.md` step 5.2) to match a save reliably. It is **normally absent** — Notion
  doesn't store the save string. Leave it as the file has it; never invent one.
- `power_torque_chart` / `engine_curve` / `gearing_tool` — **never in an export.** They are
  generated from the ACR game files by `tools/torque-curves` and `tools/gearing-charts` in the
  project repo, so the maintainer adds them when the car joins the bundled library. A template
  without them imports and onboards cleanly; the car page just gets no chart and no gearing link.
- The identity facts (`engine_layout`, `weight_bias`, `weight`, `max_power`, `max_torque`,
  `class`, `gearbox`, `steering_lock`) and the per-entry `order` and `surface` are **optional in
  both directions** — a template missing any of them imports exactly as before.

### 5. Verify the exported file loads
Before showing anything, run the loader on the file you just wrote:

```
python scripts/load_catalog.py exports/<slug>.yaml
```

It must exit 0. Then compare its output with the catalog you loaded in step 1:

- **Row count**: the same number of rows.
- **Adjustment names**: the same set, in the same order.

Anything else is a **bug in the header rewrite, not a gap** — fix it and re-run. (Genuinely blank
`discrete_steps` from step 2 are expected; a row that has steps in the loaded catalog but not in
the export is not.)

### 6. Present to user
Show the exported file's contents as a fenced code block in chat:

````
```yaml
<the contents of exports/<slug>.yaml>
```
````

Then tell the user:
> "Save this as `.claude/skills/acr-setup-engineer/car-templates/{slug}.yaml` in the skill repo — this is
> the **same folder the bundled templates live in**, so the skill picks it up automatically (a
> bare `car-templates/` at the repo root is the wrong place and won't be loaded). The slug is the
> car name lowercased with spaces and special characters replaced by hyphens, e.g.
> `lancia-stratos-hf.yaml`. Once committed, the skill will offer it automatically to anyone who
> onboards this car."

### 7. Offer to share it with the community
After showing the code block, invite the user to contribute it back — warmly, and without any
pressure:

> "You built this catalog from scratch, so right now it only lives in your Notion. If you share
> it, the next person who drives the **{Car}** can onboard it in one click — no screenshots, no
> typing. Want me to make a quick share link?
> (It just needs a free GitHub account. If you already have one, it'd be a lovely thing to give
> back to the community. No account, or not in the mood? No problem at all — we'll skip it.)"

- **If the user says yes:** Give them the **submission form link**. They sign in to GitHub (if
  asked), drop the YAML into one box, and click Submit. Nothing to install, no command line,
  and — this is the point — **no fork and no pull request**.

  ```
  https://github.com/fredmayor88/acr-setup-engineer/issues/new?template=car-template.yml&title=%5BCar+template%5D+{Car}
  ```

  where `{Car}` is the car name URL-encoded (spaces as `+`), e.g.
  `%5BCar+template%5D+Peugeot+208+Rally4+2020`. The form fills in the title and asks for the car
  name, game version, the YAML, and where the values came from.

  **Do NOT prefill the YAML body in the URL.** A template runs to several KB and a
  contents-prefilled link blows past GitHub's URL length limit — the user gets *"Your request URL
  is too long."* Prefill only the title; the user copies the body in from the code block above.

  **Do NOT send users to the `/new/main?filename=...` web-editor link.** Writing a file directly
  requires push access to this repo, which contributors don't have, so GitHub stops them with
  *"You need to fork this repository to propose changes."* The inline **Fork this repository**
  button on that screen fails outright for accounts that have never created a repo. That path
  loses people; the form doesn't.

  Then hand the user the link with friendly, jargon-free steps:
  > "Here's your share link: {link}
  >
  > 1. Click it (sign in to GitHub if it asks).
  > 2. **Copy the YAML I showed above** into the big *The YAML* box.
  > 3. Answer the two short questions above it, tick the two boxes at the bottom.
  > 4. Click the green **Create** button.
  >
  > That's it — the maintainers will review it and bundle it into the next release. Thank you 🙏"

- **If the user says no:** Done — no follow-up, no nagging.

## Rules
- Export reads the car's catalog; it never writes to the user's Notion.
- The export is a copy of the car's list as it is now. If the user changes it later
  (`edit-catalog.md`), they can re-run the export to get a fresh copy.
- Never include personal data (user name, email, Notion IDs) in the exported YAML.
- **Save-file import uses `version`** (`import-savegame.md` step 5): when a setup's game version
  matches it (major.minor), import validates and snaps that setup's values to the catalog
  ("official parse") instead of writing them as-is; an `"unknown"` version simply skips that check
  (import falls back to the as-is path).
