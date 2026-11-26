import { avatarColour, initials } from "@/lib/initials";

// Full class names (not built from the number) so Tailwind can see and keep them.
const COLOURS = [
  "bg-av1-bg text-av1-fg",
  "bg-av2-bg text-av2-fg",
  "bg-av3-bg text-av3-fg",
  "bg-av4-bg text-av4-fg",
  "bg-av5-bg text-av5-fg",
];

/** A round badge with a person's initials. Decorative: the name is always written next to it, so
 * it is hidden from screen readers. */
export function Avatar({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  const box = size === "lg" ? "h-14 w-14 text-xl" : "h-12 w-12 text-lg";
  return (
    <span
      aria-hidden
      className={`flex shrink-0 items-center justify-center rounded-full font-extrabold ${box} ${COLOURS[avatarColour(name)]}`}
    >
      {initials(name)}
    </span>
  );
}
