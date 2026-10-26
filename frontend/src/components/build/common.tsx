import type { SlotType } from "../../lib/api";
import { Crosshair, Heart, type LucideIcon, Sparkles } from "lucide-react";

export const CATEGORY: Record<SlotType, { label: string; color: string; border: string; text: string; icon: LucideIcon }> = {
  weapon: { label: "Weapon", color: "#d95926", border: "border-cw", text: "text-cw", icon: Crosshair },
  vitality: { label: "Vitality", color: "#199e70", border: "border-cv", text: "text-cv", icon: Heart },
  spirit: { label: "Spirit", color: "#9085e9", border: "border-cs", text: "text-cs", icon: Sparkles },
};

export const SLOT_TYPES: SlotType[] = ["weapon", "vitality", "spirit"];

export function souls(n: number | null | undefined): string {
  return n == null ? "–" : `${n.toLocaleString("en-US")}`;
}
