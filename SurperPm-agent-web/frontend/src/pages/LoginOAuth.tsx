import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Search } from 'lucide-react'
import { api } from '@/lib/api'
import type { Repo, User } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/retroui/Button'
import { Input } from '@/components/retroui/Input'
import { Label } from '@/components/retroui/Label'
import { Text } from '@/components/retroui/Text'
import { Alert } from '@/components/retroui/Alert'

// ---- inline icons ----

const GithubIcon = ({ size = 20, className = '' }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
)

const UserAvatar = ({ avatarUrl, username, size = 36 }: { avatarUrl?: string; username: string; size?: number }) => {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        width={size}
        height={size}
        className="rounded-full border-2 border-border flex-shrink-0"
      />
    )
  }
  return (
    <div
      style={{ width: size, height: size }}
      className="flex items-center justify-center rounded-full border-2 border-border bg-muted/30 font-bold text-base flex-shrink-0"
    >
      {username.charAt(0).toUpperCase()}
    </div>
  )
}

// ---- types ----

type Step = 'connect' | 'select' | 'final'

// ---- step indicator ----

const STEPS = [
  { key: 'connect' as Step, label: '连接 GitHub' },
  { key: 'select' as Step, label: '选择仓库' },
  { key: 'final'  as Step, label: '开始使用' },
]

function StepDots({ current }: { current: Step }) {
  const idx = STEPS.findIndex((s) => s.key === current)
  return (
    <>
      <div className="flex items-center gap-0">
        {STEPS.map((s, i) => (
          <span key={s.key} className="contents">
            <div
              className={`flex items-center justify-center w-8 h-8 border-2 text-[13px] font-bold ${
                i < idx
                  ? 'bg-foreground text-background border-border'
                  : i === idx
                    ? 'bg-primary border-border shadow-[3px_3px_0_0_var(--border)]'
                    : 'border-muted text-muted-foreground'
              }`}
            >
              {i < idx ? '✓' : i + 1}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 mx-1 ${i < idx ? 'bg-foreground' : 'bg-muted'}`} />
            )}
          </span>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground -mt-3">
        {STEPS.map((s) => (
          <span key={s.key} className="font-head">{s.label}</span>
        ))}
      </div>
    </>
  )
}

// ==================== CONNECT STEP ====================

function ConnectStep({ loading, error, onConnect }: {
  loading: boolean
  error: string
  onConnect: () => void
}) {
  return (
    <div className="w-full max-w-md mx-auto">
      <div className="border-2 border-border shadow-[4px_4px_0_0_#000] bg-card">
        <div className="p-6 pb-4">
          <Text as="h1" className="text-3xl mb-1">SuperPmAgent</Text>
          <p className="text-sm text-muted-foreground">
            连接 GitHub 即可开始。无需注册，授权后自动列出你的仓库。
          </p>
        </div>

        <div className="px-6 pb-6 space-y-5">
          <StepDots current="connect" />

          <div className="pt-2">
            <Button
              className="w-full py-3 text-base"
              onClick={onConnect}
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  正在跳转 GitHub 授权...
                </span>
              ) : (
                <>
                  <GithubIcon size={20} />
                  Connect with GitHub
                </>
              )}
            </Button>
          </div>

          <div className="border-t-2 pt-4">
            <p className="text-xs text-muted-foreground mb-2 font-head">授权后我们将获取：</p>
            <div className="space-y-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-2">
                <span className="text-green-600 leading-none">✓</span>
                <span>读取你的公开仓库和私有仓库列表</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-600 leading-none">✓</span>
                <span>读写所选仓库的代码、Issues、PR</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-destructive leading-none">✗</span>
                <span className="text-muted-foreground/60">不会访问你的 GitHub 密码或设置</span>
              </div>
            </div>
          </div>

          {error && (
            <Alert status="warning">
              <Alert.Title>连接失败</Alert.Title>
              <Alert.Description>
                {error}
                {error.includes('not configured') && (
                  <span className="block mt-1">本地开发请使用下方 PAT 登录。</span>
                )}
              </Alert.Description>
            </Alert>
          )}

          <div className="border-t-2 pt-4">
            <Link to="/login-pat" className="block">
              <Button variant="outline" className="w-full">
                使用 Personal Access Token 登录
              </Button>
            </Link>
            <p className="text-xs text-muted-foreground mt-2 text-center">
              适合本地开发或无 OAuth App 配置的场景
            </p>
          </div>

          <div className="text-xs text-muted-foreground pt-2 border-t-2">
            <strong>没有账号？</strong> SuperPmAgent 不做注册 — 能访问仓库就能登录。
          </div>
        </div>
      </div>
    </div>
  )
}

// ==================== SELECT STEP ====================

function SelectStep({
  username, avatarUrl, repos, loading, searchQuery, selectedRepo,
  onSearch, onSelect, onConfirm, onBack,
}: {
  username: string
  avatarUrl: string
  repos: Repo[]
  loading: boolean
  searchQuery: string
  selectedRepo: Repo | null
  onSearch: (q: string) => void
  onSelect: (r: Repo) => void
  onConfirm: () => void
  onBack: () => void
}) {
  const q = searchQuery.toLowerCase()
  const filtered = repos.filter((r) =>
    r.name.toLowerCase().includes(q) ||
    r.owner.toLowerCase().includes(q) ||
    (r.desc && r.desc.toLowerCase().includes(q)),
  )

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="border-2 border-border shadow-[4px_4px_0_0_#000] bg-card">
        {/* header — title left, avatar right */}
        <div className="p-6 pb-2">
          <div className="flex items-center justify-between mb-2">
            <Text as="h2">SuperPmAgent</Text>
            <div className="flex items-center gap-2">
              <UserAvatar avatarUrl={avatarUrl} username={username} size={36} />
              <span className="text-sm font-medium">{username}</span>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6 space-y-4">
          <StepDots current="select" />

          {/* search */}
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-10 font-mono"
              placeholder="搜索仓库..."
              value={searchQuery}
              onChange={(e) => onSearch(e.target.value)}
            />
          </div>

          {/* repo list */}
          {loading ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent mb-2" />
              <br />
              加载仓库列表中...
            </div>
          ) : (
            <div style={{ maxHeight: 320, overflowY: 'auto', overflowX: 'hidden' }}>
              {filtered.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  没有匹配的仓库
                </div>
              ) : (
                filtered.map((repo) => {
                  const sel = selectedRepo?.name === repo.name && selectedRepo?.owner === repo.owner
                  return (
                    <button
                      key={`${repo.owner}/${repo.name}`}
                      onClick={() => onSelect(repo)}
                      className={`w-full text-left flex items-center gap-3 px-4 py-3 border-l-2 border-r-2 border-b border-[#d4d4d4] cursor-pointer transition-all duration-100
                        first:border-t-2 first:border-t-border
                        last:border-b-2 last:border-b-border
                        ${sel ? 'bg-primary border-l-[#8B5CF6]' : 'bg-white hover:bg-primary hover:border-l-[#8B5CF6]'}`}
                    >
                      <GithubIcon size={18} className="shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold truncate">{repo.owner}/{repo.name}</span>
                          <span className={`inline-flex text-[11px] px-2 py-0.5 border border-border font-semibold shrink-0 ${repo.private ? 'bg-[#f0f0f0] text-muted-foreground' : 'bg-[#cfc] text-[#060]'}`}>
                            {repo.private ? 'Private' : 'Public'}
                          </span>
                        </div>
                        {repo.desc && (
                          <div className="text-xs text-muted-foreground mt-0.5 truncate">{repo.desc}</div>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground text-right shrink-0">
                        <div className="flex items-center gap-1 justify-end">
                          ★ {repo.stars}
                        </div>
                        <div className="text-gray-300">{repo.updated}</div>
                      </div>
                    </button>
                  )
                })
              )}
            </div>
          )}

          {/* actions */}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onBack}>
              &larr; 返回
            </Button>
            <Button className="flex-1" disabled={!selectedRepo} onClick={onConfirm}>
              确认选择
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ==================== FINAL STEP ====================

function FinalStep({
  username, avatarUrl, selectedRepo, anthropicKey, showKey, loading, error,
  onKeyChange, onToggleKey, onSubmit, onBack,
}: {
  username: string
  avatarUrl: string
  selectedRepo: Repo
  anthropicKey: string
  showKey: boolean
  loading: boolean
  error: string
  onKeyChange: (v: string) => void
  onToggleKey: () => void
  onSubmit: () => void
  onBack: () => void
}) {

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="border-2 border-border shadow-[4px_4px_0_0_#000] bg-card">
        {/* header — title left, avatar right */}
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between mb-2">
            <Text as="h2">SuperPmAgent</Text>
            <div className="flex items-center gap-2">
              <UserAvatar avatarUrl={avatarUrl} username={username} size={36} />
              <span className="text-sm font-medium">{username}</span>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6 space-y-4">
          <StepDots current="final" />

          {/* selected repo badge */}
          <div className="flex items-center gap-3 p-3 border-2 border-border bg-gray-50">
            <GithubIcon size={18} />
            <span className="font-mono text-sm flex-1">{selectedRepo.owner}/{selectedRepo.name}</span>
            <button onClick={onBack} className="ml-auto text-xs text-[#8B5CF6] underline decoration-[#8B5CF6] decoration-2 underline-offset-4 hover:decoration-4 cursor-pointer">
              更换
            </button>
          </div>

          {/* api key */}
          <div>
            <Label htmlFor="anthropic-key" className="mb-1.5 block font-head text-sm">Anthropic API Key（可选）</Label>
            <div className="relative">
              <Input
                id="anthropic-key"
                type={showKey ? 'text' : 'password'}
                placeholder="sk-ant-..."
                value={anthropicKey}
                onChange={(e) => onKeyChange(e.target.value)}
                className="font-mono pr-10"
              />
              <button
                type="button"
                onClick={onToggleKey}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              <a
                className="text-[#8B5CF6] underline decoration-[#8B5CF6] decoration-2 underline-offset-4 hover:decoration-4"
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noreferrer"
              >
                获取 API Key &rarr;
              </a>
            </p>
          </div>

          {error && (
            <Alert status="warning">
              <Alert.Title>登录失败</Alert.Title>
              <Alert.Description>{error}</Alert.Description>
            </Alert>
          )}

          <Button
            className="w-full py-3 text-base"
            disabled={loading}
            onClick={onSubmit}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                验证中...
              </span>
            ) : '开始使用'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ==================== MAIN PAGE ====================

export default function LoginOAuth() {
  const navigate = useNavigate()
  const { refresh } = useAuth()

  const [step, setStep] = useState<Step>('connect')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [username, setUsername] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [repos, setRepos] = useState<Repo[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null)

  const [anthropicKey, setAnthropicKey] = useState('')
  const [showKey, setShowKey] = useState(false)

  // detect OAuth callback return
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const stepParam = params.get('step')
    const errorParam = params.get('error')

    if (errorParam) {
      setError(errorParam === 'access_denied' ? 'GitHub 授权被取消' : 'GitHub 授权失败，请重试')
      window.history.replaceState({}, '', '/login')
      return
    }

    if (stepParam === 'select') {
      window.history.replaceState({}, '', '/login')
      loadRepos()
    }
  }, [])

  useEffect(() => {
    if (step === 'select') setSearchQuery('')
  }, [step])

  const loadRepos = async () => {
    setError('')
    setLoading(true)
    setStep('select')
    try {
      const [user, repos] = await Promise.all([api.get<User>('/auth/me'), api.get<Repo[]>('/auth/github/repos')])
      setUsername(user.username)
      setAvatarUrl(user.avatar_url || '')
      setRepos(repos)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载仓库列表失败')
      setStep('connect')
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async () => {
    setError('')
    setLoading(true)
    try {
      const { url } = await api.get<{ url: string }>('/auth/github/authorize')
      window.location.href = url
    } catch (e) {
      setError(e instanceof Error ? e.message : '无法启动 GitHub 授权')
      setLoading(false)
    }
  }

  const handleConfirmRepo = () => {
    if (!selectedRepo) return
    setStep('final')
  }

  const handleSubmit = async () => {
    if (!selectedRepo) return
    setError('')
    setLoading(true)
    try {
      const repoFullName = `${selectedRepo.owner}/${selectedRepo.name}`
      await api.post('/auth/github/complete', {
        repo: repoFullName,
        anthropic_key: anthropicKey.trim(),
      })
      refresh()

      const workspaces = await api.get<{ id: string; name: string; slug: string; repo_url?: string }[]>('/workspaces')
      let ws = workspaces.find((w) => w.repo_url === repoFullName)
      if (!ws) {
        const slug = selectedRepo.name.toLowerCase().replace(/[^a-z0-9-]/g, '-')
        ws = await api.post<{ id: string; name: string; slug: string }>('/workspaces', { name: selectedRepo.name, slug, repo_url: repoFullName })
      }
      navigate(`/workspace/${ws.slug}/goals`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 [background-image:radial-gradient(#000_1px,transparent_1px)] [background-size:20px_20px]">
      {step === 'connect' && (
        <ConnectStep loading={loading} error={error} onConnect={handleConnect} />
      )}
      {step === 'select' && (
        <SelectStep
          username={username}
          avatarUrl={avatarUrl}
          repos={repos}
          loading={loading}
          searchQuery={searchQuery}
          selectedRepo={selectedRepo}
          onSearch={setSearchQuery}
          onSelect={setSelectedRepo}
          onConfirm={handleConfirmRepo}
          onBack={() => { setStep('connect'); setError('') }}
        />
      )}
      {step === 'final' && selectedRepo && (
        <FinalStep
          username={username}
          avatarUrl={avatarUrl}
          selectedRepo={selectedRepo}
          anthropicKey={anthropicKey}
          showKey={showKey}
          loading={loading}
          error={error}
          onKeyChange={setAnthropicKey}
          onToggleKey={() => setShowKey((v) => !v)}
          onSubmit={handleSubmit}
          onBack={() => { setStep('select'); setError('') }}
        />
      )}
    </div>
  )
}
