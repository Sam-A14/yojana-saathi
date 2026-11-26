"use client";

import { useEffect, useRef, useState } from "react";
import { loadGoogle } from "@/lib/google";

// Google's own button is drawn by Google, in an iframe, so its look and wording stay official.
// Its largest size is 40px tall with 14px text, which is smaller than our 48px and 16px minimums
// (decisions 018 and 021). We scale the whole button up instead of drawing our own: a home-made
// button cannot give us the ID token Google's one does. 1.4 x 40 = 56px, like our other buttons.
const SCALE = 1.4;
const GOOGLE_MIN_WIDTH = 200; // the limits Google allows for the button's width
const GOOGLE_MAX_WIDTH = 400;

type Props = {
  clientId: string;
  locale: "en" | "hi";
  /** Google handed us an ID token. The page sends it to our server. */
  onCredential: (credential: string) => void;
  /** The word on the divider line between this button and the email form. */
  orLabel: string;
};

/**
 * "Continue with Google" plus the "or" line under it. Renders nothing at all if Google's script
 * cannot load (offline, ad blocker), so the email form below is never left under a lone "or".
 */
export function GoogleSignIn({ clientId, locale, onCredential, orLabel }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLDivElement>(null);
  const [unavailable, setUnavailable] = useState(false);

  // Google keeps the first callback it was given, so always call the newest one.
  const latest = useRef(onCredential);
  useEffect(() => {
    latest.current = onCredential;
  });

  useEffect(() => {
    let cancelled = false;
    loadGoogle()
      .then((google) => {
        if (cancelled || !box.current || !button.current) return;
        google.initialize({
          client_id: clientId,
          callback: (response) => latest.current(response.credential),
          auto_select: false, // never sign in without a tap: a shared phone must not do it silently
        });
        const width = Math.floor(box.current.clientWidth / SCALE);
        button.current.replaceChildren(); // a second run (language change) draws it fresh
        google.renderButton(button.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          logo_alignment: "left",
          width: Math.min(GOOGLE_MAX_WIDTH, Math.max(GOOGLE_MIN_WIDTH, width)),
          locale,
        });
      })
      .catch(() => {
        if (!cancelled) setUnavailable(true);
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, locale]);

  if (unavailable) return null;

  return (
    <>
      {/* The height is reserved from the start, so the page does not jump when Google's button appears. */}
      <div ref={box} className="h-14">
        <div ref={button} style={{ transform: `scale(${SCALE})`, transformOrigin: "top left" }} />
      </div>
      <div className="flex items-center gap-4 text-lg font-semibold text-muted" role="separator" aria-label={orLabel}>
        <span aria-hidden className="h-px flex-1 bg-line" />
        <span aria-hidden>{orLabel}</span>
        <span aria-hidden className="h-px flex-1 bg-line" />
      </div>
    </>
  );
}
