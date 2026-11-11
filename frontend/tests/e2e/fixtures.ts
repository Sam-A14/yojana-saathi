import { test as base } from "@playwright/test";
import { FakeApi } from "./fake-api";

// Every e2e test gets a page whose API calls are answered by a fresh FakeApi.
export const test = base.extend<{ api: FakeApi }>({
  api: async ({ page }, provide) => {
    const api = new FakeApi();
    await api.install(page);
    await provide(api);
  },
});
export { expect } from "@playwright/test";

export const STORAGE_KEY = "yojana.session";
