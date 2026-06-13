import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/retroui/Button'
import { Card } from '@/components/retroui/Card'
import { Text } from '@/components/retroui/Text'
import { QUESTIONS, SUMMARY_CATEGORIES, type Question } from './setup/questions'

const CACHE_KEY = 'SuperPmAgent_setup_draft'

// 模块级内存缓存：profile 数据加载一次后不再重复请求
let _stateCache: { completed: boolean; auto_detected_languages: Record<string, number>; answers: Record<string, unknown> | null } | null = null
let _teamCache: {
  team_name: string
  description: string
  members: { login: string; avatar_url: string }[]
  languages: Record<string, number>
} | null = null

type Answers = Record<string, string | string[]>
type Phase = 'overview' | 'interview' | 'done' | 'profile'

// ── Main component ────────────────────────────────────────────

export default function SetupNew() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('overview')
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Answers>({})
  const [teamProfile, setTeamProfile] = useState<{
    team_name: string
    description: string
    members: { login: string; avatar_url: string }[]
    languages: Record<string, number>
  } | null>(null)
  const [autoLang, setAutoLang] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [profileCompleted, setProfileCompleted] = useState(false)

  // Load cached draft from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (raw) setAnswers(JSON.parse(raw))
    } catch { /* ignore */ }
  }, [])

  // Fetch setup state + team profile（首次加载走 API，之后走内存缓存）
  useEffect(() => {
    async function load() {
      try {
        if (_stateCache && _teamCache) {
          // 已有缓存，直接使用，无需等待
          setAutoLang(_stateCache.auto_detected_languages || {})
          setProfileCompleted(_stateCache.completed)
          setTeamProfile(_teamCache)
          if (_stateCache.answers) {
            setAnswers(_stateCache.answers as Answers)
          }
          setLoading(false)
          return
        }
        const [stateRes, teamRes] = await Promise.all([
          api.get<{ completed: boolean; auto_detected_languages: Record<string, number>; answers: Record<string, unknown> | null }>('/setup/state'),
          api.get<{ team_name: string; description: string; members: { login: string; avatar_url: string }[]; languages: Record<string, number> }>('/setup/team-profile'),
        ])
        _stateCache = stateRes
        _teamCache = teamRes
        setAutoLang(stateRes.auto_detected_languages || {})
        setProfileCompleted(stateRes.completed)
        setTeamProfile(teamRes)
        // 后端返回已保存的 answers 时，优先使用（比 localStorage 更权威）
        if (stateRes.answers) {
          setAnswers(stateRes.answers as Answers)
        }
      } catch {
        // API may fail (not logged in, etc.) — page still works without it
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

  // Save draft to localStorage on change
  useEffect(() => {
    if (Object.keys(answers).length > 0) {
      localStorage.setItem(CACHE_KEY, JSON.stringify(answers))
    }
  }, [answers])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <Text className="text-muted-foreground">加载中...</Text>
      </div>
    )
  }

  // Only auto-show profile if completed AND has real answers (not just auto-detected languages)
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
        onSkip={() => navigate('/goal')}
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
      autoLang={autoLang}
      onGoProfile={() => {
        setProfileCompleted(true)
        setPhase('profile')
      }}
    />
  )

  // unreachable but helps TS
  return null
}

// ── Overview ──────────────────────────────────────────────────

function OverviewPhase({
  teamProfile,
  autoLang,
  onStart,
  onSkip,
}: {
  teamProfile: {
    team_name: string
    description: string
    members: { login: string; avatar_url: string }[]
    languages: Record<string, number>
  } | null
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

      <div className="bg-card border-2 border-foreground p-6">
        {/* Team header */}
        <div className="bg-primary border-b-2 border-foreground -mx-6 -mt-6 px-6 py-4 mb-5 flex items-center justify-between">
          <span className="font-head text-lg">{teamProfile?.team_name ?? 'Team'}</span>
          <span className="px-2.5 py-0.5 border-2 border-foreground bg-card text-xs font-bold">
            {members.length || '?'} 位成员
          </span>
        </div>

        {/* Description */}
        {teamProfile?.description && (
          <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
            {teamProfile.description}
          </p>
        )}

        {/* Members */}
        {members.length > 0 && (
          <>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">成员</p>
            <div className="flex items-center mb-5">
              {members.slice(0, 5).map((m) => (
                <img
                  key={m.login}
                  src={m.avatar_url}
                  alt={m.login}
                  className="w-8 h-8 rounded-full border-2 border-foreground object-cover -mr-2 relative"
                />
              ))}
              {members.length > 5 && (
                <span className="w-8 h-8 rounded-full border-2 border-foreground bg-purple-50 text-purple-600 text-[10px] font-bold flex items-center justify-center -mr-2">
                  +{members.length - 5}
                </span>
              )}
              <div className="w-2" />
            </div>
          </>
        )}

        {/* Languages */}
        {langEntries.length > 0 && (
          <>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">技术栈（自动检测）</p>
            <div className="flex flex-wrap gap-2">
              {langEntries.map(([lang, pct]) => (
                <span key={lang} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border border-foreground text-xs font-semibold">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: langColors[lang] ?? '#888' }} />
                  {lang} <span className="text-muted-foreground font-normal">{pct}%</span>
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="h-0.5 bg-foreground/10 my-6" />

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

// ── Interview ─────────────────────────────────────────────────

function InterviewPhase({
  idx,
  setIdx,
  answers,
  setAnswers,
  autoLang,
  onFinish,
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

      {/* Step bar */}
      <div className="flex items-center gap-0 mb-8">
        {QUESTIONS.map((_, i) => (
          <span key={i} className="contents">
            <div className={`w-8 h-8 border-2 flex items-center justify-center text-sm font-bold shrink-0 ${
              i < idx ? 'bg-foreground text-background border-foreground'
                : i === idx ? 'bg-primary border-foreground shadow-[3px_3px_0_0_var(--foreground)]'
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

      {/* Question card */}
      <div className="bg-card border-2 border-foreground">
        <div className="p-5 pb-0">
          <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2.5 py-1 border-2 border-foreground shadow-[2px_2px_0_0_var(--border)]">
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

      {/* Nav */}
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

// ── Single select ──────────────────────────────────────────────

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
              ? 'border-foreground bg-primary shadow-[3px_3px_0_0_var(--border)] font-bold'
              : 'border-muted hover:border-purple hover:bg-purple-50'
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

// ── Multi select ──────────────────────────────────────────────

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
              isSel ? 'bg-primary border-foreground shadow-[2px_2px_0_0_var(--border)]'
                : 'border-muted hover:border-purple'
            }`}
          >
            {o.label}
            {isAuto && (
              <span className="ml-1.5 text-[9px] font-bold text-purple border border-purple bg-purple-50 px-1 py-px align-middle">
                auto
              </span>
            )}
          </button>
        )
      })}
      {q.allowCustom && (
        <input
          className="px-3.5 py-2 border-2 border-dashed border-muted bg-muted/5 text-sm font-medium outline-none min-w-[100px] focus:border-purple focus:bg-purple-50"
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

// ── Done ──────────────────────────────────────────────────────

function DonePhase({ answers, autoLang, onGoProfile }: {
  answers: Answers; autoLang: Record<string, number>; onGoProfile: () => void
}) {
  const [saving, setDoneSaving] = useState(false)

  const handleSave = async () => {
    setDoneSaving(true)
    try {
      await api.post('/setup/finish', { answers: answers as Record<string, unknown>, auto_detected_languages: autoLang })
      _stateCache = { completed: true, auto_detected_languages: autoLang, answers: answers as Record<string, unknown> }
    } catch (e) {
      // Still allow viewing profile even if save fails
      console.error('Failed to save profile:', e)
    } finally {
      setDoneSaving(false)
      onGoProfile()
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 py-12">
      {/* Title with deco */}
      <div className="relative mb-2">
        <div className="absolute -top-2.5 -left-7 w-3.5 h-3.5 bg-primary border border-foreground rotate-[12deg]" />
        <div className="absolute -top-1 -right-9 w-2.5 h-2.5 bg-purple border border-foreground -rotate-45" />
        <div className="absolute -bottom-2 -left-10 w-2 h-2 bg-purple border border-foreground rotate-45" />
        <div className="absolute -bottom-2.5 -right-5 w-3 h-3 bg-primary border border-foreground -rotate-12" />
        <Text as="h2">画像完成</Text>
      </div>
      <div className="w-14 h-1 bg-purple mb-3" />
      <p className="text-sm text-muted-foreground text-center mb-7">
        AI 会据此提供更精准的建议，随时可在 Profile 页编辑。
      </p>

      {/* Summary cards grid */}
      <div className="grid grid-cols-2 gap-3.5 w-full max-w-[560px] mb-6">
        {SUMMARY_CATEGORIES.map(({ cat, id, color }) => {
          const q = QUESTIONS.find(q => q.id === id)!
          const ans = answers[id]
          const isFullWidth = id === 'tech_stack'

          return (
            <div
              key={id}
              className={`border-2 border-foreground rounded bg-card overflow-hidden shadow-[4px_4px_0_0_var(--foreground)] hover:translate-x-[3px] hover:translate-y-[3px] hover:shadow-[1px_1px_0_0_var(--foreground)] transition-all ${
                isFullWidth ? 'col-span-2' : ''
              }`}
            >
              <div className="h-[5px]" style={{ background: color }} />
              <div className="px-4 pt-3 flex items-center gap-2">
                <div className="w-2 h-2 border-[1.5px] border-foreground shrink-0" style={{ background: color }} />
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">{cat}</span>
              </div>
              {q.type === 'multi' && Array.isArray(ans) ? (
                <div className="flex flex-wrap gap-1.5 px-4 py-3">
                  {ans.map(v => (
                    <span key={v} className="px-3 py-1 bg-primary border-2 border-foreground text-xs font-bold shadow-[2px_2px_0_0_var(--foreground)]">
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

      <Button onClick={handleSave} disabled={saving}>
        {saving ? '保存中...' : '查看我的画像 →'}
      </Button>
    </div>
  )
}

// ── ProfileView (edit existing) ───────────────────────────────

function ProfileView({ answers, setAnswers }: {
  answers: Answers; setAnswers: (a: Answers | ((prev: Answers) => Answers)) => void
}) {
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [draft, setDraft] = useState<string | string[]>('')
  const [saving, setSaving] = useState(false)

  const startEdit = (i: number) => {
    const q = QUESTIONS[i]
    setEditIdx(i)
    setDraft(answers[q.id] ?? (q.type === 'multi' ? [] : ''))
  }

  const saveEdit = async (i: number) => {
    const q = QUESTIONS[i]
    const next = { ...answers, [q.id]: draft }
    setAnswers(next)
    setEditIdx(null)
    setSaving(true)
    try {
      await api.post('/setup/update-profile', { answers: next as Record<string, unknown> })
    } catch (err) {
      console.error('Failed to update profile:', err)
    } finally {
      setSaving(false)
    }
  }

  const navigate = useNavigate()

  return (
    <div className="w-full max-w-[640px] mx-auto px-4 pt-8">
      <Text as="h2" className="mb-2">个人画像</Text>
      <p className="text-sm text-muted-foreground mb-8">
        AI 根据这些信息为你提供更精准的建议
      </p>
      <div className="space-y-5">
        {QUESTIONS.map((q, i) => (
          <Card key={q.id} className="block w-full">
            <div className="px-5 pt-5 pb-3">
              <div className="flex items-center gap-3 mb-1">
                <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2 py-0.5 border border-foreground shadow-[2px_2px_0_0_var(--border)]">
                  Q{i + 1}
                </span>
                <span className="font-head text-sm">{q.prompt}</span>
              </div>
            </div>
            {editIdx === i ? (
              <>
                <div className="w-16 h-0.5 bg-purple ml-5" />
                <div className="px-5 py-4">
                  {q.type === 'single' ? (
                    <div className="flex flex-col gap-2">
                      {q.options.map(o => (
                        <button
                          key={o.value}
                          onClick={() => setDraft(o.value)}
                          className={`w-full text-left p-3 border-2 text-sm cursor-pointer ${
                            draft === o.value ? 'border-foreground bg-primary font-bold'
                              : 'border-muted hover:border-purple'
                          }`}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {q.options.map(o => {
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
                              sel ? 'bg-primary border-foreground' : 'border-muted hover:border-purple'
                            }`}
                          >
                            {o.label}
                          </button>
                        )
                      })}
                    </div>
                  )}
                  <div className="flex gap-2 justify-end mt-3">
                    <Button variant="outline" size="sm" onClick={() => setEditIdx(null)}>取消</Button>
                    <Button size="sm" onClick={() => saveEdit(i)} disabled={saving}>
                      {saving ? '保存中...' : '保存'}
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="border-t border-gray-200 mx-5" />
                <div className="px-5 py-3 bg-gray-50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="text-sm text-muted-foreground flex-1 min-w-0">
                      {q.type === 'multi' && Array.isArray(answers[q.id])
                        ? (answers[q.id] as string[]).join(', ')
                        : q.options.find(o => o.value === answers[q.id])?.label ?? String(answers[q.id] ?? '')
                      }
                    </div>
                    <Button variant="outline" size="sm" onClick={() => startEdit(i)} className="shrink-0">
                      编辑
                    </Button>
                  </div>
                </div>
              </>
            )}
          </Card>
        ))}
      </div>
      <div className="flex justify-center mt-8 mb-12">
        <Button onClick={() => navigate('/goal')}>进入 Goal →</Button>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────

function hasAnswer(q: Question, answers: Answers): boolean {
  const v = answers[q.id]
  if (q.type === 'single') return !!v
  return Array.isArray(v) && v.length > 0
}
