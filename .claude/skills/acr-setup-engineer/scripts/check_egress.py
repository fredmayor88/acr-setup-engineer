#!/usr/bin/env python3
"""Probe, once per chat, whether this sandbox can reach Notion's API.

Every REST read in `references/notion-rest-read.md` needs outbound network to `api.notion.com`.
On Claude's Free plan the sandbox never has it (egress stops at package managers, with no switch
to widen it), and a Pro/Max user can have it switched off. Rather than let each read time out and
fall back, the skill runs this once and, on `none`, skips every REST read for the rest of the chat
(`notion-rest-read.md` -> *Offline mode*).

It sends one unauthenticated GET through urllib — which honours the sandbox's proxy variables,
exactly like `query_notion_parameters.py` — and answers `ok` only when the reply is Notion's own
JSON (its 401 for a missing token). A proxy's refusal, a refused connection or a timeout is `none`.

Usage:
  python scripts/check_egress.py            # prints `egress: ok` or `egress: none`, exits 0
"""
import argparse
import json
import urllib.error
import urllib.request

NOTION_URL = 'https://api.notion.com/v1/users/me'


def _is_notion(body):
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and data.get('object') in ('error', 'user')


def probe(url=NOTION_URL, timeout=3.0):
    req = urllib.request.Request(url, headers={'Notion-Version': '2025-09-03'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        with exc:
            body = exc.read()
    except (urllib.error.URLError, OSError):
        return 'none'
    return 'ok' if _is_notion(body) else 'none'


def main():
    ap = argparse.ArgumentParser(description='Can this sandbox reach api.notion.com?')
    ap.add_argument('--url', default=NOTION_URL, help=argparse.SUPPRESS)
    ap.add_argument('--timeout', type=float, default=3.0, help='seconds (default 3)')
    args = ap.parse_args()
    print(f'egress: {probe(args.url, args.timeout)}')


if __name__ == '__main__':
    main()
