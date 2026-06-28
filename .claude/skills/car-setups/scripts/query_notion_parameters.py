#!/usr/bin/env python3
"""Query a Notion data source and return all matching rows as JSON.

Used by the car-setups skill to read a car's Parameters catalog or a filtered
slice of Setups — the Notion MCP connector cannot list database rows reliably.

Usage:
  # All Parameters rows for one car:
  python query_notion_parameters.py <data_source_id> <token> <car_name>

  # Setups the user marked "Learn from this" (pass the Setups data_source_id):
  python query_notion_parameters.py <data_source_id> <token> <car_name> --learn-only

  # The ordered SHOW property list for a view (paste into a view's SHOW directive):
  python query_notion_parameters.py <params_data_source_id> <token> <car_name> --show-order
  python query_notion_parameters.py <params_data_source_id> <token> --all --show-order

Arguments:
  data_source_id   UUID from notion-fetch (strip the "collection://" prefix).
  token            Notion read-only integration token (secret_... / ntn_...).
  car_name         Exact value of the "Car" select property to filter on.
                   Optional (omit) when --all is given.

Options:
  --learn-only   Also filter "Learn from this" checkbox = true (Setups learn pool).
  --show-order   Print the ordered SHOW property list for a Setups view (see below)
                 instead of the rows: Name, then value columns by their Parameters
                 `Order`, then the fixed meta columns. Run against the Parameters
                 data source. Output is ready to paste after `SHOW ` in a view's
                 configure DSL.
  --all          Query every row (no "Car" filter) — the union of value columns, for
                 the main Setups table and the {Location}/{Stage} views. With
                 --show-order, omit <car_name>. For a per-car view, pass <car_name>
                 (without --all) so SHOW lists only that car's value columns.
  --pretty       Human-readable summary instead of JSON.

Output: JSON array — one object per row, property names as keys, values extracted
        by type (title/rich_text -> string, select -> string or null,
        checkbox -> bool, number -> number or null). Properties with no value
        (null select, missing) are omitted; blank rich_text returns "".

Exit codes: 0 success, 1 HTTP/network error, 2 usage error. stdlib only.
"""
import json
import sys
import urllib.error
import urllib.request

NOTION_VERSION = '2025-09-03'
BASE_URL = 'https://api.notion.com/v1/data_sources'

# Fixed trailing meta-column order for a Setups view's SHOW directive, after the
# value columns. Keep in sync with notion-structure.md ("Setups column order").
META_ORDER = [
    'Car', 'Location', 'Stage', 'Surface', 'Date', 'Source', 'Mode', 'Rating',
    'Learn from this', 'Game version', 'Notes', 'Model', 'Skill version',
]


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


def build_filter(car_name, learn_only):
    """Build the Notion query filter. car_name=None means no Car filter (--all)."""
    clauses = []
    if car_name is not None:
        clauses.append({'property': 'Car', 'select': {'equals': car_name}})
    if learn_only:
        clauses.append({'property': 'Learn from this', 'checkbox': {'equals': True}})
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


def query(data_source_id, token, car_name, learn_only=False):
    """Return all rows matching car_name as a list of property dicts."""
    url = f'{BASE_URL}/{data_source_id}/query'
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }
    filt = build_filter(car_name, learn_only)
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
    positional = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    learn_only = '--learn-only' in flags
    pretty = '--pretty' in flags
    show_order = '--show-order' in flags
    all_cars = '--all' in flags

    usage = ('usage: query_notion_parameters.py <data_source_id> <token> <car_name>'
             ' [--learn-only] [--show-order] [--pretty]\n'
             '       query_notion_parameters.py <data_source_id> <token> --all --show-order')
    # Need data_source_id + token always; car_name too unless --all.
    if len(positional) < 2 or (len(positional) < 3 and not all_cars):
        print(usage, file=sys.stderr)
        sys.exit(2)

    data_source_id, token = positional[0], positional[1]
    car_name = None if all_cars else positional[2]
    rows = query(data_source_id, token, car_name, learn_only=learn_only)

    if show_order:
        print(build_show_order(rows))
        sys.exit(0)

    if pretty:
        learn_tag = ' (learn-only)' if learn_only else ''
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
