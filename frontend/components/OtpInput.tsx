"use client";

import { useId, useState } from "react";

/**
 * A one-time code shown as separate boxes, but typed into ONE real input.
 *
 * The input sits invisibly over the boxes and covers all of them (so the whole row is one big tap
 * target). That keeps everything a normal input gives for free: the numeric keyboard, a code
 * suggested by the phone (autocomplete="one-time-code"), paste, delete, and screen readers, which
 * hear one labelled field and not six. The boxes are only a picture of what was typed.
 */
export function OtpInput({
  label,
  value,
  onChange,
  length = 6,
}: {
  label: string;
  value: string;
  onChange: (digits: string) => void;
  length?: number;
}) {
  const id = useId();
  const [focused, setFocused] = useState(false);
  // The box that the next digit goes into (the last box once all are filled).
  const active = Math.min(value.length, length - 1);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-lg font-bold">
        {label}
      </label>
      <div className="relative">
        <div aria-hidden className="grid gap-2" style={{ gridTemplateColumns: `repeat(${length}, minmax(0, 1fr))` }}>
          {Array.from({ length }, (_, index) => (
            <span
              key={index}
              data-testid="otp-box"
              className={`flex h-14 items-center justify-center rounded-xl border-2 bg-surface text-2xl font-extrabold transition ${
                focused && index === active ? "border-primary ring-4 ring-primary/30" : "border-line"
              }`}
            >
              {value[index] ?? ""}
            </span>
          ))}
        </div>
        <input
          id={id}
          value={value}
          // No maxLength: it would cut "123 456" (pasted with a space) to 5 digits before this
          // filter keeps the first six digits.
          onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, length))}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]*"
          enterKeyHint="go"
          autoCorrect="off"
          spellCheck={false}
          className="absolute inset-0 h-full w-full cursor-text opacity-0"
        />
      </div>
    </div>
  );
}
