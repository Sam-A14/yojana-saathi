"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Counts down whole seconds after `restart()`; `left` is 0 when it is not running or has finished.
 * It works from an end time instead of counting ticks, so a phone that pauses the page (screen off)
 * still shows the right number when it wakes up.
 */
export function useCountdown(seconds: number) {
  const [left, setLeft] = useState(0);
  const [endsAt, setEndsAt] = useState<number | null>(null);

  useEffect(() => {
    if (endsAt === null) return;
    const timer = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      setLeft(remaining);
      if (remaining === 0) clearInterval(timer);
    }, 1000);
    return () => clearInterval(timer);
  }, [endsAt]);

  const restart = useCallback(() => {
    setLeft(seconds);
    setEndsAt(Date.now() + seconds * 1000);
  }, [seconds]);

  return { left, restart };
}
