import { useSyncExternalStore } from "react";

// Render's free tier sleeps when idle, and the first request after a break can take up to a
// minute. A request that is still unanswered after 3 seconds counts as "slow", and the app shows a
// friendly "waking up the server" message instead of a frozen screen.
const SLOW_AFTER_MS = 3000;

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

/** True while at least one request has been waiting for more than 3 seconds. */
export function useServerWaking(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => slowCount > 0,
    () => false,
  );
}
