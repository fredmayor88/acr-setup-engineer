# Workflow: ask a question / explain a setup or tuning concept

Answer the user's **questions** about car setups and tuning — grounded in the bundled knowledge
base (`setup-tuning-principles.md`), the user's own Notion data when a specific setup is in scope,
and model knowledge, with a disclosed web-search fallback. This workflow is **read-only**: it
**never writes to Notion**. It explains and teaches; it does not build, tweak, or critique.

Examples it handles:
- *"What's the impact of a stiffer vs softer ARB?"* (conceptual)
- *"What are the basic rules for setting up ARBs and diffs?"* (conceptual)
- *"Why does my `alsace gpt1` setup have the ride height set like that?"* (setup-specific)
- *"Why is the front ARB stiffer in `alsace gpt1` than in `wales r2`?"* (comparison)

Read `setup-tuning-principles.md` (the reasoning base) before answering. Read
`notion-structure.md` and `notion-rest-read.md` only when the question is **setup-specific** and
you need to load data.

## Inputs
- **The question** — free-form. May be conceptual, or about a named setup, or a comparison of
  two setups.
- **Optional anchors** — a setup name (e.g. `alsace gpt1`), a car, a location/stage, a surface, a
  drivetrain. Use them to scope and to apply the right drivetrain filter. Game defaults to `ACR`;
  ask only if the user has data under multiple games and it's unclear which one.

## 1. Classify the question
Decide what to load **before** answering:

- **Conceptual** ("what does X do?", "basic rules for ARBs/diffs?", "why would I run more
  preload?") → no Notion needed. Go to §2.
- **Setup-specific** ("why is X set like that in setup S?") → load the one setup from Notion. Go
  to §3.
- **Comparison** ("why is X stiffer in setup A than setup B?", "what's different between A and
  B?") → load both setups from Notion. Go to §3, then §4.

If a question mixes shapes (e.g. "what does ARB stiffness do, and why is mine so soft?"), answer
the conceptual part from the base first, then load the setup for the specific part.

## 2. Conceptual path (no Notion)
Answer from `setup-tuning-principles.md`:

- **"What does parameter X do / what's the impact of more vs less?"** → explain the physics effect
  from the relevant *Parameters* subsection (e.g. *Axles — anti-roll bars* for ARBs, *Differential
  (LSD)* for diffs). When the user asks specifically what a setting *does in the game*, quote or
  paraphrase the verbatim **In-game parameter definitions** section (authoritative ACR text).
- **"Basic rules for X?"** → give the heuristics: the *Balance cheat-sheet (which way to push)*,
  the *General rule* ("stiffer where you want less grip/more response; softer where you want more
  grip/compliance"), and the *Workflow / methodology* ordering (tyre first → survival before
  balance → start soft → change a few things at a time → diff + brake bias give the most change).
- **Drivetrain filter** — apply it **only if the question names a car or drivetrain**. Otherwise
  explain the universal `[All]` effect and then note where FWD/RWD/AWD diverge (e.g. a locked
  front diff means understeer on FWD; a locked rear means power-oversteer on RWD). Don't hide the
  drivetrain-specific nuance just because no car was named.
- **User guidelines** — if the question is about *how to tune* and the user has a global
  `Tuning guidelines` page that speaks to it, fold that in and flag that their own preference
  overrides the base (later wins: base → global guidelines → surface section ("Per surface" on
  that same page) → per-car → the setup's own driving intent, most specific). Only read it if
  it's readily reachable within `Car setups → {Game}`; don't go hunting.

Keep answers concrete and physical. Cite which lever pushes which way (front vs rear, power vs
coast ramp, slow vs fast damper) rather than vague "it depends".

## 3. Setup-specific path (load from Notion)
Load data the same way `review-setup.md` does (steps 1–4) — **but to explain, not to critique**.

### 3a. Identify the setup(s)
Navigate to `Car setups → {Game} → Setups` and find the row(s) matching the given name(s). Stay
within `Car setups` scope — never issue workspace-wide Notion searches; discard any result from
outside `Car setups`.
- **Unique match:** load all value properties plus `Car`, `Location`, `Stage`, `Surface`, `Mode`,
  `Notes`, `Rating`.
- **Multiple matches:** list them (Name / Car / Stage / Date) and ask the user to pick.
- **No match:** tell the user and stop.
- If the row has **no parameter values filled** (e.g. a metadata-only import), say so — there's
  nothing to explain — and stop.

Read the car's rows via **`notion-rest-read.md`** (`scripts/query_notion_parameters.py`).

### 3b. Load constraints + drivetrain
Fetch the car's `Parameters` rows: `Adjustment`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`,
`Surface`. Read `Drivetrain` (FWD/RWD/AWD) from the `{Car}` page. **Resolve each parameter's legal
range for the setup's `Surface`** — the surface-specific row if one exists; for `Snow`, fall back
to a `Gravel` row before the baseline (see `notion-rest-read.md`).

### 3c. Load the guideline layers
Same precedence chain as `build-setup.md` / `review-setup.md` (lowest → highest):
1. **Base** — `setup-tuning-principles.md`.
2. **Global user guidelines** — `Tuning guidelines` page under `Car setups / {Game}`.
3. **Surface section** — that page's "Per surface" subsection matching the setup's `Surface`.
4. **Per-car guidelines** — the `{Car}` page's "Guidelines" section.
The setup's own **driving intent** (its page-body summary) is the most specific layer. Apply only
lines tagged `[All]` **or the car's drivetrain**.

### 3d. Load stage facts (if the setup references one)
Fetch the `{Stage}` / `{Location}` page from the catalogue (`notion-structure.md`): surface, key
corners/speeds, character. These are **objective facts** — what the driver was aiming for comes
from the setup's own page-body summary, not the stage page.

### 3e. Explain the value
For each parameter the user asked about (or, if they asked "explain this setup" broadly, the
handful that matter most given the stage/intent):
- State **what the parameter does** (from the principles / in-game text).
- Place the chosen value **in its surface-resolved range** — is it soft/stiff/low/high, near an
  end or mid-range? If `Discrete steps` are filled, say which step it is.
- Give the **reason it's there**: cite the layer that drives it — a base principle, a user
  guideline, the surface bias, the stage facts, or the setup's stated intent. When a user
  guideline or the setup's stated intent is the reason, **say so explicitly** ("because your
  guidelines say you like a planted rear", "because this setup's intent was a fast and bumpy
  tarmac stage").

This is an **explanation, not a review** — don't hunt for problems. Only raise a concern if the
user explicitly asks "is this right / good?", or if a value is a **hard constraint violation**
(outside `Min..Max` / not in `Discrete steps`), which you should mention plainly since it means
the value won't behave as intended.

## 4. Comparison path (two setups)
Load both setups (§3a–3d for each). Then:
- **Diff** the parameter(s) the user asked about (or surface the biggest handling-relevant
  differences if they asked "what's different?"). Present differences in `Order` sequence.
- For each difference, explain the **handling consequence** of the direction, grounded in the
  principles — e.g. *"front ARB is stiffer in A (X) than B (Y) → more front lateral load transfer
  → A trades front grip for less roll and a more understeer-stable, responsive front; B keeps more
  front compliance/grip."*
- Tie it back to **why** each setup went that way: each setup's `Surface`, stage facts, and
  stated intent (a tarmac/fast intent wants stiffer/lower; a bumpy/rotation intent wants
  softer/higher). If the setups are for different surfaces, lead with that — it explains most
  differences.
- If both values resolve to **different legal ranges** (different surfaces), note that the same
  raw number can mean different things; compare position-in-range, not just the absolute value.

## Web search policy
Answer from the **bundled base + model knowledge first**. Use web search **only** when the
question needs information the base doesn't cover — current/community meta, a recent ACR build
change, a car or feature not in the knowledge base — and **tell the user** when an answer leaned
on the web. Prefer the curated base over single-creator opinions when they conflict; the base was
already filtered for physical soundness.

Carry the **ACR early-access caveat** for build-dependent topics — tyre compound behaviour, the
tyre heating/pressure model, and bump/rebound transition behaviour are still changing (see
*Sources & version caveats* in `setup-tuning-principles.md`). Flag that the advice is a strong
starting point to verify in-game, not a guarantee.

## Rules
- **Read-only — never write to Notion.** This workflow only reads; it produces a chat answer. (If
  the user wants the explanation saved to the setup's page, that's the `review-setup` workflow.)
- **Stay within `Car setups` scope** — same name-resolution and scope discipline as every
  workflow; never issue workspace-wide searches; discard any out-of-scope result before it
  influences the answer.
- **Drivetrain-aware** — apply only guideline/principle lines tagged `[All]` or the car's
  drivetrain when a car is in scope.
- **Layered — the user wins.** When a user guideline or the setup's stated intent drives the
  answer, cite it; their preference overrides the base.
- **Grounded and concrete** — explain in terms of real levers and effects; never invent a
  parameter the car doesn't have, and don't fabricate a reason for a value the data doesn't
  support (if you can't tell why, say it's within range and plausibly a taste choice).
