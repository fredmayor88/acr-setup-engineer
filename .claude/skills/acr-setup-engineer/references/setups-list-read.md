# Reading `Setups` without the REST query — the car's `Setup index`

**The only way to read a car's setups when `scripts/check_egress.py` printed `egress: none`** in
this chat (`notion-rest-read.md` → *Offline mode*). With `egress: ok` the REST query is the source
for reads; only *Adding setups by link* below runs on every plan. Catalogs are never read here
(`catalog-read.md`).

The index is the `Setup index` list on the car's `Setups` page (`notion-structure.md` →
*`Setups` page*): one line per setup the skill saved, newest first. This workflow reads the list,
picks the few pages a build needs, fetches each one with `notion-fetch`, and reads `Learn from
this`, `Rating` and the values from the page's properties — **never `notion-search` for a car's
setups**, which is capped, semantic and mixes cars.

## Saving the page to a file

Every mode of `scripts/setups_list.py` reads the car's `Setups` page from a file. After the
`notion-fetch`, save the page's whole text (everything inside `<content>…</content>`) — run this in
code execution, with the fetched text in `page_text`:

    import os, pathlib
    os.makedirs('setups', exist_ok=True)
    pathlib.Path('setups/<slug>.md').write_text(page_text, encoding='utf-8')

`<slug>` is the car's slug as `catalog-read.md` forms it. Save once per chat and reuse the file;
save again only after the skill has inserted a line.

## Reading a car's setups on Free

1. **Fetch the car's `Setups` page** (`notion-fetch`; the page is a child of `{Car}` under
   `ACR Setup Engineer`, resolved by name per `notion-structure.md`) and save it per *Saving the
   page to a file*. The script starts reading after the `Setup index` heading by itself.
   - No `Setup index` heading, or no `Setups` page → the list is empty — don't run `--pick` on a
     page without the heading. Say the once-per-chat line (*Telling the user*) if not yet said,
     and go on with **no stored default and no learn pool** — exactly `build-setup.md`'s
     no-default and no-prior-setups paths.
2. **Pick the candidates** — one command, in code execution:
   ```
   python scripts/setups_list.py --pick setups/<slug>.md --stage "{Stage}" --surface {Surface} --conditions "{Conditions}"
   ```
   - **`Mode = independent`** (`build-setup.md` step 7): use only `default` and `other_defaults`
     from the output — ignore `learn`, fetch none of those pages, and skip the learn part of the
     report line.

   Pass the build's stage, surface and conditions as settled in `build-setup.md` step 3 (blank
   `--conditions` when they were left blank; blank `--stage` when there is none). It prints JSON:
   - `default` — the `Source = default` line whose stage, surface and conditions all match, or
     `null`;
   - `other_defaults` — every other `default` line for the car, newest first;
   - `learn` — every `learn: yes` line first (these don't count against the cap, so `learn` can
     hold more than 6), then up to 6 of the other non-default lines, ordered same stage, then same
     surface, then newest. `learn: no` lines are never here;
   - `skipped` — how many **unmarked** non-default lines were left out by the cap (never `learn: no`
     lines — those are excluded outright, not skipped by the cap);
   - `malformed` — how many bullet lines under the heading couldn't be read;
   - `defaults_named` — only with `--names`: names that matched only a `Source = default` line. A
     default is never learn material, so it's kept out of `learn` and reported separately from
     `not_found`.
3. **Fetch the picked pages** — `notion-fetch` on each `url` in `learn`, and on `default` if it
   isn't `null`; if `default` is `null` and `other_defaults` isn't, fetch **only the newest** of
   `other_defaults` (for `build-setup.md` step 4's "a default in a differing context" question).
   Fire the fetches together (parallel tool calls). Read every value from the page's
   **properties**, never from its body (`SKILL.md` → *A setup's real values are its row*). A page
   that fails to fetch is dropped and named in the report.
4. **Build the two results** and hand them to the calling workflow where the REST rows would have
   gone:
   - **The default anchor** (`build-setup.md` step 4): the fetched `default` page — same stage,
     surface, conditions as the build — or the fetched newest `other_defaults` page for the
     "does this match what the game gives you here?" question. Nothing → the screenshots-first
     path, unchanged (it explains what the anchor is for and builds without one if the user says
     so).
   - **The learn pool** (`build-setup.md` step 7): the fetched non-default pages whose
     `Learn from this` property is ticked, **plus every fetched page whose line says
     `learn: yes`**, whatever its checkbox. `Rating` and `Notes` come from the same fetch. None →
     *"no prior setups used"*, as today.
5. **Report**, one line in the build's report (`build-setup.md` step 12), always:
   *"Read {n} saved setups from the {Car}'s index ({names}); {k} count as `Learn from this`;
   {skipped} more not read — say "also learn from my other {Car} setups" to include them."*
   If `malformed` > 0, add: *"{malformed} line(s) in the `Setup index` couldn't be read — open the
   {Car}'s `Setups` page and check them against the format on the line above them."*

## Telling the user

Once per chat, the first time offline mode changes what a workflow does (this replaces the old
line that claimed offline setups couldn't be read at all — don't revert to that phrasing):

> *This chat can't reach Notion's API. That's normal on Claude's Free plan. I can still use the
> setups the skill saved from v{version} on: I read the ones closest to this stage, up to 6, and
> take the ones you ticked `Learn from this`. Older setups count only if you paste a link to them
> here. Say "also learn from my other {Car} setups" to read more. The `Claude Free plan` page in
> your Notion has the details.*

`{version}` is the skill version (`SKILL.md` → *Skill version*); `{Car}` the car in scope, or
"this car's" when none is yet.

## Load more

When the user asks to learn from more setups (*"also learn from my other Stratos setups"*, *"read
all of them"*) or names some (*"learn from turini fast and monte v2 too"*):

1. Re-run the picker on the same file, in code execution — for "more / all":
   ```
   python scripts/setups_list.py --pick setups/<slug>.md --stage "{Stage}" --surface {Surface} --conditions "{Conditions}" --limit 100
   ```
   or for named ones:
   ```
   python scripts/setups_list.py --pick setups/<slug>.md --stage "{Stage}" --surface {Surface} --conditions "{Conditions}" --names "{a}" "{b}"
   ```
   (`--names` returns exactly those lines, a `learn: no` line included when named — say the user
   marked it `learn: no` and ask whether to use it anyway).
2. Fetch **only** the pages not already fetched in this chat.
3. Redo the step that used the learn pool (`build-setup.md` step 7 onward, or the tweak's
   reasoning) with the larger pool, and say in one line what was added. Names in `not_found`
   are reported as not in the index, with the paste-a-link hint (*Adding setups by link*).
   Names in `defaults_named` are **not** "not in the index" — a `Source = default` line is never
   learn material — say instead: *"that's the game's default for {stage} — it is the build's
   anchor, not something to learn from"*.

## Finding one setup by name

For a workflow that needs **one named setup** (`review-setup.md`, `tweak-setup.md`,
`ask-setups.md`, `share-setup.md`) when `egress: none`:

1. The car is known from the request, or from the setup just built or loaded in this chat. If it
   isn't, ask *"Which car is that setup for?"* before reading anything.
2. Fetch the car's `Setups` page and save it per *Saving the page to a file*, then run
   ```
   python scripts/setups_list.py --find "{name}" setups/<slug>.md
   ```
   It prints `matches` (exact name first; else case-insensitive; else lines whose name contains
   the text) and `malformed`. No `Setup index` heading on the page → treat the index as empty and
   don't run the script.
3. **One match** → `notion-fetch` its `url`; that page's properties are the row. **Several** →
   list them (Name / Stage / Date) and ask the user to pick. **None** → don't search the
   database (it can't list a car's rows — never `notion-search` for them, and a database
   `notion-fetch` returns no rows). Say the setup isn't in the {Car}'s index — it may predate
   the index or have been made by hand — and offer the paste-a-link route (*Adding a setup by
   link*).

## Adding setups by link

The user pastes one or more Notion links to setups — *"index these setups: <link> <link> <link>"*,
*"add this one to the index"*, *"learn from this: <link>"* — in any wording that says to add, index,
use or learn from them. **This is the only way a setup that the skill didn't save gets into the
index** (setups saved before the index existed, or made by hand), and it works the same on every
plan. It is what to run right after a skill update, with the links of the setups worth keeping.

1. **Collect the links** from the message. One link or fifty — the steps are the same.
2. **`notion-fetch` every link** (parallel tool calls). For each page, check it is a setup: its
   `<parent-data-source>` is the `Setups` data source under `ACR Setup Engineer`, and its `Car`
   property names a car with a `{Car}` page under the root. A page that fails either check is
   **skipped**, not fatal: note it for the report and go on with the others.
3. **Group the good pages by `Car`.** For each car: fetch its `Setups` page once and save it per
   *Saving the page to a file* (no `Setup index` heading → treat the index as empty and don't run
   the script). For each page of that car run
   `python scripts/setups_list.py --find "{Name}" setups/<slug>.md`; a match with the same `url`
   means it's **already listed** — note it and don't add it again.
4. **Build one line per remaining page** from its properties — `Name`, the page URL, `Source`,
   `Stage`, `Surface`, `Conditions`, `Date` — with `scripts/setups_list.py --line` (a script error
   → skip that page and note it).
5. **One insert per car**, holding all of that car's new lines newest first, per
   `notion-structure.md` → *Adding a line to `Setup index`* (its step 3 covers a page with no
   heading yet and a car with no `Setups` page).
6. **Report**, one line per link, in the order given: *added to the {Car}'s index* / *already
   listed* / *not one of your setups* / *the {Car} has no `Setups` page — say "refresh the {Car}
   in my Notion" first*. Then one line: *"Add ` - learn: yes` or ` - learn: no` to the end of a
   line on the car's `Setups` page to force a setup in or out."*
7. When the user asked to **learn from** a link in this chat, use that fetched page as a learn-pool
   page now (its `Learn from this` checkbox still decides, unless the user says to count it: then
   treat it as `learn: yes` for this chat and suggest the ` - learn: yes` mark).

## Rules
- **Reads only on `egress: none`**; the REST query stays the source whenever it can run. *Adding
  a setup by link* runs on every plan.
- **The index and pasted links are the only way in — never `notion-search` for a car's setups.**
- **Values from properties, never from the page body.**
- **The cap is 6 and the user can lift it** — always say what was read and how to read more.
- **The skill never writes the `learn:` field** and never edits an existing line.
- Stay within `ACR Setup Engineer` scope, as always.
