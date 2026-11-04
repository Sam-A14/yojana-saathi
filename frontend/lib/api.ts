import type {
  DocumentInfo,
  Family,
  Household,
  HouseholdCreated,
  HouseholdFields,
  Member,
  MemberInput,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// status 0 means the request never reached the server (offline, or the server is still waking up).
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// What the screen should say. One place, so every page words the same problem the same way.
export function errorKind(error: unknown): "network" | "denied" | "limit" | "generic" {
  if (!(error instanceof ApiError)) return "generic";
  if (error.status === 0) return "network";
  if (error.status === 403) return "denied";
  if (error.status === 409) return "limit";
  return "generic";
}

type Options = { method?: string; token?: string; body?: unknown };

async function request<T>(path: string, { method = "GET", token, body }: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Could not reach the server.");
  }
  if (!response.ok) throw new ApiError(response.status, response.statusText);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const household = (family: Family) => `/households/${family.id}`;

export const api = {
  listDocuments: () => request<DocumentInfo[]>("/documents"),

  createHousehold: (data: HouseholdFields) =>
    request<HouseholdCreated>("/households", { method: "POST", body: data }),
  getHousehold: (family: Family) => request<Household>(household(family), { token: family.token }),

  listMembers: (family: Family) =>
    request<Member[]>(`${household(family)}/members`, { token: family.token }),
  addMember: (family: Family, data: MemberInput) =>
    request<Member>(`${household(family)}/members`, {
      method: "POST",
      token: family.token,
      body: data,
    }),
  // PATCH: only the fields sent change, so the exclusion answers survive editing a person.
  updateMember: (family: Family, memberId: string, data: Partial<MemberInput>) =>
    request<Member>(`${household(family)}/members/${memberId}`, {
      method: "PATCH",
      token: family.token,
      body: data,
    }),
  deleteMember: (family: Family, memberId: string) =>
    request<void>(`${household(family)}/members/${memberId}`, {
      method: "DELETE",
      token: family.token,
    }),
  // PUT: the full picture. A code that is left out becomes "not answered" again.
  setDocuments: (family: Family, memberId: string, documents: Record<string, boolean>) =>
    request<{ documents: Record<string, boolean> }>(
      `${household(family)}/members/${memberId}/documents`,
      { method: "PUT", token: family.token, body: { documents } },
    ),
};
