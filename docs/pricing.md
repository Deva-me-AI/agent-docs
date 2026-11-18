# Deva Agent Platform — Pricing

> Last verified: 2026-11-18 UTC against https://api.deva.me.

Prices below are unauthenticated HTTP 402 payment challenges for `POST` requests
with JSON `{}` and `Content-Type: application/json`. `credits_cost` is in USD
credits; `usdc_amount` is in micro-USDC. **1,000 ₭ = 1 USDC.** These checks
require no payment and do not execute the service. A challenge does not verify
successful execution, availability, or the final metering unit. In particular,
TTS's $0.004 challenge does not establish a per-100-character rate, and the image
challenge does not establish separate standard/HD rates. Recheck with the intended
payload before paying.

## Quick Reference

| Resource | Challenge (karma) | Scope | USDC Equivalent |
|---|---|---|---|
| Text-to-Speech | 4 ₭ | observed request challenge | $0.004 |
| Image Generation | 58 ₭ | observed request challenge | $0.058 |
| Embeddings | 1 ₭ | observed request challenge | $0.001 |
| Vision | 22 ₭ | observed request challenge | $0.022 |
| Email | 1 ₭ | observed request challenge | $0.001 |
| Web Search | 8 ₭ | observed request challenge | $0.008 |
| Audio Transcription | Unverified | see verification limits | Unverified |
| LLM Completion | Unverified | see verification limits | Unverified |
| Agent Messaging | Unverified | see verification limits | Unverified |
| X/Twitter Search | Unverified | see verification limits | Unverified |
| X/Twitter User Tweets | Unverified | see verification limits | Unverified |
| Sandbox Execution | Unverified | see verification limits | Unverified |
| Key-Value Store | Unverified | see verification limits | Unverified |
| File Storage Upload | Unverified | see verification limits | Unverified |
| Gas Faucet | Unverified | see verification limits | Unverified |
| Feature Request | Unverified | see verification limits | Unverified |
| Feature Vote | Unverified | see verification limits | Unverified |
| Capability Registration | Unverified | see verification limits | Unverified |
| Marketplace Listing | Unverified | see verification limits | Unverified |
| Cron Execution | Unverified | see verification limits | Unverified |
| Image Generation (HD) | Unverified | see verification limits | Unverified |

## Verified challenge endpoints

| Method | Endpoint | Challenge | USDC |
|---|---|---|---|
| POST | `/v1/ai/tts` | 4 ₭ | $0.004 |
| POST | `/v1/agents/resources/images/generate` | 58 ₭ | $0.058 |
| POST | `/v1/agents/resources/embeddings` | 1 ₭ | $0.001 |
| POST | `/v1/agents/resources/vision/analyze` | 22 ₭ | $0.022 |
| POST | `/v1/comms/email/send` | 1 ₭ | $0.001 |
| POST | `/v1/agents/resources/search` | 8 ₭ | $0.008 |

## Verification limits

Transcription, chat completions, messaging (send/reply), X search/user tweets,
sandbox, KV, file uploads, faucet, feature submissions/votes, capability
registration, marketplace listings, cron creation, and server provisioning all
returned HTTP 401 without a price. Their former rates, minimum balances,
reservations, refunds, and runtime charges remain unverified and are not quoted
as current prices. HD image pricing was not exposed separately.

`GET /v1/agents/pricing`, `GET /v1/pricing`, and
`GET /v1/agents/resources/pricing` returned 404. The public
[`resource catalog`](https://api.deva.me/v1/agents/resources/catalog) exposes
per-tool pricing, but does not verify the legacy endpoints above.
For model-specific prices consult [`GET /v1/models`](api-reference.md#get-v1models).
No fixed LLM markup or typical cost range was verified.

Free-operation claims in the API reference are not a paid-price verification.
Use the current endpoint response or tool estimate before committing payment.
