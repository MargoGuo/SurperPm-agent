import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";
import { executionListSchema } from "../schemas/execution";
import { parseWithFallback } from "../utils/parse-with-fallback";

export const executionKeys = {
  all: (wsId: string) => ["executions", wsId] as const,
  list: (wsId: string) => [...executionKeys.all(wsId), "list"] as const,
  byGoal: (wsId: string, goalId: number) =>
    [...executionKeys.all(wsId), "goal", goalId] as const,
};

export const executionListOptions = (workspaceId: string, goalId?: number) =>
  queryOptions({
    queryKey: goalId
      ? executionKeys.byGoal(workspaceId, goalId)
      : executionKeys.list(workspaceId),
    queryFn: async () => {
      const params = goalId ? `?goal_id=${goalId}` : "";
      const res = await api.get(`/workspaces/${workspaceId}/executions${params}`);
      return parseWithFallback(executionListSchema, res, []);
    },
  });
