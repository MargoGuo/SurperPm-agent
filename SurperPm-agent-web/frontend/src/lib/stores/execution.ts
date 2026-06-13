import { create } from "zustand";

interface ExecutionProgress {
  executionId: string;
  goalId: number;
  tokenUsed: number;
  step: string;
  detail: string;
}

interface ExecutionStore {
  progress: ExecutionProgress | null;
  updateProgress: (data: ExecutionProgress) => void;
  clearProgress: () => void;
}

export const useExecutionStore = create<ExecutionStore>((set) => ({
  progress: null,
  updateProgress: (data) => set({ progress: data }),
  clearProgress: () => set({ progress: null }),
}));
