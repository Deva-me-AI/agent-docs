"""One capped tool execution. No automatic retries; Python standard library only."""
import argparse
import json
import math
import os
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = 'https://api.deva.me/v1/agents/resources'


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirect refused', headers, fp)


_opener = build_opener(RejectRedirects())


def request(method, path, body=None, key=None):
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    req = Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                  headers=headers, method=method)
    # Never follow redirects or retry POSTs; credentials stay on the original request.
    with _opener.open(req, timeout=60) as response:
        return response.status, json.load(response)


def run_loop(query, slug, params, budget, key, *, http=request, sleep=time.sleep,
             max_polls=60, on_run=lambda run_id: print(f'Run ID: {run_id}', file=sys.stderr)):
    if not key:
        raise ValueError('Set DEVA_API_KEY')
    if not math.isfinite(budget) or budget <= 0 or not isinstance(params, dict):
        raise ValueError('Require a positive finite budget and an object for params')
    if type(max_polls) is not int or max_polls < 1:
        raise ValueError('max_polls must be a positive integer')
    _, page = http('GET', '/discover?' + urlencode({'q': query, 'limit': 100}))
    if not any(item['slug'] == slug for item in page['items']):
        raise ValueError('Slug not in this discovery page; refine your query')
    path_slug = quote(slug, safe='/')
    _, spec = http('GET', '/inspect/' + path_slug)
    # Read input_schema before preparing params; server validates the supplied object.
    body = {'params': params, 'maxTotalChargeUsd': budget}
    _, estimate = http('POST', '/estimate/' + path_slug, body)
    for floor in (spec.get('min_cap_usd'), estimate.get('min_cap_usd')):
        if floor is not None and (not math.isfinite(float(floor)) or float(floor) > budget):
            raise ValueError('Tool minimum exceeds budget')
    amount = estimate.get('amount_credits')
    if amount is not None and (not math.isfinite(float(amount)) or float(amount) < 0 or float(amount) > budget):
        raise ValueError('Estimate is invalid or exceeds budget')
    # One-call task budget: reserve the entire cap before this single POST.
    # Do not release that reservation or submit again on an ambiguous failure.
    code, result = http('POST', '/run/' + path_slug, body, key)
    if code == 200:
        if result.get('status') != 'succeeded':
            raise RuntimeError('Synchronous run failed: ' + str(result.get('message')) + '; do not resubmit')
        return result
    if code != 202 or not result.get('run_id'):
        raise RuntimeError('Unexpected run response; do not resubmit')
    run_id = result['run_id']
    on_run(run_id)
    for _ in range(max_polls):
        sleep(2)
        try:
            _, result = http('GET', '/runs/' + quote(run_id, safe=''), key=key)
        except Exception as error:
            raise RuntimeError(f'Poll failed; resume GET /runs/{quote(run_id, safe="")}; do not resubmit') from error
        if result['status'] == 'succeeded':
            return result
        if result['status'] != 'running':
            raise RuntimeError(f'Run {run_id}: {result["status"]}; do not resubmit')
    raise TimeoutError(f'Poll limit reached; resume GET /runs/{run_id}; do not resubmit')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', required=True)
    parser.add_argument('--slug', required=True)
    parser.add_argument('--params', required=True, type=json.loads)
    parser.add_argument('--budget', required=True, type=float)
    args = parser.parse_args()
    print(json.dumps(run_loop(args.query, args.slug, args.params, args.budget,
                              os.environ.get('DEVA_API_KEY')), indent=2))
