import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

// The tests run against the production build (`npm run build` first) with the API faked in the
// browser (tests/e2e/fake-api.ts), so no backend or database is needed.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    // Only for machines that already have a Chrome and cannot download Playwright's.
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || undefined },
  },
  // Mobile-first: the main flows are checked on a phone-sized screen.
  projects: [{ name: "phone", use: { ...devices["Pixel 5"] } }],
  webServer: {
    command: `npm run start -- --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { NEXT_PUBLIC_API_URL: "http://localhost:8000" },
  },
});
