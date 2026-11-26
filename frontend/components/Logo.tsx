/** The mark: a gold sun over a navy roof line. Decorative, the name is always written next to it.
 * Filled from the colour tokens, so it stays visible in the dark theme too. */
export function Logo({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true" className="shrink-0">
      <rect width="36" height="36" rx="10" className="fill-primary" />
      <circle cx="18" cy="15" r="7" className="fill-accent" />
      <path d="M5 28 L18 17 L31 28 Z" className="fill-hero" />
      <rect x="14" y="23" width="8" height="5" rx="1" className="fill-on-hero" />
    </svg>
  );
}
