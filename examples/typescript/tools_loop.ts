/** One capped execution using built-in fetch. Never automatically retry a run. */
import { parseArgs } from 'node:util';
import { pathToFileURL } from 'node:url';

export const BASE = 'https://api.deva.me/v1/agents/resources';
type Json = Record<string, any>;
type Http = (method: string, path: string, body?: Json, key?: string) => Promise<[number, Json]>;

export const request: Http = async (method, path, body, key) => {
  const response = await fetch(BASE + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
    redirect: 'error',
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return [response.status, await response.json() as Json];
};

export async function runLoop(query: string, slug: string, params: Json, budget: number, key: string,
  { http = request, sleep = (ms: number) => new Promise<void>(r => setTimeout(r, ms)),
    maxPolls = 60, onRun = (id: string) => console.error(`Run ID: ${id}`) } = {}) {
  if (!key) throw new Error('Set DEVA_API_KEY');
  if (!Number.isFinite(budget) || budget <= 0 || !params || typeof params !== 'object' || Array.isArray(params))
    throw new Error('Require a positive finite budget and an object for params');
  if (!Number.isInteger(maxPolls) || maxPolls < 1) throw new Error('maxPolls must be positive');
  const [, page] = await http('GET', '/discover?' + new URLSearchParams({ q: query, limit: '100' }));
  if (!page.items.some((item: Json) => item.slug === slug)) throw new Error('Slug not in this discovery page; refine your query');
  const pathSlug = slug.split('/').map(encodeURIComponent).join('/');
  const [, spec] = await http('GET', '/inspect/' + pathSlug);
  // Read input_schema before preparing params; the server validates the supplied object.
  const body = { params, maxTotalChargeUsd: budget };
  const [, estimate] = await http('POST', '/estimate/' + pathSlug, body);
  for (const floor of [spec.min_cap_usd, estimate.min_cap_usd]) {
    if (floor != null && (!Number.isFinite(Number(floor)) || Number(floor) > budget))
      throw new Error('Tool minimum exceeds budget');
  }
  const amount = estimate.amount_credits;
  if (amount != null && (!Number.isFinite(Number(amount)) || Number(amount) < 0 || Number(amount) > budget))
    throw new Error('Estimate is invalid or exceeds budget');
  // One-call task budget: reserve the whole cap before submitting this single POST.
  // An ambiguous failure does not release the reservation or authorize another run.
  const [code, initial] = await http('POST', '/run/' + pathSlug, body, key);
  if (code === 200) {
    if (initial.status !== 'succeeded') throw new Error(`Synchronous run failed: ${initial.message}; do not resubmit`);
    return initial;
  }
  if (code !== 202 || !initial.run_id) throw new Error('Unexpected run response; do not resubmit');
  const id = initial.run_id;
  onRun(id);
  for (let i = 0; i < maxPolls; i++) {
    await sleep(2000);
    let result: Json;
    try {
      [, result] = await http('GET', '/runs/' + encodeURIComponent(id), undefined, key);
    } catch (cause) {
      throw new Error(`Poll failed; resume GET /runs/${encodeURIComponent(id)}; do not resubmit`, { cause });
    }
    if (result.status === 'succeeded') return result;
    if (result.status !== 'running') throw new Error(`Run ${id}: ${result.status}; do not resubmit`);
  }
  throw new Error(`Poll limit reached; resume GET /runs/${id}; do not resubmit`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { values } = parseArgs({ options: {
    query: { type: 'string' }, slug: { type: 'string' }, params: { type: 'string' }, budget: { type: 'string' },
  } });
  if (!values.query || !values.slug || !values.params || !values.budget) throw new Error('Supply --query --slug --params --budget');
  const result = await runLoop(values.query, values.slug, JSON.parse(values.params), Number(values.budget), process.env.DEVA_API_KEY ?? '');
  console.log(JSON.stringify(result, null, 2));
}
