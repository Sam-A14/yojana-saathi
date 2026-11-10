"use client";

import { useMemo } from "react";
import { type Session, useSession } from "./session";
import type { Family } from "./types";

/** The signed-in person's household as an API handle: its id, and the session token that proves
 * who is asking. `family` is null when nobody is signed in or no household exists yet (`session`
 * tells which). Only id and token are returned, so unrelated changes do not make a screen reload. */
export function useFamily(): { ready: boolean; family: Family | null; session: Session | null } {
  const { ready, session } = useSession();
  const id = session?.householdId;
  const token = session?.token;
  const family = useMemo(() => (id && token ? { id, token } : null), [id, token]);
  return { ready, family, session };
}
