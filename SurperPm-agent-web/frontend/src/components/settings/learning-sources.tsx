import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { globalConfigOptions, globalConfigKeys } from "@/lib/queries/global-config";
import { Card } from "@/components/retroui/Card";
import { Button } from "@/components/retroui/Button";
import { Input } from "@/components/retroui/Input";
import { Label } from "@/components/retroui/Label";
import { Select } from "@/components/retroui/Select";
import { Trash2, Plus, Save } from "lucide-react";

interface ExternalSource {
  type: "github" | "rss" | "webpage";
  url: string;
}

interface DistillConfig {
  internal_sources: { executions: boolean; discussions: boolean };
  external_sources: ExternalSource[];
  schedule: { interval_hours: number };
  decay: { archive_threshold: number; pin_bonus: number };
  max_learnings_per_cycle: number;
}

const DEFAULT_CONFIG: DistillConfig = {
  internal_sources: { executions: true, discussions: true },
  external_sources: [],
  schedule: { interval_hours: 24 },
  decay: { archive_threshold: 0.3, pin_bonus: 0.5 },
  max_learnings_per_cycle: 10,
};

export function LearningSourcesTab() {
  const queryClient = useQueryClient();
  const { data: globalConfig } = useQuery(globalConfigOptions());

  const [config, setConfig] = useState<DistillConfig>(DEFAULT_CONFIG);
  const [newSourceType, setNewSourceType] = useState<"github" | "rss" | "webpage">("github");
  const [newSourceUrl, setNewSourceUrl] = useState("");

  useEffect(() => {
    if (globalConfig?.distill_config) {
      try {
        setConfig(JSON.parse(globalConfig.distill_config));
      } catch { /* use default */ }
    }
  }, [globalConfig?.distill_config]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.patch("/global-config", { distill_config: JSON.stringify(config) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: globalConfigKeys.all() });
    },
  });

  const addSource = () => {
    if (!newSourceUrl.trim()) return;
    setConfig((prev) => ({
      ...prev,
      external_sources: [
        ...prev.external_sources,
        { type: newSourceType, url: newSourceUrl.trim() },
      ],
    }));
    setNewSourceUrl("");
  };

  const removeSource = (index: number) => {
    setConfig((prev) => ({
      ...prev,
      external_sources: prev.external_sources.filter((_, i) => i !== index),
    }));
  };

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <Card.Header>
          <Card.Title>Internal Sources</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={config.internal_sources.executions}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    internal_sources: { ...prev.internal_sources, executions: e.target.checked },
                  }))
                }
                className="rounded border-border"
              />
              Goal executions
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={config.internal_sources.discussions}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    internal_sources: { ...prev.internal_sources, discussions: e.target.checked },
                  }))
                }
                className="rounded border-border"
              />
              AI discussions
            </label>
          </div>
        </Card.Content>
      </Card>

      <Card>
        <Card.Header>
          <Card.Title>External Sources</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="space-y-4">
            {config.external_sources.length > 0 && (
              <div className="space-y-2">
                {config.external_sources.map((src, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="px-2 py-0.5 border border-border text-xs font-mono">
                      {src.type}
                    </span>
                    <span className="flex-1 truncate font-mono text-xs">{src.url}</span>
                    <Button variant="outline" size="sm" onClick={() => removeSource(i)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-end gap-2">
              <div>
                <Label className="text-xs mb-1 block">Type</Label>
                <Select value={newSourceType} onValueChange={(v) => setNewSourceType((v ?? "github") as ExternalSource["type"])}>
                  <Select.Trigger className="w-28">
                    <Select.Value />
                  </Select.Trigger>
                  <Select.Content>
                    <Select.Item value="github">GitHub</Select.Item>
                    <Select.Item value="rss">RSS</Select.Item>
                    <Select.Item value="webpage">Webpage</Select.Item>
                  </Select.Content>
                </Select>
              </div>
              <div className="flex-1">
                <Label className="text-xs mb-1 block">URL</Label>
                <Input
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                  placeholder="https://github.com/org/repo"
                  className="font-mono text-xs"
                />
              </div>
              <Button variant="outline" size="sm" onClick={addSource} disabled={!newSourceUrl.trim()}>
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </Card.Content>
      </Card>

      <Card>
        <Card.Header>
          <Card.Title>Schedule & Decay</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs mb-1 block">Distill interval (hours)</Label>
              <Input
                type="number"
                min={1}
                max={168}
                value={config.schedule.interval_hours}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    schedule: { ...prev.schedule, interval_hours: Number(e.target.value) || 24 },
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Max items per cycle</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={config.max_learnings_per_cycle}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    max_learnings_per_cycle: Number(e.target.value) || 10,
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Archive threshold</Label>
              <Input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={config.decay.archive_threshold}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    decay: { ...prev.decay, archive_threshold: Number(e.target.value) || 0.3 },
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Pin bonus</Label>
              <Input
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={config.decay.pin_bonus}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    decay: { ...prev.decay, pin_bonus: Number(e.target.value) || 0.5 },
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
          </div>
        </Card.Content>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          <Save className="h-3.5 w-3.5 mr-1" />
          {saveMutation.isPending ? "Saving..." : "Save"}
        </Button>
        {saveMutation.isSuccess && <span className="text-xs text-green-600">Saved</span>}
        {saveMutation.isError && (
          <span className="text-xs text-destructive">
            Save failed: {(saveMutation.error as Error).message}
          </span>
        )}
      </div>
    </div>
  );
}
