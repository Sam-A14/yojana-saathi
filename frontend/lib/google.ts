// Google Identity Services ("Continue with Google"). Decision 027 (backend) and 028 (this side).
//
// The Google client ID is public (it is in the page for anyone to read), so NEXT_PUBLIC_ is fine.
// It is baked in when the site is built. Unset or blank means the feature is off: no button.

/** The client ID, or null when it is missing or only spaces. Takes the raw value so it can be tested. */
export function readClientId(raw: string | undefined): string | null {
  const value = raw?.trim();
  return value ? value : null;
}

// Must be written as the full name: Next.js only replaces NEXT_PUBLIC_ variables it can see by name.
export const GOOGLE_CLIENT_ID = readClientId(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

const SCRIPT_URL = "https://accounts.google.com/gsi/client";

// Only the parts of Google's script we use. Not worth a types package for two calls.
export type GoogleButtonOptions = {
  type: "standard";
  theme: "outline";
  size: "large";
  text: "continue_with";
  shape: "rectangular";
  logo_alignment: "left";
  width: number;
  locale: string;
};
export type GoogleId = {
  initialize(config: {
    client_id: string;
    callback: (response: { credential: string }) => void;
    auto_select: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: GoogleButtonOptions): void;
};

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleId } };
  }
}

let loading: Promise<GoogleId> | null = null;

/** Load Google's script once and give back its sign-in object. Rejects if the script cannot load
 * (offline, or blocked by an ad blocker), so the page can quietly leave the button out. */
export function loadGoogle(): Promise<GoogleId> {
  loading ??= new Promise<GoogleId>((resolve, reject) => {
    const already = window.google?.accounts?.id;
    if (already) return resolve(already);
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      const id = window.google?.accounts?.id;
      if (id) resolve(id);
      else {
        loading = null;
        reject(new Error("Google's script did not load."));
      }
    };
    script.onerror = () => {
      loading = null; // a later visit may try again
      script.remove();
      reject(new Error("Google's script is blocked or offline."));
    };
    document.head.appendChild(script);
  });
  return loading;
}
