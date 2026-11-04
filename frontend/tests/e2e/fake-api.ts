import { randomBytes, randomUUID } from "node:crypto";
import type { Page, Route } from "@playwright/test";

// A tiny stand-in for the real API, kept in the test's memory. It answers the same URLs with the
// same shapes (backend/app/api/), including the 403 for a missing or wrong token, so the
// screens are tested against realistic behaviour.

export const API = "http://localhost:8000";

export const DOCUMENTS = [
  { code: "aadhaar_card", name_en: "Aadhaar card", name_hi: "आधार कार्ड", household_level: false },
  { code: "land_record", name_en: "Land record (Khatauni / Khasra)", name_hi: "भूमि का रिकॉर्ड (खतौनी / खसरा)", household_level: false },
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

export class FakeApi {
  households = new Map<string, StoredHousehold>();
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

  /** Give an existing household `count` members, as if they were added earlier. */
  seedMembers(householdId: string, count: number) {
    const household = this.households.get(householdId);
    for (let i = 1; i <= count; i++) {
      household?.members.push({
        id: randomUUID(),
        household_id: householdId,
        ...UNANSWERED_FACTS,
        nickname: `Person ${i}`,
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

    const match = /^\/households\/([^/]+)(?:\/members(?:\/([^/]+))?(\/documents)?)?$/.exec(path);
    const household = match ? this.households.get(match[1]) : undefined;
    // Same answer for "no such household" and "wrong token", like the real API.
    if (!match || !household || authorization !== `Bearer ${household.token}`) {
      return reply(403, { detail: "Missing or invalid access token for this household." });
    }
    const [, id, memberId, documents] = match;
    const isMembers = path.includes("/members");

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
