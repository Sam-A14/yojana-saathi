import { CircleCheck, Wheat, Flower2, GraduationCap } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";

// A drawn phone showing a tiny dashboard. Pure markup and CSS: no image to download. It is for
// show only, so screen readers skip it (aria-hidden); the real dashboard is a different page.

function Avatar({ letter, colour }: { letter: string; colour: string }) {
  return (
    <span className={`flex h-9 w-9 items-center justify-center rounded-full text-base font-bold text-white ${colour}`}>
      {letter}
    </span>
  );
}

function MiniScheme({ icon, tint, children }: { icon: React.ReactNode; tint: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-line-soft bg-surface p-3 shadow-card">
      <div className="flex items-center gap-3">
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${tint}`}>{icon}</span>
        <span className="flex flex-1 flex-col gap-1.5">
          <span className="h-2.5 w-4/5 rounded-full bg-ink/80" />
          <span className="h-2 w-3/5 rounded-full bg-line-soft" />
        </span>
      </div>
      {children}
    </div>
  );
}

export function HeroPhone() {
  return (
    <div aria-hidden="true" className="float relative mx-auto w-[16rem] max-w-full">
      {/* The soft marigold light behind the phone gives it depth. */}
      <div
        className="glow absolute -inset-10 -z-10 rounded-full"
        style={{ background: "radial-gradient(circle, rgb(245 158 11 / 0.5), transparent 65%)" }}
      />
      <div className="rounded-[2.5rem] border-[6px] border-[#09241b] bg-[#09241b] shadow-[0_40px_60px_-20px_rgb(0_0_0/0.6)]">
        <div className="flex flex-col gap-3 rounded-[2rem] bg-bg p-4 pb-5">
          <span className="mx-auto h-1.5 w-16 rounded-full bg-line-soft" />
          <div className="flex items-center gap-2">
            <Avatar letter="R" colour="bg-[#1f5d46]" />
            <Avatar letter="S" colour="bg-[#8a4200]" />
            <Avatar letter="K" colour="bg-[#1e3a8a]" />
          </div>
          <div className="flex items-center gap-3 rounded-2xl bg-primary p-3 text-on-primary">
            <CircleCheck size={28} />
            <span className="flex flex-1 flex-col gap-1.5">
              <span className="h-2.5 w-4/5 rounded-full bg-on-primary/90" />
              <span className="h-2 w-3/5 rounded-full bg-on-primary/50" />
            </span>
          </div>
          <MiniScheme tint="bg-ok-bg text-ok-fg" icon={<Wheat size={22} />}>
            <StatusBadge kind="eligible" />
          </MiniScheme>
          <MiniScheme tint="bg-close-bg text-close-fg" icon={<Flower2 size={22} />}>
            <StatusBadge kind="near_miss" />
          </MiniScheme>
          <MiniScheme tint="bg-ask-bg text-ask-fg" icon={<GraduationCap size={22} />}>
            <StatusBadge kind="unknown" />
          </MiniScheme>
        </div>
      </div>
    </div>
  );
}
