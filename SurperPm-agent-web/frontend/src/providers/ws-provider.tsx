import { createContext, useContext, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WSClient } from "../lib/ws-client";
import { executionKeys } from "../lib/queries/executions";
import { goalKeys } from "../lib/queries/goals";
import { discussionKeys } from "../lib/queries/discussions";
import { workspaceKeys } from "../lib/queries/workspaces";
import { useExecutionStore } from "../lib/stores/execution";

const WSContext = createContext<WSClient | null>(null);

export function useWS() {
  return useContext(WSContext);
}

interface WSProviderProps {
  workspaceId: string;
  children: React.ReactNode;
}

export function WSProvider({ workspaceId, children }: WSProviderProps) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WSClient | null>(null);

  useEffect(() => {
    const ws = new WSClient(workspaceId);
    wsRef.current = ws;

    ws.on("goal_created", () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all(workspaceId) });
    });
    ws.on("goal_updated", () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all(workspaceId) });
    });
    ws.on("discussion_posted", () => {
      queryClient.invalidateQueries({ queryKey: discussionKeys.all(workspaceId) });
    });
    ws.on("discussion_created", () => {
      queryClient.invalidateQueries({ queryKey: discussionKeys.all(workspaceId) });
    });
    ws.on("execution_started", () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.all(workspaceId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.all(workspaceId) });
    });
    ws.on("execution_progress", (data) => {
      useExecutionStore.getState().updateProgress(data as any);
    });
    ws.on("execution_completed", () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.all(workspaceId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.all(workspaceId) });
      useExecutionStore.getState().clearProgress();
    });
    ws.on("workspace_updated", () => {
      queryClient.invalidateQueries({ queryKey: workspaceKeys.all() });
    });
    ws.on("knowledge_updated", () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-tree"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-content"] });
    });

    return () => ws.close();
  }, [workspaceId, queryClient]);

  return (
    <WSContext.Provider value={wsRef.current}>
      {children}
    </WSContext.Provider>
  );
}
