"use client";

import { Check, CircleHelp, X, type LucideIcon } from "lucide-react";
import { useId } from "react";
import { DocumentIcon } from "./icons";

type Labels = { yes: string; no: string; notSure: string };

// Each answer is a colour AND an icon AND a word, so none depends on seeing colours.
const CHOICES: { key: "yes" | "no" | "notSure"; value: boolean | null; Icon: LucideIcon; picked: string }[] = [
  { key: "yes", value: true, Icon: Check, picked: "peer-checked:border-ok-fg peer-checked:bg-ok-bg peer-checked:text-ok-fg" },
  { key: "no", value: false, Icon: X, picked: "peer-checked:border-block-fg peer-checked:bg-block-bg peer-checked:text-block-fg" },
  { key: "notSure", value: null, Icon: CircleHelp, picked: "peer-checked:border-ask-fg peer-checked:bg-ask-bg peer-checked:text-ask-fg" },
];

/**
 * One paper as a card: its picture and name, then three big answers to tap (Yes / No / Not sure).
 * The answers are real radio buttons in a named group, so a screen reader and the keyboard work
 * the same as before the card look. "Not sure" is null, which the API stores as "not answered".
 */
export function DocumentChoice({
  code,
  label,
  value,
  onChange,
  labels,
}: {
  code: string;
  label: string;
  value: boolean | null;
  onChange: (value: boolean | null) => void;
  labels: Labels;
}) {
  const name = useId();
  return (
    <div role="group" aria-labelledby={`${name}-label`} className="flex flex-col gap-3 rounded-2xl border border-line-soft bg-surface p-4 shadow-card">
      <div className="flex items-center gap-3">
        <span aria-hidden className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
          <DocumentIcon code={code} size={26} />
        </span>
        <span id={`${name}-label`} className="text-lg font-bold">
          {label}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {CHOICES.map(({ key, value: choice, Icon, picked }) => (
          <label key={key} className="relative">
            <input
              type="radio"
              name={name}
              className="peer absolute inset-0 h-full w-full cursor-pointer opacity-0"
              checked={value === choice}
              onChange={() => onChange(choice)}
            />
            <span
              className={`flex min-h-16 flex-col items-center justify-center gap-1 rounded-xl border-2 border-line bg-surface px-1 py-2 text-center text-base font-semibold leading-tight transition peer-checked:font-bold peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary peer-active:scale-95 ${picked}`}
            >
              <Icon size={22} aria-hidden />
              {labels[key]}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
