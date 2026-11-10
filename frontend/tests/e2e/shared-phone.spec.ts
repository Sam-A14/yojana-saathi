import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// Clicks through the email sign-in, like the next person who picks up the shared phone.
async function signInByClicking(page: Page, api: FakeApi, email: string) {
  await page.getByRole("link", { name: "Sign in with email" }).click();
  await page.getByLabel("Your email address").fill(email);
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await page.getByLabel("6-digit code").fill(api.lastCode(email));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

async function signOutByClicking(page: Page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("button", { name: "Yes, sign out" }).click();
  await expect(page).toHaveURL(/\/$/); // the dashboard shows a similar link for a moment
}

// Next.js keeps pages the person has left (hidden, with their state) so Back is instant. On a
// phone that several people share, that must never show one family what another typed or loaded.
// Every move below is a click (no page reload), because a reload would clear the state anyway.

test("the next family never sees the previous family's results, even while theirs load", async ({ page, api }) => {
  const first = api.seedHousehold();
  api.seedMembers(first.id, ["Kamla", "Asha"]);
  const second = api.seedHousehold();
  api.seedMembers(second.id, ["Meena"]);
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, value);
      }
    },
    [STORAGE_KEY, api.storedSession(first)],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("region", { name: "Kamla", exact: true })).toBeVisible();

  await signOutByClicking(page);

  // The second family signs in with a slow server: for a while only "loading" may show.
  api.eligibilityDelay = 1500;
  await signInByClicking(page, api, second.email);
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Checking schemes for your family…")).toBeVisible();
  await expect(page.getByText("Kamla")).toHaveCount(0);
  await expect(page.getByText("Asha")).toHaveCount(0);

  await expect(page.getByRole("region", { name: "Meena", exact: true })).toBeVisible();
  await expect(page.getByText("Kamla")).toHaveCount(0);
});

test("the email and code typed for one person are not left in the boxes for the next", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.goto("/");
  await signInByClicking(page, api, family.email);
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();

  await signOutByClicking(page);
  await page.getByRole("link", { name: "Sign in with email" }).click();

  await expect(page.getByLabel("Your email address")).toHaveValue("");
  await page.getByLabel("Your email address").fill(family.email);
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByLabel("6-digit code")).toHaveValue("");
});

test("a new person's setup form starts empty", async ({ page, api }) => {
  // Person one: the basics typed in, then the phone is handed on.
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, value);
      }
    },
    [STORAGE_KEY, api.storedSession(api.seedSession("one@example.com"))],
  );
  await page.goto("/setup/basics");
  await page.getByLabel("District (optional)").fill("Lucknow");

  // Back to the start by clicking, then someone else signs in on the same phone.
  await page.evaluate((k) => localStorage.removeItem(k), STORAGE_KEY);
  await page.getByRole("link", { name: "Yojana Saathi" }).click();
  api.seedSession("two@example.com");
  await signInByClicking(page, api, "two@example.com");

  await expect(page.getByLabel("District (optional)")).toBeVisible();
  await expect(page.getByLabel("District (optional)")).toHaveValue("");
});

test("results are asked for again after the family answers a question", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla", "Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("region", { name: "Kamla", exact: true })).toBeVisible();
  const asked = () => api.requests.filter((r) => r.path.endsWith("/eligibility")).length;
  expect(asked()).toBe(1);

  // Answer a paper on the setup screen, go through to the end, and come back.
  await page.getByRole("region", { name: "Kamla", exact: true }).getByRole("link", { name: "Answer this" }).click();
  await page.getByRole("button", { name: "Save and continue" }).click();
  await page.getByRole("button", { name: "Finish setup" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect.poll(asked).toBeGreaterThanOrEqual(2);
});

test("the edit screen never shows another family's answers", async ({ page, api }) => {
  const first = api.seedHousehold({ state: "UP", district: "Secret-District-A" });
  api.seedMembers(first.id, ["Asha"]);
  const second = api.seedHousehold({ state: "UP", district: "District-B" });
  api.seedMembers(second.id, ["Meena"]);
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, value);
      }
    },
    [STORAGE_KEY, api.storedSession(first)],
  );
  await page.goto("/dashboard");
  await page.getByRole("link", { name: "Edit household details" }).click();
  await expect(page.getByLabel("District (optional)")).toHaveValue("Secret-District-A");
  await page.getByLabel("District (optional)").fill("typed-but-never-saved");
  await page.getByRole("link", { name: "Back without saving" }).click();

  await signOutByClicking(page);
  await signInByClicking(page, api, second.email);
  await page.getByRole("link", { name: "Edit household details" }).click();

  await expect(page.getByLabel("District (optional)")).toHaveValue("District-B");
  await expect(page.getByText("Secret-District-A")).toHaveCount(0);
});
