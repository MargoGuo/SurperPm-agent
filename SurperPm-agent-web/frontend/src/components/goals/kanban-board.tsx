import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, Loader2, Eye, CheckCircle, XCircle } from "lucide-react";
import { goalListOptions } from "../../lib/queries/goals";
import { KanbanColumn } from "./kanban-column";

const COLUMNS = [
  { status: "todo",   title: "To Do",       icon: Clock,       iconColor: "text-blue-600",   bgBar: "bg-blue-400" },
  { status: "doing",  title: "In Progress",  icon: Loader2,     iconColor: "text-yellow-600", bgBar: "bg-yellow-400" },
  { status: "review", title: "Review",       icon: Eye,         iconColor: "text-purple-600", bgBar: "bg-purple-400" },
  { status: "done",   title: "Done",         icon: CheckCircle, iconColor: "text-green-600",  bgBar: "bg-green-400" },
  { status: "failed", title: "Failed",       icon: XCircle,     iconColor: "text-red-600",    bgBar: "bg-red-400" },
] as const;

function SkeletonColumn() {
  return (
    <div className="flex flex-col border-2 border-border bg-background">
      <div className="h-2 w-full bg-accent animate-pulse" />
      <div className="px-3 py-2.5 border-b-2 border-border flex items-center gap-2">
        <div className="h-4 w-4 bg-accent animate-pulse" />
        <div className="h-3 w-16 bg-accent animate-pulse" />
      </div>
      <div className="p-2 space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="border-2 border-border bg-card p-3 space-y-2 animate-pulse shadow-[3px_3px_0_0_#000]">
            <div className="flex gap-2">
              <div className="h-4 w-4 bg-accent shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-3/4 bg-accent" />
                <div className="h-2.5 w-1/2 bg-accent" />
              </div>
            </div>
            <div className="flex gap-1">
              <div className="h-7 flex-1 bg-accent" />
              <div className="h-7 w-7 bg-accent" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface KanbanBoardProps {
  search: string;
}

export function KanbanBoard({ search }: KanbanBoardProps) {
  const { data: goals = [], isLoading } = useQuery(goalListOptions());

  const filtered = useMemo(() => {
    if (!search.trim()) return goals;
    const q = search.toLowerCase();
    return goals.filter(
      (g) =>
        g.title.toLowerCase().includes(q) ||
        (g.description ?? "").toLowerCase().includes(q)
    );
  }, [goals, search]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 h-full">
        {COLUMNS.map((_, i) => (
          <SkeletonColumn key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 h-full">
      {COLUMNS.map(({ status, title, icon, iconColor, bgBar }) => (
        <KanbanColumn
          key={status}
          title={title}
          icon={icon}
          iconColor={iconColor}
          bgBar={bgBar}
          goals={filtered.filter((g) => g.status === status)}
        />
      ))}
    </div>
  );
}
