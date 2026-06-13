import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/retroui/Button'
import { Textarea } from '@/components/retroui/Textarea'
import { Card } from '@/components/retroui/Card'
import { Text } from '@/components/retroui/Text'

const STORAGE_KEY = 'SuperPmAgent_profile'

const QUESTIONS = [
  '你日常负责的工作类型?(产品 / 工程 / 数据 / ...)',
  '你最常用的开发语言 / 框架?',
  '你们团队的代码评审风格?(严格 / 轻量 / 快速合并)',
  '遇到不确定的需求时,你倾向于先问还是先做?',
  '你写代码时是先写测试还是后补测试?',
]

function loadProfile(): string[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!Array.isArray(data) || data.length !== QUESTIONS.length) return null
    if (data.every((v) => typeof v === 'string' && v.trim())) return data
    return null
  } catch {
    return null
  }
}

function saveProfile(answers: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(answers))
}

export default function Setup() {
  const existing = loadProfile()
  if (existing) return <ProfileView initial={existing} />
  return <OnboardingFlow />
}

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        {Array.from({ length: total }).map((_, i) => (
          <span key={i} className="contents">
            <div
              className={`flex items-center justify-center w-8 h-8 border-2 text-sm font-bold ${
                i < current
                  ? 'border-border bg-foreground text-background'
                  : i === current
                    ? 'border-border bg-primary text-foreground shadow-[3px_3px_0_0_var(--border)]'
                    : 'border-muted text-muted-foreground'
              }`}
            >
              {i < current ? '✓' : i + 1}
            </div>
            {i < total - 1 && (
              <div className={`h-0.5 flex-1 ${i < current ? 'bg-foreground' : 'bg-muted'}`} />
            )}
          </span>
        ))}
      </div>
      <p className="text-xs text-muted-foreground text-right">
        问题 {current + 1} / {total}
      </p>
    </div>
  )
}

function OnboardingFlow() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<'overview' | 'interview' | 'done'>('overview')
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<string[]>(Array(QUESTIONS.length).fill(''))

  if (phase === 'overview') {
    return (
      <div className="w-full max-w-2xl mx-auto p-4 sm:p-8">
        <Text as="h2" className="mb-2">欢迎</Text>
        <p className="text-sm text-muted-foreground mb-6">
          已登录到团队仓库。下面是从{' '}
          <code className="px-1.5 py-0.5 text-xs underline decoration-[#8B5CF6] decoration-2 underline-offset-4">
            knowledge/profiles/team.md
          </code>{' '}
          自动解析出的团队画像:
        </p>
        <Card className="block w-full mb-6">
          <Card.Header>
            <Card.Title className="text-base font-bold font-sans">AI Coding 小组</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-sm text-muted-foreground">
              后端为主的 8 人小队,主用 Python + TypeScript。(mock data —
              真实数据W2接通后从 GitHub API 读取)
            </p>
          </Card.Content>
        </Card>
        <p className="text-sm text-muted-foreground mb-4">
          你的个人画像还没填。下面 {QUESTIONS.length} 题,2 分钟搞定:
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button onClick={() => setPhase('interview')}>
            开始访谈 →
          </Button>
          <Button variant="outline" onClick={() => navigate('/goal')}>
            跳过
          </Button>
        </div>
      </div>
    )
  }

  if (phase === 'interview') {
    const q = QUESTIONS[idx]
    const a = answers[idx]
    const canNext = a.trim().length > 0
    const isLast = idx === QUESTIONS.length - 1
    return (
      <div className="w-full max-w-3xl mx-auto p-4 sm:p-8">
        <Text as="h2" className="mb-6">个人画像访谈</Text>
        <StepIndicator current={idx} total={QUESTIONS.length} />
        <Card className="block w-full mb-6">
          <Card.Content className="px-6 py-5">
            <div className="flex items-center gap-3 mb-4">
              <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2.5 py-1 border-2 border-border shadow-[2px_2px_0_0_var(--border)]">
                Q{idx + 1}
              </span>
            </div>
            <div className="font-head text-lg mb-5">{q}</div>
            <Textarea
              rows={4}
              value={a}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                const next = [...answers]
                next[idx] = e.target.value
                setAnswers(next)
              }}
              placeholder="..."
            />
          </Card.Content>
        </Card>
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
            disabled={idx === 0}
          >
            ← 上一题
          </Button>
          {isLast ? (
            <Button
              onClick={() => {
                saveProfile(answers)
                setPhase('done')
              }}
              disabled={!canNext}
            >
              完成 →
            </Button>
          ) : (
            <Button
              onClick={() => setIdx((i) => i + 1)}
              disabled={!canNext}
            >
              下一题 →
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-4 sm:px-8 py-16 flex flex-col items-center justify-center min-h-[70vh]">
      <div className="relative mb-4">
        <div className="absolute -top-3 -left-8 w-4 h-4 bg-primary border border-foreground rotate-12" />
        <div className="absolute -top-1 -right-10 w-3 h-3 bg-[#8B5CF6] border border-foreground -rotate-45" />
        <div className="absolute -bottom-2 -left-12 w-2.5 h-2.5 bg-[#8B5CF6] border border-foreground rotate-45" />
        <div className="absolute -bottom-3 -right-6 w-3.5 h-3.5 bg-primary border border-foreground -rotate-12" />
        <Text as="h2" className="text-center">画像完成</Text>
      </div>
      <div className="w-16 h-1 bg-[#8B5CF6] mb-4" />
      <p className="text-sm text-muted-foreground text-center mb-10 whitespace-nowrap">
        你的个人画像已保存。AI 会据此提供更精准的建议。
      </p>
      <Card className="block w-full max-w-lg mb-8">
        <div className="bg-primary border-b-2 border-foreground px-5 py-3 flex items-center justify-center gap-2">
          <span className="font-head text-sm">你的画像摘要</span>
        </div>
        <Card.Content className="!p-0">
          <div className="px-5 py-4 space-y-0">
            {answers.map((ans, i) => (
              <span key={i} className="contents">
                {i > 0 && <div className="border-t border-gray-100" />}
                <div className={`flex items-center gap-3 py-2.5 ${i % 2 === 1 ? 'bg-gray-50 -mx-5 px-5' : ''}`}>
                  <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2.5 py-1 border-2 border-foreground shadow-[2px_2px_0_0_var(--border)] shrink-0">
                    {i + 1}
                  </span>
                  <p className="text-sm text-muted-foreground">{ans}</p>
                </div>
              </span>
            ))}
          </div>
        </Card.Content>
      </Card>
      <Button onClick={() => navigate('/goal')}>
        进入 Goal →
      </Button>
    </div>
  )
}

function ProfileView({ initial }: { initial: string[] }) {
  const [answers, setAnswers] = useState(initial)
  const [editingIdx, setEditingIdx] = useState<number | null>(null)
  const [draft, setDraft] = useState('')

  const startEdit = (i: number) => {
    setEditingIdx(i)
    setDraft(answers[i])
  }

  const saveEdit = (i: number) => {
    if (!draft.trim()) return
    const next = [...answers]
    next[i] = draft.trim()
    setAnswers(next)
    saveProfile(next)
    setEditingIdx(null)
  }

  return (
    <div className="w-full max-w-2xl mx-auto p-4 sm:p-8">
      <Text as="h2" className="mb-2">个人画像</Text>
      <p className="text-sm text-muted-foreground mb-8">AI 根据这些信息为你提供更精准的建议</p>
      <div className="space-y-5">
        {QUESTIONS.map((q, i) => (
          <Card key={i} className="block w-full">
            <div className="px-5 pt-5 pb-3">
              <div className="flex items-center gap-3 mb-1">
                <span className="inline-flex items-center justify-center bg-primary text-foreground text-xs font-bold px-2 py-0.5 border border-foreground shadow-[2px_2px_0_0_var(--border)]">
                  Q{i + 1}
                </span>
                <span className="font-head text-sm">{q}</span>
              </div>
            </div>
            {editingIdx === i ? (
              <>
                <div className="w-16 h-0.5 bg-[#8B5CF6] ml-5" />
                <div className="px-5 py-4">
                  <Textarea
                    rows={3}
                    value={draft}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                    autoFocus
                  />
                  <div className="flex gap-2 justify-end mt-3">
                    <Button variant="outline" size="sm" onClick={() => setEditingIdx(null)}>
                      取消
                    </Button>
                    <Button size="sm" onClick={() => saveEdit(i)} disabled={!draft.trim()}>
                      保存
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="border-t border-gray-200 mx-5" />
                <div className="px-5 py-3 bg-gray-50">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-muted-foreground flex-1 min-w-0">{answers[i]}</p>
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
    </div>
  )
}
