import type { LucideIcon } from "lucide-react";
import { GoalCard } from "./goal-card";
import type { Goal } from "../../lib/schemas/goal";

interface KanbanColumnProps {
  title: string;
  icon: LucideIcon;
  iconColor: string;
  bgBar: string;
  goals: Goal[];
}

export function KanbanColumn({ title, icon: Icon, iconColor, bgBar, goals }: KanbanColumnProps) {
  return (
    <div className="flex flex-col border-2 border-border bg-background min-h-0">
      {/* colored top bar — thicker for visual weight */}
      <div className={`h-2 w-full shrink-0 ${bgBar}`} />

      {/* header */}
      <div className="flex items-center gap-2 px-3 py-2.5 shrink-0 border-b-2 border-border">
        <Icon size={15} className={`shrink-0 ${iconColor}`} />
        <h3 className="font-bold text-xs font-head uppercase tracking-wide flex-1">{title}</h3>
        <span className="inline-flex items-center justify-center min-w-[22px] h-5 px-1.5 text-[11px] font-head text-secondary-foreground bg-secondary border-2 border-border">
          {goals.length}
        </span>
      </div>

      {/* cards */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 nb-scrollbar">
        {goals.map((goal) => (
          <GoalCard key={goal.id} goal={goal} />
        ))}
        {goals.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-12">
            <Icon size={24} className="opacity-15" />
            <p className="text-[10px] uppercase tracking-widest font-head opacity-30">Empty</p>
          </div>
        )}
      </div>
    </div>
  );
}
