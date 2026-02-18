# Dual-Payment Architecture

This document describes Deva's dual-rail payment model: prepaid karma via API key and per-request x402 USDC payments.

## System overview

Paid endpoints can execute through either:
- API key authentication + karma debit
- x402 challenge/response + wallet-backed payment

Both paths converge into one internal accounting ledger.

```text
Client (API key or wallet)
            |
            v
API layer (payment decision middleware)
   |                       |
   v                       v
Karma rail             x402 rail
(auth + debit)    (verify + credit + debit)
   \                       /
    \                     /
            v
      Resource handler
            |
            v
Response (+ billing headers)
```

## Payment decision flow

```text
if Authorization header exists:
  authenticate principal
  estimate karma cost
  debit karma
  execute request
  return X-Deva-Karma-Cost

else if X-PAYMENT exists:
  verify proof with facilitator
  validate network, asset, recipient, amount, nonce, expiry
  map wallet to wallet principal
  credit karma equivalent
  atomically debit request cost
  execute request
  return X-Deva-Karma-Cost (+ X-Deva-USDC-Charged)

else:
  return 402 Payment Required with exact payment requirements
```

## Pricing engine

Canonical rate:
- `1,000 ₭ = 1.00 USDC`

Formula:
- `usdc = karma / 1000`
- `micro_usdc = ceil(usdc * 1_000_000)`

Rules:
- exact request amount expected
- round up micro-USDC
- same endpoint list price across both rails

## Security controls

- replay protection with nonce + expiry
- idempotency protection to prevent double-charge
- chain allowlist and asset allowlist
- recipient validation against treasury wallet
- single execution path when both auth headers are present

## Failure handling

| Condition | Behavior |
|---|---|
| Facilitator unavailable | x402 path returns retryable payment error; authenticated karma path remains available |
| Verification timeout | handler is not executed; client retries safely |
| Provider failure after billing | endpoint charge policy applies; request is audit logged for potential compensating credit |

## Reconciliation

Daily reconciliation compares:
- facilitator verification records
- on-chain settlement data
- internal ledger credits/debits

Audit fields include payment ID, nonce, wallet principal, route, karma cost, USDC amount, and timestamps.
