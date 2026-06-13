import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { globalConfigOptions, globalConfigKeys } from "@/lib/queries/global-config";
import { workspaceListOptions } from "@/lib/queries/workspaces";
import { SshKeyDisplay } from "@/components/settings/ssh-key-display";
import { SecretsManager } from "@/components/settings/secrets-manager";
import { AIModelConfig } from "@/components/settings/ai-model-config";
import { ReposManager } from "@/components/settings/repos-manager";
import { TeamContent } from "@/pages/workspace/Team";
import { SkillsTab, MCPTab, PluginsTab } from "@/pages/workspace/Plugins";
import { Text } from "@/components/retroui/Text";
import { Card } from "@/components/retroui/Card";
import { Input } from "@/components/retroui/Input";
import { Label } from "@/components/retroui/Label";
import { Button } from "@/components/retroui/Button";

type Tab =
  | "general"
  | "repositories"
  | "ssh"
  | "secrets"
  | "ai"
  | "mcp"
  | "skill"
  | "plugin"
  | "team";

const TABS: { id: Tab; label: string }[] = [
  { id: "general", label: "General" },
  { id: "repositories", label: "Repositories" },
  { id: "ssh", label: "SSH Key" },
  { id: "secrets", label: "Secrets" },
  { id: "ai", label: "AI Model" },
  { id: "mcp", label: "MCP" },
  { id: "skill", label: "Skill" },
  { id: "plugin", label: "Plugin" },
  { id: "team", label: "Team" },
];

export default function GlobalSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const { data: workspaces = [] } = useQuery(workspaceListOptions());
  const defaultWsId = workspaces[0]?.id ?? "";

  return (
    <div className="flex flex-col h-full p-6">
      <Text as="h2" className="text-2xl mb-6">Settings</Text>

      <div className="flex gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-2 transition-all ${
              activeTab === tab.id
                ? "border-border bg-primary shadow-[3px_3px_0_0_#000] text-foreground"
                : "border-border bg-background text-muted-foreground hover:bg-muted hover:shadow-[2px_2px_0_0_#000]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        {activeTab === "general" && <GeneralTab />}
        {activeTab === "repositories" && <ReposManager />}
        {activeTab === "ssh" && <SshKeyDisplay />}
        {activeTab === "secrets" && <SecretsManager />}
        {activeTab === "ai" && <AIModelConfig />}
        {activeTab === "mcp" && <MCPTab workspaceId={defaultWsId} />}
        {activeTab === "skill" && <SkillsTab workspaceId={defaultWsId} />}
        {activeTab === "plugin" && <PluginsTab />}
        {activeTab === "team" && <TeamContent />}
      </div>
    </div>
  );
}

function GeneralTab() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const { data: config } = useQuery(globalConfigOptions());

  const [knowledgeRepo, setKnowledgeRepo] = useState("");
  const [confirmingReset, setConfirmingReset] = useState(false);
  const isLocked = !!config?.knowledge_repo_url;

  const resetMutation = useMutation({
    mutationFn: () => api.delete("/global-config"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: globalConfigKeys.all() });
      refresh();
      navigate("/login");
    },
  });

  useEffect(() => {
    if (config?.knowledge_repo_url) {
      setKnowledgeRepo(config.knowledge_repo_url);
    }
  }, [config?.knowledge_repo_url]);

  const updateMutation = useMutation({
    mutationFn: (body: Record<string, string>) =>
      api.patch("/global-config", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: globalConfigKeys.all() });
    },
  });

  const handleSave = () => {
    if (!knowledgeRepo.trim() || isLocked) return;
    updateMutation.mutate({ knowledge_repo_url: knowledgeRepo.trim() });
  };

  return (
    <div className="max-w-lg">
      <Card>
        <Card.Header>
          <Card.Title>Knowledge Repository</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="space-y-4">
            <div>
              <Label htmlFor="knowledge-repo" className="mb-1.5 block text-xs">
                Knowledge Repository URL
              </Label>
              <Input
                id="knowledge-repo"
                value={knowledgeRepo}
                onChange={(e) => setKnowledgeRepo(e.target.value)}
                placeholder="https://github.com/org/knowledge"
                disabled={isLocked}
                className="font-mono text-sm"
              />
              {isLocked && (
                <p className="text-xs text-muted-foreground mt-1">
                  知识库 URL 绑定后不可修改。
                </p>
              )}
            </div>

            {updateMutation.isError && (
              <p className="text-xs text-destructive">
                保存失败: {(updateMutation.error as Error).message}
              </p>
            )}
            {updateMutation.isSuccess && (
              <p className="text-xs text-green-600">已保存</p>
            )}

            <Button
              onClick={handleSave}
              disabled={isLocked || !knowledgeRepo.trim() || updateMutation.isPending}
            >
              {updateMutation.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </Card.Content>
      </Card>

      {user?.is_founder && (
        <Card className="mt-6">
          <Card.Header>
            <Card.Title>重新初始化</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                清空全局配置（绑定仓库、SSH、AI、密钥)并删除本地知识库克隆，
                下次登录将重新运行首次初始化流程。此操作不可撤销。
              </p>

              {resetMutation.isError && (
                <p className="text-xs text-destructive">
                  重置失败: {(resetMutation.error as Error).message}
                </p>
              )}

              {confirmingReset ? (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => resetMutation.mutate()}
                    disabled={resetMutation.isPending}
                  >
                    {resetMutation.isPending ? "重置中..." : "确认重置"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setConfirmingReset(false)}
                    disabled={resetMutation.isPending}
                  >
                    取消
                  </Button>
                </div>
              ) : (
                <Button variant="outline" onClick={() => setConfirmingReset(true)}>
                  重新初始化
                </Button>
              )}
            </div>
          </Card.Content>
        </Card>
      )}
    </div>
  );
}
