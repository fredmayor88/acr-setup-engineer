# Workflow: export a car parameter template

Export a car's full parameter catalog from Notion as a YAML template file that can be bundled
with the skill and shared with the community. The exported file, once added to the skill's
`.claude/skills/acr-setup-engineer/car-templates/` folder (the same one the bundled templates live in),
lets future users onboard the same car without screenshots.

## Trigger phrases
"export template", "export car template", "create bundle file", "share my parameters",
"contribute my car", "submit my car setup parameters", or any request to produce a shareable
parameter file for a car.

**Also entered from onboarding.** `onboard-car.md` step 10 offers this at the end of a
**screenshot** onboarding — the case where the user has just hand-built a catalog for a car with no
bundled template, and is therefore the only person who can contribute it. Arriving that way, the
car and its rows are **already in hand**; see the note in step 1.

## Inputs
- **Car name** — ask if not provided or ambiguous (must match a car already onboarded in Notion).
- **Game version** — ask which game version the parameters were captured in (e.g. `0.4`), since
  tunable ranges can shift between versions. If the user doesn't know, write `"unknown"`. (No
  Notion lookup — don't try to infer it from existing setups.)

## Procedure

### 1. Read from Notion
- Navigate to `ACR Setup Engineer → Parameters` DB and fetch all rows where `Car` = the
  requested car **using [notion-rest-read.md](notion-rest-read.md)** (the connector can't list
  rows reliably — this is what made export slow and incomplete). Follow the same name-resolution
  rules as other workflows (resolve by name, no hardcoded IDs; stay within `ACR Setup Engineer` scope).
- **Read every field of every row** — the export is a full snapshot, not a range dump. Per row:
  `Section`, `Adjustment`, `Min`, `Max`, `Unit`, **`Discrete steps`**, **`Order`**, and the optional
  **`Surface`**.
  - **`Discrete steps` is the field most often lost — carry it for every row that has one.** It is
    **user-owned and usually filled *after* onboarding** (`onboard-car.md` step 9 asks the user to
    enumerate `—` rows and to pin coarse numerics like spring stiffness / ARB), so a screenshot-onboarded
    car typically has steps in Notion that were never part of the extraction. It is also **not limited
    to `—` rows**: a numeric row with a real `Min..Max` may carry a step list, and that list must
    export too. Whatever the Notion cell holds, it goes into `discrete_steps`.
  - **`Surface`**: a car may have a baseline row (blank `Surface`) **and** a surface-specific row
    (e.g. `Gravel`) for the same `Adjustment`; export **both**, each with its own `Discrete steps`.
  - **`Order`** is the display position — emitted as `order:` in the YAML.
  The REST read (`notion-rest-read.md`) returns these as row keys already, `Discrete steps` included
  (blank `""` means the cell is genuinely empty). Don't drop keys when building the in-memory catalog.
- Read the car's `Drivetrain` (FWD/RWD/AWD) from the `{Car}` page.
- Also read the car-level identity fields from the `{Car}` page, when present: `Engine layout`
  (front/mid/rear), `Weight bias` (front/balanced/rear), `Weight` (approximate kerb weight,
  e.g. `~950 kg`), `Max power` (e.g. `250 hp at 7700 rpm`), `Max torque` (e.g.
  `260 Nm at 6000 rpm`), `Class` (e.g. `Group 2/4 · H3`), `Gearbox` (e.g. `Manual 5-speed`), and
  `Steering lock` (e.g. `1332°`). These may be blank or hold the literal `couldn't determine` —
  carry whatever is there. They are car facts, **not** rows in the `Parameters` DB.
- If no rows are found, tell the user the car hasn't been onboarded yet and stop.

**Arriving from `onboard-car.md` step 10:** skip this whole section — you already hold every row,
the `Surface` tags, the `Order`s and the identity facts from the run that just wrote them
(`SKILL.md` → *Read efficiently*). Re-reading Notion here is a wasted round trip against data you
authored seconds ago. Start at step 2.

**Exception — the user has since edited Notion.** The shortcut is only valid while the in-memory
rows still match Notion. If, after the onboarding write, the user filled or changed **any** cell in
the `Parameters` DB — most commonly the `Discrete steps` the step 9 report asked them to enumerate,
whether they say so or you offered the export after they reported doing it — those edits exist
**only in Notion** and your in-memory rows are stale. **Re-read the car's rows via
`notion-rest-read.md`** (step 1) before formatting, and export from the fresh read. When in doubt,
re-read: one extra query is cheaper than shipping a template with empty `discrete_steps`.

### 2. Completeness check
Before formatting, scan for gaps and warn (but do NOT block the export):

- **Unnamed enumeration params** (`Min = —` and `Max = —`) with blank `Discrete steps`:
  list them explicitly — these entries will export with an empty `discrete_steps` field, making
  them unusable to anyone who imports the template without first filling that column.
- **Flagged numeric params** (any row where `Min` or `Max` is unexpectedly `—`): note them.

Show the warning as a numbered list of parameter names and what's missing. Then ask:
> "Export anyway with these gaps, or would you like to fill them in Notion first?"

Proceed on either answer; if the user wants to fill gaps first, stop here and remind them to
re-run the export afterwards.

### 3. Sort parameters
Order rows by each parameter's **`Order`** ascending (`notion-structure.md` → *Setups column
order*) — the in-game screen sequence (Gearbox → Suspensions → Dampers → Axles → Differentials →
Wheels/Tyres → Brakes → Electronics & Aerodynamics, Front before Rear). A row with no `Order`
falls back to the end of its section, then `Adjustment` name. When a parameter has both a baseline
and a surface-specific row (they share the same `Order`), emit the **baseline (no `surface`) first**,
then the surface-tagged rows.

### 4. Format as YAML
Produce a YAML block with this exact structure:

```yaml
car: "{Car Name}"
game: "ACR"
save_ids: ["{exact in-save car string}"]   # OPTIONAL — see rules; omit if unknown
drivetrain: "{FWD|RWD|AWD}"
engine_layout: "{descriptive engine placement, e.g. mid-rear transverse V6 behind the driver}"
weight_bias: "{front/rear percentages, e.g. ~44% front / ~56% rear}"
weight: "{approx kerb weight, e.g. ~950 kg}"
max_power: "{peak power with rpm, e.g. 250 hp at 7700 rpm}"
max_torque: "{peak torque with rpm, e.g. 260 Nm at 6000 rpm}"
class: "{in-game class badges, e.g. Group 2/4 · H3}"
gearbox: "{transmission type and gear count, e.g. Manual 5-speed}"
steering_lock: "{total lock in degrees, e.g. 1332°}"
version: "{game version the parameters were captured in, e.g. 0.4 — or unknown}"
parameters:
  - section: "{Section}"
    adjustment: "{Adjustment}"
    order: {integer display position, e.g. 2020}
    min: {numeric value or "—"}
    max: {numeric value or "—"}
    unit: "{Unit or empty string}"
    discrete_steps: "{comma-separated list or empty string}"
    surface: "{Tarmac|Gravel|Snow — OMIT this line for baseline rows}"
```

Rules:
- `min` and `max`: use a bare number (no quotes) for numeric values; use `"—"` (quoted em-dash)
  for named-selection parameters.
- `discrete_steps`: **emit the line for every parameter**, carrying the row's Notion `Discrete steps`
  cell **verbatim** as a comma-separated string (e.g. `"Short, Medium, Long"`, or
  `"42300, 50000, 57700, 65400, 73100"`). Normalise only whitespace (single space after each comma);
  never re-order, abbreviate, summarise, round, or truncate a list, and never replace a long list
  with a range. This applies to **numeric** rows too — a row with a real `Min..Max` **and** a step
  list exports both. Use an empty string `""` **only** when the Notion cell is actually blank.
- `unit`: empty string `""` when there is no unit.
- `order`: the integer display position (section-blocked, e.g. `2020`; see `notion-structure.md`
  → *Setups column order*). Emit the `Order` read from Notion; if a row has none, fall back to the
  canonical default for that parameter. A surface-specific row carries the **same** `order` as its
  baseline.
- `surface`: **optional, per-parameter.** Emit it only for a surface-specific row (the row's
  `Surface` is set); **omit the line entirely for baseline rows** (blank `Surface`). A parameter
  whose range differs on gravel appears as two entries: the baseline (no `surface`) and a second
  with `surface: "Gravel"`.
- `engine_layout`, `weight_bias`, `weight`, `max_power`, `max_torque`, `class`, `gearbox`,
  `steering_lock`: **optional** car-level header fields. Emit each only when the `{Car}` page has a
  value; omit the line entirely if blank. If the page holds the literal `couldn't determine`, carry
  it through as-is. These are not parameters. All are optional in both directions — a template
  predating any of them still imports cleanly, and onboarding fills the gaps from the car
  information screenshot or a lookup (`onboard-car.md` step 5).
- `save_ids`: **optional** list of the exact in-save car string(s) ACR writes for this car (the
  `car` field the save-file parser emits, e.g. `"MiniCooperS1275"`, `"LanciaRally037Evo2"`). It lets
  **save-file import** (`import-savegame.md` step 5.2) match a save to this template **reliably** —
  these compact IDs often drop the year or add tokens, so the human `car:` name can't be fuzzy-matched
  to them. **Export can't populate it** (Notion doesn't store the save string), so **omit the line on
  a normal export**; it's filled in only when an observed save reveals the string (the import
  confirm-match fallback prompts the user to contribute it). A template without `save_ids` imports
  exactly as before — fully backward-compatible.
- Use double quotes around all string values; no quotes around numbers.
- Produce clean YAML — no trailing spaces, consistent 2-space indentation.

### 5. Verify the YAML against the source rows
Before showing anything, check the generated YAML back against the rows you read — silent drops are
the failure mode this export has actually had:

- **Row count**: one YAML entry per source row (baseline **and** surface-tagged rows).
- **`discrete_steps`**: the number of entries with a **non-empty** `discrete_steps` equals the number
  of source rows whose `Discrete steps` cell is non-blank, and each such list matches its source cell
  item-for-item. A row that has steps in Notion but exports `""` is a **bug, not a gap** — fix it (and
  re-read Notion if your rows might be stale, per step 1's exception) rather than reporting it in the
  gap warning.
- **`order` / `surface`**: every row that had an `Order` carries it; every surface-tagged row keeps
  its `surface:` line and every baseline row omits it.

Only the genuinely blank cells from step 2 may appear as `""`.

### 6. Present to user
Always show the YAML as a fenced code block in chat regardless of what else is available:

````
```yaml
<generated YAML here>
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

- **If the user says yes:** Give them a **filename-prefilled link** to the project's web editor.
  They sign in to GitHub (if asked), **paste** the YAML into the editor, and click one green
  button — GitHub quietly makes their own copy of the project and opens the share request for
  them. No tokens, no command line, nothing to install.

  **Do NOT prefill the file *contents* in the URL.** A template is several KB, and a
  contents-prefilled link exceeds GitHub's URL length limit — the user gets *"Your request URL is
  too long."* Prefill **only the filename** (short and safe); the user pastes the body, which you
  already showed in the code block above.

  The link is just (no code sandbox needed — the filename is short):

  ```
  https://github.com/fredmayor88/acr-setup-engineer/new/main?filename=.claude/skills/acr-setup-engineer/car-templates/{slug}.yaml
  ```

  where `{slug}` is the car name lowercased with spaces and special characters replaced by hyphens
  (e.g. `lancia-stratos-hf`). **Use the full `.claude/skills/acr-setup-engineer/car-templates/` path** —
  that's where the bundled templates live and where the skill loads them from; a bare
  `car-templates/` at the repo root is the wrong place and won't be picked up.

  Then hand the user the link with friendly, jargon-free steps:
  > "Here's your share link: {link}
  >
  > 1. Click it (sign in to GitHub if it asks).
  > 2. **Paste the YAML I showed above** into the editor box.
  > 3. Scroll down and click the green **Commit changes** / **Propose new file** button.
  > 4. Click the green button once more on the next screen to open the request.
  >
  > That's it — the maintainers will review it and bundle it into the next release. Thank you 🙏"

- **If the user says no:** Done — no follow-up, no nagging.

## Rules
- Export reads Notion; it never writes to Notion.
- The exported file is a snapshot of the current Notion state. If the user updates parameters
  later, they can re-run the export to get a fresh copy.
- Never include personal data (user name, email, Notion IDs) in the exported YAML.
- The `version` field records the **game version the parameters were captured for** (e.g. `0.4`),
  taken from the user's answer to the Game version input; write `"unknown"` if they don't know.
  **Save-file import uses it** (`import-savegame.md` step 5): when a setup's game version matches
  this `version` (major.minor), import validates and snaps that setup's values to the catalog
  ("official parse") instead of writing them as-is; an `"unknown"` version simply skips that check
  (import falls back to the as-is path). The `save_ids` and `engine_layout` /
  `weight_bias` / `weight` / `max_power` / `max_torque` / `class` / `gearbox` / `steering_lock`
  header fields, the per-parameter `surface`
  field, and the per-parameter `order` field remain **optional and backward-compatible**: a template
  missing any of them imports
  exactly as before (a missing `order` falls back to the canonical defaults in
  `notion-structure.md`; a missing `save_ids` just means import matches by name only), regardless of
  the `version` value.
