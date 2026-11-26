// Ten bits of paper that fly out once. Pure CSS (see "confetti" in globals.css): no script, and
// switched off for people who ask for less motion. Decorative, so hidden from screen readers.
// Where each piece flies (x, y, turn), when it starts, and its colour.
const PIECES = [
  { x: "-70px", y: "-60px", r: "-200deg", d: "0s", c: "bg-accent" },
  { x: "-40px", y: "-85px", r: "140deg", d: "0.05s", c: "bg-primary" },
  { x: "0px", y: "-95px", r: "-90deg", d: "0.1s", c: "bg-av4-fg" },
  { x: "40px", y: "-85px", r: "220deg", d: "0.03s", c: "bg-av5-fg" },
  { x: "70px", y: "-60px", r: "-160deg", d: "0.08s", c: "bg-accent" },
  { x: "-85px", y: "-20px", r: "180deg", d: "0.12s", c: "bg-av3-fg" },
  { x: "85px", y: "-20px", r: "-120deg", d: "0.04s", c: "bg-primary" },
  { x: "-55px", y: "-40px", r: "90deg", d: "0.15s", c: "bg-av5-fg" },
  { x: "55px", y: "-40px", r: "-70deg", d: "0.07s", c: "bg-av2-fg" },
  { x: "15px", y: "-70px", r: "300deg", d: "0.11s", c: "bg-av4-fg" },
] as const;

export function Celebration() {
  return (
    <span aria-hidden data-testid="celebration" className="pointer-events-none absolute inset-0">
      {PIECES.map((piece, index) => (
        <span
          key={index}
          className={`confetti-piece ${piece.c}`}
          style={{ "--x": piece.x, "--y": piece.y, "--r": piece.r, "--d": piece.d } as React.CSSProperties}
        />
      ))}
    </span>
  );
}
