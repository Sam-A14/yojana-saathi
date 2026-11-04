"use client";

import Link from "next/link";
import { type ComponentProps, type ReactNode, useId } from "react";

// Small building blocks. Every tap target is at least 48px tall (min-h-12) and text is 16px or
// bigger, so the screens work with a thumb on a cheap phone.

const buttonBase =
  "inline-flex min-h-12 items-center justify-center rounded-lg px-5 text-base font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:cursor-not-allowed disabled:opacity-50";
const buttonLook = {
  primary: "bg-emerald-700 text-white hover:bg-emerald-800",
  secondary: "border border-zinc-400 hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800",
  danger: "border border-red-700 text-red-800 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950",
};
type Look = keyof typeof buttonLook;

/** The look of a button, for places that need a real link (an official website opens in a new tab). */
export const buttonClass = (variant: Look = "primary", extra = "") =>
  `${buttonBase} ${buttonLook[variant]} ${extra}`;

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<"button"> & { variant?: Look }) {
  return (
    <button type="button" className={`${buttonBase} ${buttonLook[variant]} ${className}`} {...props} />
  );
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Look }) {
  return <Link className={`${buttonBase} ${buttonLook[variant]} ${className}`} {...props} />;
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-base text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100"
    >
      {children}
    </p>
  );
}

const inputLook =
  "min-h-12 w-full rounded-lg border border-zinc-400 bg-transparent px-3 text-base dark:border-zinc-600";

function FieldShell({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-base font-semibold">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-zinc-600 dark:text-zinc-400">
          {hint}
        </p>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextField({
  label,
  hint,
  error,
  value,
  onChange,
  ...props
}: {
  label: string;
  hint?: string;
  error?: string | null;
  value: string;
  onChange: (value: string) => void;
} & Omit<ComponentProps<"input">, "value" | "onChange">) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} hint={hint} error={error}>
      <input
        id={id}
        className={inputLook}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined}
        {...props}
      />
    </FieldShell>
  );
}

export type Option = { value: string; label: string };

/** A dropdown. The first entry (empty value) means "no answer", which the API stores as null. */
export function SelectField({
  label,
  hint,
  error,
  value,
  onChange,
  options,
  emptyLabel,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  value: string | null;
  onChange: (value: string | null) => void;
  options: Option[];
  emptyLabel: string;
}) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} hint={hint} error={error}>
      <select
        id={id}
        className={inputLook}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value || null)}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined}
      >
        <option value="">{emptyLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

/**
 * A question with a few big answers to tap, plus "Not sure" (value null).
 * Null is what the API stores as "not answered", and the rules engine then answers "unknown"
 * instead of guessing, so "Not sure" is always offered.
 */
export function ChoiceGroup({
  legend,
  hint,
  options,
  value,
  onChange,
  notSureLabel,
}: {
  legend: string;
  hint?: string;
  options: Option[];
  value: string | null;
  onChange: (value: string | null) => void;
  notSureLabel: string;
}) {
  const name = useId();
  const all: { value: string | null; label: string }[] = [
    ...options,
    { value: null, label: notSureLabel },
  ];
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-base font-semibold">{legend}</legend>
      {hint && <p className="text-sm text-zinc-600 dark:text-zinc-400">{hint}</p>}
      <div className="flex flex-wrap gap-2">
        {all.map((option) => (
          <label key={option.value ?? "not-sure"} className="relative">
            <input
              type="radio"
              name={name}
              className="peer absolute inset-0 opacity-0"
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span className="flex min-h-12 items-center rounded-lg border border-zinc-400 px-4 text-base peer-checked:border-emerald-700 peer-checked:bg-emerald-50 peer-checked:font-semibold peer-focus-visible:outline-2 peer-focus-visible:outline-emerald-700 dark:border-zinc-600 dark:peer-checked:bg-emerald-950">
              {option.label}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** Yes / No / Not sure for a true-false fact. */
export function YesNoGroup({
  legend,
  hint,
  value,
  onChange,
  labels,
}: {
  legend: string;
  hint?: string;
  value: boolean | null;
  onChange: (value: boolean | null) => void;
  labels: { yes: string; no: string; notSure: string };
}) {
  return (
    <ChoiceGroup
      legend={legend}
      hint={hint}
      options={[
        { value: "yes", label: labels.yes },
        { value: "no", label: labels.no },
      ]}
      value={value === null ? null : value ? "yes" : "no"}
      onChange={(choice) => onChange(choice === null ? null : choice === "yes")}
      notSureLabel={labels.notSure}
    />
  );
}
