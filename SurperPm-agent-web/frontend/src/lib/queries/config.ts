import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";

export interface Integration {
  name: string;
  endpoint: string;
  connected: boolean;
}

export interface Extension {
  name: string;
  category: string;
  path: string;
}

export interface UsageStats {
  total_tokens: number;
  total_executions: number;
}

export const configKeys = {
  integrations: ["config", "integrations"] as const,
  profile: ["config", "profile"] as const,
  extensions: ["config", "extensions"] as const,
  usage: ["config", "usage"] as const,
};

export const integrationsOptions = queryOptions({
  queryKey: configKeys.integrations,
  queryFn: () => api.get<Integration[]>("/config/integrations"),
});

export const profileOptions = queryOptions({
  queryKey: configKeys.profile,
  queryFn: () => api.get<{ content: string }>("/config/profile"),
});

export const extensionsOptions = queryOptions({
  queryKey: configKeys.extensions,
  queryFn: () => api.get<Extension[]>("/config/extensions"),
});

export const usageOptions = queryOptions({
  queryKey: configKeys.usage,
  queryFn: () => api.get<UsageStats>("/config/usage"),
});
