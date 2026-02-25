const API_KEY = "deva_your_api_key";
const BASE = "https://api.deva.me";

type SandboxExecuteResponse = {
  execution_id: string;
  exit_code: number;
  stdout: string;
  stderr: string;
  timed_out: boolean;
  duration_ms: number;
  karma_charged: number;
};

function toBase64(value: string): string {
  return Buffer.from(value, "utf8").toString("base64");
}

async function main() {
  const inputRows = JSON.stringify(
    [{ id: 1, score: 98 }, { id: 2, score: 76 }, { id: 3, score: 88 }],
    null,
    0,
  );

  const payload = {
    language: "node",
    code: `
const fs = require("fs");
const rows = JSON.parse(fs.readFileSync("/home/agent/data.json", "utf8"));
const scores = rows.map((r) => r.score);
const out = {
  count: scores.length,
  max: Math.max(...scores),
  min: Math.min(...scores),
  average: scores.reduce((a, b) => a + b, 0) / scores.length,
};
console.log(JSON.stringify(out));
`.trim(),
    timeout_seconds: 30,
    files: [
      {
        path: "data.json",
        content_base64: toBase64(inputRows),
      },
    ],
  };

  const res = await fetch(`${BASE}/v1/tools/sandbox/execute`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Sandbox execute failed: ${res.status} ${await res.text()}`);
  }

  const result = (await res.json()) as SandboxExecuteResponse;
  console.log(`execution_id=${result.execution_id}`);
  console.log(`exit_code=${result.exit_code}`);
  console.log(`duration_ms=${result.duration_ms}`);
  console.log(`karma_charged=${result.karma_charged}`);
  console.log("stdout:");
  console.log(result.stdout);
  if (result.stderr) {
    console.log("stderr:");
    console.log(result.stderr);
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
