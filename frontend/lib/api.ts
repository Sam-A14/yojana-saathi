import { clearSession } from "./session";
import { trackRequest } from "./slow-requests";
import type {
  AlertItem,
  Alerts,
  DocumentInfo,
  Eligibility,
  Family,
  Household,
  HouseholdFields,
  Me,
  Member,
  MemberInput,
  SchemeSummary,
  SessionToken,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// status 0 means the request never reached the server (offline, or the server is still waking up).
// `code` is the machine-readable reason the sign-in endpoints send (detail.code), e.g. "invalid_code".
// `timedOut` is true when we gave up waiting (see WRITE_TIMEOUT_MS): the answer may still be coming.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code: string | null = null,
    readonly attemptsLeft: number | null = null,
    readonly timedOut = false,
  ) {
    super(message);
  }
}

export type ErrorKind = "network" | "timeout" | "signedOut" | "denied" | "limit" | "generic";

// What the screen should say. One place, so every page words the same problem the same way.
export function errorKind(error: unknown): ErrorKind {
  if (!(error instanceof ApiError)) return "generic";
  if (error.status === 0) return error.timedOut ? "timeout" : "network";
  if (error.status === 401) return "signedOut"; // not signed in, or the session ended
  if (error.status === 403) return "denied"; // signed in, but not this household
  if (error.status === 409) return "limit";
  return "generic";
}

type Options = { method?: string; token?: string; body?: unknown };

// FastAPI sends {"detail": "text"} for most errors and {"detail": {"code", "message", ...}} for
// the sign-in ones. Anything else (a 422 list, an HTML page) just has no code.
async function problemFrom(response: Response): Promise<ApiError> {
  let code: string | null = null;
  let attemptsLeft: number | null = null;
  try {
    const detail = ((await response.json()) as { detail?: unknown }).detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const d = detail as { code?: unknown; attempts_left?: unknown };
      if (typeof d.code === "string") code = d.code;
      if (typeof d.attempts_left === "number") attemptsLeft = d.attempts_left;
    }
  } catch {
    // Not JSON: keep the plain status.
  }
  return new ApiError(response.status, response.statusText, code, attemptsLeft);
}

// A save that gets no answer at all (a connection that went stale while the page sat open) used to
// leave "Saving…" on the screen forever, because fetch has no time limit of its own. Every request
// that changes something now gives up after this long.
//
// Reads (GET) are NOT timed out: the first request after the host has slept can legitimately take up
// to a minute, and the "waking up" banner promises exactly that. Giving up at 15 s would turn a slow
// start into an error. `limits` is an object so a test can shorten it.
export const limits = { writeTimeoutMs: 15_000 };

// PATCH and PUT set fields to the values sent, so doing one twice leaves the same result: safe to
// repeat. POST (adds something), DELETE and the rest are never repeated automatically, because a
// first attempt that "timed out" may still have arrived.
const RETRIED_AFTER_TIMEOUT = new Set(["PATCH", "PUT"]);

/** fetch that gives up after `ms` (null = wait as long as it takes). True in `timedOut` when it was
 * our timer, not the network, that ended it. */
async function fetchWithin(
  url: string,
  init: RequestInit,
  ms: number | null,
): Promise<{ response: Response } | { timedOut: true }> {
  if (ms === null) return { response: await fetch(url, init) };
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, ms);
  try {
    return { response: await fetch(url, { ...init, signal: controller.signal }) };
  } catch (error) {
    if (timedOut) return { timedOut: true };
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function request<T>(path: string, { method = "GET", token, body }: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const finished = trackRequest(); // shows "waking up the server" if this takes over 4 seconds
  try {
    const init: RequestInit = {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    };
    const limit = method === "GET" ? null : limits.writeTimeoutMs;
    const attempts = RETRIED_AFTER_TIMEOUT.has(method) ? 2 : 1;
    let response: Response | undefined;
    for (let attempt = 1; response === undefined; attempt++) {
      let outcome: Awaited<ReturnType<typeof fetchWithin>>;
      try {
        outcome = await fetchWithin(`${API_URL}${path}`, init, limit);
      } catch {
        throw new ApiError(0, "Could not reach the server.");
      }
      if ("response" in outcome) {
        response = outcome.response;
      } else if (attempt >= attempts) {
        throw new ApiError(0, "The server did not answer in time.", null, null, true);
      } // else: stalled once, so try again on a fresh connection
    }
    if (!response.ok) {
      // A request that carried a session and got 401: that session is over. Forget it, so every
      // screen sends the person to sign in instead of retrying with a dead token.
      if (response.status === 401 && token) clearSession();
      throw await problemFrom(response);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } finally {
    finished();
  }
}

/** Wake the backend while the person is still reading the home page, so the first real request
 * is not the slow one. Fire and forget: no banner, and a failure is ignored. */
export function warmUpServer() {
  fetch(`${API_URL}/health`).catch(() => undefined);
}

const household = (family: Family) => `/households/${family.id}`;

export const api = {
  listDocuments: () => request<DocumentInfo[]>("/documents"),
  // Public: the schemes we check, with no family involved. Used by the home page.
  listSchemes: () => request<SchemeSummary[]>("/schemes"),

  // Sign in (decision 019). The first two need no session.
  requestCode: (email: string, language: "en" | "hi") =>
    request<{ status: "sent"; expires_in_minutes: number }>("/auth/request-code", {
      method: "POST",
      body: { email, language },
    }),
  verifyCode: (email: string, code: string) =>
    request<SessionToken>("/auth/verify", { method: "POST", body: { email, code } }),
  // The ID token Google's button gave the page. The server checks it (decision 027).
  signInWithGoogle: (credential: string, language: "en" | "hi") =>
    request<SessionToken>("/auth/google", { method: "POST", body: { credential, language } }),
  getMe: (token: string) => request<Me>("/me", { token }),
  signOut: (token: string) => request<void>("/auth/sign-out", { method: "POST", token }),
  // Delete my data: the user, their email, and everything under them.
  deleteMe: (token: string) => request<void>("/me", { method: "DELETE", token }),

  createHousehold: (token: string, data: HouseholdFields) =>
    request<Household>("/households", { method: "POST", token, body: data }),
  getHousehold: (family: Family) => request<Household>(household(family), { token: family.token }),

  // PATCH: only the fields sent change, and null clears an answer ("not sure").
  updateHousehold: (family: Family, data: HouseholdFields) =>
    request<Household>(household(family), { method: "PATCH", token: family.token, body: data }),
  getEligibility: (family: Family) =>
    request<Eligibility>(`${household(family)}/eligibility`, { token: family.token }),

  // "What's new for your family": made by the daily job, read and marked read here.
  getAlerts: (family: Family) =>
    request<Alerts>(`${household(family)}/alerts`, { token: family.token }),
  markAlertRead: (family: Family, alertId: number) =>
    request<AlertItem>(`${household(family)}/alerts/${alertId}/read`, { method: "POST", token: family.token }),
  markAllAlertsRead: (family: Family) =>
    request<Alerts>(`${household(family)}/alerts/read-all`, { method: "POST", token: family.token }),

  listMembers: (family: Family) =>
    request<Member[]>(`${household(family)}/members`, { token: family.token }),
  addMember: (family: Family, data: MemberInput) =>
    request<Member>(`${household(family)}/members`, {
      method: "POST",
      token: family.token,
      body: data,
    }),
  // PATCH: only the fields sent change, so the exclusion answers survive editing a person.
  updateMember: (family: Family, memberId: string, data: Partial<MemberInput>) =>
    request<Member>(`${household(family)}/members/${memberId}`, {
      method: "PATCH",
      token: family.token,
      body: data,
    }),
  deleteMember: (family: Family, memberId: string) =>
    request<void>(`${household(family)}/members/${memberId}`, {
      method: "DELETE",
      token: family.token,
    }),
  // PUT: the full picture. A code that is left out becomes "not answered" again.
  setDocuments: (family: Family, memberId: string, documents: Record<string, boolean>) =>
    request<{ documents: Record<string, boolean> }>(
      `${household(family)}/members/${memberId}/documents`,
      { method: "PUT", token: family.token, body: { documents } },
    ),
};
