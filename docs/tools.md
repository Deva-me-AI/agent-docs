# Discover and run tools

Use one loop for Deva and third-party tools: **discover → inspect → estimate → run → poll**. The REST base URL is `https://api.deva.me/v1/agents/resources`. See the [API reference](api-reference.md#resource-discovery) for curl requests and captured live responses, or the [MCP guide](mcp-server.md) for tool names.

## The loop

1. **Discover:** `GET /discover?q=...` returns `items`, `total`, and `next_cursor`. Choose a relevant `items[].slug`; do not construct a slug or select based on its provider prefix. Discover is public and free.
2. **Inspect:** `GET /inspect/{slug}` returns `input_schema`, `defaults`, `pricing`, and `caps`. Build `params` from that schema. Inspect is public and free.
3. **Estimate:** `POST /estimate/{slug}` with `{"params": {...}, "maxTotalChargeUsd": 0.01}` returns `amount_credits`, `deterministic`, `basis`, and cap information. Estimate is public and free; it neither runs the tool nor reserves funds. The numeric cap here is only an example: your chosen tool may require more.
4. **Run:** `POST /run/{slug}` with the same parameters and cap, plus `Authorization: Bearer $DEVA_API_KEY`. This is the spending step. The key must permit resource execution and have sufficient spendable credits. Run can reserve a budget before actual usage is settled. Some tools are free or included in your plan; check the estimate and final charge.
5. **Poll, when needed:** `GET /runs/{run_id}` with the same key until `status` is `succeeded` or `failed`. Polling does not start another paid execution; it can settle the charge for the existing run. The key needs resource read access. Save the run ID before polling so you can resume after a timeout.

For REST, keep `/` characters inside a slug as path segments. The older `POST /estimate` accepts `slug` in its body. Bare `POST /run` is not a working route.

## Synchronous and asynchronous results

Discovery advertises `run_kind` (`SYNC` or `ASYNC`). Handle the actual run response as authoritative:

- HTTP **200** returns a synchronous result. Check `status`, read `output`, and record `credits_charged`. A nullable `run_id` is not an instruction to poll.
- HTTP **202** returns `run_id` and `poll`. Wait between GETs (for example, two seconds) and stop at a terminal status. Terminal output is in `items`, with `result_count` and `credits_charged`. A successful HTTP response can still contain `status: "failed"`.

A poll timeout does not cancel execution. Keep the ID and resume polling; do not submit another run. `cap_hit: true` means the result was truncated at the spending cap. Poll options `fields`, `max_items`, and `summary` only reduce the response displayed; they do not reduce the bill. Save large results to a file instead of copying them into model context.

## Errors and budget guards

| HTTP status | Meaning | Action |
|---|---|---|
| 401 | Missing or invalid API key | Supply a valid Bearer key for run/poll. |
| 402 | Insufficient credits or a cap that exceeds spendable balance | Read the error reason. `cap_preflight` can include `max_allowed_cap_credits`; reduce the cap only if it still meets the tool minimum. `cap_floor_above_balance` requires funding before that tool can run. |
| 403 | Key scope or resource access is restricted | Check key permissions and account access. |
| 404 | Unknown tool/run or incorrect route | Discover again or check the saved run ID. |
| 422 | Invalid parameters or cap | Follow the inspected schema and error details. |
| 503 | Provider unavailable | Preserve any known run ID and check it later. Do not automatically repeat the run POST. |

**Never automatically retry a run POST**, including after a timeout, connection loss, or 503. The request may already have started an execution. The REST run route supports an `Idempotency-Key` header for intentional duplicate protection; keep the same key for the same intended request, but do not assume an ambiguous response means nothing ran.

> **Budget guard:** Keep both a per-task credit budget and a maximum run count. Before each POST, require a positive finite cap no larger than your remaining task budget and no smaller than `min_cap_usd`. Compare `amount_credits` to your cap, but do not mistake an estimate for enforcement. Send `maxTotalChargeUsd` on the run itself. Reserve the full cap locally before submitting, and keep that reservation after ambiguous failures until reconciled. One credit equals one USD. Never raise a budget automatically to satisfy a tool minimum.

## Runnable examples and tests

The examples use HTTP directly, accept an exact discovered slug plus schema-valid JSON, and submit at most one run. They fail closed on invalid caps, over-budget estimates, and unknown statuses. No run POST is retried.

```bash
export DEVA_API_KEY=deva_your_api_key
# This command can spend up to the supplied cap.
python3 examples/python/tools_loop.py \
  --query 'market intel leaderboard' --slug 'deva/market-intel-leaderboard' \
  --params '{"chain":"hl","limit":1,"window":"30d"}' --budget 0.01

# Node.js 22.18+ (native TypeScript type stripping); same spending behavior.
node examples/typescript/tools_loop.ts \
  --query 'market intel leaderboard' --slug 'deva/market-intel-leaderboard' \
  --params '{"chain":"hl","limit":1,"window":"30d"}' --budget 0.01
```

- [Python example](../examples/python/tools_loop.py) uses the standard library.
- [TypeScript example](../examples/typescript/tools_loop.ts) uses built-in `fetch`.

Run mocked HTTP unit tests from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/tools_loop.test.ts
```

Both suites include a live smoke test skipped unless `DEVA_API_KEY` is set. The smoke tests discover, inspect, estimate, and verify authenticated run lookup; they never start a paid run. Successful paid run/poll responses were not captured for this docs update because no key was available.
