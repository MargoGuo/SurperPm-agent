import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";
import { goalGroupListSchema } from "../schemas/goal-group";
import { parseWithFallback } from "../utils/parse-with-fallback";

export const goalGroupKeys = {
  all: () => ["goal-groups"] as const,
  list: (workspaceId: string) =>
    [...goalGroupKeys.all(), "list", workspaceId] as const,
};

export const goalGroupListOptions = (workspaceId: string) =>
  queryOptions({
    queryKey: goalGroupKeys.list(workspaceId),
    queryFn: async () => {
      const res = await api.get(
        `/goal-groups?workspace_id=${encodeURIComponent(workspaceId)}`
      );
      return parseWithFallback(goalGroupListSchema, res, []);
    },
  });
