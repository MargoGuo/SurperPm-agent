import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";
import { goalSchema, goalListSchema } from "../schemas/goal";
import { parseWithFallback } from "../utils/parse-with-fallback";

export const goalKeys = {
  all: () => ["goals"] as const,
  list: () => [...goalKeys.all(), "list"] as const,
  detail: (id: number) => ["goals", "detail", id] as const,
};

export const goalListOptions = () =>
  queryOptions({
    queryKey: goalKeys.list(),
    queryFn: async () => {
      const res = await api.get("/goals");
      return parseWithFallback(goalListSchema, res, []);
    },
  });

export const goalDetailOptions = (goalId: number) =>
  queryOptions({
    queryKey: goalKeys.detail(goalId),
    queryFn: async () => {
      const res = await api.get(`/goals/${goalId}`);
      return goalSchema.parse(res);
    },
  });
