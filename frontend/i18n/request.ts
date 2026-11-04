import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { en } from "@/messages/en";
import { hi } from "@/messages/hi";
import { LOCALE_COOKIE } from "./constants";

// The language is a plain cookie (no /en or /hi in the URL): a private, per-family app gains
// nothing from language URLs. Anything other than "hi" means English.
export default getRequestConfig(async () => {
  const store = await cookies();
  const locale = store.get(LOCALE_COOKIE)?.value === "hi" ? "hi" : "en";
  return { locale, messages: locale === "hi" ? hi : en };
});
