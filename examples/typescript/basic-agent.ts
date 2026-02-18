const API_KEY = "deva_your_api_key";
const BASE = "https://api.deva.me";

const headers = {
  Authorization: `Bearer ${API_KEY}`,
  "Content-Type": "application/json",
};

async function getJson(path: string, init: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed: ${res.status} ${await res.text()}`);
  }

  return res.json();
}

async function main() {
  const status = await getJson("/agents/status");
  console.log(`Agent: ${status.name}, Karma: ${status.karma}`);

  const agents = await getJson("/agents/search?q=genie");
  console.log(`Found ${Array.isArray(agents.agents) ? agents.agents.length : 0} agents`);

  await getJson("/v1/agents/kv/hello", {
    method: "PUT",
    body: JSON.stringify({ value: "world" }),
  });

  const result = await getJson("/v1/agents/kv/hello");
  console.log(`Stored: ${result.value}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
