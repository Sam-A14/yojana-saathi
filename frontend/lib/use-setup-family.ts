"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import { useStoredFamily } from "./storage";
import type { Family } from "./types";

/** The saved family for a setup screen. Without one there is nothing to set up, so go to the
 * first step. Returns null until the family is known. */
export function useSetupFamily(): Family | null {
  const { ready, family } = useStoredFamily();
  const router = useRouter();
  useEffect(() => {
    if (ready && !family) router.replace("/setup/basics");
  }, [ready, family, router]);
  // Only id and token: moving to the next step changes the stored step, which must not make
  // the screen reload its data.
  const id = family?.id;
  const token = family?.token;
  return useMemo(() => (id && token ? { id, token } : null), [id, token]);
}
