// "Source: ..." on every scheme page: where the rules were read from, linked to that page. The
// credit says who published it. Kept in one place so the wording and the host check are tested.

export type SourceCredit = { kind: "myscheme"; href: string } | { kind: "official"; href: string; host: string };

const MYSCHEME_HOSTS = new Set(["myscheme.gov.in", "www.myscheme.gov.in"]);

/** The credit for a source address, or null when there is none or it is not a web address (so the
 * page shows no line rather than a broken link). Only http(s) addresses become links. */
export function sourceCredit(sourceUrl: string | undefined | null): SourceCredit | null {
  if (!sourceUrl) return null;
  let url: URL;
  try {
    url = new URL(sourceUrl);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  if (MYSCHEME_HOSTS.has(url.hostname.toLowerCase())) return { kind: "myscheme", href: url.href };
  return { kind: "official", href: url.href, host: url.hostname.replace(/^www\./, "") };
}
