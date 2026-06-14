import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import {
  workspaceListOptions,
  workspaceReposOptions,
  workspaceRepoKeys,
} from "@/lib/queries/workspaces";
import { Card } from "@/components/retroui/Card";
import { Input } from "@/components/retroui/Input";
import { Button } from "@/components/retroui/Button";

export function ReposManager() {
  const { data: workspaces = [] } = useQuery(workspaceListOptions());
  const workspaceId = workspaces[0]?.id ?? "";

  if (!workspaceId) {
    return (
      <div className="max-w-lg">
        <p className="text-sm text-muted-foreground">No workspace yet.</p>
      </div>
    );
  }

  return (
    <div className="max-w-lg">
      <ReposCard workspaceId={workspaceId} />
    </div>
  );
}

function ReposCard({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [newUrl, setNewUrl] = useState("");
  const { data: repos = [] } = useQuery(workspaceReposOptions(workspaceId));

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: workspaceRepoKeys.all(workspaceId) });

  const addMutation = useMutation({
    mutationFn: (url: string) =>
      api.post(`/workspaces/${workspaceId}/repos`, { url }),
    onSuccess: invalidate,
  });

  const removeMutation = useMutation({
    mutationFn: (index: number) =>
      api.delete(`/workspaces/${workspaceId}/repos/${index}`),
    onSuccess: invalidate,
  });

  const handleAdd = () => {
    const url = newUrl.trim();
    if (!url) return;
    addMutation.mutate(url, { onSuccess: () => setNewUrl("") });
  };

  const pending = addMutation.isPending || removeMutation.isPending;

  return (
    <Card>
      <Card.Header>
        <Card.Title>Git Repositories</Card.Title>
      </Card.Header>
      <Card.Content>
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Global repo list — select from these when creating goals.
          </p>
          {repos.map((url, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-sm font-mono flex-1 truncate">{url}</span>
              <button
                onClick={() => removeMutation.mutate(idx)}
                disabled={pending}
                className="p-1 text-muted-foreground hover:text-destructive transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <Input
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://github.com/org/repo"
              className="flex-1 font-mono text-sm"
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <Button onClick={handleAdd} disabled={!newUrl.trim() || pending}>
              <Plus size={14} />
              Add
            </Button>
          </div>
          {addMutation.isError && (
            <p className="text-xs text-destructive">
              Add failed: {(addMutation.error as Error).message}
            </p>
          )}
        </div>
      </Card.Content>
    </Card>
  );
}
