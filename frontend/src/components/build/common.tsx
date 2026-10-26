import type { SlotType } from "../../lib/api";

export const CATEGORY: Record<SlotType, { label: string; color: string; border: string; text: string; icon: string }> = {
  weapon: { label: "Weapon", color: "#d95926", border: "border-cw", text: "text-cw", icon: "⚔" },
  vitality: { label: "Vitality", color: "#199e70", border: "border-cv", text: "text-cv", icon: "✚" },
  spirit: { label: "Spirit", color: "#9085e9", border: "border-cs", text: "text-cs", icon: "✦" },
};

export const SLOT_TYPES: SlotType[] = ["weapon", "vitality", "spirit"];

export function souls(n: number | null | undefined): string {
  return n == null ? "–" : `${n.toLocaleString("en-US")}`;
}
