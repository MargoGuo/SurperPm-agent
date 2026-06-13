import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { workspaceListOptions } from "@/lib/queries/workspaces";
import { SshKeyDisplay } from "@/components/settings/ssh-key-display";
import { SecretsManager } from "@/components/settings/secrets-manager";
import { Text } from "@/components/retroui/Text";
import { Card } from "@/components/retroui/Card";
import { Input } from "@/components/retroui/Input";
import { Label } from "@/components/retroui/Label";

type Tab = "general" | "ssh" | "secrets";

const TABS: { id: Tab; label: string }[] = [
  { id: "general", label: "General" },
  { id: "ssh", label: "SSH Key" },
  { id: "secrets", label: "Secrets" },
];

export default function SettingsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const { data: workspaces = [] } = useQuery(workspaceListOptions());

  if (!slug) return null;

  const workspace = workspaces.find((w) => w.slug === slug);

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

      <div className="flex-1 min-h-0">
        {activeTab === "general" && (
          <GeneralTab workspaceName={workspace?.name ?? slug} />
        )}
        {activeTab === "ssh" && <SshKeyDisplay workspaceSlug={slug} />}
        {activeTab === "secrets" && <SecretsManager workspaceSlug={slug} />}
      </div>
    </div>
  );
}

function GeneralTab({ workspaceName }: { workspaceName: string }) {
  return (
    <Card className="max-w-lg">
      <Card.Header>
        <Card.Title>Workspace Info</Card.Title>
      </Card.Header>
      <Card.Content>
        <div className="space-y-4">
          <div>
            <Label htmlFor="ws-name" className="mb-1.5 block font-head text-sm">Workspace Name</Label>
            <Input
              id="ws-name"
              value={workspaceName}
              readOnly
              className="font-mono cursor-not-allowed opacity-70"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              Workspace name editing is not available yet.
            </p>
          </div>
        </div>
      </Card.Content>
    </Card>
  );
}
