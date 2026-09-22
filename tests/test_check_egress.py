"""Validate scripts/check_egress.py — the once-per-chat probe for network access to Notion's API.

The code sandbox reaches the internet through an egress proxy. On Claude's Free plan the proxy
never lets `api.notion.com` through, and it answers a blocked host itself (a 403 that isn't
Notion's). So the probe only says `ok` when the reply is Notion's own JSON error shape; anything
else — a proxy refusal, a refused connection, a timeout — is `none`.

These tests stand up a local HTTP server in each role instead of mocking urllib.

Run: python -m unittest discover -s tests
"""
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRIPTS = os.path.join(REPO, '.claude', 'skills', 'acr-setup-engineer', 'scripts')
SCRIPT = os.path.join(SCRIPTS, 'check_egress.py')
sys.path.insert(0, SCRIPTS)

import check_egress  # noqa: E402

NOTION_401 = json.dumps({
    'object': 'error', 'status': 401, 'code': 'unauthorized',
    'message': 'API token is invalid.',
}).encode()


def serve(status, body, content_type='application/json', delay=0.0):
    """Start a one-behaviour HTTP server on a free port; return (url, server)."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if delay:
                time.sleep(delay)
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{server.server_address[1]}/v1/users/me', server


def closed_port_url():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    return f'http://127.0.0.1:{port}/v1/users/me'


class ProbeTest(unittest.TestCase):
    def setUp(self):
        # A proxy variable in the developer's shell must not reroute the local test servers.
        self._env = {k: os.environ.pop(k) for k in list(os.environ)
                     if k.lower() in ('http_proxy', 'https_proxy', 'all_proxy')}
        os.environ['NO_PROXY'] = '127.0.0.1'

    def tearDown(self):
        os.environ.pop('NO_PROXY', None)
        os.environ.update(self._env)

    def _probe(self, url, timeout=2.0):
        return check_egress.probe(url, timeout=timeout)

    def test_notion_unauthorized_reply_means_reachable(self):
        url, server = serve(401, NOTION_401)
        try:
            self.assertEqual(self._probe(url), 'ok')
        finally:
            server.shutdown()

    def test_proxy_refusal_means_no_egress(self):
        url, server = serve(403, b'Host not in allowlist', content_type='text/plain')
        try:
            self.assertEqual(self._probe(url), 'none')
        finally:
            server.shutdown()

    def test_json_that_is_not_notions_means_no_egress(self):
        url, server = serve(403, json.dumps({'error': 'blocked'}).encode())
        try:
            self.assertEqual(self._probe(url), 'none')
        finally:
            server.shutdown()

    def test_refused_connection_means_no_egress(self):
        self.assertEqual(self._probe(closed_port_url()), 'none')

    def test_timeout_means_no_egress(self):
        url, server = serve(401, NOTION_401, delay=1.5)
        try:
            self.assertEqual(self._probe(url, timeout=0.3), 'none')
        finally:
            server.shutdown()

    def test_cli_prints_one_line_and_exits_zero(self):
        url, server = serve(403, b'blocked', content_type='text/plain')
        try:
            env = {k: v for k, v in os.environ.items()}
            out = subprocess.run([sys.executable, SCRIPT, '--url', url],
                                 capture_output=True, text=True, env=env, timeout=30)
        finally:
            server.shutdown()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), 'egress: none')

    def test_default_target_is_notions_api(self):
        self.assertTrue(check_egress.NOTION_URL.startswith('https://api.notion.com/'))


if __name__ == '__main__':
    unittest.main()
