import { Outlet, useParams, NavLink, Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Play, Settings, ArrowLeft } from "lucide-react";
import { goalDetailOptions } from "@/lib/queries/goals";
import { GoalWSProvider } from "@/providers/ws-provider";
import { Text } from "@/components/retroui/Text";
import { Badge } from "@/components/retroui/Badge";

const subNav = [
  { to: "execute", icon: Play, label: "Execute" },
  { to: "settings", icon: Settings, label: "Settings" },
];

const statusLabel: Record<string, string> = {
  todo: "To Do",
  doing: "In Progress",
  review: "Review",
  done: "Done",
  failed: "Failed",
};

export function GoalLayout() {
  const { goalId: goalIdStr } = useParams<{ goalId: string }>();
  const goalId = Number(goalIdStr);
  const valid = !!goalIdStr && !isNaN(goalId);

  const { data: goal } = useQuery({ ...goalDetailOptions(goalId), enabled: valid });

  if (!valid) return <Navigate to="/" replace />;

  return (
    <GoalWSProvider goalId={goalId}>
      <div className="flex flex-col h-full">
        <div className="shrink-0 border-b-2 border-border bg-card px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <NavLink
              to="/goals"
              className="p-1 hover:bg-muted transition-colors rounded-sm"
            >
              <ArrowLeft size={14} />
            </NavLink>
            <Text as="h2" className="text-sm font-bold truncate flex-1">
              {goal?.title ?? `Goal #${goalId}`}
            </Text>
            {goal && (
              <Badge size="sm">
                {statusLabel[goal.status] ?? goal.status}
              </Badge>
            )}
          </div>
          <nav className="flex gap-1">
            {subNav.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium transition-all rounded-sm ${
                    isActive
                      ? "bg-primary text-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`
                }
              >
                <Icon size={14} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex-1 min-h-0">
          <Outlet />
        </div>
      </div>
    </GoalWSProvider>
  );
}
