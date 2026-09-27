import type { Question, SystemOneResponse } from "./types";

// Same-origin path: the playground is served by the API server it talks to.
const ENDPOINT = "/v1/systemone";

export type Outcome =
  | { ok: true; response: SystemOneResponse; serverMs: number | null; totalMs: number }
  | { ok: false; kind: "auth" | "rate" | "busy" | "invalid" | "down" | "network"; message: string };

export function requestBody(state: string, questions: Question[]) {
  return {
    state,
    model: "julia-1",
    questions: Object.fromEntries(
      questions.map((question, index) => [questionKey(index), apiQuestion(question)]),
    ),
  };
}

export function questionKey(index: number) {
  return `q${index + 1}`;
}

/** Trim text and drop blank option rows, which the editor keeps for typing. */
export function cleanQuestion(question: Question): Question {
  return {
    ...question,
    instructions: question.instructions.trim(),
    options: question.type === "noul" ? [] : question.options.map((o) => o.trim()).filter(Boolean),
  };
}

function apiQuestion(question: Question) {
  const { type, instructions: text, options: clean } = cleanQuestion(question);
  if (type === "noul") return { type, instructions: text };
  if (type === "score") return { type, instructions: text, criteria: clean };
  // A null description tells the server to use the option itself as the description.
  return { type, instructions: text, criteria: Object.fromEntries(clean.map((o) => [o, null])) };
}

export async function ask(body: object, apiKey: string): Promise<Outcome> {
  const started = performance.now();
  let response: Response;
  try {
    response = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch {
    return { ok: false, kind: "network", message: "Couldn't reach the server. Check your connection and try again." };
  }
  const totalMs = performance.now() - started;
  const payload = await response.json().catch(() => null);
  if (response.ok) {
    return { ok: true, response: payload as SystemOneResponse, serverMs: serverTiming(response), totalMs };
  }
  const wait = response.headers.get("Retry-After");
  switch (response.status) {
    case 401:
      return { ok: false, kind: "auth", message: "This server needs an API key." };
    case 429:
      return { ok: false, kind: "rate", message: `You're going a bit fast. Try again in ${wait ?? "a few"} seconds.` };
    case 529:
      return { ok: false, kind: "busy", message: "Julia-1 is busy with other requests. Try again in a moment." };
    case 422:
      return { ok: false, kind: "invalid", message: describeInvalid(payload?.detail) };
    case 503:
      return { ok: false, kind: "down", message: "The model is still starting up. Try again in a minute." };
    default:
      return { ok: false, kind: "down", message: "Something went wrong on the server. Try again." };
  }
}

function serverTiming(response: Response): number | null {
  const match = response.headers.get("Server-Timing")?.match(/dur=([\d.]+)/);
  return match ? Number(match[1]) : null;
}

/** Turn FastAPI's validation details into a sentence that points at the question. */
function describeInvalid(detail: unknown): string {
  if (typeof detail === "string") {
    if (detail.includes("48-token")) return "One of the options is too long. Keep each option to a short phrase.";
    if (detail.toLowerCase().includes("token")) return "The text and questions are too long for Julia-1. Try shortening them.";
    return detail;
  }
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const key = first.loc?.find((part) => typeof part === "string" && /^q\d+$/.test(part));
    const where = typeof key === "string" ? `Question ${key.slice(1)}: ` : "";
    return `${where}${first.msg ?? "Something in the request isn't valid."}`;
  }
  return "Something in the request isn't valid.";
}

export function curlCommand(body: object, origin: string) {
  return [
    `curl ${origin}${ENDPOINT} \\`,
    `  -H 'Content-Type: application/json' \\`,
    `  -d '${JSON.stringify(body, null, 2).replaceAll("'", "'\\''")}'`,
  ].join("\n");
}
