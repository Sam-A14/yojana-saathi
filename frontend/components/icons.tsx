import {
  Accessibility,
  Baby,
  BadgeIndianRupee,
  Flower2,
  Fingerprint,
  FileText,
  GraduationCap,
  HandHeart,
  Heart,
  House,
  IdCard,
  IndianRupee,
  Landmark,
  Map as MapIcon,
  CircleCheck,
  CircleHelp,
  CircleX,
  Ribbon,
  ShoppingBasket,
  Stamp,
  Target,
  Users,
  Vote,
  Wheat,
  type LucideIcon,
} from "lucide-react";
import type { ResultKind } from "./StatusBadge";

// One place that decides which picture stands for what. Icons come from lucide-react (named
// imports, so only the ones listed here end up in the page). They are decorative: a word is
// always written next to them, so they carry aria-hidden and never stand alone.

const DOCUMENT_ICONS: Record<string, LucideIcon> = {
  aadhaar_card: Fingerprint,
  bank_account_aadhaar_linked: Landmark,
  birth_certificate: Baby,
  bpl_card: IdCard,
  caste_certificate: Stamp,
  disability_certificate: Accessibility,
  domicile_certificate: House,
  family_register: Users,
  income_certificate: IndianRupee,
  land_record: MapIcon,
  marksheet: GraduationCap,
  marriage_certificate: Heart,
  ration_card: ShoppingBasket,
  spouse_death_certificate: Ribbon,
  voter_id: Vote,
};

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  student: GraduationCap,
  farmer: Wheat,
  pension: HandHeart,
  widow_pension: Flower2,
};

const STATUS_ICONS: Record<ResultKind, LucideIcon> = {
  eligible: CircleCheck,
  near_miss: Target,
  unknown: CircleHelp,
  excluded: CircleX,
};

/** The words for a category (messages "categories"); a category we have no words for reads "Other". */
export function categoryKey(category: string): "student" | "farmer" | "pension" | "widow_pension" | "other" {
  return category in CATEGORY_ICONS ? (category as "student" | "farmer" | "pension" | "widow_pension") : "other";
}

type IconProps = { className?: string; size?: number };

export function DocumentIcon({ code, ...props }: IconProps & { code: string }) {
  const Icon = DOCUMENT_ICONS[code] ?? FileText; // a paper we have no picture for still shows
  return <Icon {...props} />;
}

export function CategoryIcon({ category, ...props }: IconProps & { category: string }) {
  const Icon = CATEGORY_ICONS[category] ?? BadgeIndianRupee; // a new category must not break a page
  return <Icon {...props} />;
}

export function StatusIcon({ kind, ...props }: IconProps & { kind: ResultKind }) {
  const Icon = STATUS_ICONS[kind];
  return <Icon {...props} />;
}
