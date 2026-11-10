import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// Someone who is already signed in on this phone (as if they signed in earlier).
async function signedIn(page: Page, api: FakeApi, person: { token: string; email: string; id?: string | null }) {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(person)],
  );
}

async function addPerson(page: Page, name: string, birthYear: number, relation?: string) {
  await page.getByLabel("Name or nickname").fill(name);
  if (relation) await page.getByLabel("Who is this to you?").selectOption({ label: relation });
  await page.getByLabel("Year of birth").fill(String(birthYear));
  await page.getByRole("button", { name: "Save this person" }).click();
}

test("a family goes from the home page, through sign-in, to a finished setup", async ({ page, api }) => {
  const thisYear = new Date().getFullYear();

  // Home -> basics
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "See every government benefit your family may be missing" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Start" }).click();

  // Not signed in yet: Start leads to the email sign-in.
  await expect(page).toHaveURL(/\/signin$/);
  await page.getByLabel("Your email address").fill("asha@example.com");
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await page.getByLabel("6-digit code").fill(api.lastCode("asha@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  await expect(page.getByText("Step 1 of 4")).toBeVisible();
  await page.getByLabel("District (optional)").fill("Lucknow");
  await page.getByLabel("Village (rural)").check();
  await page.getByLabel("Yearly income of the whole family").selectOption("1_to_2_lakh");
  await page.getByRole("button", { name: "Continue" }).click();

  // Members: the first form opens by itself, with "Myself" chosen.
  await expect(page.getByText("Step 2 of 4")).toBeVisible();
  await expect(page.getByLabel("Who is this to you?")).toHaveValue("self");
  await addPerson(page, "Asha", 1985);
  await page.getByRole("button", { name: "Add a person" }).click();
  await addPerson(page, "Ramesh", 1960, "Father");
  await page.getByRole("button", { name: "Add a person" }).click();
  await addPerson(page, "Gudiya", thisYear - 10, "Daughter");
  await expect(page.getByRole("listitem")).toHaveCount(3);
  await page.getByRole("button", { name: "Continue" }).click();

  // Documents: family papers once, then each person.
  await expect(page.getByText("Step 3 of 4")).toBeVisible();
  await page.getByRole("group", { name: "Ration card" }).getByLabel("Yes", { exact: true }).check();
  await page.getByRole("group", { name: "BPL (below poverty line) card" }).getByLabel("No", { exact: true }).check();
  await page.getByRole("group", { name: "Aadhaar card" }).first().getByLabel("Yes", { exact: true }).check();
  await page.getByRole("button", { name: "Save and continue" }).click();

  // Exclusion questions: adults only (Gudiya is 10).
  await expect(page.getByText("Step 4 of 4")).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Asha" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Ramesh" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Gudiya" })).toHaveCount(0);
  const ramesh = page.getByRole("region", { name: "For Ramesh" });
  await ramesh.getByRole("group", { name: /income tax/ }).getByLabel("Yes", { exact: true }).check();
  await ramesh.getByRole("group", { name: /government pension/ }).getByLabel("Yes, less than ₹10,000 a month").check();
  await page.getByRole("button", { name: "Finish setup" }).click();

  // The dashboard: the setup answers lead straight to results, one card per person.
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  for (const name of ["Asha", "Ramesh", "Gudiya"]) {
    await expect(page.getByRole("region", { name, exact: true })).toBeVisible();
  }
  const session = JSON.parse((await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY))!);
  expect(session.email).toBe("asha@example.com");
  expect(session.householdId).toBe([...api.households.keys()][0]);

  // What the API was told.
  const household = [...api.households.values()][0];
  expect(household.fields).toMatchObject({ state: "UP", district: "Lucknow", area_type: "rural", income_band: "1_to_2_lakh", category: null });
  const [asha, rameshRow, gudiya] = household.members;
  // A "no" for a family paper is written for everyone; "not sure" answers are left out.
  expect(asha.documents).toEqual({ ration_card: true, bpl_card: false, aadhaar_card: true });
  expect(rameshRow.documents).toEqual({ ration_card: true, bpl_card: false });
  expect(gudiya.documents).toEqual({ ration_card: true, bpl_card: false });
  expect(rameshRow).toMatchObject({ paid_income_tax_last_year: true, pension_band: "below_10k", govt_employee: null });
  expect(asha).toMatchObject({ paid_income_tax_last_year: null, holds_constitutional_post: null });
  // The child was never asked, so nothing was sent for her: only the two adults were updated.
  expect(gudiya.paid_income_tax_last_year).toBeNull();
  expect(api.requests.filter((r) => r.method === "PATCH")).toHaveLength(2);

  // Every call about the household carried the session token, as a Bearer header.
  const token = session.token;
  const protectedCalls = api.requests.filter((r) => r.path.startsWith("/households/"));
  expect(protectedCalls.length).toBeGreaterThan(5);
  for (const call of protectedCalls) expect(call.authorization).toBe(`Bearer ${token}`);
  // The token never appears in a URL.
  expect(api.requests.some((r) => r.path.includes(token))).toBe(false);
});

test("a person can be edited and removed, and needs a name", async ({ page, api }) => {
  await signedIn(page, api, api.seedSession("asha@example.com"));
  await page.goto("/setup/basics");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/setup\/members$/);

  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Please enter a name or nickname.")).toBeVisible();

  await page.getByLabel("Name or nickname").fill("Asha");
  await page.getByLabel("Year of birth").fill("1850");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText(/Enter a year between 1900 and \d{4}/)).toBeVisible();

  await page.getByLabel("Year of birth").fill("1985");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Born 1985")).toBeVisible();

  await page.getByRole("button", { name: "Edit: Asha" }).click();
  await page.getByLabel("Name or nickname").fill("Asha Devi");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Asha Devi")).toBeVisible();

  await page.getByRole("button", { name: "Remove: Asha Devi" }).click();
  await page.getByRole("button", { name: "No, keep" }).click();
  await expect(page.getByText("Asha Devi")).toBeVisible();
  await page.getByRole("button", { name: "Remove: Asha Devi" }).click();
  await page.getByRole("button", { name: "Yes, remove" }).click();
  await expect(page.getByText("Asha Devi")).toHaveCount(0);

  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Add at least one person to continue.")).toBeVisible();
});

test("the family stops at 20 people", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, 20);
  await signedIn(page, api, family);

  await page.goto("/setup/members");

  await expect(page.getByRole("listitem")).toHaveCount(20);
  await expect(page.getByText("You have added the most people allowed (20).")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a person" })).toHaveCount(0);
});

test("signing in again carries on from where the server says the family is", async ({ page, api }) => {
  const done = api.seedHousehold({ state: "UP" }, "done@example.com");
  api.seedMembers(done.id, ["Asha"]);
  await signedIn(page, api, done);
  await page.goto("/setup/basics");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("a household with nobody added yet continues at the family screen", async ({ page, api }) => {
  await signedIn(page, api, api.seedHousehold({ state: "UP" }, "half@example.com"));

  await page.goto("/setup/basics");

  await expect(page).toHaveURL(/\/setup\/members$/);
});

test("a second household cannot be made: a person has one", async ({ page, api }) => {
  const person = api.seedHousehold({ state: "UP" }, "one@example.com");
  api.seedMembers(person.id, ["Asha"]);
  // The phone thinks there is no household yet (it was made on another phone a moment ago).
  await signedIn(page, api, { ...person, id: null });

  await page.goto("/setup/basics");
  await page.getByRole("button", { name: "Continue" }).click();

  // The server says 409; the app finds the household that already exists and goes on to it.
  await expect(page).toHaveURL(/\/dashboard$/);
  expect(api.households.size).toBe(1);
});

test("a setup screen with no household yet goes back to the first step", async ({ page, api }) => {
  await signedIn(page, api, api.seedSession("new@example.com"));

  await page.goto("/setup/members");

  await expect(page).toHaveURL(/\/setup\/basics$/);
});

test("Back from the family screen opens the home answers, and saving returns to the family screen", async ({ page, api }) => {
  await signedIn(page, api, api.seedHousehold({ state: "UP", district: "Lucknow" }, "half@example.com"));
  await page.goto("/setup/members");

  await page.getByRole("button", { name: "Cancel" }).click(); // the empty family opens the add form itself
  await page.getByRole("link", { name: "Back" }).click();
  await expect(page).toHaveURL(/\/household\/edit$/);
  await expect(page.getByLabel("District (optional)")).toHaveValue("Lucknow");
  await page.getByLabel("District (optional)").fill("Kanpur");
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page).toHaveURL(/\/setup\/members$/);
  expect([...api.households.values()][0].fields).toMatchObject({ district: "Kanpur" });
});
