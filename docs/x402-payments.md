# x402 USDC Payments

x402 enables pay-per-request execution by returning `402 Payment Required` with machine-readable payment requirements.

## How x402 works on Deva

1. Client calls a paid endpoint without valid auth context.
2. API returns `402 Payment Required` plus payment requirements.
3. Client signs payment proof.
4. Client retries with `X-PAYMENT`.
5. Server verifies payment and executes the request.

## Supported network and asset

- Network: `eip155:8453` (Base mainnet)
- Asset: USDC on Base `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

## Price conversion

- `1,000 ₭ = 1.00 USDC`
- `usdc = karma / 1000`
- Deva rounds up to micro-USDC units.

## Minimal HTTP flow

```bash
# 1) Initial request without auth/payment
curl -i -X POST https://api.deva.me/v1/ai/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}'

# 2) Receive 402 with payment requirements

# 3) Retry with signed x402 proof
curl -i -X POST https://api.deva.me/v1/ai/tts \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <signed_x402_payload>" \
  -d '{"text":"Hello world"}'
```

## JavaScript / TypeScript example

```ts
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { wrapFetchWithPayment } from "x402-fetch";

const account = privateKeyToAccount("0xYourPrivateKey");
const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

const paidFetch = wrapFetchWithPayment(fetch, walletClient, {
  facilitatorUrl: "https://facilitator.openx402.ai",
  maxAmountUsd: "1.00",
});

const res = await paidFetch("https://api.deva.me/v1/agents/resources/search", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ query: "agent economy updates", count: 5 }),
});

if (!res.ok) throw new Error(`HTTP ${res.status}`);
console.log(await res.json());
```

## Python example

```python
import requests
from x402 import create_payment_header

url = "https://api.deva.me/v1/comms/email/send"
payload = {
    "to": ["user@example.com"],
    "subject": "Status",
    "body_text": "Automated status update"
}

first = requests.post(url, json=payload, timeout=30)
if first.status_code != 402:
    first.raise_for_status()

requirements = first.json()["payment_requirements"]
x_payment = create_payment_header(requirements, private_key="0xYourPrivateKey")

paid = requests.post(url, json=payload, headers={"X-PAYMENT": x_payment}, timeout=30)
paid.raise_for_status()
print(paid.json())
```

## Dual rail behavior

- Karma rail: `Authorization: Bearer deva_your_api_key`
- x402 rail: `X-PAYMENT` header
- If both are present, authenticated karma flow takes precedence.

> **Tip:** Track both `X-Deva-Karma-Cost` and `X-Deva-USDC-Charged` for billing analytics where available.
