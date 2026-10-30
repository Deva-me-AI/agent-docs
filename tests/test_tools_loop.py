import importlib.util
import io
import json
import os
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('tools_loop', Path(__file__).parents[1] / 'examples/python/tools_loop.py')
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)
SLUG = 'deva/example'


class Response(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(json.dumps(body).encode())
        self.status = status


@contextmanager
def redirect_server(code):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.command, self.path, self.headers.get('Authorization')))
            self.send_response(code if self.path != '/destination' else 200)
            self.send_header('Location', f'http://localhost:{self.server.server_port}/destination')
            self.end_headers()
            self.wfile.write(b'{}')

        do_POST = do_GET

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class LoopTests(unittest.TestCase):
    def execute(self, tail, *, estimate=None, budget=0.01, max_polls=3):
        replies = [Response(200, {'items': [{'slug': SLUG}]}),
                   Response(200, {'input_schema': {}, 'min_cap_usd': None}),
                   Response(200, estimate or {'amount_credits': 0.001})] + tail
        with patch.object(loop._opener, 'open', side_effect=replies) as http:
            self.http = http
            return loop.run_loop('example', SLUG, {}, budget, 'test-key',
                                 sleep=lambda _: None, on_run=lambda _: None, max_polls=max_polls)

    def test_sync_and_cap_and_auth(self):
        result = self.execute([Response(200, {'status': 'succeeded', 'output': {'ok': True}, 'cap_hit': True})])
        self.assertTrue(result['output']['ok'])
        self.assertTrue(result['cap_hit'])
        requests = [call.args[0] for call in self.http.call_args_list]
        self.assertEqual(len(requests), 4)
        self.assertFalse(requests[0].has_header('Authorization'))
        self.assertEqual(requests[-1].get_header('Authorization'), 'Bearer test-key')
        self.assertEqual(json.loads(requests[-1].data)['maxTotalChargeUsd'], 0.01)
        self.assertTrue(requests[-1].full_url.endswith('/run/deva/example'))

    def test_async_polls_same_id(self):
        result = self.execute([Response(202, {'run_id': 'run-1', 'status': 'running'}),
                               Response(200, {'status': 'running'}),
                               Response(200, {'status': 'succeeded', 'items': [1]})])
        self.assertEqual(result['items'], [1])
        self.assertEqual([c.args[0].method for c in self.http.call_args_list], ['GET', 'GET', 'POST', 'POST', 'GET', 'GET'])
        self.assertTrue(self.http.call_args.args[0].full_url.endswith('/runs/run-1'))

    def test_failures_never_retry_post(self):
        for error in [TimeoutError('timeout'), HTTPError('url', 402, 'credits', {}, None), HTTPError('url', 503, 'unavailable', {}, None)]:
            with self.subTest(error=error), self.assertRaises(type(error)):
                self.execute([error])
            self.assertEqual(self.http.call_count, 4)

    def test_rejects_estimate_above_cap_and_minimum(self):
        for estimate in [{'amount_credits': 1}, {'amount_credits': None, 'min_cap_usd': 1}, {'amount_credits': 'NaN'}]:
            with self.subTest(estimate=estimate), self.assertRaises(ValueError):
                self.execute([], estimate=estimate)
            self.assertEqual(self.http.call_count, 3)

    def test_invalid_budgets_do_not_call_http(self):
        for budget in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                self.execute([], budget=budget)
            self.assertEqual(self.http.call_count, 0)

    def test_terminal_failure_and_timeout(self):
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            self.execute([Response(202, {'run_id': 'run-1'}), Response(200, {'status': 'failed'})])
        with self.assertRaisesRegex(TimeoutError, 'resume GET /runs/run-1'):
            self.execute([Response(202, {'run_id': 'run-1'}), Response(200, {'status': 'running'})], max_polls=1)

    def test_rejects_redirects_without_forwarding_credentials(self):
        for code in [301, 302, 303, 307, 308]:
            for method, path, body in [('POST', '/run/example', {}), ('GET', '/runs/r1', None)]:
                with self.subTest(code=code, method=method), redirect_server(code) as (base, calls):
                    with patch.object(loop, 'BASE', base), self.assertRaises(HTTPError) as error:
                        loop.request(method, path, body, 'test-key')
                    self.assertEqual(error.exception.code, code)
                    error.exception.close()
                    self.assertEqual(calls, [(method, path, 'Bearer test-key')])

    def test_invalid_poll_limits_do_not_call_http(self):
        for limit in [1.5, 1.0, True, False, '2', None, 0, -1, float('nan'), float('inf')]:
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'positive integer'):
                self.execute([], max_polls=limit)
            self.assertEqual(self.http.call_count, 0)

    def test_sync_non_success_never_polls_or_resubmits(self):
        for status in ['failed', 'running', 'unknown', None]:
            with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, 'do not resubmit'):
                self.execute([Response(200, {'status': status})])
            self.assertEqual(self.http.call_count, 4)

    def test_unexpected_success_response_never_polls_or_resubmits(self):
        for code, body in [(201, {'status': 'succeeded'}), (206, {'run_id': 'r1'}),
                           (202, {}), (202, {'run_id': None}), (202, {'run_id': ''})]:
            with self.subTest(code=code, body=body), self.assertRaisesRegex(RuntimeError, 'do not resubmit'):
                self.execute([Response(code, body)])
            self.assertEqual(self.http.call_count, 4)

    def test_poll_errors_preserve_resume_guidance_and_cause(self):
        for error in [TimeoutError('timeout'), HTTPError('url', 503, 'unavailable', {}, None)]:
            with self.subTest(error=error), self.assertRaisesRegex(RuntimeError, 'resume GET /runs/run-1; do not resubmit') as raised:
                self.execute([Response(202, {'run_id': 'run-1'}), error])
            self.assertIs(raised.exception.__cause__, error)
            self.assertEqual(self.http.call_count, 5)

    @unittest.skipUnless(os.getenv('DEVA_API_KEY'), 'DEVA_API_KEY not set; no paid execution')
    def test_live_smoke(self):
        _, page = loop.request('GET', '/discover?q=market%20intel%20leaderboard&limit=1')
        slug = page['items'][0]['slug']
        _, spec = loop.request('GET', '/inspect/' + loop.quote(slug, safe='/'))
        self.assertIn('input_schema', spec)
        _, estimate = loop.request('POST', '/estimate/' + loop.quote(slug, safe='/'), {'params': {}})
        self.assertIn('amount_credits', estimate)
        # A missing run must reach authenticated lookup (404), not authentication (401).
        with self.assertRaises(HTTPError) as error:
            loop.request('GET', '/runs/00000000-0000-0000-0000-000000000000', key=os.environ['DEVA_API_KEY'])
        self.assertEqual(error.exception.code, 404)
