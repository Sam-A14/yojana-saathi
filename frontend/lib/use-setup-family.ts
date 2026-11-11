"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useFamily } from "./use-family";
import type { Family } from "./types";

/** The household for a setup screen. Not signed in: go to sign-in. Signed in but no household yet:
 * go to the first step. Returns null until the family is known. */
export function useSetupFamily(): Family | null {
  const { ready, family, session } = useFamily();
  const router = useRouter();
  useEffect(() => {
    if (!ready || family) return;
    router.replace(session ? "/setup/basics" : "/signin");
  }, [ready, family, session, router]);
  return family;
}
