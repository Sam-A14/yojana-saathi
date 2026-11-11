import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

const NAMES = ["Kamla", "Asha", "Ramesh", "Gudiya"];

// A finished family on this phone, whose results are the sample family's (see fake-api.ts).
async function openDashboard(page: Page, api: FakeApi) {
  const family = api.seedHousehold();
  api.seedMembers(family.id, NAMES);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  return family;
}

const card = (page: Page, name: string) => page.getByRole("region", { name, exact: true });

test("a summary line and one card per person", async ({ page, api }) => {
  await openDashboard(page, api);

  await expect(
    page.getByText("Your family may qualify for 1 scheme. 1 more is close, and 7 need one more answer."),
  ).toBeVisible();
  await expect(page.getByText("Checked on 3 November 2026")).toBeVisible();
  for (const name of NAMES) await expect(card(page, name)).toBeVisible();
});

test("a scheme that may fit, with its verification label", async ({ page, api }) => {
  await openDashboard(page, api);
  const kamla = card(page, "Kamla");

  await expect(kamla.getByRole("heading", { name: "May qualify" })).toBeVisible();
  const ignwps = kamla.getByRole("listitem").filter({ hasText: "Indira Gandhi National Widow Pension" });
  await expect(ignwps).toContainText("Not yet verified");
  // A verified scheme shows when it was last checked.
  await expect(card(page, "Asha").getByText("Last checked on 15 September 2026")).toBeVisible();
});

test("a blocked scheme says who caused it", async ({ page, api }) => {
  await openDashboard(page, api);

  const blocked = card(page, "Kamla").getByRole("listitem").filter({ hasText: "PM-KISAN" });
  await expect(blocked).toContainText("Not available because of Ramesh.");
  await expect(card(page, "Kamla").getByRole("heading", { name: "Not available for your family" })).toBeVisible();
});

test("a near miss says what would fix it", async ({ page, api }) => {
  await openDashboard(page, api);
  const asha = card(page, "Asha");

  const nearMiss = asha.getByRole("listitem").filter({ hasText: "Example Scholarship" });
  await expect(asha.getByRole("heading", { name: "Close: one thing is missing" })).toBeVisible();
  await expect(nearMiss).toContainText("Has Bank account linked to Aadhaar");
  await expect(nearMiss).toContainText("You can fix this");
});

test("an unknown result explains why in plain words and asks what it needs", async ({ page, api }) => {
  await openDashboard(page, api);

  // Only the birth year is known, and the rule needs the exact age.
  const age = card(page, "Asha").getByRole("listitem").filter({ hasText: "Indira Gandhi" });
  await expect(age).toContainText("This depends on the exact age. We only know the year of birth, so we cannot be sure yet.");
  // Only an income range is known, and the rule's limit falls inside it.
  const income = card(page, "Kamla").getByRole("listitem").filter({ hasText: "Example Income-Limit" });
  await expect(income).toContainText("This depends on your family’s exact income.");
  // A paper that was never answered is a question, with a link to where it can be answered.
  const paper = card(page, "Kamla").getByRole("listitem").filter({ hasText: "Example Scholarship" });
  await expect(paper).toContainText("Does Kamla have this paper: Bank account linked to Aadhaar?");
  await paper.getByRole("link", { name: "Answer this" }).click();
  await expect(page).toHaveURL(/\/setup\/documents$/);
});

test("schemes that do not fit are counted, not listed", async ({ page, api }) => {
  await openDashboard(page, api);

  await expect(card(page, "Gudiya").getByText("2 other schemes do not fit.")).toBeVisible();
});

test("the dashboard speaks Hindi", async ({ page, api }) => {
  await openDashboard(page, api);

  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(page.getByRole("heading", { name: "आपके परिवार की योजनाएँ" })).toBeVisible();
  await expect(page.getByText("आपका परिवार 1 योजनाओं के लिए पात्र हो सकता है।")).toBeVisible();
  await expect(card(page, "Kamla").getByText("परिवार में कम से कम एक व्यक्ति")).toHaveCount(0);
  await expect(card(page, "Kamla").getByText("आपके परिवार के लिए उपलब्ध नहीं").first()).toBeVisible();
});

test("a session the server no longer knows leads back to sign-in", async ({ page, api }) => {
  const family = api.seedHousehold();
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession({ ...family, token: "A".repeat(43) })], // not a live session
  );

  await page.goto("/dashboard");

  // The 401 ends the session on this phone; the screen says so and offers sign-in.
  await expect(page.getByText("You are not signed in on this phone.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in with email" })).toBeVisible();
  expect(await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY)).toBeNull();
});

test("someone else's household is refused and never shown", async ({ page, api }) => {
  const mine = api.seedHousehold({ state: "UP" }, "mine@example.com");
  const other = api.seedHousehold({ state: "BR" }, "other@example.com");
  api.seedMembers(other.id, ["Secret"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession({ ...mine, id: other.id })], // my session, their household id
  );

  await page.goto("/dashboard");

  await expect(page.getByText("We could not open this family. Please sign in again.")).toBeVisible();
  await expect(page.getByText("Secret")).toHaveCount(0);
});

test("a lost connection can be retried", async ({ page, api }) => {
  api.offline = true;
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  await expect(page.getByText(/We could not reach the server/)).toBeVisible();

  api.offline = false;
  await page.getByRole("button", { name: "Try again" }).click();

  await expect(card(page, "Asha")).toBeVisible();
});

test("when nobody is signed in there is nothing to show, and signing in is offered", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByText("You are not signed in on this phone.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in with email" })).toBeVisible();
});

test("signed in without a household goes to the first setup screen", async ({ page, api }) => {
  const person = api.seedSession("new@example.com");
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(person)],
  );

  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/setup\/basics$/);
});
