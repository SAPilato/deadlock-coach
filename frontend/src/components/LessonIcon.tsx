import { Amphora, BookOpen, Castle, FastForward, Footprints, Handshake, Package, Repeat, ShoppingCart, Skull, Snowflake, Waves, type LucideIcon } from "lucide-react";
import { Icon } from "./ui";

// Lesson icons are named in backend/app/learn/lessons.py; unknown names fall back to a book.
const ICONS: Record<string, LucideIcon> = {
  waves: Waves,
  "fast-forward": FastForward,
  snowflake: Snowflake,
  repeat: Repeat,
  package: Package,
  "shopping-cart": ShoppingCart,
  castle: Castle,
  handshake: Handshake,
  skull: Skull,
  footprints: Footprints,
  amphora: Amphora,
};

export const LESSON_ICON_NAMES = Object.keys(ICONS);

export default function LessonIcon({ name, className = "" }: { name: string; className?: string }) {
  return <Icon icon={ICONS[name] ?? BookOpen} className={className} />;
}
