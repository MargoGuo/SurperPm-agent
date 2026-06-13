import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";
import { executionListSchema } from "../schemas/execution";
import { parseWithFallback } from "../utils/parse-with-fallback";

export const executionKeys = {
  all: (goalId?: number) =>
    goalId != null ? (["executions", goalId] as const) : (["executions"] as const),
  list: (goalId: number) => [...executionKeys.all(goalId), "list"] as const,
};

export const executionListOptions = (goalId: number) =>
  queryOptions({
    queryKey: executionKeys.list(goalId),
    queryFn: async () => {
      const res = await api.get(`/goals/${goalId}/executions`);
      return parseWithFallback(executionListSchema, res, []);
    },
  });
