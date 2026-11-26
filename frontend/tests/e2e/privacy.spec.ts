import { type Page } from "@playwright/test";
import { expect, test, STORAGE_KEY } from "./fixtures";

const SECTIONS = [
  "What we keep",
  "What we never ask for",
  "Why we need it",
  "How it is used",
  "Who else sees it",
  "How long we keep it",
  "How to delete it",
  "See for yourself",
];

test("the privacy page has a section for each question, in plain words", async ({ page }) => {
  await page.goto("/privacy");

  await expect(page.getByRole("heading", { level: 1, name: "How we handle your information" })).toBeVisible();
  for (const title of SECTIONS) {
    await expect(page.getByRole("heading", { level: 2, name: title })).toBeVisible();
  }
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(SECTIONS.length);
});

test("it says plainly that the email goes to Resend, and what deleting cannot reach", async ({ page }) => {
  await page.goto("/privacy");

  await expect(page.getByText("Our email service, Resend, gets your email address and the sign-in code, so it can send you the code.")).toBeVisible();
  await expect(page.getByText("We do not sell your information, and we do not use it for advertising.")).toBeVisible();
  // The limits of deleting are stated, not hidden.
  await expect(page.getByText(/It cannot reach copies outside our control/)).toBeVisible();
  await expect(page.getByText(/may keep backups for a while/)).toBeVisible();
  // Deleting is explained with the same words as the button.
  await expect(page.getByText("At the bottom of the page, choose “Delete my data”.")).toBeVisible();
});

test("it is public, and the official code link opens in a new tab", async ({ page, api }) => {
  await page.goto("/privacy");
  const code = page.getByRole("link", { name: "See the code on GitHub" });
  await expect(code).toHaveAttribute("href", "https://github.com/Sam-A14/yojana-saathi");
  await expect(code).toHaveAttribute("target", "_blank");
  await expect(code).toHaveAttribute("rel", /noopener/);
  expect(api.requests.filter((r) => r.path !== "/health")).toEqual([]); // no server data needed
});

test("it is in Hindi when the language is Hindi", async ({ page }) => {
  await page.goto("/privacy");
  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "हम आपकी जानकारी कैसे सँभालते हैं" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "हम क्या कभी नहीं माँगते" })).toBeVisible();
  await expect(page.getByText(/Resend/).first()).toBeVisible();
});

// --- Links to it ---

for (const path of ["/", "/signin", "/schemes", "/example"]) {
  test(`${path} links to the privacy page from the footer or the page, with a big enough tap target`, async ({ page }) => {
    await page.goto(path);
    const link = page.getByRole("link", { name: "How we handle your information" }).last();
    await expect(link).toHaveAttribute("href", "/privacy");
    expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(48);
  });
}

test("the dashboard's 'Your data' block and the deleted page link to it too", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  const mine = page.getByRole("region", { name: "Your data" });
  await expect(mine.getByRole("link", { name: "How we handle your information" })).toHaveAttribute("href", "/privacy");

  await page.goto("/deleted");
  await expect(page.getByText(/Copies outside our control/)).toBeVisible();
  await expect(page.getByRole("link", { name: "How we handle your information" }).first()).toHaveAttribute("href", "/privacy");
});

// --- No promise about something that is not built ---

// Alerts are not built yet, so no screen may promise them. When they are built, change this test
// together with the privacy page (docs/decisions/025-privacy-page.md says why).
async function textOf(page: Page, path: string) {
  await page.goto(path);
  return page.locator("body").innerText();
}

for (const path of ["/", "/signin", "/privacy", "/deleted"]) {
  test(`${path} makes no promise about alerts, in English or Hindi`, async ({ page }) => {
    expect(await textOf(page, path)).not.toMatch(/alert/i);
    await page.getByRole("button", { name: "हिन्दी" }).click();
    await page.waitForLoadState("networkidle");
    expect(await page.locator("body").innerText()).not.toMatch(/अलर्ट/);
  });
}

test("the dashboard's 'Your data' text makes no promise about alerts either", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  const mine = page.getByRole("region", { name: "Your data" });
  await expect(mine).toContainText("Our email service, Resend, gets it only to send you the code. We do not sell it.");
  expect(await mine.innerText()).not.toMatch(/alert/i);
});
