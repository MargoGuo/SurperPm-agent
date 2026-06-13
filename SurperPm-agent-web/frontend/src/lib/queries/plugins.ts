import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";
import { marketplaceStatusSchema, pluginListSchema } from "../schemas/plugin";
import { parseWithFallback } from "../utils/parse-with-fallback";

export const pluginKeys = {
  all: () => ["plugins"] as const,
  installed: () => [...pluginKeys.all(), "installed"] as const,
  marketplace: () => [...pluginKeys.all(), "marketplace"] as const,
};

export const pluginInstalledOptions = () =>
  queryOptions({
    queryKey: pluginKeys.installed(),
    queryFn: async () => {
      const res = await api.get("/plugins/installed");
      return parseWithFallback(pluginListSchema, res, []);
    },
  });

export const pluginMarketplaceStatusOptions = () =>
  queryOptions({
    queryKey: pluginKeys.marketplace(),
    queryFn: async () => {
      const res = await api.get("/plugins/marketplace");
      return parseWithFallback(marketplaceStatusSchema, res, {
        imported: false,
        repo_url: null,
        plugins: [],
      });
    },
  });
