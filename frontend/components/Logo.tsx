/** The mark: a marigold sun over a green roof line. Decorative, the name is always written next to it. */
export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true" className="shrink-0">
      <rect width="36" height="36" rx="10" fill="#1f5d46" />
      <circle cx="18" cy="15" r="7" fill="#f59e0b" />
      <path d="M5 28 L18 17 L31 28 Z" fill="#0f3a2b" />
      <rect x="14" y="23" width="8" height="5" rx="1" fill="#fff8ec" />
    </svg>
  );
}
