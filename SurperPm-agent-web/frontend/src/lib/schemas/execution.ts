import { z } from "zod";

export const executionSchema = z.object({
  id: z.string(),
  goal_id: z.number(),
  workspace_id: z.string(),
  status: z.enum(["pending", "running", "success", "failed", "timeout"]),
  branch: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
  log_path: z.string().nullable().optional(),
  pr_url: z.string().nullable().optional(),
  token_used: z.number().nullable().optional(),
  token_budget: z.number().nullable().optional(),
  summary: z.string().nullable().optional(),
  artifacts: z.string().nullable().optional(),
  logs: z
    .array(
      z.object({
        kind: z.string(),
        text: z.string(),
        tool: z.string().optional(),
      })
    )
    .nullable()
    .optional(),
  created_at: z.string(),
});

export type Execution = z.infer<typeof executionSchema>;

export const executionListSchema = z.array(executionSchema);
