import { z } from "zod";

export const goalGroupSchema = z.object({
  id: z.number(),
  workspace_id: z.string(),
  name: z.string(),
  created_at: z.string().optional().default(""),
  updated_at: z.string().optional().default(""),
});

export type GoalGroup = z.infer<typeof goalGroupSchema>;

export const goalGroupListSchema = z.array(goalGroupSchema);
