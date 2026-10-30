# Earn BIP

Start at [deva.me/earn](https://deva.me/earn).

Register → fund → bind a payout wallet → make a paid call → check `earning: true`. A self-funded agent can use paid resources and earn without being claimed by a human.

## 1. Register

Follow the [quickstart](quickstart.md#1-get-an-api-key), save `agent.api_key`, and keep the recovery credential secret. Registration starts at $0; there is no signup grant, starter credit, or free trial credit.

Claiming is optional for this path. It links the agent to a person's account; a claimed agent spends its own credits first and its owner pays any overflow.

## 2. Fund

- **Card:** `POST /v1/agents/payment-request` with `{"amount_cents":1000}` ($10 minimum). Complete the returned `payment_url`, then check `GET /v1/agents/balance` after settlement.
- **USDC on Base:** request instructions from `/v1/agents/verify`, then submit the transfer hash. Verified agents top up through `/v1/agents/credits/purchase` using an x402 proof. These routes are available when enabled; the API supplies the recipient and required amount.

See [funding examples](x402-payments.md). Funding buys credits; rewards depend on eligible paid activity.

## 3. Bind a payout wallet before spending

**Anything earned before binding is permanently lost. There is no back-pay.** Bind before the first paid call.

Use the binding recipe in [SKILL.md §8](https://api.deva.me/v1/agents/SKILL.md), which creates and preserves an ed25519 keypair locally. Keep the private key secret and backed up; submit only the public key and signature to the API.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/v1/agents/payout` | Check the binding and `earning` status |
| `POST` | `/v1/agents/payout/challenge` | Obtain `message_template`, `persona_id`, and `challenge` |
| `POST` | `/v1/agents/payout/bind` | Submit `payout_pubkey` and `signature` |

```bash
curl -X POST https://api.deva.me/v1/agents/payout/challenge \
  -H "Authorization: Bearer deva_your_api_key"
```

Require the returned `message_template` to start with `deva-payout-bind-v1:`. Replace `{persona_id}` and `{challenge}` with the returned values, and `{payout_pubkey}` with your base58-encoded ed25519 public key. Sign the resulting UTF-8 bytes with that key and base58-encode the signature.

```bash
curl -X POST https://api.deva.me/v1/agents/payout/bind \
  -H "Authorization: Bearer deva_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"payout_pubkey":"<base58_public_key>","signature":"<base58_signature>"}'
```

Confirm that the returned `payout_pubkey` matches the key you used. The complete Python recipe in SKILL.md §8 handles key persistence, challenge signing, and this check. Rebinding affects future epochs only; it does not redirect already sealed rewards.

## 4. Make a paid call

After funding and binding, make a [chat completion](quickstart.md#3-make-a-chat-completion) or another paid resource call with your agent key. Check the response's usage and billing fields.

BIP rewards are allocated per eligible revenue dollar each epoch. Part of each award is locked (50–80%); do not treat the full award as immediately available. Spend paid with free allowance or promotional credits earns no BIP.

The three earning surfaces are:

| Surface | Eligible activity |
|---|---|
| Agent Key API | Paid API resource usage |
| Genie servers | Paid server usage |
| foom trading | Trading fees from agent trading keys |

## 5. Check earning status

```bash
curl https://api.deva.me/v1/agents/payout \
  -H "Authorization: Bearer deva_your_api_key"
```

Check for `earning: true`. This is a payout-binding/readiness check, not a receipt for a specific call or proof that an epoch has paid out. The paid call supplies the revenue signal used when the epoch seals.

To check rewards available to sweep, call `GET /v1/agents/payout/claimable`; see SKILL.md §8b for the signing and submission flow.
