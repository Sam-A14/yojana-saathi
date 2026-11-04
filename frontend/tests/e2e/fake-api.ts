import { randomBytes, randomUUID } from "node:crypto";
import type { Page, Route } from "@playwright/test";
import eligibility from "../fixtures/eligibility.json";

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

type Json = Record<string, unknown>;

// The real API always sends every fact about a person, as null when it was never answered.
const UNANSWERED_FACTS = Object.fromEntries(
  [
    "birth_year", "gender", "marital_status", "occupation", "education", "is_student", "disability",
    "owns_cultivable_land", "is_remarried", "paid_income_tax_last_year", "govt_employee",
    "pension_band", "is_registered_professional", "holds_constitutional_post",
  ].map((name) => [name, null]),
);
type StoredMember = Json & { id: string; documents: Record<string, boolean> };
type StoredHousehold = { fields: Json; token: string; members: StoredMember[] };

// The answer the real engine gave for a sample family (generated from the backend with the seeded
// schemes plus two example ones). Each person in the household gets the results of the sample
// person with the same nickname, or of one in the same position.
function eligibilityFor(householdId: string, household: StoredHousehold) {
  const members = household.members.map((member, index) => {
    const sample =
      eligibility.members.find((m) => m.nickname === member.nickname) ??
      eligibility.members[index % eligibility.members.length];
    return { ...sample, member_id: member.id, nickname: member.nickname };
  });
  return { ...eligibility, household_id: householdId, members };
}

export class FakeApi {
  households = new Map<string, StoredHousehold>();
  /** While true, every request fails as if the phone had no internet. */
  offline = false;
  /** Milliseconds the eligibility answer is held back (a slow server waking up). */
  eligibilityDelay = 0;
  /** Every request the page made, so a test can check what was sent. */
  requests: { method: string; path: string; authorization: string | null; body: unknown }[] = [];

  async install(page: Page) {
    await page.route(`${API}/**`, (route) => this.handle(route));
  }

  /** A household that already exists, as if set up earlier. Returns its family code. */
  seedHousehold(): { id: string; token: string; code: string } {
    const id = randomUUID();
    const token = randomBytes(32).toString("base64url");
    this.households.set(id, { fields: { state: "UP" }, token, members: [] });
    return { id, token, code: `${id}.${token}` };
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

    if (path === "/documents") return reply(200, DOCUMENTS);
    if (path === "/households" && request.method() === "POST") {
      const id = randomUUID();
      const token = randomBytes(32).toString("base64url");
      this.households.set(id, { fields: { ...body }, token, members: [] });
      return reply(201, { id, ...body, access_token: token, token_notice: "Save this token." });
    }

    const match = /^\/households\/([^/]+)(?:\/members(?:\/([^/]+))?(\/documents)?|\/eligibility)?$/.exec(path);
    const household = match ? this.households.get(match[1]) : undefined;
    // Same answer for "no such household" and "wrong token", like the real API.
    if (!match || !household || authorization !== `Bearer ${household.token}`) {
      return reply(403, { detail: "Missing or invalid access token for this household." });
    }
    const [, id, memberId, documents] = match;
    const isMembers = path.includes("/members");

    if (path.endsWith("/eligibility")) {
      if (this.eligibilityDelay) await new Promise((done) => setTimeout(done, this.eligibilityDelay));
      return reply(200, eligibilityFor(id, household));
    }
    if (!isMembers && request.method() === "DELETE") {
      this.households.delete(id);
      return reply(204);
    }
    if (!isMembers) return reply(200, { id, ...household.fields });
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
