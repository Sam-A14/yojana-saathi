"use client";

import { useMemo } from "react";
import { useStoredFamily } from "./storage";
import type { Family } from "./types";

/** The saved family (id and token), if any. `ready` is false until the browser's storage has been
 * read. Only id and token are returned, so moving to another wizard step (which changes the
 * stored step) does not make a screen reload its data. */
export function useFamily(): { ready: boolean; family: Family | null } {
  const { ready, family } = useStoredFamily();
  const id = family?.id;
  const token = family?.token;
  const stable = useMemo(() => (id && token ? { id, token } : null), [id, token]);
  return { ready, family: stable };
}
