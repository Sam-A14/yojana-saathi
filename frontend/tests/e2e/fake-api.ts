import { randomBytes, randomUUID } from "node:crypto";
import type { Page, Route } from "@playwright/test";
import eligibility from "../fixtures/eligibility.json";
import emptyResults from "../fixtures/eligibility-empty.json";
import missingHome from "../fixtures/eligibility-missing-home.json";

// A sample family for whom no scheme may fit, is close, needs an answer or is blocked (each person
// only has schemes that do not fit, which are counted, not listed).
export const EMPTY_RESULTS = emptyResults;

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
const HOME_DEFAULTS = { state: null, district: null, area_type: null, house_type: null, income_band: null, category: null, is_bpl: null };

type Fixture = { members: ({ nickname: string } & Record<string, unknown>)[] } & Record<string, unknown>;

// The real API always sends every fact about a person, as null when it was never answered.
const UNANSWERED_FACTS = Object.fromEntries(
  [
    "birth_year", "gender", "marital_status", "occupation", "education", "is_student", "current_study_level", "disability",
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
    const own = [ignoapsFor(member, household), pmayGFor(household, member)].filter(Boolean);
    const schemes = (sample.schemes as { scheme: { slug: string } }[]).filter(
      (s) => s.scheme.slug !== "ignoaps" && s.scheme.slug !== "pmay-g",
    );
    return {
      ...sample,
      schemes: [...own, ...schemes],
      member_id: member.id,
      nickname: member.nickname,
      relation: member.relation,
    };
  });
  return { ...fixture, household_id: householdId, members };
}

// IGNOAPS is decided by two rules: the family is below the poverty line (the household's yes/no
// answer) and the person is 60 or over. This fake mirrors them so a test can add a person and see
// the scheme appear. The real engine's answer for the same facts is proved in the backend test
// `test_a_person_added_after_setup_is_checked_straight_away`.
function ignoapsFor(member: Json, household: StoredHousehold) {
  const born = member.birth_year as number | null | undefined;
  const age = born ? new Date().getFullYear() - born : null;
  if (household.fields.is_bpl !== true || age === null || age < 61) return null; // 61: certainly 60 or over
  return {
    scheme: {
      slug: "ignoaps",
      name_en: "Indira Gandhi National Old Age Pension Scheme",
      name_hi: "इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन योजना",
      level: "central",
      state: null,
      category: "pension",
      official_url: "https://www.myscheme.gov.in/schemes/nsap-ignoaps",
      benefit_text_en: "₹200 a month from the Centre up to age 79, ₹500 from age 80. The State Government may add more on top.",
      benefit_text_hi: null,
      not_checked_en: [],
      not_checked_hi: null,
      deadline_start: null,
      deadline_end: null,
      verified: true,
      verified_at: "2026-11-27T00:00:00Z",
    },
    status: "eligible",
    reasons: [],
    passed_rules: [
      { rule: { field: "is_bpl", op: "is_true" }, fields: ["is_bpl"], matched_members: [], fixable: false, reasons: [] },
      { rule: { field: "age", op: "gte", value: 60 }, fields: ["age"], matched_members: [], fixable: false, reasons: [] },
    ],
    failed_rules: [],
    unknown_rules: [],
    excluded_by: [],
    missing_documents: [],
  };
}

// PMAY-Gramin is decided here by two household answers: the family lives in a village, and its
// house is kutcha or it has none. This fake mirrors those two rules so a test can change the
// answers on the edit screen and watch the scheme come and go. The real engine's answer for the
// same facts is proved in the backend tests (a rule on area_type and house_type).
function pmayGFor(household: StoredHousehold, member: StoredMember) {
  const { area_type, house_type } = household.fields;
  if (area_type !== "rural" || (house_type !== "no_house" && house_type !== "kutcha")) return null;
  return {
    scheme: {
      slug: "pmay-g",
      name_en: "Pradhan Mantri Awaas Yojana - Gramin",
      name_hi: "प्रधानमंत्री आवास योजना – ग्रामीण",
      level: "central",
      state: null,
      category: "housing",
      official_url: "https://www.myscheme.gov.in/schemes/pmay-g",
      benefit_text_en: "Money to build a pucca house: ₹1,20,000 in plain areas, or ₹1,30,000 in hilly and difficult areas.",
      benefit_text_hi: null,
      not_checked_en: [],
      not_checked_hi: null,
      for_whole_family: true, // its rules are about the house, the village and "no member pays income tax"
      deadline_start: null,
      deadline_end: null,
      verified: true,
      verified_at: "2026-11-28T00:00:00Z",
    },
    status: "eligible",
    reasons: [],
    passed_rules: [
      { rule: { field: "area_type", op: "eq", value: "rural" }, fields: ["area_type"], matched_members: [], fixable: false, reasons: [] },
      { rule: { field: "house_type", op: "in", value: ["no_house", "kutcha"] }, fields: ["house_type"], matched_members: [], fixable: false, reasons: [] },
    ],
    failed_rules: [],
    unknown_rules: [],
    excluded_by: [],
    // Papers are about the person: a person who said they have no Aadhaar card is missing it.
    missing_documents:
      member.documents.aadhaar_card === false
        ? [
            {
              code: "aadhaar_card",
              name_en: "Aadhaar card",
              name_hi: "आधार कार्ड",
              how_to_get_en: null,
              how_to_get_hi: null,
              official_link: null,
              state: "no",
            },
          ]
        : [],
  };
}

// What Google's script (accounts.google.com/gsi/client) does, reduced to a plain button. The test
// never talks to Google. Tapping the button hands the page the credential in window.__fakeCredential
// (default: a token for person@example.com), like Google's real button hands over an ID token. The
// options the page asked for are kept in window.__gsiButtonOptions so a test can look at them.
export const GOOGLE_SCRIPT_URL = "https://accounts.google.com/gsi/client";
const FAKE_GOOGLE_SCRIPT = `
window.google = { accounts: { id: {
  initialize(config) { window.__gsiConfig = config; },
  renderButton(parent, options) {
    window.__gsiButtonOptions = options;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = options.locale === "hi" ? "Google के साथ जारी रखें" : "Continue with Google";
    button.style.cssText = "width:" + options.width + "px;height:40px;font-size:14px";
    button.onclick = () => window.__gsiConfig.callback({
      credential: window.__fakeCredential || "fake-google:person@example.com",
    });
    parent.appendChild(button);
  },
} } };
`;

/** The credential a test puts in window.__fakeCredential to be "signed in as" this address. */
export const googleCredentialFor = (email: string) => `fake-google:${email}`;

export class FakeApi {
  households = new Map<string, StoredHousehold>();
  /** Signed-up people, by email. */
  users = new Map<string, StoredUser>();
  /** Session token -> email, like the real API's sessions. */
  sessions = new Map<string, string>();
  /** The code last "emailed" to each address, and how many wrong guesses it has had. */
  codes = new Map<string, { code: string; wrong: number }>();
  /** Make POST /auth/google answer 503 google_unavailable, like a backend with no GOOGLE_CLIENT_ID. */
  googleUnavailable = false;
  /** Make request-code fail like the real API (429 too_many_codes, 503 busy...). */
  requestCodeFailure: { status: number; code: string } | null = null;
  private counter = 0;
  /** Milliseconds every answer is held back (a sleeping server waking up). */
  latency = 0;
  /** Which sample family's results the eligibility route returns. */
  fixture: Fixture = eligibility;
  /** The family's "What's new" list, newest first. Empty unless a test fills it. */
  alerts: { id: number; type: string; payload: Json; created_at: string; read: boolean }[] = [];
  /** While true, every request fails as if the phone had no internet. */
  offline = false;
  /** Milliseconds the eligibility answer is held back (a slow server waking up). */
  eligibilityDelay = 0;
  /** Every request the page made, so a test can check what was sent. */
  requests: { method: string; path: string; authorization: string | null; body: unknown }[] = [];

  async install(page: Page) {
    await page.route(`${API}/**`, (route) => this.handle(route));
    await page.route(GOOGLE_SCRIPT_URL, (route) =>
      route.fulfill({ contentType: "application/javascript", body: FAKE_GOOGLE_SCRIPT }),
    );
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
  seedMembers(householdId: string, who: number | string[], relations: Record<string, string> = {}) {
    const household = this.households.get(householdId);
    const names = typeof who === "number" ? Array.from({ length: who }, (_, i) => `Person ${i + 1}`) : who;
    for (const name of names) {
      household?.members.push({
        id: randomUUID(),
        household_id: householdId,
        ...UNANSWERED_FACTS,
        nickname: name,
        relation: relations[name] ?? "other",
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

    if (path === "/auth/google") {
      if (this.googleUnavailable) {
        return reply(503, { detail: { code: "google_unavailable", message: "no" } });
      }
      const credential = String((body as Json).credential);
      if (!credential.startsWith("fake-google:")) {
        return reply(401, { detail: { code: "invalid_google_token", message: "no" } });
      }
      const { token } = this.seedSession(credential.slice("fake-google:".length).toLowerCase());
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

    // The "What's new" list (backend/app/api/alerts.py): a test fills `api.alerts` first.
    const alertsRoute = /^\/households\/([^/]+)\/alerts(?:\/(read-all)|\/(\d+)\/read)?$/.exec(path);
    if (alertsRoute) {
      const owner = this.households.get(alertsRoute[1]);
      if (!owner || owner.owner !== email) return reply(403, { detail: "No such household for your account." });
      if (alertsRoute[2]) this.alerts.forEach((a) => (a.read = true));
      if (alertsRoute[3]) {
        const one = this.alerts.find((a) => a.id === Number(alertsRoute[3]));
        if (!one) return reply(404, { detail: "No such alert." });
        one.read = true;
        return reply(200, one);
      }
      return reply(200, { unread: this.alerts.filter((a) => !a.read).length, alerts: this.alerts });
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
