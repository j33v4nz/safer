export class GuardBlocked extends Error {
  constructor(result) { super(`Prompt blocked by local Safer policy (${Math.round(Math.max(...Object.values(result.scores).map((s) => s.probability)) * 100)}% risk)`); this.name = "GuardBlocked"; this.result = result; }
}

export async function inspect(prompt, { endpoint = process.env.SAFER_ENDPOINT || "http://127.0.0.1:8787", token = process.env.SAFER_TOKEN, source = "typescript-sdk", signal } = {}) {
  if (!token) throw new Error("SAFER_TOKEN is required");
  const response = await fetch(`${endpoint.replace(/\/$/, "")}/v1/inspect`, { method: "POST", signal, headers: { "content-type": "application/json", "x-safer-token": token }, body: JSON.stringify({ text: prompt, source }) });
  if (!response.ok) throw new Error(`Safer service unavailable (${response.status})`);
  return response.json();
}

export async function requireAllowed(prompt, options) {
  const result = await inspect(prompt, options);
  if (result.decision !== "allow") throw new GuardBlocked(result);
  return result;
}
