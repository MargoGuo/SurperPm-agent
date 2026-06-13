import { useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search, Plug, Cpu, Wrench, Plus, Trash2, RefreshCw,
  Power, PowerOff, Download, CheckCircle, AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Text } from "@/components/retroui/Text";
import { Input } from "@/components/retroui/Input";
import { Textarea } from "@/components/retroui/Textarea";
import { Card } from "@/components/retroui/Card";
import { Badge } from "@/components/retroui/Badge";
import { Button } from "@/components/retroui/Button";
import { Dialog } from "@/components/retroui/Dialog";
import { Label } from "@/components/retroui/Label";
import { skillKeys, skillListOptions } from "@/lib/queries/skills";
import { workspaceListOptions } from "@/lib/queries/workspaces";
import { mcpListOptions, mcpKeys } from "@/lib/queries/mcp";
import { pluginInstalledOptions, pluginMarketplaceStatusOptions, pluginKeys } from "@/lib/queries/plugins";
import { SkillCard } from "@/components/skills/skill-card";
import { CreateSkillDialog } from "@/components/skills/create-skill-dialog";

type PluginTab = "skills" | "mcp" | "plugins";

const TABS: { id: PluginTab; label: string; icon: React.ElementType }[] = [
  { id: "skills", label: "Skills", icon: Wrench },
  { id: "mcp", label: "MCP Servers", icon: Cpu },
  { id: "plugins", label: "Plugins", icon: Plug },
];

export default function PluginsPage() {
  const [activeTab, setActiveTab] = useState<PluginTab>("skills");
  const { data: workspaces = [] } = useQuery(workspaceListOptions());
  const wsId = workspaces[0]?.id ?? "";

  return (
    <div className="flex flex-col h-full p-6 overflow-auto">
      <Text as="h2" className="text-2xl mb-6">
        Plugins
      </Text>

      <div className="flex gap-2 mb-6">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-2 transition-all ${
                activeTab === tab.id
                  ? "border-border bg-primary shadow-[3px_3px_0_0_#000] text-foreground"
                  : "border-border bg-background text-muted-foreground hover:bg-muted hover:shadow-[2px_2px_0_0_#000]"
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="flex-1 min-h-0">
        {activeTab === "skills" && <SkillsTab workspaceId={wsId} />}
        {activeTab === "mcp" && <MCPTab workspaceId={wsId} />}
        {activeTab === "plugins" && <PluginsTab />}
      </div>
    </div>
  );
}

export function SkillsTab({ workspaceId }: { workspaceId: string }) {
  const navigate = useNavigate();

  if (!workspaceId) {
    return (
      <Card className="max-w-lg">
        <Card.Content>
          <p className="text-sm text-muted-foreground py-4">
            No workspace configured. Please set up a workspace first.
          </p>
        </Card.Content>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <CreateSkillDialog workspaceId={workspaceId} />
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        <SkillsGrid
          workspaceId={workspaceId}
          onSelect={(id) => navigate(`/skills/${id}`)}
        />
      </div>
    </div>
  );
}

function SkillsGrid({
  workspaceId,
  onSelect,
}: {
  workspaceId: string;
  onSelect: (id: number) => void;
}) {
  const queryClient = useQueryClient();
  const { data: skills, isLoading } = useQuery(skillListOptions(workspaceId));

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/workspaces/${workspaceId}/skills/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skillKeys.list(workspaceId) });
    },
  });

  function handleDelete(skill: { id: number; name: string }) {
    if (confirm(`确定要删除 "${skill.name}"？`)) {
      deleteMutation.mutate(skill.id);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Text className="text-muted-foreground">加载中...</Text>
      </div>
    );
  }

  if (!skills || skills.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 gap-2">
        <Text className="text-muted-foreground">还没有插件</Text>
        <p className="text-sm text-muted-foreground">点击上方按钮创建或导入你的第一个插件</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {skills.map((skill) => (
        <SkillCard key={skill.id} skill={skill} onClick={() => onSelect(skill.id)} onDelete={handleDelete} />
      ))}
    </div>
  );
}

// ── MCP Tab ─────────────────────────────────────────────────────

export function MCPTab({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, { ok: boolean; error?: string; status?: number; stdout?: string }>>({});
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  const { data: servers = [], isLoading } = useQuery(mcpListOptions(workspaceId));

  const importMutation = useMutation({
    mutationFn: () => api.post(`/workspaces/${workspaceId}/mcp/import`, { json_text: jsonText }),
    onSuccess: (data: unknown) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.list(workspaceId) });
      const d = data as { created: number };
      alert(`成功导入 ${d.created} 个 MCP Server`);
      setAddOpen(false);
      setJsonText("");
      setJsonError(null);
    },
    onError: (e: Error) => setJsonError(e.message),
  });

  const updateJsonMutation = useMutation({
    mutationFn: (id: number) => api.put(`/workspaces/${workspaceId}/mcp/servers/${id}/import`, { json_text: jsonText }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.list(workspaceId) });
      setEditingId(null);
      setJsonText("");
      setJsonError(null);
    },
    onError: (e: Error) => setJsonError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/workspaces/${workspaceId}/mcp/servers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.list(workspaceId) });
    },
  });

  const discoverMutation = useMutation({
    mutationFn: () => api.post(`/workspaces/${workspaceId}/mcp/discover`),
    onSuccess: (data: unknown) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.list(workspaceId) });
      const d = data as { discovered: number };
      alert(`发现 ${d.discovered} 个 MCP server，已同步到数据库`);
    },
    onError: (e: Error) => alert(`发现失败: ${e.message}`),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      api.put(`/workspaces/${workspaceId}/mcp/servers/${id}`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.list(workspaceId) });
    },
  });

  function serverToJson(srv: {
    name: string;
    transport: string;
    command: string | null;
    args: string | null;
    env: string | null;
    url: string | null;
    headers: string | null;
  }): string {
    const cfg: Record<string, unknown> = {};
    if (srv.transport !== "stdio") cfg.type = srv.transport;
    if (srv.command) cfg.command = srv.command;
    if (srv.args) {
      try { cfg.args = JSON.parse(srv.args); } catch { cfg.args = srv.args; }
    }
    if (srv.env) {
      try { cfg.env = JSON.parse(srv.env); } catch { cfg.env = srv.env; }
    }
    if (srv.url) cfg.url = srv.url;
    if (srv.headers) {
      try { cfg.headers = JSON.parse(srv.headers); } catch { cfg.headers = srv.headers; }
    }
    return JSON.stringify({ mcpServers: { [srv.name]: cfg } }, null, 2);
  }

  function openAdd() {
    setEditingId(null);
    setJsonText("");
    setJsonError(null);
    setAddOpen(true);
  }

  function openEdit(srv: {
    id: number | null;
    name: string;
    transport: string;
    command: string | null;
    args: string | null;
    env: string | null;
    url: string | null;
    headers: string | null;
    enabled: boolean;
  }) {
    if (srv.id == null) return;
    setEditingId(srv.id);
    setJsonText(serverToJson(srv));
    setJsonError(null);
  }

  async function testConnection(id: number | null) {
    if (id == null) return;
    try {
      const res = await api.post(`/workspaces/${workspaceId}/mcp/servers/${id}/test`) as { ok: boolean; error?: string; status?: number; stdout?: string };
      setTestResults((prev) => ({ ...prev, [id]: res }));
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { ok: false, error: "Request failed" } }));
    }
  }

  if (!workspaceId) {
    return (
      <Card className="max-w-lg">
        <Card.Content>
          <p className="text-sm text-muted-foreground py-4">
            No workspace configured. Please set up a workspace first.
          </p>
        </Card.Content>
      </Card>
    );
  }

  if (isLoading) {
    return <Text className="text-muted-foreground">加载中...</Text>;
  }

  return (
    <div className="flex flex-col h-full max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          配置 MCP (Model Context Protocol) 服务器，给 AI 提供外部工具
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => discoverMutation.mutate()}
            disabled={discoverMutation.isPending}
          >
            <Search size={14} className="mr-1" />
            {discoverMutation.isPending ? "扫描中..." : "自动发现"}
          </Button>
          <Button size="sm" onClick={openAdd}>
            <Plus size={14} className="mr-1" />
            添加 Server
          </Button>
        </div>
      </div>

      {servers.length === 0 ? (
        <Card className="max-w-lg">
          <Card.Content>
            <p className="text-sm text-muted-foreground py-4">
              还没有 MCP 服务器。点击 "添加 Server" 粘贴 .mcp.json 配置，或 "自动发现" 从已安装插件中扫描。
            </p>
          </Card.Content>
        </Card>
      ) : (
        <div className="space-y-3 flex-1 overflow-auto">
          {servers.map((srv) => {
            const testR = srv.id != null ? testResults[srv.id] : null;
            const isDiscovered = !!srv.plugin_source;
            const hasId = srv.id != null;
            return (
              <div
                key={srv.id ?? srv.name}
                className="border-2 border-border bg-card p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <Cpu size={18} className="text-muted-foreground shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">{srv.name}</p>
                        <Badge variant="surface" size="sm">{srv.transport}</Badge>
                        {isDiscovered && (
                          <Badge variant="default" size="sm" className="text-xs">
                            {srv.plugin_source}
                          </Badge>
                        )}
                        {srv.enabled
                          ? <CheckCircle size={12} className="text-green-600" />
                          : <AlertTriangle size={12} className="text-muted-foreground" />
                        }
                      </div>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">
                        {srv.transport === "stdio"
                          ? srv.command ?? "(no command)"
                          : srv.url ?? "(no url)"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0 ml-2">
                    {hasId && (
                      <>
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => toggleMutation.mutate({ id: srv.id!, enabled: !srv.enabled })}
                          title={srv.enabled ? "禁用" : "启用"}
                        >
                          {srv.enabled ? <PowerOff size={14} /> : <Power size={14} />}
                        </Button>
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => testConnection(srv.id!)}
                          title="测试连接"
                        >
                          <RefreshCw size={14} />
                        </Button>
                        {!isDiscovered && (
                          <>
                            <Button variant="ghost" size="sm" onClick={() => openEdit(srv)} title="编辑">
                              <Wrench size={14} />
                            </Button>
                            <Button
                              variant="ghost" size="sm"
                              onClick={() => { if (confirm(`删除 ${srv.name}？`)) deleteMutation.mutate(srv.id!); }}
                              title="删除"
                            >
                              <Trash2 size={14} />
                            </Button>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
                {testR && (
                  <div className={`mt-2 text-xs p-2 border ${testR.ok ? "border-green-600 bg-green-50 text-green-800" : "border-destructive bg-red-50 text-destructive"}`}>
                    {testR.ok
                      ? `✅ 连接成功${testR.status != null ? ` (HTTP ${testR.status})` : ""}${testR.stdout ? `: ${testR.stdout.slice(0, 100)}` : ""}`
                      : `❌ 连接失败: ${testR.error}`}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Dialog — JSON only */}
      <Dialog open={addOpen || editingId != null} onOpenChange={(v) => { if (!v) { setAddOpen(false); setEditingId(null); setJsonText(""); setJsonError(null); } }}>
        <Dialog.Content size="md">
          <Dialog.Header>
            <Text as="h3" className="text-base font-bold">
              {editingId != null ? "编辑 MCP Server" : "添加 MCP Server"}
            </Text>
          </Dialog.Header>

          <div className="p-4 space-y-3">
            <div>
              <Label htmlFor="mcp-json" className="mb-1 block text-xs">
                粘贴 .mcp.json 配置
              </Label>
              <Textarea
                id="mcp-json"
                value={jsonText}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) => { setJsonText(e.target.value); setJsonError(null); }}
                placeholder={`{\n  "mcpServers": {\n    "mcp-server-weread": {\n      "args": ["-y", "mcp-server-weread"],\n      "command": "npx",\n      "env": {\n        "CC_ID": "您的ID",\n        "CC_PASSWORD": "您的密码",\n        "CC_URL": "https://cc.chenge.ink"\n      }\n    }\n  }\n}`}
                rows={12}
                className="font-mono text-xs"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              支持完整 .mcp.json 格式（含 mcpServers 包裹），或直接粘贴单个 server 配置。一次可导入多个。
            </p>
            {jsonError && <p className="text-sm text-destructive">{jsonError}</p>}
          </div>

          <Dialog.Footer>
            <Button variant="outline" onClick={() => { setAddOpen(false); setEditingId(null); setJsonText(""); setJsonError(null); }}>
              取消
            </Button>
            <Button
              onClick={() => {
                if (!jsonText.trim()) { setJsonError("请输入 JSON 配置"); return; }
                if (editingId != null) {
                  updateJsonMutation.mutate(editingId);
                } else {
                  importMutation.mutate();
                }
              }}
              disabled={!jsonText.trim() || importMutation.isPending || updateJsonMutation.isPending}
            >
              {importMutation.isPending || updateJsonMutation.isPending ? "保存中..." : editingId != null ? "更新" : "导入"}
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog>
    </div>
  );
}

// ── Plugins Tab ──────────────────────────────────────────────────

type PluginSubTab = "installed" | "marketplace";

export function PluginsTab() {
  const [subTab, setSubTab] = useState<PluginSubTab>("installed");
  const queryClient = useQueryClient();

  // ── Installed ────────────────────────────────────────────────

  const { data: installed = [], isLoading: loadingInstalled } = useQuery(pluginInstalledOptions());

  const uninstallMutation = useMutation({
    mutationFn: (name: string) => api.post(`/plugins/${name}/uninstall`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pluginKeys.all() }),
  });

  const updateMutation = useMutation({
    mutationFn: (name: string) => api.post(`/plugins/${name}/update`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pluginKeys.all() }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ name, enable }: { name: string; enable: boolean }) =>
      api.post(`/plugins/${name}/${enable ? "enable" : "disable"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pluginKeys.all() }),
  });

  // ── Marketplace ──────────────────────────────────────────────

  const {
    data: mktStatus,
    isLoading: loadingMkt,
  } = useQuery(pluginMarketplaceStatusOptions());

  const [mktImportUrl, setMktImportUrl] = useState("");
  const [mktImportError, setMktImportError] = useState<string | null>(null);

  const mktImportMutation = useMutation({
    mutationFn: (url: string) => api.post("/plugins/marketplace/import", { url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.marketplace() });
      setMktImportUrl("");
      setMktImportError(null);
    },
    onError: (e: Error) => setMktImportError(e.message),
  });

  const mktRemoveMutation = useMutation({
    mutationFn: () => api.delete("/plugins/marketplace"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.marketplace() });
    },
  });

  const mktInstallMutation = useMutation({
    mutationFn: (name: string) => api.post(`/plugins/marketplace/install/${name}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pluginKeys.all() }),
    onError: (e: Error) => alert(`安装失败: ${e.message}`),
  });

  // ── Plugin import state & dialog ────────────────────────────

  const [pluginImportOpen, setPluginImportOpen] = useState(false);
  const [pluginImportUrl, setPluginImportUrl] = useState("");
  const [pluginImportError, setPluginImportError] = useState<string | null>(null);

  const pluginImportMutation = useMutation({
    mutationFn: (url: string) => api.post("/plugins/import", { url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.all() });
      setPluginImportOpen(false);
      setPluginImportUrl("");
      setPluginImportError(null);
    },
    onError: (e: Error) => setPluginImportError(e.message),
  });

  // ── Render ───────────────────────────────────────────────────

  const [mktSearch, setMktSearch] = useState("");
  const mktPlugins = mktStatus?.plugins ?? [];

  return (
    <div className="flex flex-col h-full max-w-4xl">
      {/* Sub-tabs */}
      <div className="flex gap-2 mb-4">
        {([
          { id: "installed" as const, label: `已安装 (${installed.length})` },
          { id: "marketplace" as const, label: `市场${mktStatus?.imported ? " ✓" : ""}` },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setSubTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-2 transition-all ${
              subTab === t.id
                ? "border-border bg-primary shadow-[3px_3px_0_0_#000] text-foreground"
                : "border-border bg-background text-muted-foreground hover:bg-muted hover:shadow-[2px_2px_0_0_#000]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ═══ Installed ═══ */}
      {subTab === "installed" && (
        <div className="flex-1 overflow-auto">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">已安装的插件包</p>
            <Button size="sm" onClick={() => { setPluginImportOpen(true); setPluginImportUrl(""); setPluginImportError(null); }}>
              <Download size={14} className="mr-1" />
              导入插件
            </Button>
          </div>

          {loadingInstalled ? (
            <Text className="text-muted-foreground">加载中...</Text>
          ) : installed.length === 0 ? (
            <Card className="max-w-lg">
              <Card.Content>
                <p className="text-sm text-muted-foreground py-4">
                  还没有安装任何插件。从 GitHub 导入，或先导入市场后从市场安装。
                </p>
              </Card.Content>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {installed.map((p) => (
                <div key={p.name} className="border-2 border-border bg-card p-4">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">{p.name}</p>
                        <Badge variant="surface" size="sm">v{p.version}</Badge>
                        {p.enabled
                          ? <CheckCircle size={12} className="text-green-600" />
                          : <AlertTriangle size={12} className="text-muted-foreground" />
                        }
                      </div>
                      {p.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {p.description}
                        </p>
                      )}
                      {p.source_url && (
                        <p className="text-xs text-muted-foreground mt-1 font-mono truncate">{p.source_url}</p>
                      )}
                      <div className="flex gap-2 mt-2">
                        {p.commands.length > 0 && (
                          <span className="text-xs text-muted-foreground">{p.commands.length} commands</span>
                        )}
                        {p.skills.length > 0 && (
                          <span className="text-xs text-muted-foreground">{p.skills.length} skills</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => toggleMutation.mutate({ name: p.name, enable: !p.enabled })}
                        title={p.enabled ? "禁用" : "启用"}
                      >
                        {p.enabled ? <PowerOff size={14} /> : <Power size={14} />}
                      </Button>
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => updateMutation.mutate(p.name)}
                        title="更新"
                      >
                        <RefreshCw size={14} />
                      </Button>
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => { if (confirm(`确定要卸载 ${p.name}？`)) uninstallMutation.mutate(p.name); }}
                        title="卸载"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══ Marketplace ═══ */}
      {subTab === "marketplace" && (
        <div className="flex-1 overflow-auto">
          {loadingMkt ? (
            <Text className="text-muted-foreground">加载中...</Text>
          ) : !mktStatus?.imported ? (
            /* ── Not imported yet: show import form ── */
            <Card className="max-w-lg">
              <Card.Header>
                <Card.Title className="flex items-center gap-2">
                  <Plug size={16} />
                  导入市场仓库
                </Card.Title>
              </Card.Header>
              <Card.Content>
                <p className="text-sm text-muted-foreground mb-3">
                  输入包含 <code className="text-xs bg-muted px-1 rounded">marketplace.json</code> 的 GitHub 仓库地址。
                </p>

                <details className="mb-3">
                  <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                    marketplace.json 格式示例
                  </summary>
                  <pre className="mt-2 text-xs font-mono bg-muted/50 p-3 overflow-auto max-h-48 border border-border whitespace-pre-wrap">
{`{
  "plugins": [
    {
      "name": "SuperPmAgent-coding",
      "source": "https://github.com/user/SuperPmAgent-plugins",
      "subdir": "SuperPmAgent-coding",
      "version": "1.0.0",
      "description": "编码 skill 库",
      "author": "SuperPmAgent Team",
      "skills": ["coding", "run-tests", "submit-pr"]
    },
    {
      "name": "SuperPmAgent-core",
      "source": "https://github.com/user/SuperPmAgent-plugins",
      "subdir": "SuperPmAgent-core",
      "version": "1.0.0",
      "description": "编排核心"
    }
  ]
}`}</pre>
                  <p className="text-xs text-muted-foreground mt-1">
                    <strong>name</strong>: 插件名 · <strong>source</strong>: GitHub 仓库 · <strong>subdir</strong>: 仓库中插件子目录
                  </p>
                </details>

                <div className="space-y-3">
                  <div>
                    <Label htmlFor="mkt-import-url" className="mb-1 block text-xs">GitHub 仓库 URL *</Label>
                    <Input
                      id="mkt-import-url"
                      value={mktImportUrl}
                      onChange={(e) => { setMktImportUrl(e.target.value); setMktImportError(null); }}
                      placeholder="https://github.com/user/SuperPmAgent-marketplace"
                    />
                  </div>
                  {mktImportError && <p className="text-sm text-destructive">{mktImportError}</p>}
                  <Button
                    onClick={() => {
                      if (!mktImportUrl.trim()) { setMktImportError("请输入 GitHub URL"); return; }
                      mktImportMutation.mutate(mktImportUrl.trim());
                    }}
                    disabled={!mktImportUrl.trim() || mktImportMutation.isPending}
                  >
                    {mktImportMutation.isPending ? "导入中..." : "导入市场"}
                  </Button>
                </div>
              </Card.Content>
            </Card>
          ) : (
            /* ── Imported: show marketplace plugins ── */
            <div className="flex flex-col h-full">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <Plug size={16} className="text-muted-foreground shrink-0" />
                  <p className="text-xs font-mono text-muted-foreground truncate">
                    {mktStatus.repo_url}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    variant="outline" size="sm"
                    onClick={() => { if (confirm("确定要移除市场仓库？")) mktRemoveMutation.mutate(); }}
                  >
                    <Trash2 size={14} className="mr-1" />
                    移除
                  </Button>
                </div>
              </div>

              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                <Input
                  placeholder="搜索市场..."
                  value={mktSearch}
                  onChange={(e) => setMktSearch(e.target.value)}
                  className="pl-9"
                />
              </div>

              {mktPlugins.length === 0 ? (
                <Card className="max-w-lg">
                  <Card.Content>
                    <p className="text-sm text-muted-foreground py-4">
                      市场中暂无可用插件。
                    </p>
                  </Card.Content>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 overflow-auto">
                  {mktPlugins
                    .filter((p) => {
                      if (!mktSearch) return true;
                      const q = mktSearch.toLowerCase();
                      return p.name.toLowerCase().includes(q)
                        || (p.description && p.description.toLowerCase().includes(q));
                    })
                    .map((p) => (
                      <div key={p.name} className="border-2 border-border bg-card p-4">
                        <div className="flex items-start justify-between">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium">{p.name}</p>
                              <Badge variant="surface" size="sm">v{p.version}</Badge>
                              {p.installed && <Badge variant="default" size="sm">已安装</Badge>}
                            </div>
                            {p.description && (
                              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                {p.description}
                              </p>
                            )}
                            {p.author && (
                              <p className="text-xs text-muted-foreground mt-1">作者: {p.author}</p>
                            )}
                            {p.source_url && (
                              <p className="text-xs text-muted-foreground mt-1 font-mono truncate">{p.source_url}</p>
                            )}
                            <div className="flex gap-2 mt-2">
                              {p.skills.length > 0 && (
                                <span className="text-xs text-muted-foreground">{p.skills.length} skills</span>
                              )}
                            </div>
                          </div>
                          <div className="shrink-0 ml-2">
                            {p.installed ? (
                              <Badge variant="default" size="sm">
                                <CheckCircle size={12} className="mr-1 inline" />已安装
                              </Badge>
                            ) : (
                              <Button
                                size="sm"
                                onClick={() => mktInstallMutation.mutate(p.name)}
                                disabled={mktInstallMutation.isPending}
                              >
                                <Download size={14} className="mr-1" />
                                安装
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Dialog: import plugin from GitHub */}
      <Dialog open={pluginImportOpen} onOpenChange={(v) => { if (!v) { setPluginImportOpen(false); setPluginImportError(null); } }}>
        <Dialog.Content size="md">
          <Dialog.Header>
            <Text as="h3" className="text-base font-bold">导入插件</Text>
          </Dialog.Header>
          <div className="p-4 space-y-3">
            <div>
              <Label htmlFor="plugin-import-url" className="mb-1 block text-xs">GitHub URL *</Label>
              <Input
                id="plugin-import-url"
                value={pluginImportUrl}
                onChange={(e) => { setPluginImportUrl(e.target.value); setPluginImportError(null); }}
                placeholder="https://github.com/user/SuperPmAgent-plugins/tree/main/SuperPmAgent-coding"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              仓库根目录需包含 <code>.claude-plugin/plugin.json</code>，或指定子目录路径。
            </p>
            {pluginImportError && <p className="text-sm text-destructive">{pluginImportError}</p>}
          </div>
          <Dialog.Footer>
            <Button variant="outline" onClick={() => { setPluginImportOpen(false); setPluginImportError(null); }}>
              取消
            </Button>
            <Button
              onClick={() => {
                if (!pluginImportUrl.trim()) { setPluginImportError("请输入 URL"); return; }
                pluginImportMutation.mutate(pluginImportUrl.trim());
              }}
              disabled={pluginImportMutation.isPending}
            >
              {pluginImportMutation.isPending ? "导入中..." : "导入"}
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog>
    </div>
  );
}
