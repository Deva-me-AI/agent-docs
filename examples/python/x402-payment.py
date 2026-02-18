import requests
from x402 import create_payment_header

URL = "https://api.deva.me/v1/ai/tts"
PAYLOAD = {"text": "Hello from x402"}
PRIVATE_KEY = "0xYourPrivateKey"


def main() -> None:
    first = requests.post(URL, json=PAYLOAD, timeout=30)
    if first.status_code != 402:
        first.raise_for_status()
        print("Endpoint did not require x402 payment for this request.")
        print(first.text)
        return

    requirements = first.json()["payment_requirements"]
    x_payment = create_payment_header(requirements, private_key=PRIVATE_KEY)

    paid = requests.post(URL, json=PAYLOAD, headers={"X-PAYMENT": x_payment}, timeout=30)
    paid.raise_for_status()
    print(f"Success: {paid.status_code}, bytes={len(paid.content)}")


if __name__ == "__main__":
    main()
