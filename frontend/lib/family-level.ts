import type { Eligibility, ExcludedScheme, MemberEligibility, SchemeResult } from "./types";

/**
 * Schemes about the whole family are shown once, not on every member's card.
 *
 * A scheme is "for the whole family" (the API says so, `for_whole_family`) when every rule is about
 * the household or about the members as a group ("no member pays income tax"). Its answer is the
 * same whichever member you ask, so one member's result stands for all of them. A scheme that is
 * about a person stays on that person's card.
 */
export type FamilyResults = {
  schemes: SchemeResult[];
  excluded: ExcludedScheme[];
  /** The member whose result stands for the family (the first one): used for links and papers. */
  viaMemberId: string | null;
  viaMemberName: string | null;
};

const ORDER: Record<SchemeResult["status"], number> = { eligible: 0, near_miss: 1, unknown: 2 };

export function splitFamilyLevel(eligibility: Eligibility): {
  family: FamilyResults;
  members: MemberEligibility[];
} {
  const seen = new Set<string>();
  const schemes: SchemeResult[] = [];
  const excluded: ExcludedScheme[] = [];
  for (const member of eligibility.members) {
    for (const result of member.schemes) {
      if (result.scheme.for_whole_family && !seen.has(result.scheme.slug)) {
        seen.add(result.scheme.slug);
        schemes.push(result);
      }
    }
    for (const item of member.excluded) {
      if (item.scheme.for_whole_family && !seen.has(item.scheme.slug)) {
        seen.add(item.scheme.slug);
        excluded.push(item);
      }
    }
  }
  schemes.sort((a, b) => ORDER[a.status] - ORDER[b.status] || a.scheme.name_en.localeCompare(b.scheme.name_en));
  const first = eligibility.members[0];
  const members = eligibility.members.map((member) => ({
    ...member,
    schemes: member.schemes.filter((s) => !s.scheme.for_whole_family),
    excluded: member.excluded.filter((e) => !e.scheme.for_whole_family),
  }));
  return {
    family: {
      schemes,
      excluded,
      viaMemberId: schemes.length + excluded.length > 0 && first ? first.member_id : null,
      viaMemberName: schemes.length + excluded.length > 0 && first ? first.nickname : null,
    },
    members,
  };
}

/** How many results fall in each group: a family scheme once, a person's scheme once per person. */
export function countResults(eligibility: Eligibility) {
  const { family, members } = splitFamilyLevel(eligibility);
  const all = [...family.schemes, ...members.flatMap((m) => m.schemes)];
  const of = (status: string) => all.filter((s) => s.status === status).length;
  return { fit: of("eligible"), close: of("near_miss"), unsure: of("unknown") };
}

/** True when nothing at all was found for anyone (see the dashboard). */
export function nothingFound(eligibility: Eligibility): boolean {
  const { family, members } = splitFamilyLevel(eligibility);
  const { fit, close, unsure } = countResults(eligibility);
  return (
    fit + close + unsure === 0 && family.excluded.length === 0 && members.every((m) => m.excluded.length === 0)
  );
}
