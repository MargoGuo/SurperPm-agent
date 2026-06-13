import { create } from "zustand";

export interface LogLine {
  kind: string; // thinking | tool_use | tool_result | error | text
  text: string;
  tool?: string;
  // Streaming deltas: event ∈ start | delta | stop, index = content-block index.
  // Set on incremental lines so updateProgress can coalesce them into one line.
  streaming?: boolean;
  event?: string;
  index?: number;
}

// Find the last still-streaming line matching a content-block index. A new
// assistant turn restarts indices at 0, but its predecessor was finalized
// (streaming:false) on stop, so only the current turn's open line matches.
function findStreamingIndex(lines: LogLine[], index?: number): number {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].streaming && lines[i].index === index) return i;
  }
  return -1;
}

interface ExecutionProgress {
  execution_id: string;
  goal_id: number;
  token_used?: number;
  paused?: boolean;
  logs?: LogLine[];
}

interface ExecutionStore {
  progress: ExecutionProgress | null;
  logsByExec: Record<string, LogLine[]>;
  updateProgress: (data: ExecutionProgress) => void;
  clearProgress: () => void;
}

export const useExecutionStore = create<ExecutionStore>((set) => ({
  progress: null,
  logsByExec: {},
  updateProgress: (data) =>
    set((state) => {
      // Merge into the current progress so partial events (e.g. a pause toggle
      // with no token_used) don't clobber prior fields. Reset on a new run.
      const base =
        state.progress?.execution_id === data.execution_id ? state.progress : null;
      const progress = { ...base, ...data };
      if (!data.logs || data.logs.length === 0) {
        return { progress };
      }
      const prev = state.logsByExec[data.execution_id] ?? [];
      const next = [...prev];
      for (const line of data.logs) {
        if (!line.streaming) {
          next.push(line);
          continue;
        }
        if (line.event === "start") {
          // Begin a new growing line for this content-block index.
          next.push({ ...line, streaming: true });
        } else if (line.event === "delta") {
          // Append text to the still-streaming line with the same index.
          const i = findStreamingIndex(next, line.index);
          if (i >= 0) {
            next[i] = { ...next[i], text: next[i].text + line.text };
          } else {
            next.push({ ...line, streaming: true });
          }
        } else if (line.event === "stop") {
          // Finalize the matching streaming line.
          const i = findStreamingIndex(next, line.index);
          if (i >= 0) {
            next[i] = { ...next[i], streaming: false };
          }
        }
      }
      return {
        progress,
        logsByExec: {
          ...state.logsByExec,
          [data.execution_id]: next,
        },
      };
    }),
  // Keep logsByExec so completed-run logs stay visible until the query refetch
  // loads the DB-persisted copy — only the live token banner is cleared.
  clearProgress: () => set({ progress: null }),
}));
