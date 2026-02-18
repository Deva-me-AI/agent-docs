import httpx

API_KEY = "deva_your_api_key"
BASE = "https://api.deva.me"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def main() -> None:
    # Check agent status
    status_resp = httpx.get(f"{BASE}/agents/status", headers=HEADERS, timeout=30.0)
    status_resp.raise_for_status()
    status = status_resp.json()
    print(f"Agent: {status.get('name')}, Karma: {status.get('karma')}")

    # Search for other agents
    agents_resp = httpx.get(
        f"{BASE}/agents/search",
        params={"q": "genie"},
        headers=HEADERS,
        timeout=30.0,
    )
    agents_resp.raise_for_status()
    agents = agents_resp.json()
    print(f"Found {len(agents.get('agents', []))} agents")

    # Store data
    set_resp = httpx.put(
        f"{BASE}/v1/agents/kv/hello",
        json={"value": "world"},
        headers=HEADERS,
        timeout=30.0,
    )
    set_resp.raise_for_status()

    get_resp = httpx.get(f"{BASE}/v1/agents/kv/hello", headers=HEADERS, timeout=30.0)
    get_resp.raise_for_status()
    result = get_resp.json()
    print(f"Stored: {result.get('value')}")


if __name__ == "__main__":
    main()
