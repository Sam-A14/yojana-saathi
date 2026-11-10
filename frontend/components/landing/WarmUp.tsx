"use client";

import { useEffect } from "react";
import { warmUpServer } from "@/lib/api";

/** Draws nothing. Wakes the sleeping backend while the person reads the home page, so the first
 * real request (sending the sign-in code) is not the slow one. */
export function WarmUp() {
  useEffect(() => {
    warmUpServer();
  }, []);
  return null;
}
