# Workflow: export a car parameter template

Export a car's full parameter catalog from Notion as a YAML template file that can be bundled
with the skill and shared with the community. The exported file, once added to the skill's
`.claude/skills/car-setups/car-templates/` folder (the same one the bundled templates live in),
lets future users onboard the same car without screenshots.

## Trigger phrases
"export template", "export car template", "create bundle file", "share my parameters",
"contribute my car", "submit my car setup parameters", or any request to produce a shareable
parameter file for a car.

## Inputs
- **Car name** — ask if not provided or ambiguous (must match a car already onboarded in Notion).
- **Game** — defaults to ACR; ask only if the user has multiple games and it's unclear.
- **Game version** — ask which game version the parameters were captured in (e.g. `0.4`), since
  tunable ranges can shift between versions. If the user doesn't know, write `"unknown"`. (No
  Notion lookup — don't try to infer it from existing setups.)

## Procedure

### 1. Read from Notion
- Navigate to `Car setups → {Game} → Parameters` DB and fetch all rows where `Car` = the
  requested car **using [notion-rest-read.md](notion-rest-read.md)** (the connector can't list
  rows reliably — this is what made export slow and incomplete). Follow the same name-resolution
  rules as other workflows (resolve by name, no hardcoded IDs; stay within `Car setups` scope).
  Read each row's optional **`Surface`** tag too — a car may have a baseline row (blank `Surface`)
  **and** a surface-specific row (e.g. `Gravel`) for the same `Adjustment`; export **both**.
- Read the car's `Drivetrain` (FWD/RWD/AWD) from the `{Car}` page under `{Game}`.
- Also read the car-level identity fields from the `{Car}` page, when present: `Engine layout`
  (front/mid/rear), `Weight bias` (front/balanced/rear), and `Weight` (approximate kerb weight,
  e.g. `~950 kg`). These may be blank or hold the literal `couldn't determine` — carry whatever
  is there. They are car facts, **not** rows in the `Parameters` DB.
- If no rows are found, tell the user the car hasn't been onboarded yet and stop.

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
Order rows to match the standard in-game screen order:

1. Gearbox
2. Suspensions
3. Dampers
4. Axles
5. Differential / Differentials
6. Wheels/Tyres
7. Brakes
8. Electronics

Within each section, list Front parameters before Rear; otherwise sort by `Adjustment` name
alphabetically. When a parameter has both a baseline and a surface-specific row, emit the
**baseline (no `surface`) first**, then the surface-tagged rows.

### 4. Format as YAML
Produce a YAML block with this exact structure:

```yaml
car: "{Car Name}"
game: "{Game}"
drivetrain: "{FWD|RWD|AWD}"
engine_layout: "{descriptive engine placement, e.g. mid-rear transverse V6 behind the driver}"
weight_bias: "{front/rear percentages, e.g. ~44% front / ~56% rear}"
weight: "{approx kerb weight, e.g. ~950 kg}"
version: "{game version the parameters were captured in, e.g. 0.4 — or unknown}"
parameters:
  - section: "{Section}"
    adjustment: "{Adjustment}"
    min: {numeric value or "—"}
    max: {numeric value or "—"}
    unit: "{Unit or empty string}"
    discrete_steps: "{comma-separated list or empty string}"
    surface: "{Tarmac|Gravel|Snow — OMIT this line for baseline rows}"
```

Rules:
- `min` and `max`: use a bare number (no quotes) for numeric values; use `"—"` (quoted em-dash)
  for named-selection parameters.
- `discrete_steps`: use a comma-separated string for filled values (e.g.
  `"Short, Medium, Long"`); use an empty string `""` for blank entries.
- `unit`: empty string `""` when there is no unit.
- `surface`: **optional, per-parameter.** Emit it only for a surface-specific row (the row's
  `Surface` is set); **omit the line entirely for baseline rows** (blank `Surface`). A parameter
  whose range differs on gravel appears as two entries: the baseline (no `surface`) and a second
  with `surface: "Gravel"`.
- `engine_layout`, `weight_bias`, `weight`: **optional** car-level header fields. Emit each only
  when the `{Car}` page has a value; omit the line entirely if blank. If the page holds the
  literal `couldn't determine`, carry it through as-is. These are not parameters.
- Use double quotes around all string values; no quotes around numbers.
- Produce clean YAML — no trailing spaces, consistent 2-space indentation.

### 5. Present to user
Always show the YAML as a fenced code block in chat regardless of what else is available:

````
```yaml
<generated YAML here>
```
````

Then tell the user:
> "Save this as `.claude/skills/car-setups/car-templates/{slug}.yaml` in the skill repo — this is
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
  https://github.com/fredmayor88/car-setups/new/main?filename=.claude/skills/car-setups/car-templates/{slug}.yaml
  ```

  where `{slug}` is the car name lowercased with spaces and special characters replaced by hyphens
  (e.g. `lancia-stratos-hf`). **Use the full `.claude/skills/car-setups/car-templates/` path** —
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
  It is informational metadata — nothing validates it on import. The `engine_layout` /
  `weight_bias` / `weight` header fields and the per-parameter `surface` field remain **optional
  and backward-compatible**: a template with none of them imports exactly as before (all baseline
  rows), regardless of the `version` value.
