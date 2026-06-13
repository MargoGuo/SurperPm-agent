import { queryOptions } from "@tanstack/react-query";
import { api } from "../api";

export const globalConfigKeys = {
  all: () => ["global-config"] as const,
  detail: () => [...globalConfigKeys.all(), "detail"] as const,
  sshKey: () => [...globalConfigKeys.all(), "ssh-key"] as const,
};

export interface GlobalConfig {
  knowledge_repo_url: string | null;
  knowledge_repo_path: string | null;
  ssh_public_key: string | null;
  ai_base_url: string | null;
  ai_api_key_set: boolean;
  ai_model: string | null;
}

export interface SshKeyInfo {
  ssh_public_key: string | null;
  has_private_key: boolean;
}

export const globalConfigOptions = () =>
  queryOptions({
    queryKey: globalConfigKeys.detail(),
    queryFn: () => api.get<GlobalConfig>("/global-config"),
  });

export const sshKeyOptions = () =>
  queryOptions({
    queryKey: globalConfigKeys.sshKey(),
    queryFn: () => api.get<SshKeyInfo>("/global-config/ssh-key"),
  });
