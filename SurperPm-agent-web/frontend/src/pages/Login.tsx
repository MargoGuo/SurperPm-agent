import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/retroui/Button'
import { Input } from '@/components/retroui/Input'
import { Label } from '@/components/retroui/Label'
import { Card } from '@/components/retroui/Card'
import { Text } from '@/components/retroui/Text'
import { Alert } from '@/components/retroui/Alert'

export default function Login() {
  const [pat, setPat] = useState('')
  const [repo, setRepo] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPat, setShowPat] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [touched, setTouched] = useState<Record<string, boolean>>({})
  const navigate = useNavigate()
  const { refresh } = useAuth()

  const handleLogin = async () => {
    setError('')
    setLoading(true)
    try {
      const result = await api.auth.login(pat, repo, anthropicKey)
      refresh()
      navigate(result.profile_missing ? '/setup' : '/goal')
    } catch (e) {
      setError(e instanceof Error ? e.message : '登录失败，检查输入')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && canSubmit && !loading) {
      handleLogin()
    }
  }

  const canSubmit = pat.trim() && repo.trim() && anthropicKey.trim()

  const fieldError = (field: string, value: string) =>
    touched[field] && !value.trim() ? '此项必填' : undefined

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 [background-image:radial-gradient(#000_1px,transparent_1px)] [background-size:20px_20px]">
      <Card className="w-full max-w-md mx-auto shadow-xl hover:shadow-xl">
        <Card.Header>
          <Text as="h1" className="mb-1">SuperPmAgent</Text>
          <p className="text-sm text-muted-foreground">
            填写以下信息即可开始使用。无注册，凭你对仓库的访问权限。
          </p>
        </Card.Header>
        <Card.Content>
          <div className="space-y-4" onKeyDown={handleKeyDown}>
            <div>
              <Label htmlFor="repo" className="mb-1.5 block font-head text-sm">团队仓库地址</Label>
              <Input
                id="repo"
                placeholder="myorg/claude-for-SuperPmAgent-fork"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, repo: true }))}
                aria-invalid={!!fieldError('repo', repo)}
                className="font-mono"
              />
              {fieldError('repo', repo) && (
                <p className="text-xs text-destructive mt-1">{fieldError('repo', repo)}</p>
              )}
            </div>
            <div>
              <Label htmlFor="pat" className="mb-1.5 block font-head text-sm">GitHub Personal Access Token</Label>
              <div className="relative">
                <Input
                  id="pat"
                  type={showPat ? 'text' : 'password'}
                  placeholder="ghp_..."
                  value={pat}
                  onChange={(e) => setPat(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, pat: true }))}
                  aria-invalid={!!fieldError('pat', pat)}
                  className="font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPat((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {showPat ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {fieldError('pat', pat) && (
                <p className="text-xs text-destructive mt-1">{fieldError('pat', pat)}</p>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                需要 repo 权限 ·{' '}
                <a
                  className="text-[#8B5CF6] underline decoration-[#8B5CF6] decoration-2 underline-offset-4 hover:decoration-4"
                  href="https://github.com/settings/tokens/new"
                  target="_blank"
                  rel="noreferrer"
                >
                  前往 GitHub 创建 →
                </a>
              </p>
            </div>
            <div>
              <Label htmlFor="anthropic-key" className="mb-1.5 block font-head text-sm">Anthropic API Key</Label>
              <div className="relative">
                <Input
                  id="anthropic-key"
                  type={showKey ? 'text' : 'password'}
                  placeholder="sk-ant-..."
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, key: true }))}
                  aria-invalid={!!fieldError('key', anthropicKey)}
                  className="font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {fieldError('key', anthropicKey) && (
                <p className="text-xs text-destructive mt-1">{fieldError('key', anthropicKey)}</p>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                <a
                  className="text-[#8B5CF6] underline decoration-[#8B5CF6] decoration-2 underline-offset-4 hover:decoration-4"
                  href="https://console.anthropic.com/settings/keys"
                  target="_blank"
                  rel="noreferrer"
                >
                  获取 API Key
                </a>
              </p>
            </div>

            {error && (
              <Alert status="error">
                <Alert.Title>登录失败</Alert.Title>
                <Alert.Description>{error}</Alert.Description>
              </Alert>
            )}

            <Button
              onClick={handleLogin}
              disabled={loading || !canSubmit}
              className="w-full"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  验证中...
                </span>
              ) : '开始使用'}
            </Button>
          </div>

          <div className="mt-6 pt-4 border-t-2 text-sm text-muted-foreground">
            <strong>没有账号？</strong> SuperPmAgent 不做注册 — 能 clone 仓库就能登录。
          </div>
        </Card.Content>
      </Card>
    </div>
  )
}
