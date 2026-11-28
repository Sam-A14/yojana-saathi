import { expect, test } from "@playwright/test";
import { countResults, nothingFound, splitFamilyLevel } from "../../lib/family-level";
import type { Eligibility, ExcludedScheme, MemberEligibility, SchemeResult } from "../../lib/types";

// A scheme about the whole family is shown once, above the people. One about a person stays on
// that person's card. These tests use small made-up results; the rule of which scheme is which
// (every rule about the household or any_member) is the API's, tested in the backend.

function scheme(slug: string, familyWide: boolean | undefined) {
  return {
    slug,
    name_en: slug.toUpperCase(),
    name_hi: null,
    level: "central",
    state: null,
    category: "housing",
    official_url: "https://example.org",
    benefit_text_en: null,
    benefit_text_hi: null,
    not_checked_en: [],
    not_checked_hi: null,
    for_whole_family: familyWide,
    deadline_start: null,
    deadline_end: null,
    verified: true,
    verified_at: null,
  };
}

const result = (slug: string, familyWide: boolean | undefined, status: SchemeResult["status"]): SchemeResult => ({
  scheme: scheme(slug, familyWide),
  status,
  reasons: [],
  passed_rules: [],
  failed_rules: [],
  unknown_rules: [],
  excluded_by: [],
  missing_documents: [],
});

const blocked = (slug: string, familyWide: boolean): ExcludedScheme => ({
  scheme: scheme(slug, familyWide),
  excluded_by: ["Ramesh"],
  failed_rules: [],
});

const person = (id: string, name: string, schemes: SchemeResult[], excluded: ExcludedScheme[] = []): MemberEligibility => ({
  member_id: id,
  nickname: name,
  schemes,
  excluded,
  not_eligible_count: 0,
});

const family = (members: MemberEligibility[]): Eligibility => ({
  household_id: "h1",
  computed_on: "2026-11-28",
  members,
  skipped_schemes: [],
});

test.describe("the whole-family section", () => {
  test("a family scheme on every card is taken out of the cards and shown once", () => {
    const e = family([
      person("a", "Asha", [result("pmay-g", true, "eligible"), result("pension", false, "eligible")]),
      person("b", "Ravi", [result("pmay-g", true, "eligible")]),
    ]);

    const { family: shown, members } = splitFamilyLevel(e);

    expect(shown.schemes.map((s) => s.scheme.slug)).toEqual(["pmay-g"]);
    expect(members[0].schemes.map((s) => s.scheme.slug)).toEqual(["pension"]);
    expect(members[1].schemes).toEqual([]);
    expect(shown.viaMemberId).toBe("a"); // the first person stands for the family
    expect(shown.viaMemberName).toBe("Asha");
  });

  test("the family's main person (relation self) stands for the family, else the first", () => {
    const withRelation = (m: MemberEligibility, relation: string) => ({ ...m, relation });
    const a = withRelation(person("a", "Meena", [result("pmay-g", true, "eligible")]), "mother");
    const b = withRelation(person("b", "Asha", [result("pmay-g", true, "eligible")]), "self");

    expect(splitFamilyLevel(family([a, b])).family.viaMemberId).toBe("b");
    expect(splitFamilyLevel(family([a, b])).family.viaMemberName).toBe("Asha");
    // no "self" among them (or an older server): the first person
    expect(splitFamilyLevel(family([person("a", "Meena", [result("pmay-g", true, "eligible")]), person("b", "Ravi", [])])).family.viaMemberId).toBe("a");
  });

  test("a scheme that is about a person stays on that person's card", () => {
    const e = family([person("a", "Asha", [result("pension", false, "eligible")]), person("b", "Ravi", [])]);

    const { family: shown, members } = splitFamilyLevel(e);

    expect(shown.schemes).toEqual([]);
    expect(shown.viaMemberId).toBeNull();
    expect(members[0].schemes).toHaveLength(1);
  });

  test("an older server that sends no for_whole_family changes nothing", () => {
    const e = family([
      person("a", "Asha", [result("pmay-g", undefined, "eligible")]),
      person("b", "Ravi", [result("pmay-g", undefined, "eligible")]),
    ]);

    const { family: shown, members } = splitFamilyLevel(e);

    expect(shown.schemes).toEqual([]);
    expect(members.map((m) => m.schemes.length)).toEqual([1, 1]);
    expect(countResults(e).fit).toBe(2); // counted per person, as before
  });

  test("a family scheme that is blocked by a member is also shown once", () => {
    const e = family([
      person("a", "Asha", [], [blocked("pmay-g", true)]),
      person("b", "Ravi", [], [blocked("pmay-g", true), blocked("kisan", false)]),
    ]);

    const { family: shown, members } = splitFamilyLevel(e);

    expect(shown.excluded.map((x) => x.scheme.slug)).toEqual(["pmay-g"]);
    expect(members[0].excluded).toEqual([]);
    expect(members[1].excluded.map((x) => x.scheme.slug)).toEqual(["kisan"]);
  });

  test("the family section is ordered: may fit, then close, then needs an answer", () => {
    const e = family([
      person("a", "Asha", [
        result("c", true, "unknown"),
        result("a", true, "eligible"),
        result("b", true, "near_miss"),
      ]),
    ]);

    expect(splitFamilyLevel(e).family.schemes.map((s) => s.status)).toEqual(["eligible", "near_miss", "unknown"]);
  });

  test("the counts count a family scheme once and a person's scheme once per person", () => {
    const e = family([
      person("a", "Asha", [result("pmay-g", true, "eligible"), result("pension", false, "eligible")]),
      person("b", "Ravi", [result("pmay-g", true, "eligible"), result("pension", false, "unknown")]),
      person("c", "Meena", [result("pmay-g", true, "eligible")]),
    ]);

    expect(countResults(e)).toEqual({ fit: 2, close: 0, unsure: 1 }); // pmay-g once + Asha's pension; Ravi's is unsure
  });

  test("nothing is found only when there is nothing for anyone, family schemes included", () => {
    expect(nothingFound(family([person("a", "Asha", []), person("b", "Ravi", [])]))).toBe(true);
    expect(nothingFound(family([person("a", "Asha", [result("pmay-g", true, "unknown")])]))).toBe(false);
    expect(nothingFound(family([person("a", "Asha", [], [blocked("pmay-g", true)])]))).toBe(false);
  });
});
