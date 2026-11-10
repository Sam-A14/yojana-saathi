import { randomBytes, randomUUID } from "node:crypto";
import type { Page, Route } from "@playwright/test";
import eligibility from "../fixtures/eligibility.json";
import missingHome from "../fixtures/eligibility-missing-home.json";

// A sample family that has not told us its state, area or income (real engine output).
export const MISSING_HOME = missingHome;

// A tiny stand-in for the real API, kept in the test's memory. It answers the same URLs with the
// same shapes (backend/app/api/), including the 403 for a missing or wrong token, so the
// screens are tested against realistic behaviour.

export const API = "http://localhost:8000";

export const DOCUMENTS = [
  { code: "aadhaar_card", name_en: "Aadhaar card", name_hi: "आधार कार्ड", household_level: false },
  { code: "land_record", name_en: "Land record (Khatauni / Khasra)", name_hi: "भूमि का रिकॉर्ड (खतौनी / खसरा)", household_level: false },
  { code: "income_certificate", name_en: "Income certificate", name_hi: "आय प्रमाण पत्र", household_level: false },
  { code: "spouse_death_certificate", name_en: "Death certificate of husband", name_hi: "पति का मृत्यु प्रमाण पत्र", household_level: false },
  { code: "bank_account_aadhaar_linked", name_en: "Bank account linked to Aadhaar", name_hi: "आधार से जुड़ा बैंक खाता", household_level: false },
  { code: "ration_card", name_en: "Ration card", name_hi: "राशन कार्ड", household_level: true },
  { code: "bpl_card", name_en: "BPL (below poverty line) card", name_hi: "बीपीएल (गरीबी रेखा से नीचे) कार्ड", household_level: true },
];

// GET /schemes: the schemes that appear in the sample eligibility result, once each.
const SCHEMES = [
  ...new Map(
    (eligibility as { members: { schemes: { scheme: { slug: string } }[] }[] }).members
      .flatMap((m) => m.schemes)
      .map((s) => [s.scheme.slug, s.scheme]),
  ).values(),
];

type Json = Record<string, unknown>;

// The real API always sends all five answers about a home, null when never answered.
const HOME_DEFAULTS = { state: null, district: null, area_type: null, income_band: null, category: null };

type Fixture = { members: ({ nickname: string } & Record<string, unknown>)[] } & Record<string, unknown>;

// The real API always sends every fact about a person, as null when it was never answered.
const UNANSWERED_FACTS = Object.fromEntries(
  [
    "birth_year", "gender", "marital_status", "occupation", "education", "is_student", "disability",
    "owns_cultivable_land", "is_remarried", "paid_income_tax_last_year", "govt_employee",
    "pension_band", "is_registered_professional", "holds_constitutional_post",
  ].map((name) => [name, null]),
);
type StoredMember = Json & { id: string; documents: Record<string, boolean> };
type StoredHousehold = { fields: Json; owner: string; members: StoredMember[] };
type StoredUser = { householdId: string | null };

// The answer the real engine gave for a sample family (generated from the backend with the seeded
// schemes plus two example ones). Each person in the household gets the results of the sample
// person with the same nickname, or of one in the same position.
function eligibilityFor(fixture: Fixture, householdId: string, household: StoredHousehold) {
  const members = household.members.map((member, index) => {
    const sample =
      fixture.members.find((m) => m.nickname === member.nickname) ??
      fixture.members[index % fixture.members.length];
    return { ...sample, member_id: member.id, nickname: member.nickname };
  });
  return { ...fixture, household_id: householdId, members };
}

export class FakeApi {
  households = new Map<string, StoredHousehold>();
  /** Signed-up people, by email. */
  users = new Map<string, StoredUser>();
  /** Session token -> email, like the real API's sessions. */
  sessions = new Map<string, string>();
  /** The code last "emailed" to each address, and how many wrong guesses it has had. */
  codes = new Map<string, { code: string; wrong: number }>();
  /** Make request-code fail like the real API (429 too_many_codes, 503 busy...). */
  requestCodeFailure: { status: number; code: string } | null = null;
  private counter = 0;
  /** Milliseconds every answer is held back (a sleeping server waking up). */
  latency = 0;
  /** Which sample family's results the eligibility route returns. */
  fixture: Fixture = eligibility;
  /** While true, every request fails as if the phone had no internet. */
  offline = false;
  /** Milliseconds the eligibility answer is held back (a slow server waking up). */
  eligibilityDelay = 0;
  /** Every request the page made, so a test can check what was sent. */
  requests: { method: string; path: string; authorization: string | null; body: unknown }[] = [];

  async install(page: Page) {
    await page.route(`${API}/**`, (route) => this.handle(route));
  }

  /** Someone who is signed in but has not set up a household yet. Returns their session token. */
  seedSession(email = `person${++this.counter}@example.com`): { email: string; token: string } {
    this.users.set(email, this.users.get(email) ?? { householdId: null });
    const token = randomBytes(32).toString("base64url");
    this.sessions.set(token, email);
    return { email, token };
  }

  /** A signed-in person with a household that already exists, as if set up earlier. `token` is
   * their session token; `id` the household's id. */
  seedHousehold(fields: Json = { state: "UP" }, email = `family${++this.counter}@example.com`) {
    const { token } = this.seedSession(email);
    const id = randomUUID();
    this.households.set(id, { fields: { ...HOME_DEFAULTS, ...fields }, owner: email, members: [] });
    this.users.get(email)!.householdId = id;
    return { id, token, email };
  }

  /** The text a phone keeps in localStorage when this person is signed in. */
  storedSession(family: { token: string; email: string; id?: string | null }) {
    return JSON.stringify({ token: family.token, email: family.email, householdId: family.id ?? null });
  }

  /** The code in the last email sent to this address. */
  lastCode(email: string): string {
    return this.codes.get(email)!.code;
  }

  /** Give an existing household members, as if they were added earlier: a number of anonymous
   * people, or a list of names. */
  seedMembers(householdId: string, who: number | string[]) {
    const household = this.households.get(householdId);
    const names = typeof who === "number" ? Array.from({ length: who }, (_, i) => `Person ${i + 1}`) : who;
    for (const name of names) {
      household?.members.push({
        id: randomUUID(),
        household_id: householdId,
        ...UNANSWERED_FACTS,
        nickname: name,
        relation: "other",
        documents: {},
      });
    }
  }

  private cors(origin: string | undefined) {
    return {
      "access-control-allow-origin": origin ?? "*",
      "access-control-allow-headers": "Authorization, Content-Type",
      "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE",
    };
  }

  private async handle(route: Route) {
    const request = route.request();
    if (this.offline) return route.abort("internetdisconnected");
    const headers = this.cors(request.headers()["origin"]);
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers });

    const path = new URL(request.url()).pathname;
    const body = request.postDataJSON() ?? null;
    const authorization = request.headers()["authorization"] ?? null;
    this.requests.push({ method: request.method(), path, authorization, body });

    const reply = (status: number, data?: unknown) =>
      route.fulfill({
        status,
        headers,
        ...(data === undefined ? {} : { contentType: "application/json", body: JSON.stringify(data) }),
      });

    if (this.latency) await new Promise((done) => setTimeout(done, this.latency));
    if (path === "/health") return reply(200, { status: "ok" });
    if (path === "/documents") return reply(200, DOCUMENTS);
    if (path === "/schemes") return reply(200, SCHEMES);

    // --- sign-in (backend/app/api/auth.py) ---
    if (path === "/auth/request-code") {
      if (this.requestCodeFailure) {
        const { status, code } = this.requestCodeFailure;
        return reply(status, { detail: { code, message: code } });
      }
      const email = String((body as Json).email).trim().toLowerCase();
      this.codes.set(email, { code: "482913", wrong: 0 });
      return reply(202, { status: "sent", expires_in_minutes: 10 });
    }
    if (path === "/auth/verify") {
      const { email, code } = body as { email: string; code: string };
      const entry = this.codes.get(email);
      if (!entry || entry.wrong >= 5) {
        return reply(401, { detail: { code: entry ? "too_many_attempts" : "invalid_code", message: "no" } });
      }
      if (entry.code !== code) {
        entry.wrong += 1;
        return reply(401, { detail: { code: "invalid_code", message: "no", attempts_left: 5 - entry.wrong } });
      }
      this.codes.delete(email);
      const { token } = this.seedSession(email);
      return reply(200, { access_token: token, expires_at: "2026-12-10T00:00:00Z" });
    }

    // Everything below needs a signed-in person: 401 otherwise, like the real API.
    const email = this.sessions.get((authorization ?? "").replace(/^Bearer /, ""));
    if (!email) return reply(401, { detail: "Please sign in." });
    const user = this.users.get(email)!;

    if (path === "/me" && request.method() === "GET") {
      return reply(200, { email, language: "en", household_id: user.householdId });
    }
    if (path === "/me" && request.method() === "DELETE") {
      if (user.householdId) this.households.delete(user.householdId);
      this.users.delete(email);
      for (const [token, owner] of this.sessions) if (owner === email) this.sessions.delete(token);
      return reply(204);
    }
    if (path === "/auth/sign-out") {
      this.sessions.delete(authorization!.replace(/^Bearer /, ""));
      return reply(204);
    }
    if (path === "/households" && request.method() === "POST") {
      if (user.householdId) return reply(409, { detail: "You already have a household." });
      const id = randomUUID();
      this.households.set(id, { fields: { ...HOME_DEFAULTS, ...body }, owner: email, members: [] });
      user.householdId = id;
      return reply(201, { id, ...HOME_DEFAULTS, ...body });
    }

    const match = /^\/households\/([^/]+)(?:\/members(?:\/([^/]+))?(\/documents)?|\/eligibility)?$/.exec(path);
    const household = match ? this.households.get(match[1]) : undefined;
    // Same answer for "no such household" and "someone else's", like the real API.
    if (!match || !household || household.owner !== email) {
      return reply(403, { detail: "No such household for your account." });
    }
    const [, id, memberId, documents] = match;
    const isMembers = path.includes("/members");

    if (path.endsWith("/eligibility")) {
      if (this.eligibilityDelay) await new Promise((done) => setTimeout(done, this.eligibilityDelay));
      return reply(200, eligibilityFor(this.fixture, id, household));
    }
    if (!isMembers) {
      if (request.method() === "PATCH") Object.assign(household.fields, body); // only what was sent changes
      return reply(200, { id, ...household.fields });
    }
    if (!memberId) {
      if (request.method() === "GET") return reply(200, household.members);
      const member: StoredMember = { ...UNANSWERED_FACTS, ...(body as Json), id: randomUUID(), household_id: id, documents: {} };
      household.members.push(member);
      return reply(201, member);
    }
    const member = household.members.find((m) => m.id === memberId);
    if (!member) return reply(404, { detail: "No such member in this household." });
    if (documents) {
      member.documents = (body as { documents: Record<string, boolean> }).documents;
      return reply(200, { documents: member.documents });
    }
    if (request.method() === "DELETE") {
      household.members = household.members.filter((m) => m.id !== memberId);
      return reply(204);
    }
    Object.assign(member, body); // PATCH: only the fields sent change
    return reply(200, member);
  }
}
