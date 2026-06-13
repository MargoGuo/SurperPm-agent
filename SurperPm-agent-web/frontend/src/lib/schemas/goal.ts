import { z } from "zod";

export const goalSchema = z.object({
  id: z.number(),
  workspace_id: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  status: z.enum(["todo", "doing", "review", "done", "failed"]),
  reviewed_by: z.string().nullable().optional(),
  reviewed_at: z.string().nullable().optional(),
  priority: z.number(),
  assigned_to: z.string().nullable().optional(),
  suggested_assignee: z.string().nullable().optional(),
  parent_goal_id: z.number().nullable().optional(),
  token_budget: z.number().nullable().optional(),
  slug: z.string().nullable().optional(),
  repo_url: z.string().nullable().optional(),
  repo_path: z.string().nullable().optional(),
  repos: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Goal = z.infer<typeof goalSchema>;

export const goalListSchema = z.array(goalSchema);
