import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/retroui/Button'
import { Badge } from '@/components/retroui/Badge'
import { Text } from '@/components/retroui/Text'

const navItems = [
  { to: '/goal', label: 'Goal' },
  { to: '/knowledge', label: 'Knowledge' },
  { to: '/config', label: 'Config' },
  { to: '/setup', label: 'Profile' },
]

export default function Layout() {
  const navigate = useNavigate()
  const { user, logout: doLogout } = useAuth()

  if (!user) return null

  const logout = async () => {
    await doLogout()
    navigate('/login')
  }

  const copyRepo = () => {
    void navigator.clipboard?.writeText(user.repo)
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <nav className="border-b-2 bg-card px-4 sm:px-6 py-3 flex items-center gap-4 sm:gap-6 sticky top-0 z-10">
        <Text as="h3" className="font-bold shrink-0">SuperPmAgent</Text>

        <div className="flex gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-1.5 border-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary text-primary-foreground border-border'
                    : 'border-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={copyRepo}
            className="cursor-pointer"
            title="点击复制仓库地址"
          >
            <Badge variant="outline" className="font-mono cursor-pointer">{user.repo}</Badge>
          </button>
          <div className="w-px h-4 bg-border" />
          {user.avatar_url && (
            <img
              src={user.avatar_url}
              alt={user.username}
              className="w-6 h-6 rounded-full border border-border object-cover shrink-0"
            />
          )}
          <span className="text-sm font-medium">@{user.username}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            退出
          </Button>
        </div>
      </nav>

      <main className="flex-1 min-h-0 overflow-auto nb-scrollbar flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
