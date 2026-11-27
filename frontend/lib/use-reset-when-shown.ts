import { useEffect, useEffectEvent } from "react";

/**
 * Run `reset` every time this page is shown: when it first appears, and again each time the person
 * comes back to it.
 *
 * Why this exists: Next.js does not throw a page away when you navigate off it. It keeps it alive,
 * hidden, with all its state, and shows that same page again when you return. A button that was set
 * to "Saving…" just before a successful save and navigation therefore still says "Saving…" (and is
 * disabled) the next time the page is opened, with nothing running and nothing to wait for. Pages
 * that set a "busy" flag and rely on the navigation to get rid of it must clear it here.
 * (The sign-in page learned the same lesson; see its verify function.)
 *
 * Effects run again when a hidden page is shown, which is what makes this work.
 */
export function useResetWhenShown(reset: () => void): void {
  const onShown = useEffectEvent(reset);
  useEffect(() => {
    onShown();
  }, []);
}
