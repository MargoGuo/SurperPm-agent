import { useState, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle, XCircle, Clock, Loader2, RotateCcw,
  Ban, Eye, Pause, Play, Trash2,
} from "lucide-react";
import { motion } from "motion/react";
import { api } from "../../lib/api";
import { goalKeys } from "../../lib/queries/goals";
import { executionListOptions, executionKeys } from "../../lib/queries/executions";
import { useExecutionStore } from "../../lib/stores/execution";
import type { Goal } from "../../lib/schemas/goal";
import { Button } from "@/components/retroui/Button";
import { Badge } from "@/components/retroui/Badge";
import { Dialog } from "@/components/retroui/Dialog";
import { Text } from "@/components/retroui/Text";

/* ─── helpers ─── */

const statusCfg: Record<string, { icon: typeof Clock; label: string; borderL: string; bar: string; iconColor: string }> = {
  todo:   { icon: Clock,       label: "To Do",       borderL: "border-l-blue-400",   bar: "bg-blue-400",   iconColor: "text-blue-600" },
  doing:  { icon: Loader2,     label: "In Progress",  borderL: "border-l-yellow-400", bar: "bg-yellow-400", iconColor: "text-yellow-600" },
  review: { icon: Eye,         label: "Review",       borderL: "border-l-purple-400", bar: "bg-purple-400", iconColor: "text-purple-600" },
  done:   { icon: CheckCircle, label: "Done",         borderL: "border-l-green-400",  bar: "bg-green-400",  iconColor: "text-green-600" },
  failed: { icon: XCircle,     label: "Failed",       borderL: "border-l-red-400",    bar: "bg-red-400",    iconColor: "text-red-600" },
};

interface GoalCardProps { goal: Goal }

export function GoalCard({ goal }: GoalCardProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [confirmDelete, setConfirmDelete] = useState(false);

  /* ── optimistic local state ── */
  const [localExecId, setLocalExecId] = useState<string | null>(null);
  const [localPaused, setLocalPaused] = useState<boolean | null>(null);

  const cfg = statusCfg[goal.status] ?? statusCfg.todo;
  const Icon = cfg.icon;

  const progress = useExecutionStore((s) => s.progress);
  const execId = progress?.execution_id ?? localExecId;
  const isExecuting = goal.status === "doing" && !!execId;
  const isPaused = localPaused ?? (progress?.paused === true);

  /* ── executions query (background only, not gating buttons) ── */
  const { data: executions = [] } = useQuery({
    ...executionListOptions(goal.id),
    enabled: goal.status === "doing",
    staleTime: 10_000,   // don't refetch constantly
  });

  const runningExecution = executions.find(e => e.status === "pending" || e.status === "running");
  const finalExecId = execId ?? runningExecution?.id;

  /* ── cache helpers ── */
  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: goalKeys.all() });
    queryClient.invalidateQueries({ queryKey: executionKeys.all(goal.id) });
  }, [queryClient, goal.id]);

  /* ── mutations with optimistic updates ── */

  const executeMutation = useMutation({
    mutationFn: () => api.post(`/goals/${goal.id}/execute`) as Promise<{ execution_id: string }>,
    onMutate: () => {
      // Optimistic: show doing state immediately
      setLocalExecId("pending"); // placeholder — real ID comes from onSuccess
    },
    onSuccess: (data: { execution_id?: string }) => {
      if (data?.execution_id) setLocalExecId(data.execution_id);
      invalidate();
    },
    onError: () => setLocalExecId(null),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => api.post(`/goals/${goal.id}/executions/${id}/pause`),
    onMutate: () => setLocalPaused(true),
    onSuccess: () => {
      useExecutionStore.getState().updateProgress({ paused: true } as any);
      invalidate();
    },
    onError: () => setLocalPaused(null),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/goals/${goal.id}/executions/${id}/resume`),
    onMutate: () => setLocalPaused(false),
    onSuccess: () => {
      useExecutionStore.getState().updateProgress({ paused: false } as any);
      invalidate();
    },
    onError: () => setLocalPaused(null),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.post(`/goals/${goal.id}/executions/${id}/cancel`),
    onMutate: () => setLocalExecId(null),
    onSuccess: () => invalidate(),
    onError: () => setLocalExecId(null),
  });

  const reviewMutation = useMutation({
    mutationFn: (action: string) => api.post(`/goals/${goal.id}/review`, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/goals/${goal.id}`),
    onSuccess: () => {
      setConfirmDelete(false);
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
    },
  });

  return (
    <>
      {isExecuting && !isPaused ? (
        <motion.div
          animate={{ boxShadow: ["3px 3px 0 0 #000", "3px 3px 0 0 rgba(250,204,21,0.7)", "3px 3px 0 0 #000"] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className={`border-2 border-border bg-card cursor-pointer hover:shadow-[1px_1px_0_0_#000] hover:translate-x-[2px] hover:translate-y-[2px] transition-all ${cfg.borderL} border-l-4`}
          onClick={() => navigate(`/goals/${goal.id}/execute`)}
        >
          <CardContent {...{ goal, cfg, Icon, isExecuting, isPaused, progress, finalExecId,
            executeMutation, pauseMutation, resumeMutation, cancelMutation, reviewMutation,
            setConfirmDelete }} />
        </motion.div>
      ) : (
        <div
          className={`border-2 border-border bg-card cursor-pointer hover:shadow-[1px_1px_0_0_#000] hover:translate-x-[2px] hover:translate-y-[2px] transition-all shadow-[3px_3px_0_0_#000] ${cfg.borderL} border-l-4`}
          onClick={() => navigate(`/goals/${goal.id}/execute`)}
        >
          <CardContent {...{ goal, cfg, Icon, isExecuting, isPaused, progress, finalExecId,
            executeMutation, pauseMutation, resumeMutation, cancelMutation, reviewMutation,
            setConfirmDelete }} />
        </div>
      )}

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <Dialog.Content size="sm">
          <Dialog.Header><Text as="h3" className="text-sm">Delete Goal</Text></Dialog.Header>
          <div className="p-4 space-y-4">
            <p className="text-sm text-foreground/70">
              Delete "{goal.title}"? This removes the goal and its execution history and cannot be undone.
            </p>
            {deleteMutation.isError && <p className="text-xs text-red-600">Failed to delete. Try again.</p>}
            <Dialog.Footer>
              <Dialog.Close render={<Button type="button" variant="outline">Cancel</Button>} />
              <Button type="button" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </Button>
            </Dialog.Footer>
          </div>
        </Dialog.Content>
      </Dialog>
    </>
  );
}

/* ─── card body (avoid duplication) ─── */

function CardContent({ goal, cfg, Icon, isExecuting, isPaused, progress, finalExecId,
  executeMutation, pauseMutation, resumeMutation, cancelMutation, reviewMutation, setConfirmDelete,
}: any) {
  return (
    <>
      <div className={`h-1 w-full ${cfg.bar}`} />
      <div className="p-3">
        <div className="flex items-start gap-2">
          <Icon size={18} className={`mt-0.5 shrink-0 ${cfg.iconColor} ${isExecuting && !isPaused ? "animate-spin" : ""}`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold truncate">{goal.title}</p>
            {goal.description && <p className="text-xs text-foreground/60 mt-1 line-clamp-2">{goal.description}</p>}
          </div>
        </div>

        {isExecuting && progress && (
          <div className="mt-2.5 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground/60">
                Tokens: <span className="font-bold tabular-nums text-foreground">{(progress.token_used ?? 0).toLocaleString()}</span>
                {goal.token_budget && <> / <span className="font-bold tabular-nums text-foreground">{goal.token_budget.toLocaleString()}</span></>}
              </span>
              {isPaused && <Badge size="sm" variant="outline">PAUSED</Badge>}
              {goal.token_budget && <span className="font-bold tabular-nums text-foreground">{Math.round(((progress.token_used ?? 0) / goal.token_budget) * 100)}%</span>}
            </div>
            {goal.token_budget && (
              <div className="h-2 w-full border-2 border-border bg-background">
                <div className="h-full bg-primary transition-all duration-500" style={{ width: `${Math.min(100, ((progress.token_used ?? 0) / goal.token_budget) * 100)}%` }} />
              </div>
            )}
          </div>
        )}

        <div className="mt-2.5 flex gap-1" onClick={e => e.stopPropagation()}>
          {(goal.status === "todo" || goal.status === "failed") && (
            <Button size="sm" onClick={() => executeMutation.mutate()} disabled={executeMutation.isPending} className="flex-1">
              {goal.status === "failed" ? <RotateCcw size={14} /> : <Play size={14} />}
              {executeMutation.isPending ? "..." : goal.status === "failed" ? "Retry" : "Execute"}
            </Button>
          )}

          {goal.status === "doing" && finalExecId && (
            <>
              {isPaused ? (
                <Button size="sm" variant="outline" onClick={() => resumeMutation.mutate(finalExecId!)} disabled={resumeMutation.isPending} className="flex-1">
                  <Play size={14} /> {resumeMutation.isPending ? "..." : "Resume"}
                </Button>
              ) : (
                <Button size="sm" variant="outline" onClick={() => pauseMutation.mutate(finalExecId!)} disabled={pauseMutation.isPending} className="flex-1">
                  <Pause size={14} /> {pauseMutation.isPending ? "..." : "Pause"}
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => cancelMutation.mutate(finalExecId!)} disabled={cancelMutation.isPending} className="flex-1">
                <Ban size={14} /> {cancelMutation.isPending ? "..." : "Cancel"}
              </Button>
            </>
          )}

          {goal.status === "review" && (
            <>
              <Button size="sm" onClick={() => reviewMutation.mutate("approve")} disabled={reviewMutation.isPending} className="flex-1">
                <CheckCircle size={14} /> {reviewMutation.isPending ? "..." : "Approve"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => reviewMutation.mutate("reject")} disabled={reviewMutation.isPending} className="flex-1">
                <XCircle size={14} /> {reviewMutation.isPending ? "..." : "Reject"}
              </Button>
            </>
          )}

          {goal.status !== "doing" && (
            <Button size="sm" variant="outline" onClick={() => setConfirmDelete(true)} aria-label="Delete goal">
              <Trash2 size={14} />
            </Button>
          )}
        </div>
      </div>
    </>
  );
}
