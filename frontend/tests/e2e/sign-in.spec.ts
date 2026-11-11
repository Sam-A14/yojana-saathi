import { type Page } from "@playwright/test";
import { expect, test, STORAGE_KEY } from "./fixtures";

const stored = (page: Page) => page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY);

async function askForCode(page: Page, email: string) {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill(email);
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
}

test("home page 'Sign in with email' opens the sign-in screen, with the privacy promise", async ({ page, api }) => {
  void api;
  await page.goto("/");
  await page.getByRole("link", { name: "Sign in with email" }).click();

  await expect(page).toHaveURL(/\/signin$/);
  await expect(
    page.getByText("We keep one email address, only to sign you in and, later, to send you alerts.").filter({ visible: true }),
  ).toBeVisible();
});

test("a new person signs in with a code and goes to the first setup screen", async ({ page, api }) => {
  await askForCode(page, "  New@Example.com ");
  // Trimmed and lower-cased, like the server does, so one person is one account.
  await expect(page.getByText("We sent a 6-digit code to new@example.com.")).toBeVisible();
  expect(api.requests.find((r) => r.path === "/auth/request-code")?.body).toEqual({
    email: "new@example.com",
    language: "en",
  });

  await page.getByLabel("6-digit code").fill(api.lastCode("new@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  await expect(page).toHaveURL(/\/setup\/basics$/);
  const session = JSON.parse((await stored(page))!);
  expect(session.email).toBe("new@example.com");
  expect(session.householdId).toBeNull();
  // The token is sent as a Bearer header, never in a URL.
  const me = api.requests.find((r) => r.path === "/me");
  expect(me?.authorization).toBe(`Bearer ${session.token}`);
});

test("someone with a family goes straight to the dashboard", async ({ page, api }) => {
  const family = api.seedHousehold({ state: "UP" }, "asha@example.com");
  api.seedMembers(family.id, ["Asha"]);
  await askForCode(page, "asha@example.com");

  await page.getByLabel("6-digit code").fill(api.lastCode("asha@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
});

test("someone with a household but nobody added yet goes to add the family", async ({ page, api }) => {
  api.seedHousehold({ state: "UP" }, "asha@example.com");
  await askForCode(page, "asha@example.com");

  await page.getByLabel("6-digit code").fill(api.lastCode("asha@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  await expect(page).toHaveURL(/\/setup\/members$/);
});

test("a wrong code says so and how many tries are left; the right one then works", async ({ page, api }) => {
  await askForCode(page, "asha@example.com");

  await page.getByLabel("6-digit code").fill("000000");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("That code is not right. Check it and try again. 4 tries left.")).toBeVisible();
  expect(await stored(page)).toBeNull();

  await page.getByLabel("6-digit code").fill(api.lastCode("asha@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/setup\/basics$/);
});

test("after too many wrong tries a new code is asked for", async ({ page, api }) => {
  await askForCode(page, "asha@example.com");
  for (let i = 0; i < 5; i++) {
    await page.getByLabel("6-digit code").fill("000000");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByText(/That code is not right/)).toBeVisible();
  }

  await page.getByLabel("6-digit code").fill("000000");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  await expect(page.getByText("Too many wrong tries. Please ask for a new code.")).toBeVisible();
  void api;
});

test("the code box takes only six digits", async ({ page, api }) => {
  void api; // installs the fake server the code request goes to
  await askForCode(page, "asha@example.com");
  const box = page.getByLabel("6-digit code");

  await box.fill("12ab34-5678");
  await expect(box).toHaveValue("123456");

  await box.fill("482 913"); // as copied from an email, with a space in the middle
  await expect(box).toHaveValue("482913");
  await expect(box).toHaveAttribute("autocomplete", "one-time-code");
});

test("an address that is not an email is refused before anything is sent", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill("not-an-email");
  await page.getByRole("button", { name: "Send me a code" }).click();

  await expect(page.getByText("Please enter your full email address")).toBeVisible();
  expect(api.requests.some((r) => r.path === "/auth/request-code")).toBe(false);
});

test("a new code can be sent, and a different email can be used", async ({ page, api }) => {
  await askForCode(page, "asha@example.com");

  await page.getByRole("button", { name: "Send me a new code" }).click();
  await expect(page.getByText("A new code is on its way.")).toBeVisible();
  expect(api.requests.filter((r) => r.path === "/auth/request-code")).toHaveLength(2);

  await page.getByRole("button", { name: "Use a different email" }).click();
  await expect(page.getByLabel("Your email address")).toBeVisible();
});

test("the friendly messages for too many codes and a busy day", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill("asha@example.com");

  api.requestCodeFailure = { status: 429, code: "too_many_codes" };
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByText("Too many codes for this email. Please try again in an hour.")).toBeVisible();

  api.requestCodeFailure = { status: 503, code: "busy" };
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByText("Sign-in is busy today. Please try again tomorrow.")).toBeVisible();

  api.requestCodeFailure = { status: 503, code: "email_failed" };
  await page.getByRole("button", { name: "Send me a code" }).click();
  await expect(page.getByText("We could not send the email. Please try again in a minute.")).toBeVisible();
});

test("sign-in speaks Hindi when the language is Hindi", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.getByRole("heading", { name: "ईमेल से साइन इन करें" })).toBeVisible();

  await page.getByLabel("आपका ईमेल पता").fill("asha@example.com");
  await page.getByRole("button", { name: "मुझे कोड भेजें" }).click();

  await expect(page.getByRole("heading", { name: "अपना ईमेल देखें" })).toBeVisible();
  expect(api.requests.find((r) => r.path === "/auth/request-code")?.body).toMatchObject({ language: "hi" });
});

test("the sign-in boxes are empty for the next person on a shared phone", async ({ page, api }) => {
  await askForCode(page, "asha@example.com");
  await page.getByLabel("6-digit code").fill(api.lastCode("asha@example.com"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/setup\/basics$/);

  await page.getByRole("link", { name: "Yojana Saathi" }).click(); // header link home
  await page.evaluate((k) => localStorage.removeItem(k), STORAGE_KEY); // someone signed out
  await page.goto("/signin");

  await expect(page.getByLabel("Your email address")).toHaveValue("");
});

test("someone who is already signed in is not asked again", async ({ page, api }) => {
  const family = api.seedHousehold({ state: "UP" });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );

  await page.goto("/signin");

  await expect(page).toHaveURL(/\/dashboard$/);
});

test("the setup screens need a sign-in", async ({ page, api }) => {
  void api;
  await page.goto("/setup/members");
  await expect(page).toHaveURL(/\/signin$/);
});

test("a session that ends while using the app sends the person to sign in", async ({ page, api }) => {
  const family = api.seedHousehold({ state: "UP" });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(family)],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Asha" })).toBeVisible();

  api.sessions.delete(family.token); // expired on the server
  await page.reload();

  await expect(page.getByText("You are not signed in on this phone.")).toBeVisible();
  expect(await stored(page)).toBeNull();
});
