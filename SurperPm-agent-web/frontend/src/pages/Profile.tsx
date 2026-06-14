import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/retroui/Button'
import { Text } from '@/components/retroui/Text'
import { UserCircle } from 'lucide-react'
import { QUESTIONS, SUMMARY_CATEGORIES, type Question } from './setup/questions'

export const DRAFT_KEY = 'SuperPmAgent_setup_draft'
export const DONE_KEY = 'SuperPmAgent_setup_done'

// 模块级内存缓存
let _teamCache: {
  team_name: string
  description: string
  members: { login: string; avatar_url: string }[]
  languages: Record<string, number>
} | null = null

type Answers = Record<string, string | string[]>
type Phase = 'overview' | 'interview' | 'done' | 'profile'

// ── Types ───────────────────────────────────────────────────────

interface TeamProfile {
  team_name: string
  description: string
  members: { login: string; avatar_url: string }[]
  languages: Record<string, number>
}

// ── Helpers (module-level so login pages can also use) ──────────

export function hasProfileInStorage(): boolean {
  return localStorage.getItem(DONE_KEY) === '1'
}

/** 返回本地保存的 answers，没有则返回 null */
export function loadLocalAnswers(): Answers | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (raw) return JSON.parse(raw) as Answers
  } catch { /* ignore */ }
  return null
}

export function saveLocalAnswers(answers: Answers) {
  if (Object.keys(answers).length > 0) {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(answers))
  }
}

// ── Main component ──────────────────────────────────────────────

export default function ProfilePage() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('overview')
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Answers>({})
  const [teamProfile, setTeamProfile] = useState<TeamProfile | null>(null)
  const [autoLang, setAutoLang] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [profileCompleted] = useState(hasProfileInStorage())
  const initialLoadDone = useRef(false)

  // Load cached draft from localStorage
  useEffect(() => {
    const local = loadLocalAnswers()
    if (local) setAnswers(local)
  }, [])

  // Fetch team profile（仅团队信息，不含个人画像状态）
  useEffect(() => {
    async function load() {
      try {
        if (_teamCache) {
          setTeamProfile(_teamCache)
          setAutoLang(_teamCache.languages || {})
          setLoading(false)
          return
        }
        const teamRes = await api.get<TeamProfile>('/setup/team-profile')
        _teamCache = teamRes
        setTeamProfile(teamRes)
        setAutoLang(teamRes.languages || {})
      } catch {
        // API may fail — page still works without team info
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Pre-select auto-detected languages
  useEffect(() => {
    if (Object.keys(autoLang).length > 0 && !answers.tech_stack) {
      const topLangs = Object.entries(autoLang)
        .sort(([, a], [, b]) => b - a)
        .filter(([, pct]) => pct >= 5)
        .map(([lang]) => lang)
      setAnswers(prev => ({ ...prev, tech_stack: topLangs }))
    }
  }, [autoLang])

  // Save draft to localStorage（跳过首次从 localStorage 还原的触发）
  useEffect(() => {
    if (loading) return
    if (!initialLoadDone.current) {
      initialLoadDone.current = true
      return
    }
    saveLocalAnswers(answers)
  }, [answers, loading])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <Text className="text-muted-foreground">加载中...</Text>
      </div>
    )
  }

  // 已有完成画像 → 直接展示 ProfileView
  const hasProfile = profileCompleted && Object.keys(answers).length > 1
  if ((hasProfile && phase === 'overview') || phase === 'profile') {
    return <ProfileView answers={answers} setAnswers={setAnswers} />
  }

  if (phase === 'overview') {
    return (
      <OverviewPhase
        teamProfile={teamProfile}
        autoLang={autoLang}
        onStart={() => setPhase('interview')}
        onSkip={() => navigate('/')}
      />
    )
  }

  if (phase === 'interview') {
    return (
      <InterviewPhase
        idx={idx}
        setIdx={setIdx}
        answers={answers}
        setAnswers={setAnswers}
        autoLang={autoLang}
        onFinish={() => setPhase('done')}
      />
    )
  }

  return (
    <DonePhase
      answers={answers}
      onGoProfile={() => setPhase('profile')}
    />
  )
}

// ── Overview ────────────────────────────────────────────────────

function OverviewPhase({
  teamProfile,
  autoLang,
  onStart,
  onSkip,
}: {
  teamProfile: TeamProfile | null
  autoLang: Record<string, number>
  onStart: () => void
  onSkip: () => void
}) {
  const members = teamProfile?.members ?? []
  const languages = teamProfile?.languages ?? autoLang
  const langEntries = Object.entries(languages).sort(([, a], [, b]) => b - a)
  const langColors: Record<string, string> = {
    Python: '#3572A5', TypeScript: '#3178c6', JavaScript: '#f1e05a',
    Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', Shell: '#89e051',
    'C++': '#f34b7d', Ruby: '#701516', PHP: '#4F5D95', Swift: '#F05138', Kotlin: '#A97BFF',
  }

  return (
    <div className="w-full max-w-[640px] mx-auto px-4 pt-8">
      <Text as="h2" className="mb-1">欢迎</Text>
      <p className="text-sm text-muted-foreground mb-6">
        已登录到团队仓库 — 以下是自动解析的团队信息:
      </p>

      <div className="bg-card border-2 border-border p-6">
        {/* Team header */}
        <div className="bg-primary border-b-2 border-border -mx-6 -mt-6 px-6 py-4 mb-5 flex items-center justify-between">
          <span className="font-head text-lg">{teamProfile?.team_name ?? 'Team'}</span>
          <span className="px-2.5 py-0.5 border-2 border-border bg-card text-xs font-bold">
            {members.length || '?'} 位成员
          </span>
        </div>

        {teamProfile?.description && (
          <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
            {teamProfile.description}
          </p>
        )}

        {members.length > 0 && (
          <>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">成员</p>
            <div className="flex items-center mb-5">
              {members.slice(0, 5).map((m) => (
                <img
                  key={m.login}
                  src={m.avatar_url}
                  alt={m.login}
                  className="w-8 h-8 rounded-full border-2 border-border object-cover -mr-2 relative"
                />
              ))}
              {members.length > 5 && (
                <span className="w-8 h-8 rounded-full border-2 border-border bg-[#8B5CF6]/10 text-[#8B5CF6] text-[10px] font-bold flex items-center justify-center -mr-2">
                  +{members.length - 5}
                </span>
              )}
              <div className="w-2" />
            </div>
          </>
        )}

        {langEntries.length > 0 && (
          <>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">技术栈（自动检测）</p>
            <div className="flex flex-wrap gap-2">
              {langEntries.map(([lang, pct]) => (
                <span key={lang} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-background border border-border text-xs font-semibold">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: langColors[lang] ?? '#888' }} />
                  {lang} <span className="text-muted-foreground font-normal">{pct}%</span>
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="h-0.5 bg-border/30 my-6" />

      <p className="text-sm font-semibold mb-1">你的个人画像还没填</p>
      <p className="text-sm text-muted-foreground mb-4">
        下面 {QUESTIONS.length} 题，约 2 分钟搞定 — AI 会据此为你提供更精准的建议。
      </p>

      <div className="flex gap-3">
        <Button onClick={onStart}>开始访谈 →</Button>
        <Button variant="outline" onClick={onSkip}>跳过</Button>
      </div>
    </div>
  )
}

// ── Interview ───────────────────────────────────────────────────

function InterviewPhase({
  idx, setIdx, answers, setAnswers, autoLang, onFinish,
}: {
  idx: number
  setIdx: (i: number | ((prev: number) => number)) => void
  answers: Answers
  setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
  autoLang: Record<string, number>
  onFinish: () => void
}) {
  const q = QUESTIONS[idx]
  const canNext = hasAnswer(q, answers)
  const isLast = idx === QUESTIONS.length - 1

  return (
    <div className="w-full max-w-[640px] mx-auto px-4 pt-8">
      <Text as="h2" className="mb-6">个人画像访谈</Text>

      <div className="flex items-center gap-0 mb-8">
        {QUESTIONS.map((_, i) => (
          <span key={i} className="contents">
            <div className={`w-8 h-8 border-2 flex items-center justify-center text-sm font-bold shrink-0 ${
              i < idx ? 'bg-foreground text-background border-border'
                : i === idx ? 'bg-primary border-border shadow-[3px_3px_0_0_#000]'
                : 'border-muted text-muted-foreground'
            }`}>
              {i < idx ? '✓' : i + 1}
            </div>
            {i < QUESTIONS.length - 1 && (
              <div className={`h-0.5 flex-1 ${i < idx ? 'bg-foreground' : 'bg-muted'}`} />
            )}
          </span>
        ))}
      </div>

      <div className="bg-card border-2 border-border">
        <div className="p-5 pb-0">
          <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2.5 py-1 border-2 border-border shadow-[2px_2px_0_0_#000]">
            Q{idx + 1}
          </span>
        </div>
        <div className="p-5">
          <div className="font-head text-lg mb-5">{q.prompt}</div>
          {q.type === 'single' ? (
            <SingleSelect q={q} answers={answers} setAnswers={setAnswers} />
          ) : (
            <MultiSelect q={q} answers={answers} setAnswers={setAnswers} autoLang={autoLang} />
          )}
        </div>
      </div>

      <div className="flex justify-between mt-7">
        <Button variant="outline" onClick={() => setIdx(i => Math.max(0, i - 1))} disabled={idx === 0}>
          ← 上一题
        </Button>
        {isLast ? (
          <Button onClick={onFinish} disabled={!canNext}>完成 →</Button>
        ) : (
          <Button onClick={() => setIdx(i => i + 1)} disabled={!canNext}>下一题 →</Button>
        )}
      </div>
    </div>
  )
}

// ── Single select ───────────────────────────────────────────────

function SingleSelect({ q, answers, setAnswers }: {
  q: Question; answers: Answers; setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
}) {
  const selected = answers[q.id] as string | undefined
  return (
    <div className="flex flex-col gap-2">
      {q.options.map((o) => (
        <button
          key={o.value}
          onClick={() => setAnswers(prev => ({ ...prev, [q.id]: o.value }))}
          className={`w-full text-left p-3.5 border-2 flex items-center gap-3 transition-all cursor-pointer ${
            selected === o.value
              ? 'border-border bg-primary shadow-[3px_3px_0_0_#000] font-bold'
              : 'border-muted hover:border-[#8B5CF6] hover:bg-[#8B5CF6]/5'
          }`}
        >
          <div className={`w-4.5 h-4.5 rounded-full border-2 flex items-center justify-center shrink-0 ${
            selected === o.value ? 'border-foreground' : 'border-muted'
          }`}>
            {selected === o.value && <div className="w-2 h-2 rounded-full bg-foreground" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium">{o.label}</div>
            {o.sub && <div className="text-xs text-muted-foreground font-normal">{o.sub}</div>}
          </div>
        </button>
      ))}
    </div>
  )
}

// ── Multi select ────────────────────────────────────────────────

function MultiSelect({ q, answers, setAnswers, autoLang }: {
  q: Question; answers: Answers; setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
  autoLang: Record<string, number>
}) {
  const selected = (answers[q.id] as string[]) || []
  const autoKeys = Object.keys(autoLang)

  const toggle = (val: string) => {
    setAnswers(prev => {
      const cur = (prev[q.id] as string[]) || []
      const next = cur.includes(val) ? cur.filter(v => v !== val) : [...cur, val]
      return { ...prev, [q.id]: next }
    })
  }

  const addCustom = (val: string) => {
    if (!val.trim() || selected.includes(val.trim())) return
    setAnswers(prev => ({
      ...prev,
      [q.id]: [...((prev[q.id] as string[]) || []), val.trim()],
    }))
  }

  return (
    <div className="flex flex-wrap gap-2">
      {q.options.map((o) => {
        const isAuto = autoKeys.includes(o.value)
        const isSel = selected.includes(o.value)
        return (
          <button
            key={o.value}
            onClick={() => toggle(o.value)}
            className={`px-4 py-2 border-2 text-sm font-semibold transition-all cursor-pointer ${
              isSel ? 'bg-primary border-border shadow-[2px_2px_0_0_#000]'
                : 'border-muted hover:border-[#8B5CF6]'
            }`}
          >
            {o.label}
            {isAuto && (
              <span className="ml-1.5 text-[9px] font-bold text-[#8B5CF6] border border-[#8B5CF6] bg-[#8B5CF6]/10 px-1 py-px align-middle">
                auto
              </span>
            )}
          </button>
        )
      })}
      {q.allowCustom && (
        <input
          className="px-3.5 py-2 border-2 border-dashed border-muted bg-muted/5 text-sm font-medium outline-none min-w-[100px] focus:border-[#8B5CF6] focus:bg-[#8B5CF6]/5"
          placeholder="+ 自定义..."
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              addCustom((e.target as HTMLInputElement).value)
              ;(e.target as HTMLInputElement).value = ''
            }
          }}
        />
      )}
    </div>
  )
}

// ── Done ────────────────────────────────────────────────────────

function DonePhase({ answers, onGoProfile }: {
  answers: Answers; onGoProfile: () => void
}) {
  const handleSave = async () => {
    localStorage.setItem(DONE_KEY, '1')
    saveLocalAnswers(answers)
    try {
      await api.post('/setup/finish', { answers })
    } catch { /* backend sync is best-effort */ }
    onGoProfile()
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 py-12">
      <div className="relative mb-2">
        <div className="absolute -top-2.5 -left-7 w-3.5 h-3.5 bg-primary border border-border rotate-[12deg]" />
        <div className="absolute -top-1 -right-9 w-2.5 h-2.5 bg-[#8B5CF6] border border-border -rotate-45" />
        <div className="absolute -bottom-2 -left-10 w-2 h-2 bg-[#8B5CF6] border border-border rotate-45" />
        <div className="absolute -bottom-2.5 -right-5 w-3 h-3 bg-primary border border-border -rotate-12" />
        <Text as="h2">画像完成</Text>
      </div>
      <div className="w-14 h-1 bg-[#8B5CF6] mb-3" />
      <p className="text-sm text-muted-foreground text-center mb-7">
        AI 会据此提供更精准的建议，随时可在 Profile 页编辑。
      </p>

      <div className="grid grid-cols-2 gap-3.5 w-full max-w-[560px] mb-6">
        {SUMMARY_CATEGORIES.map(({ cat, id, color }) => {
          const q = QUESTIONS.find(q => q.id === id)!
          const ans = answers[id]
          const isFullWidth = id === 'tech_stack'

          return (
            <div
              key={id}
              className={`border-2 border-border bg-card overflow-hidden shadow-[4px_4px_0_0_#000] hover:translate-x-[3px] hover:translate-y-[3px] hover:shadow-[1px_1px_0_0_#000] transition-all ${
                isFullWidth ? 'col-span-2' : ''
              }`}
            >
              <div className="h-[5px]" style={{ background: color }} />
              <div className="px-4 pt-3 flex items-center gap-2">
                <div className="w-2 h-2 border-[1.5px] border-border shrink-0" style={{ background: color }} />
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">{cat}</span>
              </div>
              {q.type === 'multi' && Array.isArray(ans) ? (
                <div className="flex flex-wrap gap-1.5 px-4 py-3">
                  {ans.map(v => (
                    <span key={v} className="px-3 py-1 bg-primary border-2 border-border text-xs font-bold shadow-[2px_2px_0_0_#000]">
                      {v}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="px-4 py-3 text-sm font-bold">
                  {q.options.find(o => o.value === ans)?.label ?? (ans as string)}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Button onClick={handleSave}>
        查看我的画像 →
      </Button>
    </div>
  )
}

// ── ProfileView (for /profile full-screen) ──────────────────────

function ProfileView({ answers, setAnswers }: {
  answers: Answers; setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
}) {
  const navigate = useNavigate()

  const resetProfile = () => {
    if (!confirm('确定要重置个人画像吗？将重新走引导流程。')) return
    localStorage.removeItem(DRAFT_KEY)
    localStorage.removeItem(DONE_KEY)
    window.location.reload()
  }

  return (
    <div className="w-full max-w-[640px] mx-auto px-4 pt-8">
      <div className="flex items-center justify-between mb-2">
        <Text as="h2">个人画像</Text>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={resetProfile}>重新填写</Button>
          <Button variant="outline" size="sm" onClick={() => navigate('/')}>进入 Goal →</Button>
        </div>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        AI 根据这些信息为你提供更精准的建议
      </p>
      <ProfileGrid answers={answers} setAnswers={setAnswers} />
    </div>
  )
}

// ── ProfileSummary (exported for inline use in Team/Settings) ───

export function ProfileSummary() {
  const [answers, setAnswers] = useState<Answers>(loadLocalAnswers() || {})

  if (Object.keys(answers).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <UserCircle size={40} className="text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">还没有个人画像</p>
        <Button size="sm" onClick={() => window.location.href = '/profile'}>
          去填写 →
        </Button>
      </div>
    )
  }

  return <ProfileGrid answers={answers} setAnswers={(a) => {
    const next = typeof a === 'function' ? a(answers) : a
    setAnswers(next)
    saveLocalAnswers(next)
  }} />
}

// ── ProfileGrid (shared compact summary + edit) ─────────────────

function ProfileGrid({ answers, setAnswers }: {
  answers: Answers; setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
}) {
  const [editId, setEditId] = useState<string | null>(null)
  const [draft, setDraft] = useState<string | string[]>('')

  const startEdit = (q: Question) => {
    setEditId(q.id)
    setDraft(answers[q.id] ?? (q.type === 'multi' ? [] : ''))
  }

  const saveEdit = (q: Question) => {
    const next = { ...answers, [q.id]: draft }
    setAnswers(next)
    saveLocalAnswers(next)
    api.post('/setup/update-profile', { answers: next }).catch(() => {})
    setEditId(null)
  }

  const resetProfile = () => {
    if (!confirm('确定要重置个人画像吗？将重新走引导流程。')) return
    localStorage.removeItem(DRAFT_KEY)
    localStorage.removeItem(DONE_KEY)
    window.location.reload()
  }

  const editQ = editId ? QUESTIONS.find(q => q.id === editId) : null

  if (editQ) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setEditId(null)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回画像总览
        </button>
        <div className="bg-card border-2 border-border">
          <div className="px-5 pt-5 pb-3">
            <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2 py-0.5 border border-border shadow-[2px_2px_0_0_#000]">
              {editQ.prompt}
            </span>
          </div>
          <div className="px-5 pb-5">
            {editQ.type === 'single' ? (
              <div className="flex flex-col gap-2 mt-3">
                {editQ.options.map(o => (
                  <button
                    key={o.value}
                    onClick={() => setDraft(o.value)}
                    className={`w-full text-left p-3 border-2 text-sm cursor-pointer transition-all ${
                      draft === o.value
                        ? 'border-border bg-primary shadow-[2px_2px_0_0_#000] font-bold'
                        : 'border-muted hover:border-[#8B5CF6]'
                    }`}
                  >
                    <span>{o.label}</span>
                    {o.sub && <span className="block text-xs text-muted-foreground font-normal mt-0.5">{o.sub}</span>}
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2 mt-3">
                {editQ.options.map(o => {
                  const sel = Array.isArray(draft) && draft.includes(o.value)
                  return (
                    <button
                      key={o.value}
                      onClick={() => {
                        const arr = Array.isArray(draft) ? [...draft] : []
                        const next = arr.includes(o.value) ? arr.filter(v => v !== o.value) : [...arr, o.value]
                        setDraft(next)
                      }}
                      className={`px-3 py-1.5 border-2 text-xs font-semibold cursor-pointer ${
                        sel ? 'bg-primary border-border shadow-[1px_1px_0_0_#000]' : 'border-muted hover:border-[#8B5CF6]'
                      }`}
                    >
                      {o.label}
                    </button>
                  )
                })}
                {editQ.allowCustom && (
                  <input
                    className="px-3 py-1.5 border-2 border-dashed border-muted text-xs font-medium outline-none min-w-[80px] focus:border-[#8B5CF6]"
                    placeholder="+ 自定义"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const val = (e.target as HTMLInputElement).value.trim()
                        if (val && Array.isArray(draft) && !draft.includes(val)) {
                          setDraft([...draft, val])
                        }
                        ;(e.target as HTMLInputElement).value = ''
                      }
                    }}
                  />
                )}
              </div>
            )}
            <div className="flex gap-2 justify-end mt-4 pt-3 border-t border-border/30">
              <Button variant="outline" size="sm" onClick={() => setEditId(null)}>取消</Button>
              <Button size="sm" onClick={() => saveEdit(editQ)}>保存</Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {SUMMARY_CATEGORIES.map(({ cat, id, color }) => {
          const q = QUESTIONS.find(q => q.id === id)!
          const ans = answers[id]
          const isFullWidth = id === 'tech_stack'

          return (
            <button
              key={id}
              onClick={() => startEdit(q)}
              className={`text-left border-2 border-border bg-card overflow-hidden transition-all hover:shadow-[3px_3px_0_0_#000] hover:-translate-x-0.5 hover:-translate-y-0.5 cursor-pointer ${isFullWidth ? 'col-span-2' : ''}`}
            >
              <div className="h-[4px]" style={{ background: color }} />
              <div className="px-3 pt-2.5 pb-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{cat}</span>
                </div>
                {q.type === 'multi' && Array.isArray(ans) ? (
                  <div className="flex flex-wrap gap-1">
                    {ans.map(v => (
                      <span key={v} className="px-2 py-0.5 bg-primary/60 border border-border text-[11px] font-semibold">{v}</span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm font-bold">
                    {q.options.find(o => o.value === ans)?.label ?? (ans as string ?? '—')}
                  </p>
                )}
              </div>
            </button>
          )
        })}
      </div>

      <div className="flex justify-end pt-2">
        <Button variant="outline" size="sm" onClick={resetProfile}>
          重新填写
        </Button>
      </div>
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────

function hasAnswer(q: Question, answers: Answers): boolean {
  const v = answers[q.id]
  if (q.type === 'single') return !!v
  return Array.isArray(v) && v.length > 0
}
