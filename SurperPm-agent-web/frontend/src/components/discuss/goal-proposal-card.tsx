import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Target, Calendar, Check, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { goalKeys } from "@/lib/queries/goals";
import { workspaceListOptions } from "@/lib/queries/workspaces";
import { Button } from "@/components/retroui/Button";

export interface GoalProposal {
  title: string;
  description?: string;
  deadline?: string;
}

export function parseGoalProposals(content: string): { text: string; proposals: GoalProposal[] } {
  const proposals: GoalProposal[] = [];
  const text = content.replace(/```goal-proposal\s*\n([\s\S]*?)```/g, (_match, json: string) => {
    try {
      const parsed = JSON.parse(json.trim());
      if (parsed.title) proposals.push(parsed);
    } catch { /* skip malformed */ }
    return "";
  });
  return { text: text.trim(), proposals };
}

function GoalProposalItem({ proposal, workspaceId }: { proposal: GoalProposal; workspaceId: string }) {
  const [created, setCreated] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const goal = await api.post<{ id: number }>("/goals", {
        workspace_id: workspaceId,
        title: proposal.title,
        description: proposal.description || null,
        ...(proposal.deadline ? { deadline: proposal.deadline } : {}),
      });
      try {
        await api.post(`/goals/${goal.id}/execute`);
      } catch {
        // execute may fail if no repo — still count as created
      }
      return goal;
    },
    onSuccess: () => {
      setCreated(true);
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
    },
  });

  return (
    <div className="flex items-start gap-3 border-2 border-border bg-card p-3 shadow-[2px_2px_0_0_#000]">
      <Target size={16} className="mt-0.5 shrink-0 text-foreground/60" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{proposal.title}</p>
        {proposal.description && (
          <p className="text-xs text-muted-foreground mt-0.5">{proposal.description}</p>
        )}
        {proposal.deadline && (
          <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
            <Calendar size={10} />
            <span>{proposal.deadline}</span>
          </div>
        )}
      </div>
      {created ? (
        <span className="flex items-center gap-1 text-xs text-green-600 font-medium shrink-0">
          <Check size={12} /> 已创建
        </span>
      ) : (
        <Button
          size="sm"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="shrink-0 text-xs"
        >
          {mutation.isPending ? <Loader2 size={12} className="animate-spin" /> : "创建并执行"}
        </Button>
      )}
    </div>
  );
}

export function GoalProposalCards({ proposals }: { proposals: GoalProposal[] }) {
  const { data: workspaces = [] } = useQuery(workspaceListOptions());
  const workspaceId = workspaces[0]?.id ?? "";
  const queryClient = useQueryClient();
  const [allCreated, setAllCreated] = useState(false);

  const batchMutation = useMutation({
    mutationFn: () =>
      api.post("/goals/batch", {
        workspace_id: workspaceId,
        goals: proposals.map((p) => ({
          workspace_id: workspaceId,
          title: p.title,
          description: p.description || null,
          ...(p.deadline ? { deadline: p.deadline } : {}),
        })),
      }),
    onSuccess: () => {
      setAllCreated(true);
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
    },
  });

  if (!workspaceId || proposals.length === 0) return null;

  return (
    <div className="mt-2 space-y-2">
      {proposals.map((p, idx) => (
        <GoalProposalItem key={idx} proposal={p} workspaceId={workspaceId} />
      ))}
      {proposals.length > 1 && (
        <div className="flex justify-end">
          {allCreated ? (
            <span className="text-xs text-green-600 font-medium flex items-center gap-1">
              <Check size={12} /> 全部已创建
            </span>
          ) : (
            <Button
              size="sm"
              onClick={() => batchMutation.mutate()}
              disabled={batchMutation.isPending}
              className="text-xs"
            >
              {batchMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : "全部创建"}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
