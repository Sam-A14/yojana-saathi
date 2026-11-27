import { useSyncExternalStore } from "react";

// Render's free tier sleeps when idle, and the free database (Neon) suspends after a few quiet
// minutes, so the first request after a break can take a while. A request that is still unanswered
// after 4 seconds counts as "slow", and the app shows a friendly "waking up the server" message
// instead of a frozen screen. Four, not fewer: an ordinary save on a slow phone connection can take
// two or three seconds, and a banner on every save would cry wolf.
export const SLOW_AFTER_MS = 4000;

let slowCount = 0;
const listeners = new Set<() => void>();

function change(by: number) {
  slowCount += by;
  listeners.forEach((listener) => listener());
}

/** Call when a request starts; call the returned function when it ends (either way). */
export function trackRequest(): () => void {
  let slow = false;
  const timer = setTimeout(() => {
    slow = true;
    change(1);
  }, SLOW_AFTER_MS);
  return () => {
    clearTimeout(timer);
    if (slow) change(-1);
  };
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => void listeners.delete(listener);
};

/** True while at least one request has been waiting for more than 4 seconds. */
export function useServerWaking(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => slowCount > 0,
    () => false,
  );
}
