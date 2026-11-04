"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorKind } from "./api";
import type { DocumentInfo, Eligibility, Family } from "./types";

export type Results =
  | { state: "loading" }
  | { state: "error"; kind: "network" | "denied" | "limit" | "generic" }
  | { state: "ready"; eligibility: Eligibility; documents: DocumentInfo[] };

/** The family's results, plus the paper names the rule texts need. `reload` tries again. */
export function useFamilyResults(family: Family | null): { results: Results; reload: () => void } {
  const [results, setResults] = useState<Results>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    Promise.all([api.getEligibility(family), api.listDocuments()])
      .then(([eligibility, documents]) => {
        if (!cancelled) setResults({ state: "ready", eligibility, documents });
      })
      .catch((error) => {
        if (!cancelled) setResults({ state: "error", kind: errorKind(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [family, attempt]);

  const reload = useCallback(() => {
    setResults({ state: "loading" });
    setAttempt((n) => n + 1);
  }, []);
  return { results, reload };
}
