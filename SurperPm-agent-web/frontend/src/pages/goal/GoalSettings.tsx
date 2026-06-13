import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { goalKeys, goalDetailOptions } from "@/lib/queries/goals";
import { Card } from "@/components/retroui/Card";
import { Input } from "@/components/retroui/Input";
import { Label } from "@/components/retroui/Label";
import { Button } from "@/components/retroui/Button";
import { Textarea } from "@/components/retroui/Textarea";

export default function GoalSettingsPage() {
  const { goalId: goalIdStr } = useParams<{ goalId: string }>();
  const goalId = Number(goalIdStr);
  const queryClient = useQueryClient();

  if (!goalIdStr || isNaN(goalId)) return null;

  const { data: goal } = useQuery(goalDetailOptions(goalId));

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (goal) {
      setTitle(goal.title);
      setDescription(goal.description ?? "");
    }
  }, [goal]);

  const updateMutation = useMutation({
    mutationFn: (body: Record<string, string>) =>
      api.patch(`/goals/${goalId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.all() });
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(goalId) });
    },
  });

  const handleSave = () => {
    if (!title.trim()) return;
    updateMutation.mutate({ title: title.trim(), description: description.trim() });
  };

  const repos: string[] = goal?.repos ? JSON.parse(goal.repos) : [];

  return (
    <div className="p-6 space-y-6 max-w-lg">
      <Card>
        <Card.Header>
          <Card.Title>Goal Info</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="space-y-4">
            <div>
              <Label htmlFor="goal-title" className="mb-1.5 block text-xs">
                Title
              </Label>
              <Input
                id="goal-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="goal-desc" className="mb-1.5 block text-xs">
                Description
              </Label>
              <Textarea
                id="goal-desc"
                value={description}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
                rows={4}
              />
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
              disabled={!title.trim() || updateMutation.isPending}
            >
              {updateMutation.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </Card.Content>
      </Card>

      <GoalReposCard goalId={goalId} repos={repos} />
    </div>
  );
}

function GoalReposCard({ goalId, repos }: { goalId: number; repos: string[] }) {
  const queryClient = useQueryClient();
  const [newUrl, setNewUrl] = useState("");

  const mutation = useMutation({
    mutationFn: (updated: string[]) =>
      api.patch(`/goals/${goalId}`, { repos: JSON.stringify(updated) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(goalId) });
    },
  });

  const handleAdd = () => {
    const url = newUrl.trim();
    if (!url) return;
    mutation.mutate([...repos, url]);
    setNewUrl("");
  };

  const handleRemove = (idx: number) => {
    mutation.mutate(repos.filter((_, i) => i !== idx));
  };

  return (
    <Card>
      <Card.Header>
        <Card.Title>Git Repositories</Card.Title>
      </Card.Header>
      <Card.Content>
        <div className="space-y-3">
          {repos.map((url, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-sm font-mono flex-1 truncate">{url}</span>
              <button
                onClick={() => handleRemove(idx)}
                disabled={mutation.isPending}
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
            <Button
              onClick={handleAdd}
              disabled={!newUrl.trim() || mutation.isPending}
            >
              <Plus size={14} />
              Add
            </Button>
          </div>
          {mutation.isError && (
            <p className="text-xs text-destructive">
              保存失败: {(mutation.error as Error).message}
            </p>
          )}
        </div>
      </Card.Content>
    </Card>
  );
}
