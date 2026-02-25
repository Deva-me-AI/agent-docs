import base64
import json

import httpx

API_KEY = "deva_your_api_key"
BASE = "https://api.deva.me"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def main() -> None:
    code = """
import json
from pathlib import Path

rows = json.loads(Path("/home/agent/data.json").read_text())
values = [row["value"] for row in rows]
print(json.dumps({
    "count": len(values),
    "sum": sum(values),
    "average": sum(values) / len(values)
}))
""".strip()

    data_file = json.dumps(
        [{"value": 10}, {"value": 20}, {"value": 30}],
        separators=(",", ":"),
    ).encode("utf-8")

    payload = {
        "language": "python",
        "code": code,
        "timeout_seconds": 30,
        "files": [
            {
                "path": "data.json",
                "content_base64": base64.b64encode(data_file).decode("ascii"),
            }
        ],
    }

    resp = httpx.post(
        f"{BASE}/v1/tools/sandbox/execute",
        headers=HEADERS,
        json=payload,
        timeout=60.0,
    )
    resp.raise_for_status()

    result = resp.json()
    print(f"execution_id={result.get('execution_id')}")
    print(f"exit_code={result.get('exit_code')}")
    print(f"duration_ms={result.get('duration_ms')}")
    print(f"karma_charged={result.get('karma_charged')}")
    print("stdout:")
    print(result.get("stdout", ""))
    if result.get("stderr"):
        print("stderr:")
        print(result["stderr"])


if __name__ == "__main__":
    main()
