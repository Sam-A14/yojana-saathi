import {
  Accessibility,
  Baby,
  BadgeIndianRupee,
  CarFront,
  Contact,
  CreditCard,
  Flower2,
  Fingerprint,
  FileText,
  Gift,
  GraduationCap,
  HandHeart,
  Hammer,
  Heart,
  HeartPulse,
  House,
  IdCard,
  IndianRupee,
  ListChecks,
  Landmark,
  Map as MapIcon,
  CircleCheck,
  CircleHelp,
  CircleX,
  PartyPopper,
  Receipt,
  Ribbon,
  ShieldCheck,
  ShoppingBasket,
  Stamp,
  Target,
  Users,
  Vote,
  Wheat,
  type LucideIcon,
} from "lucide-react";
import { CATEGORIES, type Category } from "@/lib/categories";
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
  driving_licence: CarFront,
  family_register: Users,
  income_certificate: IndianRupee,
  land_record: MapIcon,
  marksheet: GraduationCap,
  mgnrega_job_card: Hammer,
  marriage_certificate: Heart,
  pan_card: CreditCard,
  fee_receipt_or_admission_letter: Receipt,
  ration_card: ShoppingBasket,
  spouse_death_certificate: Ribbon,
  student_id_card: Contact,
  voter_id: Vote,
};

const CATEGORY_ICONS: Record<Category, LucideIcon> = {
  education: GraduationCap,
  health: HeartPulse,
  housing: House,
  family_welfare: Users,
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
export function categoryKey(category: string): Category | "other" {
  return (CATEGORIES as readonly string[]).includes(category) ? (category as Category) : "other";
}

/** The picture at the top of each section of a scheme page (the heading always carries the words). */
export const SECTION_ICONS = {
  summary: Gift,
  why: ListChecks,
  unchecked: CircleHelp, // "Rules we can't check: ask the office"
  docs: FileText,
  official: ShieldCheck,
  celebrate: PartyPopper,
} satisfies Record<string, LucideIcon>;

type IconProps = { className?: string; size?: number };

export function DocumentIcon({ code, ...props }: IconProps & { code: string }) {
  const Icon = DOCUMENT_ICONS[code] ?? FileText; // a paper we have no picture for still shows
  return <Icon {...props} />;
}

export function CategoryIcon({ category, ...props }: IconProps & { category: string }) {
  const Icon = CATEGORY_ICONS[categoryKey(category) as Category] ?? BadgeIndianRupee; // a new category must not break a page
  return <Icon {...props} />;
}

export function StatusIcon({ kind, ...props }: IconProps & { kind: ResultKind }) {
  const Icon = STATUS_ICONS[kind];
  return <Icon {...props} />;
}
