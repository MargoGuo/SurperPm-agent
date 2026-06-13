import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Check, Hash, Coins, User, GitBranch, Sparkles } from "lucide-react";
import { api } from "../../lib/api";
import { goalKeys } from "../../lib/queries/goals";
import {
  workspaceListOptions,
  workspaceReposOptions,
  workspaceRepoKeys,
} from "../../lib/queries/workspaces";
import { Dialog } from "@/components/retroui/Dialog";
import { Button } from "@/components/retroui/Button";
import { Input } from "@/components/retroui/Input";
import { Textarea } from "@/components/retroui/Textarea";
import { Text } from "@/components/retroui/Text";
import { Select } from "@/components/retroui/Select";

interface TeamMember {
  login: string;
  avatar_url: string;
}
interface TeamProfile {
  members: TeamMember[];
}

const UNASSIGNED = "__unassigned__";

function SectionLabel({ icon: Icon, children }: { icon: typeof Hash; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 mb-1.5">
      <Icon size={12} className="text-foreground/40" />
      <span className="text-[10px] uppercase tracking-widest font-head text-foreground/50">
        {children}
      </span>
    </div>
  );
}

export function CreateGoalDialog() {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tokenBudget, setTokenBudget] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [newRepoUrl, setNewRepoUrl] = useState("");
  const queryClient = useQueryClient();
  const { data: workspaces = [] } = useQuery(workspaceListOptions());
  const defaultWsId = workspaces[0]?.id ?? "";
  const { data: configuredRepos = [] } = useQuery(workspaceReposOptions(defaultWsId));
  const { data: teamProfile } = useQuery<TeamProfile>({
    queryKey: ["setup", "team-profile"],
    queryFn: () => api.get<TeamProfile>("/setup/team-profile"),
  });
  const members = teamProfile?.members ?? [];

  const addRepoMutation = useMutation({
    mutationFn: (url: string) =>
      api.post(`/workspaces/${defaultWsId}/repos`, { url }),
    onSuccess: (_data, url) => {
      queryClient.invalidateQueries({ queryKey: workspaceRepoKeys.all(defaultWsId) });
      setSelectedRepos((prev) => (prev.includes(url) ? prev : [...prev, url]));
      setNewRepoUrl("");
    },
  });

  const toggleRepo = (url: string) =>
    setSelectedRepos((prev) =>
      prev.includes(url) ? prev.filter((r) => r !== url) : [...prev, url]
    );

  const handleAddRepo = () => {
    const url = newRepoUrl.trim();
    if (!url) return;
    if (configuredRepos.includes(url)) {
      toggleRepo(url);
      setNewRepoUrl("");
      return;
    }
    addRepoMutation.mutate(url);
  };

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/goals", {
        workspace_id: defaultWsId,
        title,
        description: description || null,
        ...(tokenBudget ? { token_budget: parseInt(tokenBudget, 10) } : {}),
        ...(assignedTo.trim() ? { assigned_to: assignedTo.trim() } : {}),
        ...(selectedRepos.length ? { repos: JSON.stringify(selectedRepos) } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
      setTitle("");
      setDescription("");
      setTokenBudget("");
      setAssignedTo("");
      setSelectedRepos([]);
      setNewRepoUrl("");
      setOpen(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    mutation.mutate();
  };

  return (
    <>
      <Button onClick={() => setOpen(true)} className="text-sm">
        <Plus size={16} />
        New Goal
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <Dialog.Content size="md">
          <Dialog.Header>
            <div className="flex items-center gap-2">
              <Sparkles size={16} />
              <Text as="h3" className="text-sm">Create Goal</Text>
            </div>
          </Dialog.Header>

          <form onSubmit={handleSubmit} className="divide-y-2 divide-border">
            {/* ── Title & Description ── */}
            <div className="p-5 space-y-4">
              <div>
                <SectionLabel icon={Hash}>Title *</SectionLabel>
                <Input
                  id="goal-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="What should this goal accomplish?"
                  autoFocus
                />
              </div>
              <div>
                <SectionLabel icon={Hash}>Description</SectionLabel>
                <Textarea
                  id="goal-desc"
                  value={description}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
                  placeholder="Add context, success criteria, or notes…"
                  rows={3}
                />
              </div>
            </div>

            {/* ── Budget & Assignee ── */}
            <div className="grid grid-cols-2 divide-x-2 divide-border">
              <div className="p-5 space-y-1.5">
                <SectionLabel icon={Coins}>Token Budget</SectionLabel>
                <Input
                  id="goal-budget"
                  type="number"
                  value={tokenBudget}
                  onChange={(e) => setTokenBudget(e.target.value)}
                  placeholder="e.g. 50000"
                  min="0"
                />
              </div>
              <div className="p-5 space-y-1.5">
                <SectionLabel icon={User}>Assignee</SectionLabel>
                <Select
                  value={assignedTo || UNASSIGNED}
                  onValueChange={(v) => setAssignedTo(v === UNASSIGNED ? "" : (v ?? ""))}
                >
                  <Select.Trigger id="goal-assign" className="w-full">
                    <Select.Value placeholder="Unassigned" />
                  </Select.Trigger>
                  <Select.Content>
                    <Select.Item value={UNASSIGNED}>Unassigned</Select.Item>
                    {members.map((m) => (
                      <Select.Item key={m.login} value={m.login}>
                        {m.login}
                      </Select.Item>
                    ))}
                  </Select.Content>
                </Select>
              </div>
            </div>

            {/* ── Repos ── */}
            <div className="p-5 space-y-3">
              <SectionLabel icon={GitBranch}>Repositories</SectionLabel>

              {configuredRepos.length > 0 && (
                <div className="space-y-1.5">
                  {configuredRepos.map((url) => {
                    const selected = selectedRepos.includes(url);
                    return (
                      <button
                        key={url}
                        type="button"
                        onClick={() => toggleRepo(url)}
                        className={`flex w-full items-center gap-2.5 border-2 px-3 py-2 text-left transition-all ${
                          selected
                            ? "border-border bg-primary shadow-[2px_2px_0_0_#000] translate-x-0"
                            : "border-border bg-background hover:bg-accent"
                        }`}
                      >
                        <span
                          className={`flex h-4 w-4 shrink-0 items-center justify-center border-2 border-border ${
                            selected ? "bg-foreground text-background" : "bg-background"
                          }`}
                        >
                          {selected && <Check size={10} />}
                        </span>
                        <span className="flex-1 truncate font-mono text-[11px]">{url}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="flex gap-2">
                <Input
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  placeholder="https://github.com/org/repo"
                  className="flex-1 font-mono text-xs"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddRepo();
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  onClick={handleAddRepo}
                  disabled={!newRepoUrl.trim() || addRepoMutation.isPending}
                >
                  <Plus size={14} />
                </Button>
              </div>

              {mutation.isError && (
                <p className="text-xs text-destructive font-bold">
                  {(mutation.error as Error).message}
                </p>
              )}
            </div>

            {/* ── Footer ── */}
            <div className="p-5">
              <Dialog.Footer>
                <Dialog.Close
                  render={
                    <Button type="button" variant="outline">
                      Cancel
                    </Button>
                  }
                />
                <Button
                  type="submit"
                  disabled={!title.trim() || mutation.isPending}
                >
                  {mutation.isPending ? "Creating..." : "Create Goal"}
                </Button>
              </Dialog.Footer>
            </div>
          </form>
        </Dialog.Content>
      </Dialog>
    </>
  );
}
