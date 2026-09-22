# Catalog as a template file — bundled or in Notion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every car's catalog is a template-format YAML file — bundled in the skill, or stored on a `Parameters` page under the car in Notion — read by one script, edited in chat, with no `Parameters` database and no snapshot/paste machinery.

**Architecture:** `load_catalog.py` becomes the only catalog reader and gains `--to-template` so YAML is never hand-formatted. Workflows fetch a screenshot car's `Parameters` page with the Notion connector, save the YAML block to the sandbox, and run the same script they run on a bundled file. The REST script keeps only the `Setups` reads and template-based column ordering. All references and the README are rewritten to the one read path; a new `edit-catalog.md` workflow changes a car's list (forking a bundled car on first edit).

**Tech Stack:** Python 3 stdlib scripts (the code sandbox has no PyYAML); `unittest` tests (PyYAML allowed in tests only); Markdown skill references.

**Spec:** `docs/superpowers/specs/2026-09-21-catalog-as-yaml-in-notion-design.md`

## Global Constraints

- Scripts under `.claude/skills/acr-setup-engineer/scripts/` are **stdlib only**. Output is always UTF-8.
- **Every workflow must be followable by a less capable model (Sonnet):** short numbered steps, one decision per step, the exact wording to say, and a script for anything deterministic (parsing, YAML, validation). Recorded as a project rule in Task 1.
- The child page is named **`Parameters`**. It is the complete list, read *instead of* the bundled file.
- Nothing in the user's Notion is ever deleted. The legacy `Parameters` DB is left alone and never read.
- The `Catalog source:` line formats: template car `**Catalog source:** bundled template — game version {v}, from {game files | a community export}`; screenshot car `**Catalog source:** your screenshots — game version {v}`; forked car `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
- Maintenance line of the `Parameters` page, screenshot car: *Your car's parameter list, kept by the skill. To change a range, say it in chat ("the front ARB goes 1 to 6 in steps of 1") — don't edit this page by hand. It survives refreshes.*
- Maintenance line of the `Parameters` page, forked car: *Started {YYYY-MM-DD} as a copy of the bundled template (game version {tv}), with your edits. The skill keeps this list; say changes in chat.*
- "Not in use" line (added at the top of a `Parameters` page when the car switches to a bundled template): *Not in use since {YYYY-MM-DD}: a newer bundled template (game version {v}) appeared, so this car uses that now. Say 'onboard the {Car} from my screenshots' to use this list again.*
- Dates come from `python -c "import datetime; print(datetime.date.today().isoformat())"` (the existing `Date` rule in `notion-structure.md`), never guessed.
- Run the whole suite with `python -m unittest discover -s tests` from the repo root. It must stay green after every task.
- Commits: `git add` the named files only; message ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Never push.

---

## File map

| File | Responsibility after this plan |
|---|---|
| `CLAUDE.md` | maintainer notes; gains the Sonnet-followable rule and the new file list |
| `scripts/load_catalog.py` | the only catalog reader; `--to-template`; `parameter_count` check; no `--snapshot` |
| `scripts/query_notion_parameters.py` | `Setups` reads over REST; `--show-order --from-template …` only |
| `references/notion-structure.md` | data model: five child pages, `Parameters` page, one ordering case, legacy DB note |
| `references/notion-rest-read.md` | `Setups` reads + offline mode only |
| `references/catalog-read.md` (new) | the one read path every workflow points to |
| `references/edit-catalog.md` (new) | change a car's list in chat; fork a bundled car |
| `references/onboard-car.md` | screenshot path writes the `Parameters` page; refresh + migration |
| `references/export-car-template.md` | export = the page's file |
| `references/import-savegame.md`, `build-setup.md`, `tweak-setup.md`, `capture-setup.md`, `share-setup.md`, `review-setup.md`, `ask-setups.md`, `refresh-notion.md` | point at `catalog-read.md` |
| `references/refresh-catalog-snapshot.md` | deleted |
| `references/how-to-use-template.md`, `free-plan-template.md` | one new line / bullets removed |
| `SKILL.md` | routing table, tools list, *Reading rows* rule |
| `README.md` | user docs |
| `tests/test_load_catalog.py`, `tests/test_query_notion_parameters.py`, `tests/test_references.py` (new) | tests |

All `references/` and `scripts/` paths are under `.claude/skills/acr-setup-engineer/`.

---

### Task 1: Project rule — workflows must be followable by a less capable model

**Files:**
- Modify: `CLAUDE.md` (after the "## Where things live" section, before "## Release procedure")

- [ ] **Step 1: Add the rule**

Insert this section:

```markdown
## Writing rule — every workflow must work on a less capable model

The references are executed by whatever model the user runs, often Sonnet. Write them so that
model gets it right without judgement calls:

- Short numbered steps. One decision per step, stated as a question with its answers.
- The exact wording to say to the user, in quotes, wherever a line is required.
- A script does anything deterministic: parsing, YAML, validation, ordering, dates. The model
  never hand-formats YAML, never computes a `SHOW` list, never guesses a date.
- Say which file to read *before* the step that needs it, not after.
- One place per rule. Other files point at it; they don't restate it.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: project rule - workflows must work on a less capable model

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `load_catalog.py` — `--to-template`, `parameter_count` check, drop `--snapshot`

**Files:**
- Modify: `scripts/load_catalog.py`
- Test: `tests/test_load_catalog.py`

**Interfaces:**
- Produces: `python scripts/load_catalog.py --to-template rows.json` → a complete template YAML on stdout. `rows.json` is `{"header": {...}, "rows": [...]}` where `rows` are in the REST *Output* shape (`Adjustment`, `Section`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`, optional `Surface`) and `header` holds any of `car, game, save_ids, drivetrain, engine_layout, weight_bias, weight, max_power, max_torque, class, gearbox, steering_lock, version, source, forked_from`. The script adds `written_at`, `skill_version`, `parameter_count`.
- Produces: loading a template whose header has `parameter_count: N` fails with exit 1 and message `parameter_count says N but the file has M parameters` when N ≠ M.
- Removes: `--snapshot`.

- [ ] **Step 1: Replace `TestSnapshot` with failing tests for the new behaviour**

In `tests/test_load_catalog.py`, delete the whole `class TestSnapshot(LoadCatalogTestCase)` block, delete `test_snapshot_output_is_utf8` from `TestOutputEncoding`, and change the `run(STRATOS, '--snapshot', '--surfaces', 'Gravel', expect=2)` line in `test_an_unknown_flag_is_a_usage_error` to `run(STRATOS, '--surfaces', 'Gravel', expect=2)`. Change the `TestSkillVersionResolution` docstring's first line to ```"""`--to-template` records the skill version per SKILL.md -> *Skill version*: the VERSION```. Then add:

```python
class TestToTemplate(LoadCatalogTestCase):
    """`--to-template rows.json` emits a complete template YAML from REST-shaped rows."""

    def _rows_json(self, header=None, rows=None):
        import tempfile
        payload = {
            'header': header if header is not None else {
                'car': 'Test Car 1999', 'drivetrain': 'AWD', 'version': '0.6',
                'source': 'screenshots', 'weight': '~1200 kg'},
            'rows': rows if rows is not None else [
                {'Adjustment': 'Spring Stiffness Front', 'Section': 'Suspensions', 'Min': 30000,
                 'Max': 60000, 'Unit': 'N/m', 'Discrete steps': '30000, 45000, 60000',
                 'Order': 2020, 'Car': 'Test Car 1999'},
                {'Adjustment': 'Spring Stiffness Front', 'Section': 'Suspensions', 'Min': 20000,
                 'Max': 40000, 'Unit': 'N/m', 'Discrete steps': '', 'Order': 2020,
                 'Surface': 'Gravel', 'Car': 'Test Car 1999'},
                {'Adjustment': 'Primary Gear', 'Section': 'Gearbox', 'Min': '—', 'Max': '—',
                 'Unit': '', 'Discrete steps': '35//30*33//28, 33//28*32//31', 'Order': 1020,
                 'Car': 'Test Car 1999'},
            ]}
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False)
        self.addCleanup(os.remove, path)
        return path

    def _to_template(self, **kw):
        out = subprocess.run([sys.executable, SCRIPT, '--to-template', self._rows_json(**kw)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_output_is_yaml_with_the_header_and_the_parameters(self):
        doc = yaml.safe_load(self._to_template())
        self.assertEqual(doc['car'], 'Test Car 1999')
        self.assertEqual(doc['source'], 'screenshots')
        self.assertEqual(doc['weight'], '~1200 kg')
        self.assertEqual(doc['parameter_count'], 3)
        self.assertEqual(len(doc['parameters']), 3)
        self.assertRegex(doc['written_at'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertTrue(doc['skill_version'])

    def test_parameters_are_sorted_by_order_baseline_before_surface(self):
        doc = yaml.safe_load(self._to_template())
        got = [(p['adjustment'], p.get('surface')) for p in doc['parameters']]
        self.assertEqual(got, [('Primary Gear', None), ('Spring Stiffness Front', None),
                               ('Spring Stiffness Front', 'Gravel')])

    def test_round_trips_through_the_loader_to_the_same_rows(self):
        import tempfile
        text = self._to_template()
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        rows = json.loads(run(path)[0])
        gear = next(r for r in rows if r['Adjustment'] == 'Primary Gear')
        self.assertEqual(gear['Discrete steps'], '35//30*33//28, 33//28*32//31')
        self.assertEqual(gear['Min'], '—')
        gravel = next(r for r in rows if r.get('Surface') == 'Gravel')
        self.assertEqual(gravel['Min'], 20000)
        self.assertEqual({r['Car'] for r in rows}, {'Test Car 1999'})

    def test_forked_from_is_carried_when_given(self):
        doc = yaml.safe_load(self._to_template(header={
            'car': 'Test Car 1999', 'version': '0.6', 'source': 'screenshots',
            'forked_from': 'bundled template v0.6'}))
        self.assertEqual(doc['forked_from'], 'bundled template v0.6')

    def test_an_edited_copy_of_a_bundled_car_loads_to_the_same_rows_plus_the_edit(self):
        # What edit-catalog.md does on a bundled car: load, change one row, --to-template, load.
        import tempfile
        rows = json.loads(run(STRATOS)[0])
        target = next(r for r in rows if r['Adjustment'] == 'Spring Stiffness Front' and not r.get('Surface'))
        target['Max'] = 99000
        header = {'car': 'Lancia Stratos HF 1976', 'drivetrain': 'RWD', 'version': '0.6',
                  'source': 'screenshots', 'forked_from': 'bundled template v0.6'}
        text = self._to_template(header=header, rows=rows)
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        again = json.loads(run(path)[0])
        self.assertEqual(len(again), len(rows))
        self.assertEqual({r['Adjustment'] for r in again}, {r['Adjustment'] for r in rows})
        edited = next(r for r in again if r['Adjustment'] == 'Spring Stiffness Front' and not r.get('Surface'))
        self.assertEqual(edited['Max'], 99000)

    def test_missing_rows_file_exits_one(self):
        out = subprocess.run([sys.executable, SCRIPT, '--to-template', 'no-such.json'],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 1)


class TestParameterCount(LoadCatalogTestCase):
    def _with_count(self, n):
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(f'parameter_count: {n}\n' + FIXTURE)
        self.addCleanup(os.remove, path)
        return path

    def test_matching_count_loads(self):
        rows = json.loads(run(self.fixture)[0])
        out, _ = run(self._with_count(len(rows)))
        self.assertEqual(len(json.loads(out)), len(rows))

    def test_mismatched_count_exits_one_with_a_clear_message(self):
        rows = json.loads(run(self.fixture)[0])
        _, err = run(self._with_count(len(rows) + 5), expect=1)
        self.assertIn(f'parameter_count says {len(rows) + 5} but the file has {len(rows)}', err)

    def test_snapshot_flag_is_gone(self):
        run(STRATOS, '--snapshot', expect=2)
```

Check the top of the test file: `FIXTURE` must start with `car: "Test Car 1999"` (it does) so prepending a `parameter_count:` line is valid YAML. Ensure `json`, `subprocess`, `sys`, `os` are imported (they are).

- [ ] **Step 2: Run the new tests to see them fail**

Run: `python -m unittest tests.test_load_catalog -v 2>&1 | tail -15`
Expected: `TestToTemplate` tests fail with exit code 2 / "unknown option --to-template"; `test_mismatched_count_exits_one_with_a_clear_message` fails (exit 0); `test_snapshot_flag_is_gone` fails (exit 0).

- [ ] **Step 3: Implement**

In `scripts/load_catalog.py`:

1. Update the module docstring: remove the `--snapshot` usage line and its option paragraph; add
   ```
     # A complete template YAML from REST-shaped rows (what onboarding / editing assemble):
     python scripts/load_catalog.py --to-template rows.json
   ```
   and the option text:
   ```
     --to-template F  F is JSON: {"header": {...}, "rows": [...]}, rows in the REST read's
                    Output shape and header any of the template header keys (car, game,
                    save_ids, drivetrain, engine_layout, weight_bias, weight, max_power,
                    max_torque, class, gearbox, steering_lock, version, source, forked_from).
                    Prints a complete template YAML — the body of a car's `Parameters` page —
                    adding written_at, skill_version and parameter_count. No template path.
   ```
   and under Exit codes keep `1 file/parse error`. Mention: `parameter_count` in a template header is checked on load.
2. `FLAGS = ('--pretty',)`.
3. `HEADER_FIELDS = ('car', 'version', 'source', 'drivetrain', 'gearing_tool', 'parameter_count')`.
4. In `load_template`, after `if not rows: fail(...)`, add:
   ```python
   declared = header.get('parameter_count')
   if declared is not None:
       try:
           declared = int(declared)
       except ValueError:
           fail(f'parameter_count is not a number: {declared!r}')
       if declared != len(rows):
           fail(f'parameter_count says {declared} but the file has {len(rows)} parameters '
                f'— the page fetch may be truncated; re-fetch it')
   ```
5. Replace `SNAPSHOT_KEYS` and `snapshot()` with:
   ```python
   # Template header keys, in the order export-car-template.md lists them, then the
   # bookkeeping keys this script adds.
   TEMPLATE_HEADER_ORDER = ('car', 'game', 'save_ids', 'drivetrain', 'engine_layout',
                            'weight_bias', 'weight', 'max_power', 'max_torque', 'class',
                            'gearbox', 'steering_lock', 'version', 'source', 'forked_from')
   # REST-shape row key -> template parameter key, in template order.
   ROW_TO_TEMPLATE = (('Section', 'section'), ('Adjustment', 'adjustment'), ('Order', 'order'),
                      ('Min', 'min'), ('Max', 'max'), ('Unit', 'unit'),
                      ('Discrete steps', 'discrete_steps'), ('Surface', 'surface'))


   def to_template(header, rows):
       """A complete template YAML (the body of a car's `Parameters` page) from REST-shaped rows."""
       out = []
       for key in TEMPLATE_HEADER_ORDER:
           if header.get(key) in (None, ''):
               continue
           value = header[key]
           if key == 'save_ids':
               ids = value if isinstance(value, list) else [value]
               out.append('save_ids: [' + ', '.join(yaml_scalar('save_ids', v) for v in ids) + ']')
           else:
               out.append(f'{key}: {yaml_scalar(key, str(value))}')
       out.append(f'written_at: {yaml_scalar("written_at", datetime.date.today().isoformat())}')
       out.append(f'skill_version: {yaml_scalar("skill_version", skill_version())}')
       out.append(f'parameter_count: {len(rows)}')
       out.append('parameters:')

       def sort_key(row):
           order = row.get('Order')
           return (order is None, order if order is not None else 0,
                   row.get('Adjustment', ''), 1 if row.get('Surface') else 0, row.get('Surface') or '')

       for row in sorted(rows, key=sort_key):
           first = True
           for src, dst in ROW_TO_TEMPLATE:
               if src not in row or row[src] is None or (src == 'Surface' and not row[src]):
                   continue
               lead = '  - ' if first else '    '
               out.append(f'{lead}{dst}: {yaml_scalar(src, row[src])}')
               first = False
       return '\n'.join(out) + '\n'
   ```
   `yaml_scalar` already quotes `Unit` / `Discrete steps` always and quotes anything with unusual characters (so `—`, `*`, `°` survive); every header value is passed as `str`, and the regex leaves plain words unquoted — matching the bundled files. Add `'car'` to `ALWAYS_QUOTED` so `car:` is quoted like the bundled templates: `ALWAYS_QUOTED = ('car', 'Unit', 'Discrete steps')`.
6. `USAGE`: `'usage: load_catalog.py <template.yaml> [--surface Tarmac|Gravel|Snow]\n                       [--check values.json] [--pretty]\n       load_catalog.py --to-template rows.json'`.
7. In `main()`, parse `--to-template` like `--check` (takes a value; variable `to_template_path`). Before the `if len(positional) != 1` check, add:
   ```python
   if to_template_path is not None:
       if positional or flags or surface is not None or check_path is not None:
           fail(f'--to-template takes no other arguments\n{USAGE}', 2)
       try:
           with open(to_template_path, encoding='utf-8') as fh:
               payload = json.load(fh)
       except OSError as exc:
           fail(f'cannot read rows file: {exc}')
       except json.JSONDecodeError as exc:
           fail(f'rows file is not valid JSON: {exc}')
       if not isinstance(payload, dict) or not isinstance(payload.get('rows'), list):
           fail('rows file must be {"header": {...}, "rows": [...]}', 2)
       print(to_template(payload.get('header') or {}, payload['rows']), end='')
       sys.exit(0)
   ```
   Remove the `if '--snapshot' in flags:` block.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_load_catalog -v 2>&1 | tail -5`
Expected: OK.

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK (if `test_query_notion_parameters` or another test referenced `--snapshot`, fix it there — none should).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/scripts/load_catalog.py tests/test_load_catalog.py
git commit -m "feat(scripts): load_catalog --to-template and parameter_count check; drop --snapshot

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `query_notion_parameters.py` — `Setups` reads and template ordering only

**Files:**
- Modify: `scripts/query_notion_parameters.py`
- Test: `tests/test_query_notion_parameters.py`

**Interfaces:**
- Keeps: `python scripts/query_notion_parameters.py <setups_data_source_id> <token> "<car>" [--learn-only] [--source default] [--pretty]` and `python scripts/query_notion_parameters.py --show-order --from-template <file.yaml> …`.
- Removes: `--all`; a positional query combined with `--show-order`; `drop_template_cars`, `read_template_car`.

- [ ] **Step 1: Update the tests first**

In `tests/test_query_notion_parameters.py`:
- In `TestQuery`, delete `test_all_skips_car_filter`.
- In `TestMainShowOrder`, delete `test_template_and_notion_rows_are_ordered_together_in_one_call`, `test_mixed_call_passes_the_car_name_through`, `test_token_only_show_order_still_works`, `test_legacy_rows_of_a_template_car_are_dropped_before_ordering`, `test_legacy_rows_are_dropped_through_the_skill_name_normalisation`, `test_a_notion_failure_in_a_mixed_call_prints_nothing_and_exits_1`, `test_incomplete_positional_args_with_templates_is_a_usage_error`. Keep `test_the_same_adjustment_from_two_cars_keeps_the_lower_order` only if it uses two `--from-template` files; if it mixes Notion rows, rewrite it to two templates:
  ```python
  def test_the_same_adjustment_from_two_cars_keeps_the_lower_order(self):
      a = self._write('car: "A"\nparameters:\n  - adjustment: "Brake Bias"\n    order: 7010\n')
      b = self._write('car: "B"\nparameters:\n  - adjustment: "Brake Bias"\n    order: 7005\n')
      code, out = self._run(['--show-order', '--from-template', a, '--from-template', b])
      self.assertEqual(code, 0)
      self.assertIn('"Brake Bias"', out)
  ```
- Delete `class TestNormaliseCarName` only if `normalise_car_name` is removed in step 3 (it is used by `drop_template_cars` only — check with `grep -n normalise_car_name`; if nothing else uses it, delete both the function and the test class).
- Add to `TestMainShowOrder`:
  ```python
  def test_all_flag_is_gone(self):
      with patch.object(Q, 'query', return_value=[]):
          code, _ = self._run(['ds-id', 'tok', '--all', '--show-order'])
      self.assertEqual(code, 2)

  def test_show_order_with_a_notion_query_is_a_usage_error(self):
      with patch.object(Q, 'query', return_value=[]):
          code, _ = self._run(['ds-id', 'tok', 'Some Car', '--show-order'])
      self.assertEqual(code, 2)
  ```

- [ ] **Step 2: Run the tests to see the two new ones fail**

Run: `python -m unittest tests.test_query_notion_parameters -v 2>&1 | tail -8`
Expected: the two new tests FAIL (exit 0 instead of 2); everything else passes.

- [ ] **Step 3: Implement**

In `scripts/query_notion_parameters.py`:
1. Docstring: remove the "All Parameters rows for one car" example and every mention of `Parameters` rows / `--all` / the mixed call; the script reads **`Setups` slices** and builds `SHOW` lists **from template files**. Keep `--learn-only`, `--source`, `--show-order --from-template`, `--pretty`.
2. Delete `read_template_car`, `drop_template_cars`, and `normalise_car_name` if unused elsewhere (`grep -n normalise_car_name` must return only its definition).
3. In `main()`: delete `all_cars = '--all' in flags`. Usage becomes:
   ```python
   usage = ('usage: query_notion_parameters.py <setups_data_source_id> <token> <car_name>'
            ' [--learn-only] [--source <value>] [--pretty]\n'
            '       query_notion_parameters.py --show-order --from-template <template.yaml> ...')
   ```
   Replace the template block and the Notion block with:
   ```python
   if '--all' in flags:
       print(usage, file=sys.stderr)
       sys.exit(2)

   if show_order:
       if positional or not templates:
           print(usage, file=sys.stderr)
           sys.exit(2)
       template_rows = []
       for path in templates:
           try:
               template_rows.extend(read_template_rows(path))
           except OSError as exc:
               print(f'cannot read template: {exc}', file=sys.stderr)
               sys.exit(1)
       print(build_show_order(template_rows))
       sys.exit(0)

   if templates:
       print('--from-template requires --show-order', file=sys.stderr)
       sys.exit(2)
   if len(positional) < 3:
       print(usage, file=sys.stderr)
       sys.exit(2)
   data_source_id, token, car_name = positional[0], positional[1], positional[2]
   rows = query(data_source_id, token, car_name, learn_only=learn_only, source=source)
   ```
   Keep the `pretty` / JSON printing that follows, dropping `rows = notion_rows`.
4. In `query()`, `car_name` is always given now; leave the `None` handling in `build_filter` (harmless) but make sure the `--all` tests are gone.

- [ ] **Step 4: Run all tests**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/scripts/query_notion_parameters.py tests/test_query_notion_parameters.py
git commit -m "feat(scripts): query_notion_parameters reads Setups only; SHOW from templates only

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: The one read path — `references/catalog-read.md`

**Files:**
- Create: `references/catalog-read.md`
- Create: `tests/test_references.py`

**Interfaces:**
- Produces: the section names later tasks link to: *Load a car's catalog*, *Save the file*, *Slug*.

- [ ] **Step 1: Write the guard test**

`tests/test_references.py`:

```python
"""Guard the skill references against the machinery this design removed.

Run: python -m unittest discover -s tests
"""
import glob
import os
import re
import unittest

SKILL = os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'acr-setup-engineer')
FILES = [os.path.join(SKILL, 'SKILL.md')] + sorted(glob.glob(os.path.join(SKILL, 'references', '*.md')))

# A phrase that must not appear anywhere (case-insensitive), except in the one file allowed.
BANNED = [
    ('catalog snapshot', {'notion-structure.md', 'onboard-car.md', 'catalog-read.md'}),  # legacy + migration
    ('refresh-catalog-snapshot', set()),
    ('paste the', set()),
    ('--snapshot', set()),
    ('--all', set()),
    ('params_data_source_id', set()),
    ('`parameters` rows', {'notion-structure.md', 'onboard-car.md'}),   # legacy note + migration only
    ('`parameters` db', {'notion-structure.md', 'onboard-car.md'}),
]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class TestNoRemovedMachinery(unittest.TestCase):
    def test_catalog_read_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(SKILL, 'references', 'catalog-read.md')))

    def test_snapshot_workflow_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(SKILL, 'references', 'refresh-catalog-snapshot.md')))

    def test_banned_phrases(self):
        problems = []
        for path in FILES:
            name = os.path.basename(path)
            text = read(path).lower()
            for phrase, allowed in BANNED:
                if name in allowed:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if phrase in line:
                        problems.append(f'{name}:{i}: {phrase!r}')
        self.assertFalse(problems, '\n'.join(problems))

    def test_every_catalog_loading_workflow_points_at_catalog_read(self):
        for name in ('build-setup.md', 'tweak-setup.md', 'capture-setup.md', 'share-setup.md',
                     'review-setup.md', 'ask-setups.md', 'import-savegame.md',
                     'export-car-template.md', 'edit-catalog.md'):
            self.assertIn('catalog-read.md', read(os.path.join(SKILL, 'references', name)), name)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m unittest tests.test_references -v 2>&1 | tail -8`
Expected: all four FAIL (file missing; snapshot workflow present; many banned hits; links missing).

- [ ] **Step 3: Create `references/catalog-read.md`**

```markdown
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
   batch as the car's other pages. Then check the response:
   - It has `truncated: true` or `unknown_block_count` set, or there is no ```` ```yaml ````
     block in it → the page is **unreadable**. Say: *"I can't read the {Car}'s `Parameters` page
     in full, so I can't load its parameter list. Say 'refresh the {Car} in my Notion' to rebuild
     it, or 'onboard the {Car} from my screenshots'."* and **stop this workflow**. Never fall back
     to searching Notion, and never guess values.
   - The page doesn't exist → this is a car from before catalogs became files. Run
     `onboard-car.md` → *Migration — catalog rows to the `Parameters` page* **now** (it is the
     one write a read workflow may make), then come back to step 3. If that migration ends at
     its source 3 (nothing to recover), say its line and stop.
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
   truncated: treat the page as unreadable (step 3) — don't retry with the partial file.
6. **Use the same file again** for anything else this run needs: `--check values.json` for
   legality, `--show-order --from-template <file>` for column order. Don't re-fetch.

## Save the file

Write the fetched block to disk with Python, never by retyping it:

```python
import os, pathlib
text = """<the yaml block's contents, verbatim>"""
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
```

- [ ] **Step 4: Run the guard test**

Run: `python -m unittest tests.test_references -v 2>&1 | tail -8`
Expected: `test_catalog_read_exists` passes; the other three still fail (they pass at the end of Task 10).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/catalog-read.md tests/test_references.py
git commit -m "docs(skill): catalog-read.md - the one catalog read path; guard test

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `notion-structure.md` — the data model

**Files:**
- Modify: `references/notion-structure.md`

- [ ] **Step 1: Resolution rule (top of file)**

In item 3 of *Resolution rule*, replace the sentences about the `Parameters` DB (from `The **`Parameters`** DB is created` to `has nothing to do.`) with:

```markdown
There is **no `Parameters` database** any more: a screenshot car's catalog is the
   `Parameters` **page** under the car (*`Parameters` page* below). A `Parameters` DB an older
   skill version created is left alone and never read (*Legacy `Parameters` DB* below).
```

- [ ] **Step 2: *Where a car's catalog lives***

Replace the two kind bullets and the paragraph after them (from `- **Template car**` to `and legality.`) with:

```markdown
- **Template car** — a car that has a bundled `car-templates/*.yaml` (matched on the file's
  `car:` field, by the rule in `onboard-car.md` step 1 → *Matching a car name*).
  **The template file is its catalog.** Onboarding a template car writes no catalog to Notion,
  and its values change only when the skill ships a new template.
- **Screenshot car** — a car whose catalog is **the `yaml` block on its `Parameters` page** in
  Notion: captured from the user's min/max setup-screen screenshots, or copied from a bundled
  template and then edited in chat (`edit-catalog.md`). The block is a complete template file in
  the same format as a bundled one.

Both are read by **one script on one file** — `catalog-read.md` — so every rule about the rows is
the same either way: surface resolution, `Discrete steps` vs numeric `Min..Max`, `Order`, legality.
```

Replace the paragraph starting `**Legacy `Parameters` rows of a template car**` with:

```markdown
**A legacy `Parameters` DB** — created by skill versions before every catalog became a file —
is **never read and never deleted**. A refresh migrates each screenshot car's rows into its
`Parameters` page once (`onboard-car.md` → *Migration — catalog rows to the `Parameters`
page*) and then says, once, that the table can be deleted.
```

Delete the sentence in the `source line` rule 3 area that says a user "stays one until they refresh it from the template" if still present; the version rule from the previous release remains.

- [ ] **Step 3: Hierarchy**

Replace the `├── Parameters (DB)` lines (three lines) with nothing (delete them). In the `{Car}` subtree add, between the `Log` lines and `Setups`:

```
    ├── Parameters (page)      SCREENSHOT CARS ONLY. The car's complete parameter list as a
    │                           template-format YAML block. THE SKILL'S — edited only through
    │                           chat (edit-catalog.md); never regenerated, it is the only copy
```

- [ ] **Step 4: `Parameters` DB section → legacy note**

Replace the whole `## `Parameters` DB — one row per …` section (up to but not including `## `Setups` DB`) with:

```markdown
## Legacy `Parameters` DB

Skill versions before every catalog became a file kept a screenshot car's catalog as rows in a
`Parameters` database under the root (`Car`, `Section`, `Adjustment`, `Min`, `Max`, `Unit`,
`Discrete steps`, `Order`, optional `Surface`). **The skill no longer creates, reads or writes
it.** It stays in the user's Notion until they delete it. The one thing the skill still does
with it: a refresh of a screenshot car that has no `Parameters` page yet may read that car's
rows over REST, once, to build the page (`onboard-car.md` → *Migration — catalog rows to the
`Parameters` page*).
```

- [ ] **Step 5: *Applying the order* — one case**

Replace everything from `**One call per view. Three cases, and the view decides which:**` down to (not including) `Whichever case applies, the script prints` with:

```markdown
**One form, every view.** Every car's catalog is a template file — bundled, or the screenshot
car's `parameters/<slug>.yaml` saved to the sandbox by `catalog-read.md`. Pass one
`--from-template` per car the view spans:

```
python scripts/query_notion_parameters.py --show-order --from-template <file1> --from-template <file2> …
```

- **Per-car view** (the car's `Setups` page) → that car's file only.
- **Main `Setups` table, `{Location}` and `{Stage}` views** → every onboarded car's file.

No token, no network, on every plan.

**Which files to pass, without extra reads.** The onboarded cars are the `{Car}` pages under the
root — the root fetch you already did lists them. For each: a name matching a bundled template →
`car-templates/<slug>.yaml`, **unless** its `Catalog` page was read this run and says
`your screenshots`; otherwise it is a screenshot car → fetch its `Parameters` page (batch these
fetches) and save each per `catalog-read.md` → *Save the file*. A screenshot car whose page can't
be read is left out: say in one line that its columns keep their current position until its page
is readable. **Never drop the `SHOW`** for that reason, and never assemble a list by hand.
```

Then in the bullet list that follows (`- **main `Setups` table view** → case 3; …`), delete the `case 1 or 2` / `case 3` words so each bullet just says `→ `SHOW <script output>``.

- [ ] **Step 6: Car page — five children and the maintenance table**

In *Car page*: change "exists to hold exactly four child pages" to "five child pages (four for a template car — it has no `Parameters` page)". Add a `Parameters` row to the maintenance-line table, after `Log`:

```markdown
| `Parameters` | screenshot car: *Your car's parameter list, kept by the skill. To change a range, say it in chat ("the front ARB goes 1 to 6 in steps of 1") — don't edit this page by hand. It survives refreshes.* — forked car: *Started {YYYY-MM-DD} as a copy of the bundled template (game version {tv}), with your edits. The skill keeps this list; say changes in chat.* |
```

Update the ownership table (the `| **`Log`** | **shared** …` table near *A car's pages are split by ownership* if it lives here; otherwise it is in `SKILL.md`, Task 8) to add `| **`Parameters`** | the skill's | written by onboarding and `edit-catalog.md`; **never** by a refresh (except the *Not in use* line); the only copy |`.

Delete the "**Catalog source:** … Screenshot car:" format bullet's mention of `Parameters` rows if any, and add the forked format:

```markdown
   - **Forked car** (a bundled template the user edited in chat):
     `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
     It is a screenshot car for every rule.
```

In `### `Catalog` page`, item list "Then, in order:", delete the item about the `Catalog snapshot` toggle (item 5 or wherever it sits) and the sentence in *Placement & refresh mechanics* that mentions it.

- [ ] **Step 7: Add the `Parameters` page section**

After `### `Log` page — shared; the skill only adds` (and its *Resolving the page* subsection), before `### `Setups` page`, add:

```markdown
### `Parameters` page — screenshot cars only; the skill's; edited through chat

The car's complete catalog, as a **template-format YAML file** in one fenced ```` ```yaml ````
block. Read by `catalog-read.md`; written by `onboard-car.md` (screenshot path), by
`edit-catalog.md`, and by the one-time migration in a refresh. A template car has no such page.

**Body, in this order — nothing else on the page:**

1. The maintenance line (*Car page* table above — the screenshot or the forked wording).
2. **Only when the car has switched to a bundled template:** the *Not in use* line, italic:
   *Not in use since {YYYY-MM-DD}: a newer bundled template (game version {v}) appeared, so this
   car uses that now. Say 'onboard the {Car} from my screenshots' to use this list again.*
3. One ```` ```yaml ```` block: the file printed by
   `python scripts/load_catalog.py --to-template rows.json` — header (`car`, `drivetrain`, the
   identity facts, `version`, `source: "screenshots"`, `forked_from` for a forked car,
   `written_at`, `skill_version`, `parameter_count`), then `parameters:`. **Never write this
   block by hand**: build `rows.json` from the rows in hand and paste the script's output.

**Rules:**
- **The only copy.** A refresh never regenerates it — there is nothing to regenerate it from.
  The one write a refresh makes here is inserting the *Not in use* line (item 2) when the car
  switches to a bundled template; the block stays.
- **Replace, never append.** An edit or a re-onboard replaces the block (delete it, write the new
  one), so there is exactly one block on the page.
- **A `parameter_count` mismatch on read means a truncated fetch, never a bad file** — the read
  path stops and says so (`catalog-read.md` step 5).
- **Never delete the page.** If the user asks for the car to be removed, tell them what to
  delete in Notion; the skill deletes nothing.
```

- [ ] **Step 8: Delete the `### Catalog snapshot` section**

Delete it entirely (from `### Catalog snapshot` to just before `## Locations & stages catalogue`). Then grep the file for `snapshot` and remove or reword every remaining mention (the `Read efficiently` / backfill mentions, the `Reading rows` section paragraph about "The one connector-readable copy…" → replace that paragraph with: `A screenshot car's catalog is read from its `Parameters` page through the connector — `catalog-read.md`. The REST token is only ever needed for `Setups` reads.`).

- [ ] **Step 9: Check**

Run: `grep -n -i "snapshot\|Parameters\` DB\|params_data_source" .claude/skills/acr-setup-engineer/references/notion-structure.md`
Expected: only lines inside *Legacy `Parameters` DB* and the migration cross-reference.

Run: `python -m unittest discover -s tests 2>&1 | tail -3` — the guard test still fails on other files; everything else OK.

- [ ] **Step 10: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/notion-structure.md
git commit -m "docs(skill): notion-structure - Parameters page, no Parameters DB, one ordering form

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: `notion-rest-read.md` — `Setups` reads and offline mode only

**Files:**
- Modify: `references/notion-rest-read.md`

- [ ] **Step 1: Rewrite the scope**

Replace the title and the two opening paragraphs (through `**`Setups` slices are read here for every car**, template or screenshot.`) with:

```markdown
# Reading `Setups` rows from Notion — the REST query

**The one way to read a filtered slice of the `Setups` database** (the learn pool, a stored game
default, a named setup's row when a workflow needs the row's values). Use it wherever a workflow
says "fetch this car's `Setups` rows".

**Catalogs are not read here.** A car's legal values come from a template file — bundled, or the
`yaml` block on the car's `Parameters` page — loaded by `catalog-read.md`. That path needs no
token and no network, on every plan.
```

- [ ] **Step 2: Remove the catalog parts**

- Delete the `## Resolving the range for a surface` section if it only applies to catalog rows — **keep it** if `load_catalog.py --surface` is documented as implementing it (it is: keep the section, and add one line at its top: `Applied for you by `load_catalog.py --surface`; documented here because `catalog-read.md` points to it.`).
- In the *Output* section, keep the row shape (it is the contract `load_catalog.py` honours) and say so in one line: `This is also the shape `load_catalog.py` prints, so the two sources are interchangeable downstream.`
- In *Offline mode*, delete the `a **screenshot car's `Parameters`** → its `Catalog snapshot`` bullet and the `For a **screenshot car**, add that its parameter list comes from the `Catalog snapshot`…` sentence. In the `column order` bullet, replace `the template part only (`notion-structure.md` → *Applying the order*)` with `unchanged — it never needed the network (`notion-structure.md` → *Applying the order*)`.
- In *the fallback ladder*: delete the sentence `**Template cars never enter this ladder for their catalog** … any car.`; delete the `**`Parameters` catalog reads** (a screenshot car) fall back …` bullet; delete rung 3's `Neither the query nor a valid snapshot is available` wording → `3. **The query can't run and the workflow needs the rows:** say which feature was skipped and go on without them (rung 2). Never assemble rows from search results, and never guess.`
- Delete the whole `## The catalog snapshot fallback` section.
- Any remaining `Parameters` mention in the usage examples (`<data_source_id>` for `Parameters`, `--all`) → remove; the examples are the `Setups` data source only.

- [ ] **Step 3: Check and commit**

Run: `grep -n -i "snapshot\|Parameters\|--all\|paste" .claude/skills/acr-setup-engineer/references/notion-rest-read.md`
Expected: no hits (a `parameters` word inside prose about "parameter values" is fine only if lower-case and not the DB).

```bash
git add .claude/skills/acr-setup-engineer/references/notion-rest-read.md
git commit -m "docs(skill): notion-rest-read - Setups reads and offline mode only

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: `onboard-car.md` — write the `Parameters` page; refresh; migration

**Files:**
- Modify: `references/onboard-car.md`
- Delete: `references/refresh-catalog-snapshot.md`

- [ ] **Step 1: Intro and triggers**

In the opening bullets, replace `- **The user's min/max Car Setup screenshots** make it a **screenshot car**. Its catalog is written into the Notion `Parameters` DB, one row per parameter, as it always was.` with:

```markdown
- **The user's min/max Car Setup screenshots** make it a **screenshot car**. Its catalog is
  written as a template-format YAML file onto the car's **`Parameters` page** in Notion
  (`notion-structure.md` → *`Parameters` page*) — no database rows.
```

In *Trigger phrases*, delete the sentences about snapshot phrases and `refresh-catalog-snapshot.md` (keep the pointer to `refresh-notion.md`). In step 0 of the refresh, replace `its catalog goes into the `Parameters` DB` with `its catalog is written to its `Parameters` page` and `come from your own `Parameters` rows` with `come from your own `Parameters` page`.

- [ ] **Step 2: Refresh path, steps 3 and 4**

Step 3: delete the `Catalog snapshot` toggle from the list of what the `Catalog` rebuild writes, and the `(built from the template with … --snapshot)` parenthesis.

Replace the whole of step 4 (`4. **Write no `Parameters` rows.** …` through the end of the screenshot-car bullets, i.e. up to `5. **Leave the content of `Guidelines` and `Log` completely alone.**`) with:

```markdown
4. **The catalog.**
   - **Template car** → nothing to write: the file is in the skill. If the car's `Catalog` page
     had **no `Catalog source:` line** (an older version onboarded it), say once:
     *"This car still has rows in the old `Parameters` table from an older version of the skill.
     They aren't read any more. Delete that table whenever you like."*
   - **Screenshot car with no `Parameters` page yet** → run *Migration — catalog rows to the
     `Parameters` page* (below) first, then continue with this step as a screenshot car.
   - **Screenshot car** → decide by **game version**: the version on its source line (what the
     user gave when they captured it, `unknown`, or — for a forked car — the `forked_from`
     template version) against the `version:` of a `car-templates/` file that matches the car.
     Compare as version numbers (`0.10` is newer than `0.9`).
     - **A template matches and its version is the same or newer** → **switch to the template,
       no question.** Run step 3 as a template car (its source line becomes `bundled template`),
       insert the *Not in use* line as the **second block** of the `Parameters` page, right under
       its maintenance line (exact wording: `notion-structure.md` → *`Parameters` page*, item 2)
       — leave the `yaml` block as it is — and say in one line: *"The {Car} now uses the bundled
       template (game version {template version}) instead of your own list (game version
       {capture version}). Your list stays on its `Parameters` page, not in use. To go back, say
       'onboard the {Car} from my screenshots'."*
     - **The capture version is `unknown`** → ask **once**, and recommend yes: *"The skill has a
       bundled template for the {Car} (game version {template version}). Switch to it? If you're
       not sure, say yes — the template is kept up to date with the game, and your own list stays
       on its `Parameters` page either way."* Yes → as above. No → as the next bullet.
     - **The capture is newer than the template, or no template matches** → keep the page
       untouched. When a template exists, say in one line that it is behind the user's game
       version and offer *"export the {Car} as a template"* (`export-car-template.md`).
```

- [ ] **Step 3: Migration section**

After the existing `### Migration — old one-page car → four-page structure` section, add:

```markdown
### Migration — catalog rows to the `Parameters` page

A screenshot car onboarded before every catalog became a file has **no `Parameters` page**: its
rows are in the legacy `Parameters` database, and its `Catalog` page may hold a `Catalog snapshot`
toggle (an older read fallback). This runs **once per car**, inside a refresh, or on the spot by
whichever workflow first tries to load that car's catalog (the one write a read workflow may make).

1. **Get the rows, first source that works:**
   1. **The `Catalog snapshot` toggle** on the car's `Catalog` page (you hold that page). Its
      `yaml` block has `rows:` in the REST *Output* shape — save it with Python, then convert:
      ```python
      import json, pathlib, re
      text = """<the block, verbatim>"""
      # minimal parse of the old snapshot: one `- Adjustment:` entry per row, `key: value` lines
      rows, cur = [], None
      for line in text.splitlines():
          m = re.match(r'\s*(- )?([A-Za-z ]+): (.*)$', line)
          if not m: continue
          if m.group(1): 
              if cur: rows.append(cur)
              cur = {}
          key, val = m.group(2).strip(), m.group(3).strip()
          if len(val) >= 2 and val[0] == val[-1] and val[0] in '"\'': val = val[1:-1]
          elif re.fullmatch(r'-?\d+(\.\d+)?', val): val = float(val) if '.' in val else int(val)
          if key in ('Adjustment','Section','Surface','Min','Max','Unit','Discrete steps','Order'):
              cur[key] = val
      if cur: rows.append(cur)
      pathlib.Path('rows.json').write_text(json.dumps({'header': HEADER, 'rows': rows}), encoding='utf-8')
      ```
      where `HEADER` is a dict of the identity facts from the `Catalog` page plus
      `car`, `version` (the game version on the source line, or `unknown`) and `source: "screenshots"`.
   2. **The legacy `Parameters` DB over REST**, when this chat has network and a token
      (`notion-rest-read.md`): query that data source with the car's name, and build the same
      `rows.json` from the result.
   3. **Neither** → create the `Parameters` page with its maintenance line and a `yaml` block
      holding only the header and `parameters: []`, and tell the user: *"The {Car} was onboarded
      by an older version and I can't recover its parameter list here. Say 'onboard the {Car}
      from my screenshots' to capture it again."* Its catalog can't be loaded until then.
2. **Write the page**: `python scripts/load_catalog.py --to-template rows.json`, and create the
   `Parameters` page under `{Car}` with the maintenance line and the output as its `yaml` block
   (`notion-structure.md` → *`Parameters` page*).
3. **Rebuild the `Catalog` page** without the snapshot toggle (refresh step 3 for a screenshot
   car: identity facts, source line, nothing else).
4. **Say what happened**: *"Moved the {Car}'s parameter list to its own `Parameters` page."* Once
   per run, also: *"Your old `Parameters` table isn't read any more by any car. You can delete it."*
```

Also in the old-layout migration section step 5, replace `from whichever source the car's catalog comes from — the bundled template, or its `Parameters` rows for a screenshot car` with `— the bundled template, or the car's `Parameters` page (run *Migration — catalog rows to the `Parameters` page* first when it has none)`, and delete the sentence starting `If the car's rows can't be read (no egress, no token)`.

- [ ] **Step 4: Procedure step 6 and 7 (screenshot path)**

Step 6: delete `→ **the `Parameters` DB on the screenshot path only**, and only if it doesn't exist yet (a template car never needs it)`. Change "four child pages" to "child pages (`notion-structure.md` → *Car page*)".

Step 7, first bullet: replace the whole `**Screenshot path only — upsert the `Parameters` rows.** …` bullet (through `no re-screenshotting needed.`) with:

```markdown
   - **Screenshot path only — write the `Parameters` page.** A template car writes **nothing
     here**: its catalog is the file on disk. On the screenshot path:
     1. Build `rows.json` from the rows you assembled in step 3 (and confirmed in step 4): every
        row with `Adjustment`, `Section`, `Min`, `Max`, `Unit`, `Discrete steps`, `Order`; the
        tarmac baseline rows carry no `Surface`. For `—` named-selection params put the observed
        option names in `Discrete steps`; for numeric params leave it `""`. **ACR exception:**
        `Tyre Type` gets the standard ACR tyre list and `Brake pads/shoe` (front & rear)
        `SOFT, MEDIUM, HARD`. Two-stage gear values keep their asterisks exactly (`SKILL.md` →
        *A gear value with a `*` in it is an ordinary value*). The `header` object: `car`,
        `drivetrain` and the eight other identity facts from step 5, `version` (step 2's game
        version or `unknown`), `source: "screenshots"`.
     2. Run `python scripts/load_catalog.py --to-template rows.json` and paste its output as the
        page's ```` ```yaml ```` block, under the maintenance line (`notion-structure.md` →
        *`Parameters` page*). Create the page if missing; on a re-onboard, replace the block.
     3. Keep `rows.json` and the output: step 8, step 9 and the `SHOW` calls below use them.
```

In the `Setups` value-columns bullet, replace the `SHOW` instructions (from `get the main table's `SHOW` list from **one** call` to `hides its value columns.`) with:

```markdown
     get the main table's `SHOW` list from **one** call with one `--from-template` per onboarded
     car — the bundled file for a template car, the screenshot car's saved file (`catalog-read.md`
     → *Save the file*; for the car being onboarded, save the `--to-template` output as
     `parameters/<slug>.yaml`) — per `notion-structure.md` → *Applying the order*. The main table
     spans every car, so leaving one out hides its value columns.
```

In the `Catalog` page sub-list, delete item 5 (the `Catalog snapshot` toggle) entirely. In the `Setups` child-page item, replace the `(get it from the bundled script … for a screenshot car).` parenthesis with `(one `--from-template` with this car's file — `notion-structure.md` → *Applying the order*)`.

Add a fifth child page item after `Log`:

```markdown
     4. **`Parameters`** — screenshot path only: written in the first bullet of this step. A
        template car has no such page.
     5. **`Setups`** — …
```
(renumber the existing `Setups` item to 5).

- [ ] **Step 5: Steps 8, 9, 10**

Step 8 (gravel pass): wherever it writes `Gravel`-tagged **rows** to the DB, replace with: add the gravel rows (with `Surface: "Gravel"`, mirroring the baseline `Order`) to `rows.json`, re-run `--to-template`, and **replace the page's block**. Step 9 (`Discrete steps` in chat): same — update `rows.json`, re-run, replace the block; delete the `Fill the cells in Notion later` option and replace the two options with one line: *"Give them here whenever you have them — say 'the {Car}'s {parameter} steps are …' and I'll update the list."* (that is `edit-catalog.md`). Step 10 (offer the export): unchanged in substance; where it says the rows are in hand, say the file is in hand.

Delete every remaining mention of `snapshot`, `refresh-catalog-snapshot.md`, the paste route and `params_data_source_id` in this file. Also the *When the template may be stale* section: keep; it already ends in "re-onboard from my screenshots".

- [ ] **Step 6: Delete the snapshot workflow and check**

```bash
git rm .claude/skills/acr-setup-engineer/references/refresh-catalog-snapshot.md
grep -n -i "snapshot\|paste\|params_data_source\|Parameters\` DB\|Parameters\` rows" .claude/skills/acr-setup-engineer/references/onboard-car.md
```
Expected: hits only inside *Migration — catalog rows to the `Parameters` page* and the legacy-table line in refresh step 4.

Run: `python -m unittest discover -s tests 2>&1 | tail -3` — guard test still failing on other files only.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/onboard-car.md
git commit -m "docs(skill): onboarding writes the Parameters page; refresh migrates legacy rows

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `edit-catalog.md`, `SKILL.md`, `How to use` line

**Files:**
- Create: `references/edit-catalog.md`
- Modify: `SKILL.md` (routing table, tools list, *Reading rows* rule, ownership bullets)
- Modify: `references/how-to-use-template.md` (`Covers:` line + one bullet)

- [ ] **Step 1: Create `references/edit-catalog.md`**

```markdown
# Workflow: change a car's parameter list (in chat)

Change a car's legal values — a range, its steps, a unit, add or remove a parameter, a
gravel-only range — by saying it in chat. The skill validates the change and rewrites the car's
**`Parameters` page** (`notion-structure.md` → *`Parameters` page*). This is the **only** way a
catalog changes; nobody edits YAML or rows by hand.

Read `catalog-read.md` and `notion-structure.md` → *`Parameters` page* before starting.

## Trigger phrases
"the {car}'s {parameter} goes from A to B", "{parameter} on the {car} now goes to X", "the last
step is Y", "set the steps for {parameter} to …", "add {parameter} to the {car}", "{parameter}
isn't adjustable on the {car}, remove it", "on gravel the {parameter} goes A to B" — any request
that changes what values a car's parameter may take. (A request to change a **setup's** value is
`tweak-setup.md`, not this.)

## Procedure

1. **Load the catalog** — `catalog-read.md` → *Load a car's catalog*. Keep the loader's JSON
   output; it is the list you'll edit. Note the car's kind from its `Catalog source:` line.

2. **Name the parameter exactly.** Match what the user said against the `Adjustment` names in
   the list. If it matches **more than one** (e.g. "ARB" → `Anti-roll Bar Front`, `Anti-roll Bar
   Rear`), ask: *"Front, rear, or both?"* If it matches **none** and the user isn't adding a new
   one, ask which of the closest two or three they mean. Never guess.

3. **Apply the change in memory** to the matching row(s) — the baseline row, or the row for the
   surface the user named (create that surface row from the baseline if it doesn't exist, when
   the user says "on gravel"):
   - a new min or max → set `Min` / `Max`;
   - "the last step is Y" → replace the last entry of `Discrete steps`; "steps are …" → replace
     the whole list; "add step Y" → insert it in numeric order;
   - a unit → `Unit`;
   - **add a parameter** → a new row with `Section`, `Adjustment`, `Min`, `Max`, `Unit`,
     `Discrete steps`, and an `Order` inside its section block (`notion-structure.md` →
     *Canonical ACR default order*: the section's thousands, then the next free tens slot);
   - **remove a parameter** → drop its rows (baseline and surface).

4. **Validate** — every check is a one-liner; do all that apply:
   - numeric `Min` ≤ `Max`;
   - every step is inside `Min..Max` when both are numbers, and the steps are in ascending order;
   - `Discrete steps` values keep their exact spelling (`*` in gear values, `—` for none);
   - no two rows share `Adjustment` + `Surface`.
   A failed check → say which and ask for the corrected value. Don't write.

5. **Show before → after** for each changed row (`Adjustment`, surface if any, `Min`, `Max`,
   `Unit`, `Discrete steps`) and ask: *"Write this to the {Car}'s parameter list?"* Only on yes.

6. **Write the page.**
   - Build `rows.json`: `{"header": …, "rows": <the edited list>}`. The header is the loaded
     file's header keys (`car`, `drivetrain`, the identity facts, `version`, `source`), plus:
     - **Template car (first edit — this forks it):** `source: "screenshots"`,
       `forked_from: "bundled template v{tv}"` where `{tv}` is the bundled file's `version:`.
     - **Screenshot car:** header unchanged.
   - Run `python scripts/load_catalog.py --to-template rows.json`.
   - **Template car:** create the `Parameters` page under `{Car}` with the **forked** maintenance
     line (`notion-structure.md` → *Car page* table; today's date from the `Date` one-liner) and
     the output as its `yaml` block. Then rewrite the `Catalog` page (it is disposable — one
     replacement, `onboard-car.md` refresh step 3) with the source line
     `**Catalog source:** your screenshots — started from bundled template v{tv} on {YYYY-MM-DD}`.
   - **Screenshot car:** replace the page's `yaml` block with the output. Leave the maintenance
     line as it is.

7. **A new `Adjustment`** → add its `Setups` value column (`onboard-car.md` step 7's
   *value-columns check*: Number for numeric, Select for `—`), then re-assert `SHOW` on the
   car's view and the shared views with this car's new file
   (`notion-structure.md` → *Applying the order*). A removed parameter keeps its column (columns
   are never removed). No new column → nothing to reorder.

8. **Report, one line.** Screenshot car: *"Updated the {Car}'s parameter list: {what changed}."*
   Forked template car: *"Done. The {Car} now uses its own parameter list (copied from the
   bundled template, with this change). When a newer bundled template ships, a refresh will
   offer to switch back."*

## Rules
- **Validate, show, confirm, then write.** Never write an unconfirmed change.
- **The page's block is replaced whole**, from the script's output — never patched by hand.
- **Forking a bundled car asks no question**; the one-line report says what happened.
- **Never touch `Setups` rows** — a range change doesn't rewrite existing setups.
- Stay within `ACR Setup Engineer` scope.
```

- [ ] **Step 2: `SKILL.md`**

- Routing table: add after the *Refresh an already-onboarded car* row:
  ```markdown
  | **Change a car's parameter list** — *"the {car}'s {parameter} goes from A to B"*, *"set the steps for {parameter} to …"*, *"add / remove {parameter} on the {car}"*: validates the change and rewrites the car's `Parameters` page; a bundled car is copied into its own page on the first edit, without asking | `references/edit-catalog.md` |
  ```
  In the *Refresh* row, delete the snapshot phrases and `there is no separate snapshot command`; say the switch to a template adds a *Not in use* line to the car's `Parameters` page. In the *Onboard* row, nothing.
- Tools list: `load_catalog.py` bullet — remove `--snapshot`, add `--to-template rows.json` (the body of a car's `Parameters` page — onboarding, editing, migration; never hand-format YAML). `query_notion_parameters.py` bullet — `Setups` slices over REST, and `--show-order --from-template <file> …` for every view; no `Parameters` read, no `--all`.
- *Reading rows* rule: replace it with:
  ```markdown
  - **Reading a catalog.** Every car's catalog is a template file — bundled, or the `yaml` block
    on the car's `Parameters` page — loaded by `references/catalog-read.md`: no token, no network,
    on every plan. **Reading `Setups` rows** (learn pool, stored default) is the REST query in
    `references/notion-rest-read.md`; check the network once per chat first
    (`scripts/check_egress.py`) and on `egress: none` run no REST query for the rest of the chat
    (that doc's *Offline mode*). Never substitute connector row-listing, never guess.
  ```
- *Read efficiently* bullet: `**For a template car that batch carries no `Parameters` query at all**` → `A screenshot car's `Parameters` page is fetched in that same batch (`catalog-read.md`)`; remove `(and the `Parameters` one when a screenshot car is involved)`.
- Ownership bullets (*A car's pages are split by ownership*): add
  ```markdown
  - **`Parameters` is the skill's, and the only copy** (screenshot cars only). Written by
    onboarding and `edit-catalog.md`; a refresh never regenerates it. Users change it by saying
    the change in chat.
  ```
  and change "four children" to "five children (four for a template car)".
- *Assert column order* rule: replace the three-form text with `one `--from-template` per car the view spans — `references/notion-structure.md` → *Applying the order* — no token`.
- Delete every remaining `snapshot` / `--all` / `params_ds` mention in `SKILL.md`.

- [ ] **Step 3: `How to use` template**

Add `edit-catalog.md` to the `Covers:` line, and this bullet after *Use your own ranges for a car*:

```markdown
- **Change a car's parameter list** — "the Lancia Stratos' front anti-roll bar goes 1 to 6 in
  steps of 1". It checks the change and updates the car's list.
```

- [ ] **Step 4: Tests and commit**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: `test_notion_docs_pages` OK; the guard test still fails on the workflows not yet updated.

```bash
git add .claude/skills/acr-setup-engineer/references/edit-catalog.md .claude/skills/acr-setup-engineer/SKILL.md .claude/skills/acr-setup-engineer/references/how-to-use-template.md
git commit -m "feat(skill): edit-catalog workflow; SKILL.md routes and rules for file catalogs

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Every other workflow points at `catalog-read.md`

**Files:**
- Modify: `references/build-setup.md`, `tweak-setup.md`, `capture-setup.md`, `share-setup.md`, `review-setup.md`, `ask-setups.md`, `import-savegame.md`, `export-car-template.md`, `refresh-notion.md`, `free-plan-template.md`

- [ ] **Step 1: The "load the catalog" paragraph, in each of build / tweak / capture / share / review / ask**

Find each file's sentence pair of the form `a **template car** → `python scripts/load_catalog.py …` (no token, no network); a **screenshot car** → its `Parameters` rows via [notion-rest-read.md](notion-rest-read.md) …` and replace it with:

```markdown
**Load the car's catalog per [catalog-read.md](catalog-read.md)** — a bundled file for a template
car, the car's `Parameters` page (fetched in this same batch) for a screenshot car; one
`load_catalog.py` call either way, `--surface {Surface}` when the workflow resolves a surface.
```

Keep whatever follows about the `Drivetrain` and the source line. In `build-setup.md`, also delete the parenthesis about `--snapshot` in the auto-onboard bullet (line ~99) and line ~480's `the `Parameters` row — a template car has no row to backfill` sentence (a `Discrete steps` backfill is now an `edit-catalog.md` offer: *"Say 'the {Car}'s {parameter} steps are …' and I'll add them."*). In each batched-read note (`> Load steps … as one batched read`), add `and the car's `Parameters` page for a screenshot car`.

- [ ] **Step 2: `import-savegame.md`**

Replace its catalog-loading sentence as in step 1. In the structure-creation line (~133) delete `the `Parameters`/`Setups` DBs` → `the `Setups` DB`. In 5.2/5.3 (template auto-onboard), delete the snapshot write. In 5.6, the `SHOW` call is one `--from-template` per car (point at *Applying the order*). Delete `**write no `Parameters` rows**` wording → `writes no catalog to Notion`.

- [ ] **Step 3: `export-car-template.md`**

Replace *0. Is there anything to export?* through the end of *1. Read from Notion* with:

```markdown
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
you already hold the `--to-template` output from the write — use it, don't re-fetch.
```

Replace *3. Sort parameters* and *4. Format as YAML* with:

```markdown
### 3. Normalise the header
Rewrite the file's header for sharing, with Python (never by hand):
- `source: "community"`;
- delete `written_at`, `skill_version`, `parameter_count`, `forked_from`;
- keep everything else (`car`, `game`, `save_ids` if present, `drivetrain`, the identity facts,
  `version`).
The `parameters:` list is already in `Order` (`--to-template` sorted it; baseline before surface).
```

Delete the sections *2. Completeness check*'s "fill them in Notion first" option → the offer is `edit-catalog.md`: *"Say 'the {Car}'s {parameter} steps are …' and I'll add them, then export again."* Keep steps 5–7 (verify, present, share). In step 5, verify by running `python scripts/load_catalog.py <exported file>` and comparing its row count and adjustment names with the loaded catalog.

- [ ] **Step 4: `refresh-notion.md` and `free-plan-template.md`**

`refresh-notion.md`: in step 3, replace the paste bullet with: `- **Don't wait on a car that can't be migrated.** Where the catalog-rows migration finds neither a snapshot nor REST rows (`onboard-car.md` → *Migration — catalog rows to the `Parameters` page*, source 3), create the empty page as it says, note the car, and move on. List those cars in the report with *"onboard the {Car} from my screenshots"*.` Delete "unknown-version question" text only if it references snapshots (it doesn't; keep it).

`free-plan-template.md`: delete the *Cars you onboarded from screenshots* bullet under *Things to know*. In *What works*, change `**Every bundled car, fully.** Their parameter lists are inside the skill.` to `**Every car, fully** — bundled ones and the ones you onboarded from screenshots. Their parameter lists never need the connection.`

- [ ] **Step 5: Guard test green**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK, including `tests.test_references`. If `test_banned_phrases` lists hits, fix each line it names (reword or delete) — do not widen the allow-list.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/acr-setup-engineer/references/build-setup.md .claude/skills/acr-setup-engineer/references/tweak-setup.md .claude/skills/acr-setup-engineer/references/capture-setup.md .claude/skills/acr-setup-engineer/references/share-setup.md .claude/skills/acr-setup-engineer/references/review-setup.md .claude/skills/acr-setup-engineer/references/ask-setups.md .claude/skills/acr-setup-engineer/references/import-savegame.md .claude/skills/acr-setup-engineer/references/export-car-template.md .claude/skills/acr-setup-engineer/references/refresh-notion.md .claude/skills/acr-setup-engineer/references/free-plan-template.md
git commit -m "docs(skill): every workflow loads catalogs through catalog-read.md; export hands over the file

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: README and maintainer notes

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: README**

- *Onboard a car* section: replace `A car set up this way keeps its parameter list in the **`Parameters`** table in your Notion, where you can edit it. That table is created …` with: `A car set up this way keeps its parameter list on a **`Parameters`** page under the car in your Notion. To change a value in it, say so in chat — *"the {car}'s front anti-roll bar goes 1 to 6 in steps of 1"* — and the skill checks it and updates the page.`
- The paragraph starting `**If you onboarded a bundled car with an older version of the skill**` → `**If you onboarded a car with an older version of the skill**, its parameter list may still be rows in a `Parameters` table under the root. The first refresh of that car moves the list onto its own `Parameters` page and tells you the table can be deleted. Nothing is deleted for you.` Keep the three switch bullets that follow.
- *What it creates in Notion*: delete the `├── Parameters (DB)` lines; add under `{Car}`, after `Log`: `    ├── Parameters          only for cars onboarded from screenshots (or edited away from a bundled template): the car's complete parameter list. The skill's; change it by saying so in chat`. In *Why four pages?* → *Why five pages?* and add one sentence: `A car you onboarded from screenshots gets a fifth, `Parameters`, holding its parameter list as a file; the skill writes it and you change it through chat, so there's never a table to keep in sync.`
- *Pinning a setting to exact values*: replace the paragraph starting `This is about cars you onboarded **from screenshots**.` with: `For a car you onboarded from screenshots, onboarding pre-seeds `Discrete steps` with what the screenshots show (usually the two endpoints). Add the in-between options by saying them: *"the {car}'s spring stiffness front steps are 35000, 42500, 50000"*. Tyre compounds and brake pads ship fully pre-filled. A car from a bundled template needs none of this.` Change the brake-parameters note's `add them manually in the car's `Parameters` table` to `say them in chat and they're added to the car's list`.
- *How it reads and writes Notion*: replace the *Reading rows* bullet's last sentence with `It is used for your **setup history** only.`; delete the `**When the sandbox has no network** …` bullet; change the template bullet to `**A car's parameter list never needs the token.** A bundled car's list is inside the skill; a screenshot car's is on its `Parameters` page, which the connector can read in full — on every plan.`
- *What Claude's Free plan can't do*: delete the *Reads use the snapshot* bullet and the *Screenshot-onboarded cars from an older skill version have no snapshot yet* bullet; in the intro delete `Every catalog write leaves an auto-maintained **catalog snapshot** … reads fall back to it.` and the sentence about screenshot cars → `What follows is about your setup history, which affects every car.`
- *Troubleshooting*: delete the *"No catalog snapshot" on Free* item.
- *Quick start by task*: add after *Export a car template*: 
  ```markdown
  ### Change a car's parameter list

  *"The Lancia Stratos' front anti-roll bar goes 1 to 6 in steps of 1."* It checks the change and
  updates the car's list. For a bundled car this makes a copy of the list under the car, with your
  change — the skill says so in one line.
  ```
- *The workflows* table: add `| Change a car's parameter list | [`edit-catalog.md`](…/edit-catalog.md) |`.

Run: `grep -n -i "snapshot\|Parameters\` table\|Parameters\` rows\|Parameters (DB)" README.md` — expected: only the legacy-table paragraph.

- [ ] **Step 2: `CLAUDE.md`**

In *Where things live*: add `edit-catalog.md` to the workflow list and `catalog-read.md` to the shared references; delete the `refresh-catalog-snapshot.md is internal` sentence; in the `notion-rest-read.md` bullet, replace the text after "the connector can't list database rows" with `so `Setups` slices are queried over REST with a read-only token. **Catalogs are never read that way**: every car's catalog is a template file — bundled, or the `yaml` block on the car's `Parameters` page — read by `scripts/load_catalog.py` via `references/catalog-read.md`.` In the `scripts/` bullet: `load_catalog.py` (a template file as a catalog — rows in the REST read's shape, surface resolution, `--check`, `--to-template`) and `query_notion_parameters.py` (`Setups` reads and `--show-order --from-template`).

- [ ] **Step 3: Full suite and commit**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: OK.

```bash
git add README.md CLAUDE.md
git commit -m "docs: README and maintainer notes for file-based catalogs

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: Final consistency sweep

**Files:** none new.

- [ ] **Step 1: Cross-file greps**

```bash
grep -rn -i "snapshot" .claude/skills/acr-setup-engineer README.md CLAUDE.md
grep -rn "Parameters\` DB\|Parameters\` rows\|Parameters DB" .claude/skills/acr-setup-engineer README.md
grep -rn "\-\-all\|params_data_source\|refresh-catalog-snapshot\|--snapshot" .claude/skills/acr-setup-engineer README.md CLAUDE.md
grep -rn "four child pages\|four children\|four pages" .claude/skills/acr-setup-engineer README.md
```
Expected: only the legacy note, the migration section, the README legacy paragraph, and "four for a template car" phrasings. Fix anything else.

- [ ] **Step 2: Run the whole suite and the zip check**

```bash
python -m unittest discover -s tests 2>&1 | tail -3
make zip && make check-zip
```
Expected: OK; the zip lists `references/catalog-read.md`, `references/edit-catalog.md`, no `refresh-catalog-snapshot.md`. (Rebuild the release zip from the tag afterwards if `dist/` is tracked by name: `git archive --format=zip --prefix=acr-setup-engineer/ v0.19.1:.claude/skills/acr-setup-engineer -o dist/acr-setup-engineer-skill-v0.19.1.zip`.)

- [ ] **Step 3: Commit any fixes**

```bash
git add -A .claude/skills/acr-setup-engineer README.md CLAUDE.md
git commit -m "docs: consistency sweep for file-based catalogs

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```
(Skip if nothing changed.)
