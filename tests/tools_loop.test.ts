import test from 'node:test';
import assert from 'node:assert/strict';
import { runLoop, request } from '../examples/typescript/tools_loop.ts';

const slug = 'deva/example';
async function execute(t: any, tail: any[], estimate: any = { amount_credits: 0.001 }, budget = 0.01, maxPolls = 3) {
  const replies: any[] = [ [200, { items: [{ slug }] }], [200, { input_schema: {} }], [200, estimate], ...tail ];
  const calls: any[] = [];
  t.mock.method(globalThis, 'fetch', async (url: string, init: any) => {
    calls.push({ url, ...init });
    const next = replies.shift();
    if (next instanceof Error) throw next;
    assert.ok(next, 'Unexpected HTTP call (possible retry)');
    return new Response(JSON.stringify(next[1]), { status: next[0] });
  });
  try {
    return { result: await runLoop('example', slug, {}, budget, 'test-key', {
      sleep: async () => {}, onRun: () => {}, maxPolls,
    }), calls };
  } catch (error) { return { error, calls }; }
}

test('sync output, cap, slug path and auth', async t => {
  const { result, error, calls } = await execute(t, [[200, { status: 'succeeded', output: { ok: true } }]]);
  assert.ifError(error);
  assert.equal(result?.output.ok, true);
  assert.equal(calls.length, 4);
  assert.equal(calls[0].headers.Authorization, undefined);
  assert.equal(calls[3].headers.Authorization, 'Bearer test-key');
  assert.ok(calls[3].url.endsWith('/run/deva/example'));
  assert.equal(JSON.parse(calls[3].body).maxTotalChargeUsd, 0.01);
});
test('async polls same run without another POST', async t => {
  const { result, error, calls } = await execute(t, [[202, { run_id: 'r1' }], [200, { status: 'running' }], [200, { status: 'succeeded', items: [1] }]]);
  assert.ifError(error);
  assert.deepEqual(result?.items, [1]);
  assert.deepEqual(calls.map(c => c.method), ['GET', 'GET', 'POST', 'POST', 'GET', 'GET']);
  assert.ok(calls[5].url.endsWith('/runs/r1'));
});
for (const failure of [new Error('timeout'), [402, { error: 'insufficient credits' }], [503, { error: 'unavailable' }]]) {
  test(`no retry after ${JSON.stringify(failure)}`, async t => {
    const { error, calls } = await execute(t, [failure]);
    assert.ok(error);
    assert.equal(calls.length, 4);
  });
}
for (const estimate of [{ amount_credits: 1 }, { min_cap_usd: 1 }, { amount_credits: 'NaN' }]) {
  test(`reject estimate ${JSON.stringify(estimate)}`, async t => {
    const { error, calls } = await execute(t, [], estimate);
    assert.ok(error);
    assert.equal(calls.length, 3);
  });
}
for (const budget of [0, -1, NaN, Infinity]) {
  test(`reject budget ${budget}`, async t => {
    const { error, calls } = await execute(t, [], undefined, budget);
    assert.ok(error);
    assert.equal(calls.length, 0);
  });
}
test('failed terminal state', async t => {
  const { error } = await execute(t, [[202, { run_id: 'r1' }], [200, { status: 'failed' }]]);
  assert.match(String(error), /failed/);
});
test('poll timeout preserves ID', async t => {
  const { error, calls } = await execute(t, [[202, { run_id: 'r1' }], [200, { status: 'running' }]], undefined, 0.01, 1);
  assert.match(String(error), /resume GET \/runs\/r1/);
  assert.equal(calls.length, 5);
});
test('live smoke without paid execution', { skip: !process.env.DEVA_API_KEY }, async () => {
  const [, page] = await request('GET', '/discover?q=market%20intel%20leaderboard&limit=1');
  const slugPath = page.items[0].slug.split('/').map(encodeURIComponent).join('/');
  const [, spec] = await request('GET', '/inspect/' + slugPath);
  assert.ok(spec.input_schema);
  const [, estimate] = await request('POST', '/estimate/' + slugPath, { params: {} });
  assert.ok('amount_credits' in estimate);
  await assert.rejects(request('GET', '/runs/00000000-0000-0000-0000-000000000000', undefined, process.env.DEVA_API_KEY), /HTTP 404/);
});
