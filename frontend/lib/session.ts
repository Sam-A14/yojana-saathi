import { useMemo, useSyncExternalStore } from "react";

// Who is signed in on this phone. Replaces the old "family code" (docs/decisions/019).
// The session token is a Bearer token kept in localStorage (decision 019 says why not a cookie).
// householdId is null until the person has saved the first setup screen.
export type Session = { token: string; email: string; householdId: string | null };

const KEY = "yojana.session";
const OLD_KEY = "yojana.family"; // the family code of earlier versions: useless now, so removed
const CHANGED = "yojana:session-changed";

// localStorage can be missing or throw (private windows, blocked site data). The copy in memory
// keeps the app working until the tab closes; it just will not survive a reload.
let memory: string | null = null;

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return memory;
  }
}

function announce() {
  window.dispatchEvent(new Event(CHANGED));
}

export function saveSession(session: Session) {
  memory = JSON.stringify(session);
  try {
    window.localStorage.setItem(KEY, memory);
    window.localStorage.removeItem(OLD_KEY);
  } catch {
    // Not saved on this device; the in-memory copy above still works for this tab.
  }
  announce();
}

/** Remember the household id once it exists (or after it is found on /me). */
export function setHouseholdId(householdId: string | null) {
  const current = parse(readRaw());
  if (current) saveSession({ ...current, householdId });
}

/** Sign out of this phone, or the server said the session is over. */
export function clearSession() {
  memory = null;
  try {
    window.localStorage.removeItem(KEY);
    window.localStorage.removeItem(OLD_KEY);
  } catch {
    // Nothing to remove.
  }
  announce();
}

export function currentSession(): Session | null {
  return parse(readRaw());
}

function parse(raw: string | null): Session | null {
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as Partial<Session>;
    if (typeof data.token !== "string" || typeof data.email !== "string") return null;
    const householdId = typeof data.householdId === "string" ? data.householdId : null;
    return { token: data.token, email: data.email, householdId };
  } catch {
    return null;
  }
}

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange); // another tab changed it
  window.addEventListener(CHANGED, onChange); // this tab changed it
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(CHANGED, onChange);
  };
}

/** The signed-in session, if any. `ready` is false while the server-rendered page is being
 * hydrated: the server cannot see this browser's storage, so nothing may be decided before `ready`. */
export function useSession(): { ready: boolean; session: Session | null } {
  const raw = useSyncExternalStore<string | null | undefined>(subscribe, readRaw, () => undefined);
  // Memoised so the object keeps its identity until the stored text changes; effects that load
  // data list it as a dependency and must not run again on every render.
  const session = useMemo(() => (raw === undefined ? null : parse(raw)), [raw]);
  return { ready: raw !== undefined, session };
}
