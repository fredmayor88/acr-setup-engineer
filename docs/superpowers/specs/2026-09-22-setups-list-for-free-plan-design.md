# The setup history without REST — a list of links on each car's `Setups` page

**Status:** approved 2026-09-22 · **Date:** 2026-09-22

## Summary

On Claude's Free plan the code sandbox can't reach `api.notion.com`, so the skill can't run the
REST query that lists a car's rows in the `Setups` database. Since v0.19 every catalog works
without REST. The one thing left that doesn't is the setup history: the learn pool
(`Learn from this`), ratings, and a stored game default.

The Notion connector can't list a database's rows dependably, but it **can fetch one page in
full**: a setup page's fetch returns every property, including `Learn from this`, `Rating` and
`Source` (checked on 2026-09-22 against a live workspace). So the skill needs to know *which*
pages to fetch. This design gives it that: **each car's `Setups` page carries a plain list of
links to the setups the skill saved**, one line per setup, written at save time on every plan.
On Free, a build reads that list, fetches only the few pages it needs, and reads the live
checkbox and rating from each. On a paid plan nothing changes for reads: REST stays the source.

## Goals

- On Free, a build uses the stored game default and the user's `Learn from this` setups, for
  every setup saved by the skill from this release on.
- Reads are capped so a Free chat isn't spent on fetches. The user can ask for more.
- Named-setup workflows (review, tweak, ask, share) find a setup by name without a search.
- The list is maintained by the skill only. The user never edits it and never has to.
- Every step is followable by a less capable model: line format and candidate picking are done
  by a stdlib script, not by eye.

## Non-goals

- No migration of setups saved before this release, and no rebuild command. Older or hand-made
  setups get in only when the user pastes their link in chat.
- No change to REST reads on paid plans.
- No new database, no new page. The list lives on a page that already exists.

## Decisions taken with the user (2026-09-22)

- Free reads fetch only what a build needs: the matching default and up to 6 learn candidates.
  The user can say to load more.
- The list lives on the car's `Setups` page, under the linked view.
- No migration. The list starts empty at this release. Paste a link to add anything older.
- The "no default row" path is unchanged: explain what the anchor is for, ask for screenshots,
  and build without an anchor if the user declines. Free lands on the same step.

## Data model

### The list section

On each car's `Setups` page, **below the linked view**, an H2 heading **`Setup index`**
followed by one bulleted line per setup, **newest at the top**. The page therefore holds, in
order: the maintenance line, the `Setups[Car=this]` linked view, the `Setup index`
heading, the lines. Nothing else.

Each line has exactly this shape (a hyphen with a space on each side as the separator, chosen
because it is easy to type when editing by hand; a blank field is `-`):

```
- [{Name}]({page url}) - {Source} - {Stage} - {Surface} - {Conditions} - {YYYY-MM-DD}
- [{Name}]({page url}) - {Source} - {Stage} - {Surface} - {Conditions} - {YYYY-MM-DD} - learn: {yes|no}
```

Examples:

```
- [MC-ilDrago-0.6-v2](https://www.notion.so/3dd9abc6c7738173bc65c954d9d85ece) - screenshot - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-16
- [turini dry def](https://www.notion.so/3a89abc6c7738129ba47e0d23b52b4c9) - default - Col de Turini (Uphill) - Tarmac - Dry - 2026-09-12 - learn: yes
```

The skill writes the first six fields: facts that never change after the save, so it can pick
candidates without fetching them. `Rating` and `Notes` are never on the line; they are read live
from the setup page.

**The `learn:` override** is the optional seventh field. The skill never writes it; the user adds
it by hand, on any plan:
- absent → the page's `Learn from this` checkbox decides, read live from the page;
- `learn: yes` → the setup is learn material whatever the checkbox says, and the picker returns it
  ahead of the stage-ordered candidates, so it never falls under the cap;
- `learn: no` → the setup is never fetched for learning.
On a paid plan the override also wins over the checkbox for the REST learn pool, so the list means
the same thing everywhere: the reader of the REST slice drops `learn: no` names and adds
`learn: yes` names (fetching their rows from the same slice, with `--learn-only` off) — the list is
read for this purpose on every plan, once per build, right after the REST queries.

Parsing: match the link first, then split the rest on ` - ` into six or seven fields. A line that
doesn't split into six or seven is **malformed**: the picker ignores it and counts it, and the
skill names it to the user in one line rather than guessing. No ACR stage name contains ` - `
today; the export of a stage name that does would need a different separator, not a smarter
parser.

The section is **add-only**: a line is inserted directly under the heading. Lines are never
edited, reordered or removed. If the user deletes a setup in Notion, its line stays; a fetch of
a deleted page fails, and the reader skips it and says so.

### Ownership

The `Setups` page stays the skill's. The rule in `notion-structure.md` → *`Setups` page*
changes from "the linked view and nothing else" to "the linked view, then the `Setup index` section". The user-facing `Which page is whose` text does not change (the page is already
listed as the skill's).

### What refresh does with it

Nothing. The per-car refresh and the whole-Notion refresh recreate the linked view **only when it
is missing** (as today) and never write, rewrite or remove the `Setup index` section.
Re-onboarding a car likewise leaves it. This is stated in both refresh procedures.

## Writing the list

Every workflow that creates a `Setups` row adds its line **right after the row is created, on
every plan** (REST or not). The four savers:

| Workflow | Row it creates | `Source` on the line |
| --- | --- | --- |
| `build-setup.md` step 11 | the built setup | `generated` |
| `build-setup.md` step 5 | the captured game default | `default` |
| `tweak-setup.md` (save on request) | the tweaked setup | `generated` |
| `capture-setup.md` | the user's setup from screenshots | `screenshot` |
| `import-savegame.md` step 5.5 | one row per imported setup | `imported` |

Procedure, the same in each (each workflow points at one shared section,
`notion-structure.md` → *Adding a line to `Setup index`*):

1. Take the new row's page URL from the create call's result.
2. Build the line with `python scripts/setups_list.py --line` (below), passing the row's fields.
   Never hand-format the line.
3. Fetch the car's `Setups` page. If it has no `Setup index` heading, append the heading
   at the bottom of the page, then the line. If it has one, insert the line directly under the
   heading, above the existing lines.
4. Import writes **one insert for all its lines** (newest first), not one per row.

If the car's `Setups` page doesn't exist (a car onboarded by an old version whose layout wasn't
migrated), skip the line and say in one sentence that "refresh the {Car} in my Notion" will
create the page, after which new saves are listed. Never create the page from a save.

### Adding by hand

The user pastes a setup's Notion link in chat (in any wording that says to add it, learn from
it, or use it). The skill fetches the page, checks that its parent data source is the `Setups`
database and that its `Car` is a car under the root, then adds its line with the fields read
from the page. If the page is something else, say so in one line and do nothing.

## Reading on Free

### The one entry point

A new reference, **`references/setups-list-read.md`**, is the only path to a car's setups when
`check_egress.py` printed `egress: none`. `notion-rest-read.md` → *Offline mode* sends every
`Setups` slice there instead of "empty". On `egress: ok` nothing changes: REST is the source and
the list is not read.

Procedure:

1. Fetch the car's `Setups` page. Save the text under the `Setup index` heading to a file
   in the sandbox (`setups/<slug>.md`). No heading → the list is empty: say the one offline line
   (below) and continue with no history.
2. Run the picker:

   ```
   python scripts/setups_list.py --pick setups/<slug>.md --stage "{Stage}" --surface {Surface} --conditions "{Conditions}" [--limit 6]
   ```

   It prints JSON: `default` (the one `default` line whose stage, surface and conditions all
   match, or `null`), `other_defaults` (every other `default` line for the car, newest first —
   step 4's "a default in a differing context" branch shows one of these and asks whether it
   matches, exactly as with REST rows), `learn` (up to `--limit` non-default lines, ordered same
   stage first, then same surface, then newest), and `skipped` (the count of non-default lines
   left out). A blank `--conditions` matches only lines whose conditions are blank (`-`). Lines
   with `learn: yes` come first in `learn` and don't count against `--limit`; lines with
   `learn: no` are never in `learn`. Each `learn` entry carries its `learn` value (`yes`, `no`
   or `null`) so the caller knows whether to read the checkbox.
3. Fetch each picked page. Read values from its properties, never from the page body
   (`SKILL.md` → *A setup's real values are its row*). A page that fails to fetch is dropped and
   named in the report.
4. The learn pool is the fetched non-default pages whose `Learn from this` is ticked, plus every
   fetched `learn: yes` page whatever its checkbox says. `Rating` is
   read from the same fetch. The default anchor is the fetched `default` page, if any; when
   `default` is null and `other_defaults` isn't, fetch only the newest of them for step 4's
   confirmation question.
5. Hand the results to the calling workflow exactly where the REST rows would have gone
   (`build-setup.md` step 4 for the default, step 7 for the learn pool). From there nothing is
   different: no default → the screenshots-first path with its explanation and its "build
   anyway" exit; no ticked setups → "no prior setups used".

### Telling the user

Once per chat, the offline line replaces today's "I can't read your saved setups" wording:

> *This chat can't reach Notion's API. That's normal on Claude's Free plan. I can still use the
> setups the skill saved from v{version} on: I read the ones closest to this stage, up to 6, and
> take the ones you ticked `Learn from this`. Older setups count only if you paste their link
> here. Say "also learn from my other {Car} setups" to read more. The `Claude Free plan` page in
> your Notion has the details.*

Then, in the build's report, one line: *"Read {n} saved setups ({names}); {k} had `Learn from
this`; {skipped} others left out — say 'also learn from my other {Car} setups' to include them."*

### Load more

When the user asks to learn from more setups, or names specific ones, the skill runs the picker
again with a higher `--limit` (or with `--names`), fetches only the pages not already fetched in
this chat, and re-runs the step that uses the learn pool. Named setups that aren't on the list
are reported as not found, with the paste-a-link hint.

### Named-setup workflows on Free

`review-setup.md`, `tweak-setup.md`, `ask-setups.md` and `share-setup.md` need one setup by
name. On Free they first run `python scripts/setups_list.py --find "{name}" setups/<slug>.md`
(exact name, then case-insensitive, then substring; ties are listed for the user to pick) and
fetch that page. Only when the name isn't on the list do they fall back to the search they use
today. The car is known from the request when it is; when it isn't, the skill asks which car
before reading the list.

## The script — `scripts/setups_list.py`

Stdlib only, like the other scripts. Three modes; unknown flags exit 2.

- `--line --name … --url … --source … --stage … --surface … --conditions … --date YYYY-MM-DD`
  prints one formatted line, six fields, never the `learn:` field. Blank `--stage`/`--conditions`
  become `-`. The date is the row's `Date` cut to its first 10 characters. A name, stage or
  conditions value containing ` - ` makes the script exit 1 with a message, so a line that can't
  be parsed back is never written.
- `--pick <file> --stage … --surface … --conditions … [--limit N] [--names "a" "b" …]` parses
  every line under the heading (ignores anything that isn't a line in the shape above, and
  reports the count of ignored lines as `malformed`) and prints the JSON described above.
  Matching is exact after trimming; `-` matches a blank field. `--names` bypasses the ordering
  and returns just those lines under `learn` (a `learn: no` line is still returned when named
  explicitly, with its `learn` value, so the workflow can say the user asked to skip it).
- `--overrides <file>` prints the `learn: yes` and `learn: no` names as JSON, for the paid-plan
  REST path.
- `--find "<name>" <file>` prints the matching line(s) as JSON.

## Documentation changes

- `notion-rest-read.md`: *Offline mode* sends `Setups` slices to `setups-list-read.md`; the
  once-per-chat message becomes the new text; rung 2 of the ladder (query errors with egress ok)
  stays "proceed as empty" — the list is a Free-plan path, not a retry path.
- `notion-structure.md`: `Setups` page section (the new shape), a new *Adding a line to `Setup
  index`* section, and the refresh rule that the section is never touched.
- `build-setup.md`, `tweak-setup.md`, `capture-setup.md`, `import-savegame.md`: one bullet each
  at the row-creation step pointing at the shared section; `build-setup.md` steps 4 and 7 name the
  Free path.
- `review-setup.md`, `tweak-setup.md`, `ask-setups.md`, `share-setup.md`: the list-first lookup
  on Free.
- `onboard-car.md` (refresh) and `refresh-notion.md`: the section is never written or removed.
- `free-plan-template.md`: *What doesn't work* becomes *What's different*: setups saved from
  v{version} on are used, up to 6 per build, older ones by pasted link; a saved game default is
  reused when it was saved by the skill from this version on.
- `how-to-use-template.md`: one line, *"Use an older setup on Free — paste its Notion link in
  the chat and say 'learn from this one too'"*, one line on the `learn: yes` / `learn: no`
  override in the car's `Setup index`, and the `Covers:` line gains `setups-list-read.md`.
- `SKILL.md`: the script in the scripts list, the reference in the references list, the offline
  rule updated. `README.md`: the Free-plan paragraph updated. `RELEASE_NOTES.md` when the release
  is prepared, not before.

## Testing

- `tests/test_setups_list.py`: `--line` output for full and blank fields, and exit 1 on a
  value containing ` - `; `--pick` on a fixture page (default match, no match, other-context
  defaults, ordering by stage then surface then date, limit, `learn: yes` first and uncounted,
  `learn: no` excluded, `--names`, malformed lines counted and ignored, a stage name with a plain
  hyphen such as `Monte-Carlo` parses fine); `--find` exact, case-insensitive, substring, ties;
  `--overrides`; unknown flag exits 2.
- `tests/test_references.py` gains guards: each of the four saving workflows mentions
  `Setup index`; `free-plan-template.md` and `notion-rest-read.md` no longer contain
  "can't be read back" / "can't read your saved setups"; `setups-list-read.md` never tells the
  reader to run `notion-search` for a car's setups; both refresh docs say the section is never
  written.
- `tests/test_notion_docs_pages.py`: `Covers:` includes `setups-list-read.md`.
- Manual check on a Free chat before release: build a setup, tick `Learn from this` in Notion,
  build another, confirm the report names it.
