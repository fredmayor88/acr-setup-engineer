#!/usr/bin/env python3
"""Query a Notion data source and return all matching rows as JSON.

Used by the car-setups skill to read a car's Parameters catalog or a filtered
slice of Setups — the Notion MCP connector cannot list database rows reliably.

Usage:
  # All Parameters rows for one car:
  python query_notion_parameters.py <data_source_id> <token> <car_name>

  # Setups the user marked "Learn from this" (pass the Setups data_source_id):
  python query_notion_parameters.py <data_source_id> <token> <car_name> --learn-only

Arguments:
  data_source_id   UUID from notion-fetch (strip the "collection://" prefix).
  token            Notion read-only integration token (secret_... / ntn_...).
  car_name         Exact value of the "Car" select property to filter on.

Options:
  --learn-only   Also filter "Learn from this" checkbox = true (Setups learn pool).
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
    car_clause = {'property': 'Car', 'select': {'equals': car_name}}
    if not learn_only:
        return car_clause
    return {
        'and': [
            car_clause,
            {'property': 'Learn from this', 'checkbox': {'equals': True}},
        ],
    }


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
        body = {'filter': filt, 'page_size': 100}
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

    if len(positional) < 3:
        print(
            'usage: query_notion_parameters.py <data_source_id> <token> <car_name>'
            ' [--learn-only] [--pretty]',
            file=sys.stderr,
        )
        sys.exit(2)

    data_source_id, token, car_name = positional[0], positional[1], positional[2]
    rows = query(data_source_id, token, car_name, learn_only=learn_only)

    if pretty:
        learn_tag = ' (learn-only)' if learn_only else ''
        print(f'{len(rows)} rows for "{car_name}"{learn_tag}:')
        for row in rows:
            label = row.get('Adjustment') or row.get('Name', '?')
            section = row.get('Section', '')
            suffix = f' [{section}]' if section else ''
            print(f'  {label}{suffix}: {json.dumps(row)}')
    else:
        print(json.dumps(rows, indent=2))
    sys.exit(0)


if __name__ == '__main__':
    main()
