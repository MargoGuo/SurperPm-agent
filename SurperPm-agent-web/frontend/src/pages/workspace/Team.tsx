import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Text } from "@/components/retroui/Text";
import { Card } from "@/components/retroui/Card";
import { Badge } from "@/components/retroui/Badge";
import { MarkdownContent } from "@/components/business/markdown-content";
import { User, ChevronDown, ChevronRight, UserCircle, Users } from "lucide-react";
import { ProfileSummary, hasProfileInStorage } from "@/pages/Profile";

interface TeamMember {
  login: string;
  avatar_url: string;
}

interface TeamProfile {
  team_name: string;
  description: string;
  members: TeamMember[];
  languages: Record<string, number>;
  team_md_exists: boolean;
  team_md: string;
}

type ViewMode = "team" | "personal";

export default function TeamPage() {

  return (
    <div className="flex flex-col h-full p-6 overflow-auto">
      <Text as="h2" className="text-2xl mb-6">
        Team
      </Text>
      <TeamContent />
    </div>
  );
}

export function TeamContent() {
  const [view, setView] = useState<ViewMode>("team");
  const {
    data: profile,
    isLoading,
    isError,
  } = useQuery<TeamProfile>({
    queryKey: ["setup", "team-profile"],
    queryFn: () => api.get<TeamProfile>("/setup/team-profile"),
  });

  const hasProfile = hasProfileInStorage();

  return (
    <div className="space-y-6 max-w-2xl">
      {/* View toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setView("team")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-2 transition-all ${
            view === "team"
              ? "border-border bg-primary shadow-[3px_3px_0_0_#000] text-foreground"
              : "border-border bg-background text-muted-foreground hover:bg-muted hover:shadow-[2px_2px_0_0_#000]"
          }`}
        >
          <Users size={14} />
          团队画像
        </button>
        <button
          onClick={() => setView("personal")}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-2 transition-all ${
            view === "personal"
              ? "border-border bg-primary shadow-[3px_3px_0_0_#000] text-foreground"
              : "border-border bg-background text-muted-foreground hover:bg-muted hover:shadow-[2px_2px_0_0_#000]"
          }`}
        >
          <UserCircle size={14} />
          个人画像
          {hasProfile && (
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
          )}
        </button>
      </div>

      {view === "team" ? (
        <TeamView profile={profile} isLoading={isLoading} isError={isError} />
      ) : (
        <PersonalView />
      )}
    </div>
  );
}

function TeamView({
  profile,
  isLoading,
  isError,
}: {
  profile?: TeamProfile;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading) {
    return <div className="text-muted-foreground text-sm">Loading team info...</div>;
  }

  if (isError || !profile) {
    return (
      <Card className="max-w-lg">
        <Card.Content>
          <p className="text-sm text-muted-foreground py-4">
            Unable to load team profile. Make sure a knowledge repository is
            configured and you have access.
          </p>
        </Card.Content>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <Card.Header>
          <Card.Title>{profile.team_name}</Card.Title>
        </Card.Header>
        <Card.Content>
          {profile.team_md ? (
            <MarkdownContent content={profile.team_md} className="mb-4 text-sm" />
          ) : (
            profile.description && (
              <p className="text-sm text-muted-foreground mb-4">
                {profile.description}
              </p>
            )
          )}
          {Object.keys(profile.languages).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(profile.languages)
                .sort(([, a], [, b]) => b - a)
                .map(([lang, pct]) => (
                  <Badge key={lang}>
                    {lang} {pct}%
                  </Badge>
                ))}
            </div>
          )}
        </Card.Content>
      </Card>

      <div>
        <Text as="h3" className="text-lg mb-3">
          Members ({profile.members.length})
        </Text>
        {profile.members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No members found.</p>
        ) : (
          <div className="space-y-2">
            {profile.members.map((member) => (
              <MemberRow key={member.login} member={member} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function PersonalView() {
  return (
    <div>
      <ProfileSummary />
    </div>
  );
}

function MemberRow({ member }: { member: TeamMember }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-2 border-border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-muted/50 transition-colors"
      >
        <div className="w-8 h-8 border-2 border-border bg-muted flex items-center justify-center shadow-[2px_2px_0_0_#000] overflow-hidden shrink-0">
          {member.avatar_url ? (
            <img
              src={member.avatar_url}
              alt={member.login}
              className="w-full h-full object-cover"
            />
          ) : (
            <User size={14} />
          )}
        </div>
        <span className="font-mono text-sm font-medium flex-1">
          {member.login}
        </span>
        {expanded ? (
          <ChevronDown size={14} className="text-muted-foreground" />
        ) : (
          <ChevronRight size={14} className="text-muted-foreground" />
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-3 border-t border-border/50">
          <div className="flex items-center gap-3 py-3">
            <div className="w-12 h-12 border-2 border-border bg-muted flex items-center justify-center shadow-[2px_2px_0_0_#000] overflow-hidden">
              {member.avatar_url ? (
                <img
                  src={member.avatar_url}
                  alt={member.login}
                  className="w-full h-full object-cover"
                />
              ) : (
                <User size={20} />
              )}
            </div>
            <div>
              <p className="font-mono text-sm font-medium">{member.login}</p>
              <a
                href={`https://github.com/${member.login}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                github.com/{member.login}
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
