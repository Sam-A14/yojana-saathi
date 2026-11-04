import { useMemo, useSyncExternalStore } from "react";
import { parseFamilyCode } from "./family-code";
import type { Family } from "./types";

// Which screen of the setup wizard comes next. Lets "Continue where I stopped" work.
export type SetupStep = "code" | "members" | "documents" | "exclusions" | "done";
export const STEP_PATHS: Record<SetupStep, string> = {
  code: "/setup/code",
  members: "/setup/members",
  documents: "/setup/documents",
  exclusions: "/setup/exclusions",
  done: "/dashboard",
};

export type StoredFamily = Family & { code: string; step: SetupStep };

const KEY = "yojana.family";
const CHANGED = "yojana:family-changed";

// localStorage can be missing or throw (private windows, blocked site data). The copy in memory
// keeps the wizard working until the tab closes; it just will not survive a reload.
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

export function saveFamily(code: string, step: SetupStep) {
  memory = JSON.stringify({ code, step });
  try {
    window.localStorage.setItem(KEY, memory);
  } catch {
    // Not saved on this device; the in-memory copy above still works for this tab.
  }
  announce();
}

const STEP_ORDER: SetupStep[] = ["code", "members", "documents", "exclusions", "done"];

/** Remember that the wizard reached `step`. Never moves backwards, so revisiting an earlier
 * screen and pressing Continue cannot undo progress. */
export function advanceTo(step: SetupStep) {
  const current = parseStored(readRaw());
  if (current && STEP_ORDER.indexOf(step) > STEP_ORDER.indexOf(current.step)) {
    saveFamily(current.code, step);
  }
}

export function forgetFamily() {
  memory = null;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // Nothing to remove.
  }
  announce();
}

function parseStored(raw: string | null): StoredFamily | null {
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as { code?: unknown; step?: unknown };
    const family = typeof data.code === "string" ? parseFamilyCode(data.code) : null;
    const step = data.step as SetupStep;
    if (!family || !(step in STEP_PATHS)) return null;
    return { ...family, code: data.code as string, step };
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

/** The saved family, if any. `ready` is false while the server-rendered page is being hydrated:
 * the server cannot see this browser's storage, so nothing may be decided before `ready`. */
export function useStoredFamily(): { ready: boolean; family: StoredFamily | null } {
  const raw = useSyncExternalStore<string | null | undefined>(subscribe, readRaw, () => undefined);
  // Memoised so the object keeps its identity until the stored text changes; effects that load
  // data list it as a dependency and must not run again on every render.
  const family = useMemo(() => (raw === undefined ? null : parseStored(raw)), [raw]);
  return { ready: raw !== undefined, family };
}
