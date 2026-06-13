import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  ExternalLink,
  Play,
  GitBranch,
  ChevronDown,
  TerminalSquare,
} from "lucide-react";
import { api } from "@/lib/api";
import { goalKeys, goalDetailOptions } from "@/lib/queries/goals";
import { executionListOptions, executionKeys } from "@/lib/queries/executions";
import type { Execution } from "@/lib/schemas/execution";
import { useExecutionStore, type LogLine } from "@/lib/stores/execution";
import { Text } from "@/components/retroui/Text";
import { Button } from "@/components/retroui/Button";
import { Badge } from "@/components/retroui/Badge";
import { Dialog } from "@/components/retroui/Dialog";
import { GoalConsole } from "@/components/goals/goal-console";

/* ─── helpers ─── */

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function formatDuration(startedAt?: string | null, finishedAt?: string | null): string | null {
  if (!startedAt) return null;
  const end = finishedAt ? new Date(finishedAt) : new Date();
  const diffSec = Math.max(0, Math.floor((end.getTime() - new Date(startedAt).getTime()) / 1000));
  const m = Math.floor(diffSec / 60);
  const s = diffSec % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

const logKind: Record<string, string> = {
  thinking: "text-purple-600",
  tool_use: "text-blue-600",
  tool_result: "text-foreground/50",
  error: "text-red-600",
  text: "text-foreground",
};

function LogLine({ line }: { line: LogLine }) {
  const label = line.kind === "tool_use" && line.tool ? line.tool : line.kind;
  return (
    <div className="whitespace-pre-wrap break-words">
      <span className={`${logKind[line.kind] ?? "text-foreground"} font-bold mr-1`}>[{label}]</span>
      <span>{line.text}</span>
    </div>
  );
}

/* ─── status config ─── */

const statusCfg = {
  pending:  { label: "Pending",  color: "text-foreground/30", bar: "bg-foreground/30" },
  running:  { label: "Running",  color: "text-yellow-600",   bar: "bg-yellow-400" },
  success:  { label: "Success",  color: "text-green-600",    bar: "bg-green-400" },
  failed:   { label: "Failed",   color: "text-red-600",      bar: "bg-red-400" },
  timeout:  { label: "Timeout",  color: "text-orange-600",   bar: "bg-orange-400" },
};

/* ─── page ─── */

export default function GoalExecutionsPage() {
  const { goalId: goalIdStr } = useParams<{ goalId: string }>();
  const goalId = Number(goalIdStr);
  const queryClient = useQueryClient();
  const [consoleOpen, setConsoleOpen] = useState(false);

  if (!goalIdStr || isNaN(goalId)) return null;

  const { data: goal } = useQuery(goalDetailOptions(goalId));
  const { data: executions = [], isLoading } = useQuery(executionListOptions(goalId));
  const canRun = goal?.status === "todo" || goal?.status === "failed";

  const execMutation = useMutation({
    mutationFn: () => api.post(`/goals/${goalId}/execute`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
      queryClient.invalidateQueries({ queryKey: executionKeys.all(goalId) });
    },
  });

  return (
    <div className="p-6 space-y-5">
      {/* header */}
      <div className="flex items-center justify-between">
        <div>
          <Text as="h3" className="text-lg">Executions</Text>
          <p className="text-xs text-foreground/40 mt-0.5">{executions.length} runs</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setConsoleOpen(true)}>
            <TerminalSquare size={14} />
            Console
          </Button>
          {canRun && (
            <Button onClick={() => execMutation.mutate()} disabled={execMutation.isPending}>
              <Play size={14} />
              {execMutation.isPending ? "Starting..." : "Run"}
            </Button>
          )}
        </div>
      </div>

      <Dialog open={consoleOpen} onOpenChange={setConsoleOpen}>
        <Dialog.Content size="4xl" className="h-[80vh]">
          <Dialog.Header>
            <Text as="h3" className="text-sm">Goal #{goalId} Console</Text>
          </Dialog.Header>
          <div className="h-[calc(80vh-3rem)]">
            {consoleOpen && <GoalConsole goalId={goalId} />}
          </div>
        </Dialog.Content>
      </Dialog>

      {/* loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="border-2 border-border bg-card p-5 space-y-3 shadow-[3px_3px_0_0_#000] animate-pulse">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-accent" />
                <div className="h-4 w-24 bg-accent" />
                <div className="h-3 w-16 bg-accent ml-auto" />
              </div>
              <div className="h-3 w-3/4 bg-accent" />
            </div>
          ))}
        </div>
      )}

      {/* empty */}
      {!isLoading && executions.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-20">
          <div className="border-2 border-border p-5 shadow-[4px_4px_0_0_#000] bg-card">
            <Play size={48} className="opacity-10" />
          </div>
          <p className="text-sm font-head text-foreground/30">No executions yet</p>
          {canRun && (
            <Button onClick={() => execMutation.mutate()} variant="outline" size="sm">
              <Play size={12} /> Run now
            </Button>
          )}
        </div>
      )}

      {/* list */}
      {!isLoading && executions.length > 0 && (
        <div className="space-y-3">
          {executions.map((exec) => (
            <ExecutionCard key={exec.id} exec={exec} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── single execution card ─── */

function ExecutionCard({ exec }: { exec: Execution }) {
  const c = statusCfg[exec.status] ?? statusCfg.pending;

  const liveLogs = useExecutionStore((s) => s.logsByExec[exec.id]);
  const logs: LogLine[] =
    exec.status === "running"
      ? liveLogs ?? []
      : (exec.logs as LogLine[] | null | undefined) ?? liveLogs ?? [];

  const duration = formatDuration(exec.started_at, exec.finished_at);
  const [logOpen, setLogOpen] = useState(false);

  return (
    <div className="border-2 border-border bg-card shadow-[3px_3px_0_0_#000]">
      {/* top bar + header */}
      <div className={`h-1 w-full ${c.bar}`} />
      <div className="flex items-center gap-3 px-4 py-3">
        {/* status dot — the ONE and ONLY spinning indicator */}
        {exec.status === "running" ? (
          <Loader2 size={16} className="shrink-0 text-yellow-600 animate-spin" />
        ) : exec.status === "success" ? (
          <CheckCircle size={16} className="shrink-0 text-green-600" />
        ) : exec.status === "failed" ? (
          <XCircle size={16} className="shrink-0 text-red-600" />
        ) : exec.status === "timeout" ? (
          <Clock size={16} className="shrink-0 text-orange-600" />
        ) : (
          <div className="w-[6px] h-[6px] shrink-0 border-2 border-foreground/20" />
        )}

        <Badge size="sm">{c.label}</Badge>

        {duration && (
          <span className="text-xs text-foreground/40 font-mono tabular-nums">{duration}</span>
        )}

        <span className="text-xs text-foreground/40 ml-auto">{formatDate(exec.created_at)}</span>
      </div>

      {/* body */}
      {(exec.summary || exec.token_used != null || exec.branch || exec.pr_url || exec.error) && (
        <div className="px-4 pb-3 space-y-2">
          {exec.summary && (
            <p className="text-sm text-foreground/70">{exec.summary}</p>
          )}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-foreground/50">
            {exec.token_used != null && (
              <span>
                Tokens: <span className="font-bold tabular-nums text-foreground">{exec.token_used.toLocaleString()}</span>
              </span>
            )}
            {exec.branch && (
              <span className="flex items-center gap-1">
                <GitBranch size={10} /> {exec.branch}
              </span>
            )}
            {exec.pr_url && (
              <a href={exec.pr_url} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-1 text-primary hover:underline font-bold">
                <ExternalLink size={10} /> PR
              </a>
            )}
            {exec.error && (
              <span className="text-destructive font-bold">{exec.error}</span>
            )}
          </div>
        </div>
      )}

      {/* logs toggle */}
      {logs.length > 0 && (
        <>
          <button
            onClick={() => setLogOpen(!logOpen)}
            className="flex items-center gap-1.5 w-full border-t-2 border-border px-4 py-2 text-xs font-head text-foreground/50 hover:bg-accent transition-colors cursor-pointer"
          >
            <ChevronDown size={12} className={`transition-transform ${logOpen ? "rotate-180" : ""}`} />
            Logs ({logs.length})
          </button>
          {logOpen && (
            <div className="border-t-2 border-border max-h-80 overflow-auto bg-background p-3 font-mono text-xs leading-relaxed space-y-1">
              {logs.map((line, i) => (
                <LogLine key={i} line={line} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
