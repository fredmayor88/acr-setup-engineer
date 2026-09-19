#!/usr/bin/env python3
"""Query a Notion data source and return all matching rows as JSON.

Used by the acr-setup-engineer skill to read a car's Parameters catalog or a filtered
slice of Setups — the Notion MCP connector cannot list database rows reliably.

Usage:
  # All Parameters rows for one car:
  python query_notion_parameters.py <data_source_id> <token> <car_name>

  # Setups the user marked "Learn from this" (pass the Setups data_source_id):
  python query_notion_parameters.py <data_source_id> <token> <car_name> --learn-only

  # The car's captured game-default (stock) baseline rows, for the build anchor:
  python query_notion_parameters.py <data_source_id> <token> <car_name> --source default

  # The ordered SHOW property list for a view (paste into a view's SHOW directive):
  python query_notion_parameters.py <params_data_source_id> <token> <car_name> --show-order
  python query_notion_parameters.py <params_data_source_id> <token> --all --show-order

  # Same SHOW list, computed locally from bundled template YAML(s) — no token/network.
  # A template car's catalog IS its bundled file (it has no Parameters rows), so this is the
  # form to use for it:
  python query_notion_parameters.py --show-order --from-template car-templates/<car>.yaml
  python query_notion_parameters.py --show-order --from-template a.yaml --from-template b.yaml

  # A view spanning BOTH kinds of car (the main Setups table, a {Location}/{Stage} view):
  # one call, one ordered list — template rows and Notion rows merged by their `Order`.
  python query_notion_parameters.py <ds_id> <token> --all --show-order --from-template a.yaml

Arguments:
  data_source_id   UUID from notion-fetch (strip the "collection://" prefix).
  token            Notion read-only integration token (secret_... / ntn_...).
  car_name         Exact value of the "Car" select property to filter on.
                   Optional (omit) when --all is given.
  (All three are optional when --from-template is given: omit them for a template-only
   list, or pass them to merge Notion's rows into the same ordered list.)

Options:
  --learn-only   Also filter "Learn from this" checkbox = true (Setups learn pool).
                 Additionally EXCLUDES Source=default rows: captured stock baselines
                 hold the game's values, not the user's taste, so they are consumed
                 as the build anchor and never as a learning example.
  --source <v>   Also filter the "Source" select = <v> (Setups). Use
                 `--source default` to fetch a car's captured game-default (stock)
                 baseline rows for the build anchor.
  --show-order   Print the ordered SHOW property list for a Setups view (see below)
                 instead of the rows: Name, then value columns by their Parameters
                 `Order`, then the fixed meta columns. Run against the Parameters
                 data source. Output is ready to paste after `SHOW ` in a view's
                 configure DSL.
  --from-template <path>
                 Add one or more bundled template YAML files to the --show-order
                 list. Repeatable: pass one file for a per-car view, or one per
                 template car for the main Setups table. Requires --show-order.
                 On its own it needs no data_source_id, token or network. Combined
                 with <data_source_id> <token> (plus <car_name> or --all) it queries
                 Notion as well and orders BOTH sources in one list, by each
                 parameter's `Order` — which is what a view holding template cars and
                 screenshot cars together needs. Never merge two SHOW lists by hand:
                 they carry no `Order` to interleave by.
                 In that mixed form, Notion rows whose "Car" matches a passed
                 template's `car:` are DROPPED before ordering — exact equality
                 after the skill's name normalisation (lowercase, punctuation to
                 spaces, whitespace collapsed; references/onboard-car.md step 1 ->
                 *Matching a car name*): a template car's catalog is its file, and rows an older
                 skill version left in Parameters for it are never read. The template
                 therefore always decides that car's columns and their `Order`.
  --all          Query every row (no "Car" filter) — the union of value columns, for
                 the main Setups table and the {Location}/{Stage} views. With
                 --show-order, omit <car_name>. For a per-car view, pass <car_name>
                 (without --all) so SHOW lists only that car's value columns.
  --pretty       Human-readable summary instead of JSON.

Output: JSON array — one object per row, property names as keys, values extracted
        by type (title/rich_text -> string, select -> string or null,
        checkbox -> bool, number -> number or null). Properties with no value
        (null select, missing) are omitted; blank rich_text returns "".

Exit codes: 0 success; 1 an HTTP/network error, or a template file that can't be
            read; 2 a usage error (missing/incomplete arguments). stdlib only.
            Output is always UTF-8, whatever the console locale is — a column name
            can carry `°` or an accented letter.
"""
import json
import re
import sys
import urllib.error
import urllib.request

NOTION_VERSION = '2025-09-03'
BASE_URL = 'https://api.notion.com/v1/data_sources'

# Fixed trailing meta-column order for a Setups view's SHOW directive, after the
# value columns. Keep in sync with notion-structure.md ("Setups column order").
META_ORDER = [
    'Car', 'Location', 'Stage', 'Surface', 'Conditions', 'Date', 'Source', 'Mode',
    'Rating', 'Learn from this', 'Game version', 'Notes', 'Model', 'Skill version',
]

# The "Source" value marking a captured game-default (stock) baseline row.
DEFAULT_SOURCE = 'default'


def use_utf8_output():
    """Print UTF-8 whatever the console's locale is.

    A SHOW list or a row can carry a non-ASCII column name (`°`, an accented letter). With
    stdout piped — how the skill always runs this script — Python on Windows would otherwise
    encode it with the ANSI code page, and whatever reads it back as UTF-8 gets mojibake.
    Guarded because stdout may be a plain object with no `reconfigure` (a test capturing
    output, an embedded runner).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            try:
                reconfigure(encoding='utf-8')
            except (ValueError, OSError):        # already detached / not reconfigurable
                pass


def normalise_car_name(name):
    """The skill's one car-name normalisation (references/onboard-car.md step 1 ->
    *Matching a car name*): lowercase, every punctuation character to a space, runs of
    whitespace collapsed to one. `Lancia-Stratos HF` and `lancia stratos hf` normalise alike.
    Letters keep their accents (`Citroën` stays one word), so only punctuation is removed.
    """
    return ' '.join(re.sub(r'[\W_]+', ' ', str(name).lower()).split())


def extract_value(prop):
    """Return a scalar from a Notion property object, or None to omit it."""
    ptype = prop.get('type')
    if ptype == 'title':
        return ''.join(t.get('plain_text', '') for t in prop.get('title', []))
    if ptype in ('rich_text', 'text'):
        return ''.join(t.get('plain_text', '') for t in prop.get('rich_text', []))
    if ptype == 'select':
        sel = prop.get('select')
        return sel.get('name') if sel else None
    if ptype == 'checkbox':
        return prop.get('checkbox', False)
    if ptype == 'number':
        return prop.get('number')
    if ptype == 'multi_select':
        return ', '.join(opt.get('name', '') for opt in prop.get('multi_select', []))
    return None


def build_filter(car_name, learn_only, source=None):
    """Build the Notion query filter. car_name=None means no Car filter (--all).

    `source` filters Setups rows on the "Source" select (e.g. "default" for the
    captured stock baselines). `learn_only` additionally excludes Source=default
    rows: those hold the game's own values, not the user's taste, so they are
    consumed as the build anchor and never as a learning example
    (notion-structure.md -> "Default (stock) baseline rows").
    """
    clauses = []
    if car_name is not None:
        clauses.append({'property': 'Car', 'select': {'equals': car_name}})
    if source is not None:
        clauses.append({'property': 'Source', 'select': {'equals': source}})
    if learn_only:
        clauses.append({'property': 'Learn from this', 'checkbox': {'equals': True}})
        clauses.append({'property': 'Source', 'select': {'does_not_equal': DEFAULT_SOURCE}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {'and': clauses}


def build_show_order(rows):
    """Return the ordered SHOW property list for a Setups view, as a quoted,
    comma-separated string ready to paste after `SHOW `:

        "Name", <value columns by Order>, <fixed meta columns>

    `rows` are Parameters rows (each a dict with `Adjustment` and optional `Order`).
    Baseline + surface rows of one parameter share a column and an Order — deduped
    here. Parameters with no `Order` sort last, by name.
    """
    order_by_adj = {}
    for row in rows:
        adj = row.get('Adjustment')
        if not adj:
            continue
        order = row.get('Order')
        if adj not in order_by_adj:
            order_by_adj[adj] = order
        elif order is not None and (order_by_adj[adj] is None or order < order_by_adj[adj]):
            order_by_adj[adj] = order

    def sort_key(adj):
        order = order_by_adj[adj]
        # (0, order) sorts numbered params first by Order; (1, ...) puts un-numbered last by name
        return (1, 0.0, adj.lower()) if order is None else (0, order, adj.lower())

    value_cols = sorted(order_by_adj, key=sort_key)
    names = ['Name'] + value_cols + META_ORDER
    return ', '.join(f'"{name}"' for name in names)


def read_template_rows(path):
    """Extract [{'Adjustment', 'Order'}] from a bundled template YAML's `parameters:` list.

    Deliberately minimal (stdlib only — no PyYAML, matching the skill's convention): the
    template files are flat and export-enforced (references/export-car-template.md). Reads only
    what build_show_order needs — each parameter's `adjustment` and optional `order` — so the
    local SHOW order is identical to the Notion --show-order path without a token or network.
    Header fields (incl. a block-list `save_ids:`) are ignored: collection starts at
    `parameters:` and items without an `adjustment` are skipped.
    """
    rows, cur, in_params = [], None, False
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            stripped = line.strip()
            if not in_params:
                if stripped == 'parameters:':
                    in_params = True
                continue
            # a non-indented, non-list line ends the parameters block (next top-level key)
            if line[:1].strip() and not stripped.startswith('-'):
                break
            if stripped.startswith('- '):                 # new list item → new parameter row
                if cur and cur.get('Adjustment'):
                    rows.append(cur)
                cur = {}
                stripped = stripped[2:].strip()           # a key may sit on the `- ` line too
            if cur is None:
                continue
            m = re.match(r'([\w ]+?):\s*(.*)$', stripped)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip().strip('"\'')
            if key == 'adjustment':
                cur['Adjustment'] = val
            elif key == 'order':
                try:
                    cur['Order'] = int(val)
                except ValueError:
                    pass
    if cur and cur.get('Adjustment'):
        rows.append(cur)
    return rows


def read_template_car(path):
    """Return a template's `car:` header value (its exact Notion `Car` name), or None.

    Only the top-level, column-0 key counts, so nothing nested (e.g. inside `engine_curve:`)
    can be mistaken for it. Reading stops at `parameters:`.
    """
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if line.strip() == 'parameters:':
                break
            if not line[:1].strip():                  # indented -> not a header key
                continue
            m = re.match(r'car:\s*(.+)$', line.strip())
            if m:
                return m.group(1).strip().strip('"\'')
    return None


def drop_template_cars(rows, template_cars):
    """Remove Notion rows belonging to a car whose catalog is a bundled template.

    A template car's catalog is its file; `Parameters` rows an older skill version wrote for it
    are never read (notion-structure.md -> "Where a car's catalog lives"). Left in, such a row
    could win the lowest-`Order` tie-break against the template, or add a column name the
    template no longer has. Matching is exact equality of the `Car` value and the template's
    `car:` after normalise_car_name() — the skill's one name-matching normalisation.
    """
    wanted = {normalise_car_name(c) for c in template_cars if c}
    if not wanted:
        return rows
    return [r for r in rows if normalise_car_name(r.get('Car', '')) not in wanted]


def query(data_source_id, token, car_name, learn_only=False, source=None):
    """Return all rows matching car_name as a list of property dicts."""
    url = f'{BASE_URL}/{data_source_id}/query'
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }
    filt = build_filter(car_name, learn_only, source)
    rows = []
    cursor = None

    while True:
        body = {'page_size': 100}
        if filt is not None:
            body['filter'] = filt
        if cursor:
            body['start_cursor'] = cursor

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            print(f'HTTP {exc.code}: {exc.read().decode()}', file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as exc:
            print(f'Network error: {exc.reason}', file=sys.stderr)
            sys.exit(1)

        for page in data.get('results', []):
            row = {}
            for name, prop in page.get('properties', {}).items():
                val = extract_value(prop)
                if val is not None:
                    row[name] = val
            rows.append(row)

        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')

    return rows


def main():
    use_utf8_output()
    args = sys.argv[1:]
    positional, flags, templates = [], set(), []
    source = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--from-template':
            if i + 1 >= len(args):
                print('--from-template requires a path', file=sys.stderr)
                sys.exit(2)
            templates.append(args[i + 1])
            i += 2
            continue
        if a == '--source':
            if i + 1 >= len(args):
                print('--source requires a value (e.g. default)', file=sys.stderr)
                sys.exit(2)
            source = args[i + 1]
            i += 2
            continue
        (flags.add(a) if a.startswith('--') else positional.append(a))
        i += 1
    learn_only = '--learn-only' in flags
    pretty = '--pretty' in flags
    show_order = '--show-order' in flags
    all_cars = '--all' in flags

    usage = ('usage: query_notion_parameters.py <data_source_id> <token> <car_name>'
             ' [--learn-only] [--source <value>] [--show-order] [--pretty]\n'
             '       query_notion_parameters.py <data_source_id> <token> --all --show-order\n'
             '       query_notion_parameters.py --show-order --from-template <template.yaml> ...\n'
             '       query_notion_parameters.py <data_source_id> <token> --all --show-order'
             ' --from-template <template.yaml> ...   (one ordered list from both sources)')

    # Rows from bundled template YAML(s) — no Notion, no token. They may stand alone, or be
    # merged with a Notion query below so one --show-order call covers a view that spans
    # template cars and screenshot cars.
    template_rows, template_cars = [], []
    if templates:
        if not show_order:
            print('--from-template requires --show-order', file=sys.stderr)
            sys.exit(2)
        for path in templates:
            try:
                template_rows.extend(read_template_rows(path))
                template_cars.append(read_template_car(path))
            except OSError as exc:
                print(f'cannot read template: {exc}', file=sys.stderr)
                sys.exit(1)

    # Query Notion whenever positional args were given — and always when no template was.
    notion_rows = []
    if positional or not templates:
        # Need data_source_id + token always; car_name too unless --all.
        if len(positional) < 2 or (len(positional) < 3 and not all_cars):
            print(usage, file=sys.stderr)
            sys.exit(2)
        data_source_id, token = positional[0], positional[1]
        car_name = None if all_cars else positional[2]
        notion_rows = query(data_source_id, token, car_name, learn_only=learn_only, source=source)
        # A template car's catalog is its file; any Parameters rows it still has are legacy
        # and are never read (see drop_template_cars).
        notion_rows = drop_template_cars(notion_rows, template_cars)

    if show_order:
        # One comparator over both sources: baseline/surface/duplicate Adjustments dedupe and
        # every column lands at its own `Order`, whichever source supplied it.
        print(build_show_order(template_rows + notion_rows))
        sys.exit(0)

    rows = notion_rows

    if pretty:
        tags = []
        if learn_only:
            tags.append('learn-only')
        if source is not None:
            tags.append(f'source={source}')
        learn_tag = f' ({", ".join(tags)})' if tags else ''
        print(f'{len(rows)} rows for "{car_name}"{learn_tag}:')
        for row in rows:
            label = row.get('Adjustment') or row.get('Name', '?')
            section = row.get('Section', '')
            surface = row.get('Surface', '')
            suffix = f' [{section}]' if section else ''
            suffix += f' ({surface})' if surface else ''
            print(f'  {label}{suffix}: {json.dumps(row)}')
    else:
        print(json.dumps(rows, indent=2))
    sys.exit(0)


if __name__ == '__main__':
    main()
