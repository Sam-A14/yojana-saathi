import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** One block of a page: a card with a picture and a heading. The picture is decoration; the
 * heading says what the block is. Used by the scheme page and the privacy page. */
export function IconSection({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-3xl border border-line-soft bg-surface p-5 shadow-card">
      <h2 className="flex items-center gap-3 text-xl font-extrabold">
        <span aria-hidden className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
          <Icon size={24} />
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}
