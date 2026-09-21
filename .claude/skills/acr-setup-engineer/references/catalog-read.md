# Loading a car's catalog — the one read path

Every workflow that needs a car's legal values (build, tweak, review, ask, share, capture, import,
export, edit) loads them **exactly like this**. Nothing else reads a catalog.

A car's catalog is a **template-format YAML file**. It lives in one of two places, and the car's
`Catalog source:` line (on its `Catalog` page) says which (`notion-structure.md` → *Where a car's
catalog lives*):

| The source line says | Kind | The file is |
|---|---|---|
| `bundled template …` | template car | `car-templates/<slug>.yaml` inside the skill |
| `your screenshots …` | screenshot car | the `yaml` block on the car's **`Parameters`** page in Notion |

## Load a car's catalog

1. **Fetch the car's `Catalog` page** (you usually already hold it — `SKILL.md` → *Read
   efficiently*) and read its `Catalog source:` line.
2. **Template car** → the file is on disk. Go to step 5.
3. **Screenshot car** → **fetch the car's `Parameters` page** with `notion-fetch`, in the same
   batch as the car's other pages. Then check the response. **Three outcomes:** the page comes
   back readable → go to step 4; otherwise 3a or 3b.

   **3a — the page is unreadable.** It has `truncated: true` or `unknown_block_count` set, or
   there is no ```` ```yaml ```` block in it → the page is **unreadable**. Say: *"I couldn't read
   the {Car}'s `Parameters` page in full. Open that page in Notion to check it loads, then ask me
   again. If it stays unreadable, say 'onboard the {Car} from my screenshots'."* and **stop this
   workflow**. Never fall back to searching Notion, and never guess values. **Don't offer a
   refresh here** — a refresh never regenerates a `Parameters` page.

   **3b — the page doesn't exist.** This is a car from before catalogs became files. Run
   `onboard-car.md` → *Migration — catalog rows to the `Parameters` page* **now** (it is the one
   write a read workflow may make), then come back to step 3. If that migration ends at its
   source 3 (nothing to recover), say its line and stop.
4. **Save the file** (*Save the file* below): write the block's text, exactly as fetched, to
   `parameters/<slug>.yaml` in the sandbox.
5. **Run the loader** in one code-execution block, together with any other script the workflow
   runs (`check_egress.py`, the `Setups` query, `--show-order`):
   ```
   python scripts/load_catalog.py <file> [--surface Tarmac|Gravel|Snow]
   ```
   `<file>` is `car-templates/<slug>.yaml` or `parameters/<slug>.yaml`. Its output rows are what
   every downstream rule consumes (`notion-rest-read.md` → *Output* shape; surface resolution is
   applied by `--surface`). **If it exits 1 with `parameter_count says …`**, the fetch was
   truncated: treat the page as unreadable (step 3a) — don't retry with the partial file.
   **If it exits 1 with `no parameters found`**, the car's list is empty (a migration could not
   recover it): say *"The {Car} has no parameter list yet. Say 'onboard the {Car} from my
   screenshots' to capture it."* and stop.
6. **Use the same file again** for anything else this run needs: `--check values.json` for
   legality, `--show-order --from-template <file>` for column order. Don't re-fetch.

## Save the file

Write the fetched block to disk with Python, never by retyping it:

```python
import os, pathlib
text = r"""<the yaml block's contents, verbatim>"""
os.makedirs('parameters', exist_ok=True)
pathlib.Path('parameters/<slug>.yaml').write_text(text, encoding='utf-8')
```

The block is the whole file, header and `parameters:` list. Don't edit, reorder or "clean" it.

## Slug

The file name for a screenshot car: the car's Notion name, lower-case, every run of characters
that isn't a letter or digit replaced by one `-`, no leading or trailing `-`. `Škoda Fabia R5` →
`skoda-fabia-r5` (drop accents first). A bundled car's slug is its file name in `car-templates/`.

## What this replaces

There is no `Parameters` database read, no REST query for a catalog, no snapshot fallback and no
paste route. If an older reference or memory mentions them, this file wins.
