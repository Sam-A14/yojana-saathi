"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useFamily } from "./use-family";
import type { Family } from "./types";

/** The saved family for a setup screen. Without one there is nothing to set up, so go to the
 * first step. Returns null until the family is known. */
export function useSetupFamily(): Family | null {
  const { ready, family } = useFamily();
  const router = useRouter();
  useEffect(() => {
    if (ready && !family) router.replace("/setup/basics");
  }, [ready, family, router]);
  return family;
}
