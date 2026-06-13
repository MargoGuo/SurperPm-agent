import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, Loader2, Eye, CheckCircle, XCircle, Search } from "lucide-react";
import { goalListOptions } from "@/lib/queries/goals";
import { KanbanBoard } from "@/components/goals/kanban-board";
import { CreateGoalDialog } from "@/components/goals/create-goal-dialog";
import { Text } from "@/components/retroui/Text";
import { Input } from "@/components/retroui/Input";

const STATS = [
  { status: "todo", label: "To Do", icon: Clock, color: "border-l-blue-400", textColor: "text-blue-600" },
  { status: "doing", label: "In Progress", icon: Loader2, color: "border-l-yellow-400", textColor: "text-yellow-600" },
  { status: "review", label: "Review", icon: Eye, color: "border-l-purple-400", textColor: "text-purple-600" },
  { status: "done", label: "Done", icon: CheckCircle, color: "border-l-green-400", textColor: "text-green-600" },
  { status: "failed", label: "Failed", icon: XCircle, color: "border-l-red-400", textColor: "text-red-600" },
] as const;

export default function GoalListPage() {
  const [search, setSearch] = useState("");
  const { data: goals = [] } = useQuery(goalListOptions());

  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const g of goals) {
      m[g.status] = (m[g.status] ?? 0) + 1;
    }
    return { todo: 0, doing: 0, review: 0, done: 0, failed: 0, ...m };
  }, [goals]);

  const total = goals.length;

  return (
    <div className="flex flex-col h-full p-6">
      {/* header */}
      <div className="flex items-start justify-between mb-5 gap-4">
        <div className="flex-1">
          <Text as="h2" className="text-2xl">Goals</Text>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-foreground/50 font-mono">{total} total</span>
          </div>
        </div>
        <CreateGoalDialog />
      </div>

      {/* stats bar */}
      <div className="grid grid-cols-5 gap-2 mb-5">
        {STATS.map(({ status, label, icon: Icon, color, textColor }) => (
          <div
            key={status}
            className={`flex items-center gap-2.5 border-2 border-border border-l-4 ${color} bg-card px-3 py-2.5 shadow-[2px_2px_0_0_#000]`}
          >
            <Icon size={18} className={`shrink-0 ${textColor}`} />
            <div>
              <div className="text-xl font-head leading-none">{counts[status]}</div>
              <div className="text-[10px] uppercase tracking-wider text-foreground/50 font-bold leading-tight">
                {label}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* search */}
      <div className="relative mb-4">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40 pointer-events-none"
        />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search goals..."
          className="pl-9 border-2 shadow-[2px_2px_0_0_#000]"
        />
      </div>

      {/* board */}
      {goals.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <div className="border-2 border-border p-5 shadow-[4px_4px_0_0_#000] bg-card">
            <Search size={48} className="opacity-20" />
          </div>
          <p className="text-sm font-head">No goals yet</p>
          <p className="text-xs text-foreground/40">Create your first goal to get started</p>
          <CreateGoalDialog />
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <KanbanBoard search={search} />
        </div>
      )}
    </div>
  );
}
