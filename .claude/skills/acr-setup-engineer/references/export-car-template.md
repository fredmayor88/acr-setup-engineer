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
- **Game version** — **not an input you collect.** The file's own `version:` line is
  authoritative: it was set when the car was captured, or carried over when it was forked from a
  bundled template. Take it from there and **don't ask**. The one exception is `version:
  "unknown"` — then ask once, *"Which game version did you capture the {Car} in? (If you're not
  sure, say so and I'll leave it as unknown.)"*, and if they give one, set it in step 3's snippet
  (`VERSION`). Never infer it from existing setups, and never hand-edit the line.

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
Scan the loaded catalog for gaps and warn (but do NOT block the export):

- **Unnamed enumeration params** (`min: "—"` and `max: "—"`) with a blank `discrete_steps`:
  list them explicitly — these entries export with an empty `discrete_steps`, making
  them unusable to anyone who imports the template without first filling it in.
- **Flagged numeric params** (any entry where `min` or `max` is unexpectedly `"—"`): note them.

Show the warning as a numbered list of parameter names and what's missing. Then make one offer:
> "Say 'the {Car}'s {parameter} steps are …' and I'll add them, then export again."

If they give you the steps, run `edit-catalog.md` and start this workflow again from step 1.
Anything else — carry on to step 3 with the gaps.

### 3. Normalise the header
Rewrite the file's header for sharing, with Python (**never by hand**):
- `source: "community"`;
- delete `written_at`, `skill_version`, `parameter_count`, `forked_from` (Notion-side
  bookkeeping — *Template file format* below);
- `version:` only if the user just gave one for an `unknown` file (*Inputs*) — the snippet
  rewrites that line, or adds one right before `source:` when the file has none;
- keep every other line the file has (`car`, `game`, `save_ids` if present, `drivetrain`, the
  identity facts, `version`) exactly as it is.

The `parameters:` list is already in `Order` (`--to-template` sorted it; baseline before surface).
**Don't touch it** — don't reorder, reformat or "clean" a single entry.

Run this, with `SLUG` set to the car's slug:

```python
import pathlib, sys

try:                                   # the file holds `—` and `°`; print them as UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SLUG = '<slug>'                        # e.g. fiat-131-abarth-1976
VERSION = None                         # or "0.7" — ONLY when the file says version: "unknown"
                                       # and the user just told you which version it was
DROP = ('written_at', 'skill_version', 'parameter_count', 'forked_from')

lines = pathlib.Path(f'parameters/{SLUG}.yaml').read_text(encoding='utf-8').split('\n')
out, in_header, seen_source, seen_version = [], True, False, False
for line in lines:
    if in_header and line.startswith('parameters:'):
        if VERSION and not seen_version:       # no version: and no source: line — both here
            out.append(f'version: "{VERSION}"')
        if not seen_source:
            out.append('source: "community"')
        in_header = False
    if in_header and not line.startswith((' ', '\t', '#')) and ':' in line:
        key = line.split(':', 1)[0]
        if key in DROP:
            continue
        if key == 'source':
            if VERSION and not seen_version:   # the file has no version: line — insert one
                out.append(f'version: "{VERSION}"')
                seen_version = True
            line, seen_source = 'source: "community"', True
        elif key == 'version':
            seen_version = True
            if VERSION:
                line = f'version: "{VERSION}"'
    out.append(line)

pathlib.Path('exports').mkdir(exist_ok=True)
pathlib.Path(f'exports/{SLUG}.yaml').write_text('\n'.join(out), encoding='utf-8')
print(pathlib.Path(f'exports/{SLUG}.yaml').read_text(encoding='utf-8'))
```

It edits whole lines and only top-level (column-0) keys above `parameters:` — inserting
`source:`, and `version:` when `VERSION` is set, if the file has no such line — so every entry in
the list passes through byte-for-byte. **It prints the finished file** — that printed text is what
step 5 shows the user, and it is the only version of the file you may show.

### 4. Verify the exported file loads
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

### 5. Present to user
Step 3's snippet printed the finished file. Show **exactly that printed text**, unchanged, in one
fenced ```` ```yaml ```` code block — **never retype or reformat it**, and never rebuild it from
the pre-normalisation file:

````
```yaml
<the text step 3 printed, verbatim>
```
````

Then tell the user:
> "Save this as `.claude/skills/acr-setup-engineer/car-templates/{slug}.yaml` in the skill repo — this is
> the **same folder the bundled templates live in**, so the skill picks it up automatically (a
> bare `car-templates/` at the repo root is the wrong place and won't be loaded). The slug is the
> car name lowercased with spaces and special characters replaced by hyphens, e.g.
> `lancia-stratos-hf.yaml`. Once committed, the skill will offer it automatically to anyone who
> onboards this car."

### 6. Offer to share it with the community
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

## Template file format

Reference for anyone reading a template file — **not a procedure step.** Every one of these files
is produced by `python scripts/load_catalog.py --to-template rows.json` (bundled cars: by the
maintainer tools in `tools/car-catalog` and `tools/torque-curves`). **Never write or edit one by
hand**, here or anywhere else.

```yaml
car: "Lancia Stratos HF 1976"                  # the car's name, as Notion and the game show it
game: "ACR"
save_ids: ["LanciaStratosHF"]                  # optional; see below
drivetrain: "RWD"                              # FWD | RWD | AWD
engine_layout: "mid-rear transverse V6 behind the driver"
weight_bias: "~44% front / ~56% rear"
weight: "~950 kg"
max_power: "250 hp at 7700 rpm"
max_torque: "260 Nm at 6000 rpm"
class: "Group 2/4 · H1"
gearbox: "Manual 5-speed"
steering_lock: "1170°"
version: "0.6"                                 # game version the values were captured in, or "unknown"
source: "game-files"                           # game-files | community | screenshots
# --- bundled cars only, added by the maintainer tools ---
gearing_tool: "https://…/lancia-stratos/gears/"
power_torque_chart: "https://…/lancia-stratos-power-torque.png"
engine_curve:
  source: "ACR game files - FC_LanciaStratosHF_Torque"
  peak_torque: "260 Nm at 6000 rpm"
  peak_power: "265 hp at 7750 rpm"
  rpm_step: 250
  torque_points: [[0, 0], [250, 0], …]         # [rpm, Nm]; power is derived, not stored
# --- a file stored on a car's `Parameters` page only ---
forked_from: "bundled template v0.6"           # only when the car was forked from a bundled template
written_at: "2026-09-21"
skill_version: v0.19.1
parameter_count: 42
parameters:
  - section: "Suspensions — Front"
    adjustment: "Spring Stiffness Front"
    order: 2020                                # integer display position, section-blocked
    min: 42300                                 # bare number, or "—"
    max: 73100
    unit: "N/m"                                # "" when there is no unit
    discrete_steps: "42300, 50000, 57700, 65400, 73100"
    surface: "Gravel"                          # OMIT this line on a baseline row
```

The header keys appear in exactly that order (`TEMPLATE_HEADER_ORDER` in
`scripts/load_catalog.py`); the rules:

- `min` and `max`: a bare number (no quotes) for numeric parameters; `"—"` (quoted em-dash) for
  named-selection ones.
- `unit` and `discrete_steps` are **always quoted**, `""` when empty. `discrete_steps` carries the
  car's step list **verbatim** as a comma-separated string (`"Short, Medium, Long"`,
  `"42300, 50000, 57700, 65400, 73100"`) — whitespace normalised to one space after each comma
  and nothing else. Never re-order, abbreviate, round, truncate, or replace a list with a range.
  It applies to **numeric** parameters too: a real `min..max` **and** a step list can coexist.
  A **gear value keeps its `*` exactly** (`SKILL.md` → *A gear value with a `*` in it is an
  ordinary value*) — the quoting is what carries it through.
- `order`: the integer display position (section-blocked, e.g. `2020`; `notion-structure.md` →
  *Setups column order*). A surface-specific entry carries the **same** `order` as its baseline.
- `surface`: **optional, per-entry.** Present only on a surface-specific entry (`Tarmac`,
  `Gravel`, `Snow`); **omitted entirely on a baseline entry.** At the same `order`, the
  **baseline entry comes first**, then the surface-tagged ones. A parameter whose range differs on
  gravel is two entries: the baseline, then one with `surface: "Gravel"`.
- `source`: where the values came from — `"game-files"` (the maintainer's, extracted from the ACR
  game files), `"community"` (a user's export), `"screenshots"` (a user's own catalog, on their
  `Parameters` page). It is read back into the car's catalog source line
  (`notion-structure.md` → *Car page*). **A file with no `source:` line at all is treated as
  `community`** — older templates predate the field.
- `save_ids`: the exact in-save car string(s) ACR writes for this car (what the save parser emits,
  e.g. `"MiniCooperS1275"`, `"LanciaRally037Evo2"`), which lets save-file import
  (`import-savegame.md` 5.2) match a save **reliably** — those compact IDs often drop the year or
  add tokens, so the human `car:` name can't be fuzzy-matched to them. **An export can't invent
  one**; it is filled in only when an observed save reveals the string. A file without it just
  matches by name.
- `gearing_tool` / `power_torque_chart` / `engine_curve`: generated from the ACR game files by
  `tools/gearing-charts` and `tools/torque-curves`, so they appear **only in bundled
  `car-templates/*.yaml` files** — nothing in this workflow can produce one. They are **never in
  a file stored on a car's `Parameters` page and never in an export**: `load_catalog.py
  --to-template` does not emit them, and every workflow reads them from the matching bundled file
  instead (`notion-structure.md` → *Engine chart and gearing tool*). A file without them loads
  and onboards cleanly; a car with no matching bundled file just gets no chart and no gearing
  link.
- `forked_from` / `written_at` / `skill_version` / `parameter_count`: written only onto a car's
  `Parameters` page in Notion, as bookkeeping. `parameter_count` is checked on load — it must
  equal the number of entries, which is how a truncated fetch is caught. A shared template carries
  none of them (step 3 drops them).
- Everything except `car` and `parameters:` is **optional in both directions** — a file missing any
  of it loads exactly as before, and onboarding fills what it can from the car information
  screenshot or a lookup (`onboard-car.md` step 5).

## Rules
- Export reads the car's catalog; it never writes to the user's Notion.
- The export is a copy of the car's list as it is now. If the user changes it later
  (`edit-catalog.md`), they can re-run the export to get a fresh copy.
- Never include personal data (user name, email, Notion IDs) in the exported YAML.
- **Save-file import uses `version`** (`import-savegame.md` step 5): when a setup's game version
  matches it (major.minor), import validates and snaps that setup's values to the catalog
  ("official parse") instead of writing them as-is; an `"unknown"` version simply skips that check
  (import falls back to the as-is path).
