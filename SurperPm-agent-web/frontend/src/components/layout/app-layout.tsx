import { useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import {
  MessagesSquare,
  Target,
  Lightbulb,
  Settings,
  Menu,
  X,
  LogOut,
  User,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useUIStore } from "../../lib/stores/ui";
import { useAuth } from "../../context/AuthContext";

const navItems = [
  { to: "/", icon: MessagesSquare, label: "Discuss", end: true },
  { to: "/goals", icon: Target, label: "Goal" },
  { to: "/knowledge", icon: Lightbulb, label: "Learning" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

function MobileNav() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();

  return (
    <>
      <div className="md:hidden flex items-center h-12 px-4 border-b-2 border-border bg-card">
        <button
          onClick={() => setOpen(true)}
          className="p-1.5 border-2 border-border bg-background hover:bg-primary transition-all"
        >
          <Menu size={18} />
        </button>
        <span className="ml-3 font-head text-sm font-bold">SuperPmAgent</span>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-card border-r-2 border-border flex flex-col">
            <div className="flex h-14 items-center justify-between px-4 border-b-2 border-border">
              <span className="font-head text-base font-bold">SuperPmAgent</span>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 border-2 border-border bg-background hover:bg-primary transition-all"
              >
                <X size={16} />
              </button>
            </div>

            <nav className="flex-1 py-3 space-y-1 px-2">
              {navItems.map(({ to, icon: Icon, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 text-sm font-medium border-2 transition-all ${
                      isActive
                        ? "border-border bg-primary text-foreground shadow-[3px_3px_0_0_#000]"
                        : "border-transparent text-muted-foreground hover:border-border hover:bg-background"
                    }`
                  }
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>

            <div className="border-t-2 border-border p-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 border-2 border-border bg-muted flex items-center justify-center shadow-[2px_2px_0_0_#000] shrink-0">
                  <User size={14} />
                </div>
                <span className="text-xs font-bold truncate flex-1">
                  {user?.username ?? "User"}
                </span>
                <button
                  onClick={() => {
                    logout();
                    setOpen(false);
                  }}
                  aria-label="Logout"
                  title="Logout"
                  className="flex items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors border-2 border-transparent hover:border-border shrink-0"
                >
                  <LogOut size={14} />
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

function AppSidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, logout } = useAuth();

  return (
    <aside
      className={`hidden md:flex flex-col border-r border-border bg-card transition-all ${
        sidebarCollapsed ? "w-12" : "w-44"
      }`}
    >
      <div className="flex h-10 items-center justify-between px-2.5 border-b border-border">
        {!sidebarCollapsed && (
          <span className="font-head text-xs font-bold tracking-tight">SuperPmAgent</span>
        )}
        <button onClick={toggleSidebar} className="p-1 hover:bg-muted transition-colors text-muted-foreground">
          {sidebarCollapsed ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}
        </button>
      </div>

      <nav className="flex-1 py-1.5 space-y-0.5 px-1.5">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2 px-2 py-1.5 text-xs font-medium transition-all rounded-sm ${
                isActive
                  ? "bg-primary text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <Icon size={15} />
            {!sidebarCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-2">
        {sidebarCollapsed ? (
          <div className="flex flex-col items-center">
            <div className="w-6 h-6 bg-muted flex items-center justify-center overflow-hidden rounded-sm">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <User size={12} />
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 bg-muted flex items-center justify-center overflow-hidden rounded-sm shrink-0">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <User size={10} />
              )}
            </div>
            <span className="text-[10px] font-medium truncate flex-1">
              {user?.username ?? "User"}
            </span>
            <button
              onClick={() => logout()}
              aria-label="Logout"
              title="Logout"
              className="p-1 text-muted-foreground hover:text-foreground transition-colors shrink-0"
            >
              <LogOut size={12} />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

export function AppLayout() {
  return (
    <div className="flex flex-col md:flex-row h-screen bg-background text-foreground">
      <MobileNav />
      <AppSidebar />
      <main className="flex-1 min-h-0 min-w-0 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
