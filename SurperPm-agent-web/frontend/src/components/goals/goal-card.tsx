import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, XCircle, Clock, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { goalKeys } from "../../lib/queries/goals";
import { useExecutionStore } from "../../lib/stores/execution";
import type { Goal } from "../../lib/schemas/goal";

interface GoalCardProps {
  goal: Goal;
  workspaceId: string;
}

const statusIcons = {
  todo: Clock,
  doing: Loader2,
  done: CheckCircle,
  failed: XCircle,
};

export function GoalCard({ goal, workspaceId }: GoalCardProps) {
  const queryClient = useQueryClient();
  const progress = useExecutionStore((s) => s.progress);
  const isExecuting = goal.status === "doing" && progress?.goalId === goal.id;

  const executeMutation = useMutation({
    mutationFn: () => api.post(`/workspaces/${workspaceId}/goals/${goal.id}/execute`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all(workspaceId) });
    },
  });

  const Icon = statusIcons[goal.status] ?? Clock;

  return (
    <div className="border-2 border-border bg-card p-3 shadow-[3px_3px_0_0_#000]">
      <div className="flex items-start gap-2">
        <Icon size={16} className={`mt-0.5 shrink-0 ${
          goal.status === "done" ? "text-green-600" :
          goal.status === "failed" ? "text-red-600" :
          goal.status === "doing" ? "text-yellow-600 animate-spin" :
          "text-muted-foreground"
        }`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold truncate">{goal.title}</p>
          {goal.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{goal.description}</p>
          )}
        </div>
      </div>
      {isExecuting && progress && (
        <div className="mt-2 space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Tokens: {progress.tokenUsed.toLocaleString()}</span>
            {goal.token_budget && (
              <span>{Math.round((progress.tokenUsed / goal.token_budget) * 100)}%</span>
            )}
          </div>
          {goal.token_budget && (
            <div className="h-1.5 w-full border border-border bg-muted">
              <div
                className="h-full bg-yellow-500 transition-all"
                style={{ width: `${Math.min(100, (progress.tokenUsed / goal.token_budget) * 100)}%` }}
              />
            </div>
          )}
        </div>
      )}
      {goal.status === "todo" && (
        <button
          onClick={() => executeMutation.mutate()}
          disabled={executeMutation.isPending}
          className="mt-2 w-full text-xs py-1.5 border-2 border-border bg-primary text-primary-foreground font-bold hover:shadow-[2px_2px_0_0_#000] transition-shadow disabled:opacity-50"
        >
          {executeMutation.isPending ? "Starting..." : "Execute"}
        </button>
      )}
    </div>
  );
}
