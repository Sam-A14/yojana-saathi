import { type Page } from "@playwright/test";
import { expect, test, STORAGE_KEY } from "./fixtures";
import { GOOGLE_SCRIPT_URL, googleCredentialFor } from "./fake-api";

// "Continue with Google" on the sign-in screen. Google's script is replaced by a plain button
// (fake-api.ts), so no test talks to Google.
//
// The client ID is baked in when the site is BUILT, so one build can show only one of the two
// states. These tests follow the build: the "with Google" ones run when NEXT_PUBLIC_GOOGLE_CLIENT_ID
// is set (CI builds the site twice), the "without" one when it is not.
const ENABLED = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim());

const stored = (page: Page) => page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY);
const googleButton = (page: Page) => page.getByRole("button", { name: "Continue with Google" });

async function signAs(page: Page, email: string) {
  await page.addInitScript((credential) => {
    (window as unknown as { __fakeCredential: string }).__fakeCredential = credential;
  }, googleCredentialFor(email));
}

test.describe("with a Google client ID", () => {
  test.skip(!ENABLED, "this build has no NEXT_PUBLIC_GOOGLE_CLIENT_ID");

  test("the button is above the email form, with an 'or' line between them", async ({ page, api }) => {
    void api;
    await page.goto("/signin");
    const button = googleButton(page);
    await expect(button).toBeVisible();

    const emailField = page.getByLabel("Your email address");
    const divider = page.getByRole("separator", { name: "or" });
    await expect(divider).toBeVisible();
    const [b, d, e] = await Promise.all([button.boundingBox(), divider.boundingBox(), emailField.boundingBox()]);
    expect(b!.y + b!.height).toBeLessThanOrEqual(d!.y);
    expect(d!.y + d!.height).toBeLessThanOrEqual(e!.y);
    await expect(page.getByRole("heading", { level: 1, name: "Sign in", exact: true })).toBeVisible();
    // The email option is still all there.
    await expect(page.getByRole("button", { name: "Send me a code" })).toBeVisible();
  });

  test("elder rules: the button is 48px or taller and its text and 'or' are 16px or bigger", async ({ page, api }) => {
    void api;
    await page.goto("/signin");
    const button = googleButton(page);

    const box = await button.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(48);
    const textSize = await button.evaluate((el) => {
      // Google's button is scaled up as a whole: its drawn text is the font size times that scale.
      const scale = new DOMMatrix(getComputedStyle(el.parentElement!).transform).a;
      return parseFloat(getComputedStyle(el).fontSize) * scale;
    });
    expect(textSize).toBeGreaterThanOrEqual(16);
    const orSize = await page.getByText("or", { exact: true }).evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(orSize).toBeGreaterThanOrEqual(16);
  });

  test("it asks Google for the official 'continue with' button, signed-in-never-silently, in English", async ({ page, api }) => {
    void api;
    await page.goto("/signin");
    await googleButton(page).waitFor();

    const options = await page.evaluate(() => (window as unknown as Record<string, Record<string, unknown>>).__gsiButtonOptions);
    expect(options).toMatchObject({ type: "standard", theme: "outline", size: "large", text: "continue_with", locale: "en" });
    expect(options.width).toBeGreaterThanOrEqual(200);
    expect(options.width).toBeLessThanOrEqual(400);
    const config = await page.evaluate(() => (window as unknown as Record<string, Record<string, unknown>>).__gsiConfig);
    expect(config.auto_select).toBe(false);
    expect(String(config.client_id).length).toBeGreaterThan(0);
  });

  test("a new person signs in with Google and goes to the first setup screen, like with a code", async ({ page, api }) => {
    await signAs(page, "New@Example.com");
    await page.goto("/signin");
    await googleButton(page).click();

    await expect(page).toHaveURL(/\/setup\/basics$/);
    expect(api.requests.find((r) => r.path === "/auth/google")?.body).toEqual({
      credential: googleCredentialFor("New@Example.com"),
      language: "en",
    });
    const session = JSON.parse((await stored(page))!);
    // The email comes from the server (GET /me), lower-cased.
    expect(session.email).toBe("new@example.com");
    expect(session.householdId).toBeNull();
    // The Google token goes only to our server, once, in the body: never in a URL, never kept.
    expect(JSON.stringify(session)).not.toContain("fake-google");
    expect(api.requests.find((r) => r.path === "/me")?.authorization).toBe(`Bearer ${session.token}`);
  });

  test("someone who already has a family goes straight to the dashboard", async ({ page, api }) => {
    const family = api.seedHousehold({ state: "UP" }, "asha@example.com");
    api.seedMembers(family.id, ["Asha"]);
    await signAs(page, "asha@example.com");
    await page.goto("/signin");
    await googleButton(page).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
    expect(JSON.parse((await stored(page))!).householdId).toBe(family.id);
  });

  test("a refused token says so in plain words, keeps nobody signed in, and the email form still works", async ({ page, api }) => {
    await page.addInitScript(() => {
      (window as unknown as { __fakeCredential: string }).__fakeCredential = "forged-token";
    });
    await page.goto("/signin");
    await googleButton(page).click();

    // (Next.js keeps its own empty role="alert" for route changes, so pick ours by its words.)
    await expect(
      page.getByRole("alert").filter({ hasText: "We could not check your Google sign-in. Please try again, or use your email instead." }),
    ).toBeVisible();
    expect(await stored(page)).toBeNull();
    await expect(page).toHaveURL(/\/signin$/);
    await page.getByLabel("Your email address").fill("asha@example.com");
    await page.getByRole("button", { name: "Send me a code" }).click();
    await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
    void api;
  });

  test("if the server has Google switched off, it says so and points to email", async ({ page, api }) => {
    api.googleUnavailable = true;
    await page.goto("/signin");
    await googleButton(page).click();

    await expect(
      page.getByRole("alert").filter({ hasText: "Sign-in with Google is not available right now. Please use your email instead." }),
    ).toBeVisible();
    expect(await stored(page)).toBeNull();
  });

  test("if Google's script is blocked, there is no button and no lonely 'or', only the email form", async ({ page, api }) => {
    void api;
    await page.route(GOOGLE_SCRIPT_URL, (route) => route.abort()); // an ad blocker, or no internet
    await page.goto("/signin");

    await expect(page.getByRole("button", { name: "Send me a code" })).toBeVisible();
    await expect(googleButton(page)).toHaveCount(0);
    await expect(page.getByRole("separator")).toHaveCount(0);
  });

  test("in Hindi the button is asked for in Hindi and the new account is a Hindi one", async ({ page, api }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "हिन्दी" }).click();
    await page.goto("/signin");

    await expect(page.getByRole("separator", { name: "या" })).toBeVisible();
    await page.getByRole("button", { name: "Google के साथ जारी रखें" }).click();
    await expect(page).toHaveURL(/\/setup\/basics$/);
    expect(api.requests.find((r) => r.path === "/auth/google")?.body).toMatchObject({ language: "hi" });
  });

  test("the sign-in screen says what Google tells us and what we keep", async ({ page, api }) => {
    void api;
    await page.goto("/signin");

    await expect(
      page.getByText("If you use Google, Google tells us your email address. We keep only that, not your name or photo."),
    ).toBeVisible();
  });
});

test.describe("without a Google client ID", () => {
  test.skip(ENABLED, "this build has NEXT_PUBLIC_GOOGLE_CLIENT_ID");

  test("there is no Google button, no 'or' line and no Google sentence: only the email form", async ({ page, api }) => {
    void api;
    await page.goto("/signin");

    await expect(page.getByRole("button", { name: "Send me a code" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Google/ })).toHaveCount(0);
    await expect(page.getByRole("separator")).toHaveCount(0);
    await expect(page.getByText(/Google/)).toHaveCount(0);
  });
});

test("the privacy page says Google tells us the email, what we keep, and that Google's button loads from Google", async ({ page }) => {
  await page.goto("/privacy");

  await expect(
    page.getByText(
      "If you choose “Continue with Google”, Google tells us your email address. We keep only the email, not your Google name, photo or anything else.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "The “Continue with Google” button comes from Google. When the sign-in page shows it, Google can see that the page was opened.",
    ),
  ).toBeVisible();
  // Still the same sections: the Google lines sit under "Who else sees it".
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(8);
});
