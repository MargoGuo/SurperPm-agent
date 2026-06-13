import { z } from "zod";

export const pluginInfoSchema = z.object({
  name: z.string(),
  version: z.string(),
  description: z.string().nullable(),
  author: z.string().nullable(),
  source_url: z.string().nullable(),
  subdir: z.string().nullable(),
  commands: z.array(z.string()),
  skills: z.array(z.string()),
  agents: z.array(z.string()),
  enabled: z.boolean(),
  installed: z.boolean(),
});

export const pluginListSchema = z.array(pluginInfoSchema);

export const marketplaceStatusSchema = z.object({
  imported: z.boolean(),
  repo_url: z.string().nullable(),
  plugins: z.array(pluginInfoSchema),
});

export type PluginInfo = z.infer<typeof pluginInfoSchema>;
export type MarketplaceStatus = z.infer<typeof marketplaceStatusSchema>;
