import { z } from "zod";

export const secretSchema = z.object({
  id: z.number(),
  workspace_id: z.string(),
  key: z.string(),
  value_enc: z.string(),
  category: z.string(),
});

export type Secret = z.infer<typeof secretSchema>;

export const secretListSchema = z.array(secretSchema);
