import { NavLink } from "react-router-dom";
import { LayoutDashboard, MessageSquare, BookOpen, Settings, PanelLeftClose, PanelLeft } from "lucide-react";
import { useUIStore } from "../../lib/stores/ui";

interface SidebarProps {
  workspaceSlug: string;
}

const navItems = [
  { to: "goals", icon: LayoutDashboard, label: "Goals" },
  { to: "discuss", icon: MessageSquare, label: "Discuss" },
  { to: "knowledge", icon: BookOpen, label: "Knowledge" },
  { to: "settings", icon: Settings, label: "Settings" },
];

export function Sidebar({ workspaceSlug }: SidebarProps) {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const base = `/workspace/${workspaceSlug}`;

  return (
    <aside
      className={`flex flex-col border-r-2 border-border bg-card transition-all ${
        sidebarCollapsed ? "w-16" : "w-56"
      }`}
    >
      <div className="flex h-14 items-center justify-between px-4 border-b-2 border-border">
        {!sidebarCollapsed && (
          <span className="font-head text-base font-bold tracking-tight">SuperPmAgent</span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 border-2 border-border bg-background hover:bg-primary hover:shadow-[2px_2px_0_0_#000] active:shadow-none transition-all text-foreground"
        >
          {sidebarCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>
      <nav className="flex-1 py-3 space-y-1 px-2">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={`${base}/${to}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 text-sm font-medium border-2 transition-all ${
                isActive
                  ? "border-border bg-primary text-foreground shadow-[3px_3px_0_0_#000]"
                  : "border-transparent text-muted-foreground hover:border-border hover:bg-background hover:shadow-[2px_2px_0_0_#000]"
              }`
            }
          >
            <Icon size={18} />
            {!sidebarCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
