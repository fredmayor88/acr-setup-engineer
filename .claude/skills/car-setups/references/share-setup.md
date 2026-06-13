# Workflow: share a setup as a plain-text snippet

Generate a compact, copy-pasteable plain-text summary of a setup so the user can share
it via Discord, WhatsApp, a forum, or any other channel. **Read-only** — this workflow
never writes to Notion.

## Inputs
- **Car** and **game** (default ACR)
- **Setup name** — if not specified, fetch the car's existing setups from Notion and ask
  the user to pick one

## Procedure

1. **Locate the setup.** Fetch the car's `Setups` DB rows (filtered to that car). Find
   the row matching the requested setup name. If not found, list the available setups and
   ask the user to pick; do not proceed until one is identified.

2. **Load section + unit metadata.** Fetch the car's `Parameters` rows to get `Section`,
   `Adjustment`, and `Unit` for every parameter. This is the only way to know which
   section each value belongs to and what unit label to append.

3. **Build the snippet.** Group parameters by `Section`, in the same order they appear
   on the setup screens (Gearbox → Suspensions → Dampers → Axles → Differentials →
   Wheels/Tyres → Brakes → Electronics & Aerodynamics). Within each section, list Front
   parameters before Rear, then other parameters alphabetically. One line per parameter:

   ```
   Adjustment: value unit
   ```

   - Skip any parameter whose value is blank or absent in this setup row — don't show
     empty lines.
   - Omit a section entirely if it has no non-blank values.
   - Append the `Unit` label after the value with a space (e.g. `120 mm`, `-1.5 °`,
     `57700 N/m`). If `Unit` is blank, omit it.

4. **Output the snippet** inside a fenced code block so it is easy to select and copy.
   Lead with a header line: `{Car} · {Setup name}`, then a blank line, then the grouped
   values.

### Example output

```
Lancia Stratos HF · alsace gpt1

[Gearbox]
Gear set: 2

[Suspensions]
Front ride height: 120 mm
Rear ride height: 125 mm
Spring stiffness front: 57700 N/m
Spring stiffness rear: 50000 N/m
ARB front: 3
ARB rear: 2
Camber front: -1.5 °
Camber rear: -1.0 °
Toe front: 0.1 °
Toe rear: -0.1 °

[Brakes]
Brake balance: 58 %

[Electronics]
ABS: 3
TCS: 2
```

## Rules
- Never write to or modify Notion — this workflow is strictly read-only.
- No justifications in the snippet; those live in the Notion page toggles.
- Scope reads to `Car setups` only — do not search the workspace broadly.
