import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { sshKeyOptions, globalConfigKeys } from "@/lib/queries/global-config";
import { Button } from "@/components/retroui/Button";
import { Textarea } from "@/components/retroui/Textarea";
import { Alert } from "@/components/retroui/Alert";
import { KeyRound, Copy, RefreshCw, Upload } from "lucide-react";

export function SshKeyDisplay() {
  const [copied, setCopied] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery(sshKeyOptions());
  const publicKey = data?.ssh_public_key ?? "";
  const hasPrivateKey = data?.has_private_key ?? false;

  const generateMutation = useMutation({
    mutationFn: () => api.post<{ ssh_public_key: string }>("/global-config/generate-ssh-key"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: globalConfigKeys.sshKey() });
    },
  });

  const [pushResult, setPushResult] = useState<{ ok: boolean; message: string } | null>(null);
  const pushToGithubMutation = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string }>("/global-config/push-ssh-key-to-github"),
    onSuccess: (data) => setPushResult(data),
    onError: (e: Error) => setPushResult({ ok: false, message: e.message }),
  });

  const handleCopy = async () => {
    if (!publicKey) return;
    await navigator.clipboard.writeText(publicKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return <div className="text-foreground/40 text-sm">Loading SSH key...</div>;
  }

  if (error) {
    return (
      <Alert status="warning">
        <Alert.Title>SSH Key Error</Alert.Title>
        <Alert.Description>
          Failed to load SSH key: {(error as Error).message}
        </Alert.Description>
      </Alert>
    );
  }

  if (!publicKey) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 border border-border bg-card px-4">
        <KeyRound size={32} className="opacity-15" />
        <div className="text-center">
          <p className="text-sm font-head">No SSH key generated</p>
          <p className="text-xs text-foreground/40 mt-1">
            Generate an SSH key to let SuperPmAgent access your Git repos.
          </p>
        </div>
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
        >
          <RefreshCw
            size={14}
            className={generateMutation.isPending ? "animate-spin" : ""}
          />
          {generateMutation.isPending ? "Generating..." : "Generate SSH Key"}
        </Button>
        {generateMutation.isError && (
          <p className="text-xs text-destructive font-bold">
            Failed to generate key: {(generateMutation.error as Error).message}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {!hasPrivateKey && (
        <Alert status="warning">
          <Alert.Description>
            Private key missing. Please regenerate the key pair.
          </Alert.Description>
        </Alert>
      )}
      <p className="text-sm text-foreground/60">
        Add this public key to your Git hosting provider (GitHub, GitLab, etc.)
        to allow SuperPmAgent to access your repositories.
      </p>
      <div className="relative">
        <Textarea
          readOnly
          value={publicKey}
          rows={3}
          className="font-mono text-xs resize-none pr-20"
        />
        <Button size="sm" onClick={handleCopy} className="absolute top-2 right-2">
          <Copy size={12} />
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
        >
          <RefreshCw
            size={14}
            className={generateMutation.isPending ? "animate-spin" : ""}
          />
          {generateMutation.isPending ? "Generating..." : "Regenerate"}
        </Button>
        <Button
          size="sm"
          onClick={() => { setPushResult(null); pushToGithubMutation.mutate(); }}
          disabled={pushToGithubMutation.isPending}
        >
          <Upload size={14} />
          {pushToGithubMutation.isPending ? "Adding..." : "Add to GitHub"}
        </Button>
      </div>
      {generateMutation.isError && (
        <p className="text-xs text-destructive font-bold">
          Failed to generate key: {(generateMutation.error as Error).message}
        </p>
      )}
      {pushResult && (
        <p className={`text-xs font-bold ${pushResult.ok ? "text-green-600" : "text-destructive"}`}>
          {pushResult.ok ? `✓ ${pushResult.message}` : `✗ ${pushResult.message}`}
        </p>
      )}
    </div>
  );
}
