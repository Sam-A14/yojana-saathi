"use client";

import Link from "next/link";
import { type ComponentProps, type ReactNode, useId } from "react";
import { buttonBase, buttonClass, buttonLook, type Look } from "./button-styles";

// Re-exported so client code keeps one import path.
export { buttonClass };

// Small building blocks. Every tap target is at least 48px tall (buttons are 56px) and text is
// 16px or bigger, so the screens work with a thumb on a cheap phone. Colours come from the tokens
// in globals.css, so dark mode needs no extra classes here.

/** A white card with a soft shadow. The one container every screen uses for a "thing". */
export function Card({ className = "", ...props }: ComponentProps<"div">) {
  return (
    <div
      className={`rounded-2xl border border-line-soft bg-surface p-5 shadow-card ${className}`}
      {...props}
    />
  );
}

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
      className="rounded-xl border-2 border-danger bg-danger-bg px-4 py-3 text-base font-semibold text-danger"
    >
      {children}
    </p>
  );
}

const inputLook =
  "min-h-14 w-full rounded-xl border-2 border-line bg-surface px-4 text-lg";

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
      <label htmlFor={id} className="text-lg font-bold">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-base text-muted">
          {hint}
        </p>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-base font-semibold text-danger">
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
      <legend className="text-lg font-bold">{legend}</legend>
      {hint && <p className="text-base text-muted">{hint}</p>}
      <div className="flex flex-wrap gap-3">
        {all.map((option) => (
          <label key={option.value ?? "not-sure"} className="relative">
            <input
              type="radio"
              name={name}
              className="peer absolute inset-0 h-full w-full cursor-pointer opacity-0"
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span className="flex min-h-14 items-center rounded-xl border-2 border-line bg-surface px-5 text-lg transition-colors peer-checked:border-primary peer-checked:bg-primary-soft peer-checked:font-bold peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary">
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
