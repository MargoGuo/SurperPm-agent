import { useState, useRef, useCallback, useEffect, useMemo, createContext, useContext } from 'react'
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadMessageLike,
  SimpleTextAttachmentAdapter,
  MessagePrimitive,
  BranchPickerPrimitive,
  useMessage,
  useMessageRuntime,
  useEditComposer,
} from '@assistant-ui/react'
import { Thread, type ThreadConfig, makeMarkdownText } from '@assistant-ui/react-ui'
import { Copy, RefreshCw, Pencil, ChevronLeft, ChevronRight } from 'lucide-react'

const MarkdownText = makeMarkdownText()

const EditingContext = createContext<(active: boolean) => void>(() => {})

type Node = { name: string; path: string; isDir: boolean; children?: Node[] }

const tree: Node[] = [
  {
    name: 'profiles', path: 'knowledge/profiles', isDir: true,
    children: [{ name: 'team.md', path: 'knowledge/profiles/team.md', isDir: false }],
  },
  {
    name: 'sessions', path: 'knowledge/sessions', isDir: true,
    children: [
      {
        name: 'add-phone-field', path: 'knowledge/sessions/add-phone-field', isDir: true,
        children: [
          { name: 'conversation.md', path: 'knowledge/sessions/add-phone-field/conversation.md', isDir: false },
          { name: 'notes.md', path: 'knowledge/sessions/add-phone-field/notes.md', isDir: false },
          { name: 'decisions.md', path: 'knowledge/sessions/add-phone-field/decisions.md', isDir: false },
        ],
      },
      {
        name: 'refactor-checkout', path: 'knowledge/sessions/refactor-checkout', isDir: true,
        children: [],
      },
    ],
  },
  {
    name: 'domain', path: 'knowledge/domain', isDir: true,
    children: [
      { name: 'foundations', path: 'knowledge/domain/foundations', isDir: true },
      { name: 'conventions', path: 'knowledge/domain/conventions', isDir: true },
      { name: 'context', path: 'knowledge/domain/context', isDir: true },
    ],
  },
  {
    name: 'extensions', path: 'knowledge/extensions', isDir: true,
    children: [],
  },
]

const INITIAL_MESSAGES: ThreadMessageLike[] = [
  {
    role: 'user',
    content: '给 `user` 表加 `phone` 字段',
    id: 'msg-1',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'assistant',
    content: '涉及 `user` / `user_audit` / `mobile_verifications` 三张表？需要做 E.164 格式校验，前端表单需要同步更新 phone input 组件。\n\n另外 migrations 需要同时更新 user 和 user_audit 两张表。',
    id: 'msg-2',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'user',
    content: '前两张，E.164 校验要做。前端先用基础 input，后续再优化。',
    id: 'msg-3',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'assistant',
    content: [
      '明白，已开始执行。',
      '',
      '### 执行计划',
      '',
      '1. 创建 migration 文件：`user` + `user_audit` 加 `phone` 列',
      '2. API 层：`POST /api/users/:id/phone` — E.164 校验',
      '3. 前端：基础 phone input 组件',
      '4. 测试：unit + integration',
      '',
      '> 预计 **35** 次迭代。先跑一轮看看结果。',
    ].join('\n'),
    id: 'msg-4',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'user',
    content: '好的，另外确认一下：`phone` 字段是否需要加索引？',
    id: 'msg-5',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'assistant',
    content: [
      '如果后续要做手机号登录或短信验证，建议加**唯一索引**。',
      '',
      '目前需求只是联系方式的话，普通索引就够了。',
      '',
      '```sql',
      '-- 推荐方案：普通索引',
      'CREATE INDEX idx_users_phone ON users(phone);',
      '',
      '-- 后续如需手机号登录，改为唯一索引',
      '-- CREATE UNIQUE INDEX idx_users_phone ON users(phone);',
      '```',
      '',
      '我建议先加普通索引，后续如果要做登录再改成唯一索引——这样改动最小。',
      '',
      '你觉得呢？',
    ].join('\n'),
    id: 'msg-6',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'user',
    content: '普通索引就行。继续执行吧。',
    id: 'msg-7',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
  {
    role: 'assistant',
    content: [
      '### 任务摘要',
      '',
      '| 步骤 | 内容 | 状态 |',
      '|------|------|------|',
      '| 1 | Migration 文件 | done |',
      '| 2 | API 层 | done |',
      '| 3 | 前端 PhoneInput | done |',
      '| 4 | 单元测试 | done |',
      '| 5 | 集成测试 | done |',
      '| 6 | 索引 `idx_users_phone` | done |',
      '| 7 | 文档更新 | done |',
      '',
      '全部 **7** 个步骤已完成，没有遇到阻塞。',
    ].join('\n'),
    id: 'msg-8',
    createdAt: new Date('2026-06-13T12:00:00'),
  },
]

const mockAdapter: ChatModelAdapter = {
  async *run({ messages }) {
    const lastMsg = messages[messages.length - 1]
    const text = typeof lastMsg?.content === 'string'
      ? lastMsg.content
      : Array.isArray(lastMsg?.content)
        ? lastMsg.content.map((p: any) => p.text ?? '').join(' ')
        : ''
    yield {
      content: [{ type: 'text', text: `收到: "${text.slice(0, 30)}${text.length > 30 ? '...' : ''}" — 这是一个模拟回复。` }],
    }
  },
}

function FolderIcon() {
  return (
    <svg className="shrink-0" width="14" height="14" viewBox="0 0 16 16">
      <path
        d="M1.5 4.5V3a1 1 0 011-1h3.5l1.5 1.5h6a1 1 0 011 1v8a1 1 0 01-1 1h-11a1 1 0 01-1-1V4.5z"
        fill="#ffdb33" stroke="#000" strokeWidth="1.3"
      />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="shrink-0" width="12" height="14" viewBox="0 0 14 16">
      <path
        d="M2 1.5A1 1 0 013 .5h5.5l3.5 3.5v10.5a1 1 0 01-1 1H3a1 1 0 01-1-1V1.5z"
        fill="#fff" stroke="#888" strokeWidth="1.1"
      />
      <path d="M8.5.5v4h4" fill="none" stroke="#888" strokeWidth="1.1" />
    </svg>
  )
}

export default function Knowledge() {
  const [selected, setSelected] = useState('knowledge/sessions/add-phone-field')
  const [expanded, setExpanded] = useState<Set<string>>(
    new Set(['knowledge/profiles', 'knowledge/sessions', 'knowledge/sessions/add-phone-field', 'knowledge/domain']),
  )
  const [activeTab, setActiveTab] = useState('conversation.md')

  useEffect(() => {
    const el = document.documentElement
    const prev = el.style.overflow
    el.style.overflow = 'hidden'
    return () => { el.style.overflow = prev }
  }, [])

  const containerRef = useRef<HTMLDivElement>(null)
  const leftRef = useRef<HTMLDivElement>(null)
  const centerRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)

  const toggleExpand = useCallback((path: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }, [])

  const useDivider = useCallback(
    (leftRef: React.RefObject<HTMLDivElement | null>, rightRef: React.RefObject<HTMLDivElement | null>) => {
      const dragging = useRef(false)
      const startX = useRef(0)
      const startLeftW = useRef(0)
      const startRightW = useRef(0)

      const onDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault()
        dragging.current = true
        startX.current = e.clientX
        startLeftW.current = leftRef.current?.offsetWidth ?? 0
        startRightW.current = rightRef.current?.offsetWidth ?? 0
        document.body.style.userSelect = 'none'
      }, [leftRef, rightRef])

      useEffect(() => {
        const onMove = (ev: MouseEvent) => {
          if (!dragging.current) return
          const dx = ev.clientX - startX.current
          const minW = 220
          const left = leftRef.current
          const right = rightRef.current
          if (!left || !right) return
          if (startLeftW.current + dx >= minW && startRightW.current - dx >= minW) {
            left.style.width = (startLeftW.current + dx) + 'px'
            right.style.width = (startRightW.current - dx) + 'px'
            right.style.flex = 'none'
          }
        }
        const onUp = () => {
          dragging.current = false
          document.body.style.userSelect = ''
        }
        document.addEventListener('mousemove', onMove)
        document.addEventListener('mouseup', onUp)
        return () => {
          document.removeEventListener('mousemove', onMove)
          document.removeEventListener('mouseup', onUp)
        }
      }, [leftRef, rightRef])

      return onDown
    },
    [],
  )

  const divider1 = useDivider(leftRef, centerRef)
  const divider2 = useDivider(centerRef, rightRef)

  const isSession = selected.startsWith('knowledge/sessions/') && selected.split('/').length >= 3

  return (
    <div ref={containerRef} className="hidden md:flex flex-1 min-h-0">
      {/* ===== Left: File Tree ===== */}
      <aside ref={leftRef} className="panel overflow-hidden min-w-0 flex flex-col bg-white" style={{ width: '25%' }}>
        <div className="bg-primary border-b-2 border-foreground px-5 py-3 flex items-center justify-between shrink-0 gap-2 h-[44px]">
          <span className="text-sm font-head truncate-path">knowledge/</span>
          <button className="text-xs font-bold px-3 py-1 bg-white border-2 border-foreground shadow-[2px_2px_0_0_var(--border)] hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px] transition-all cursor-pointer shrink-0">
            + 新建
          </button>
        </div>
        <div className="border-b border-gray-200 h-[40px] flex items-center px-5 shrink-0">
          <span className="text-xs text-muted-foreground">文件浏览</span>
        </div>
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-2 nb-scrollbar">
          <Tree
            nodes={tree}
            selected={selected}
            onSelect={setSelected}
            expanded={expanded}
            onToggle={toggleExpand}
            depth={0}
          />
        </div>
      </aside>

      {/* Divider 1 */}
      <div
        className="w-[2px] cursor-col-resize bg-gray-200 shrink-0 z-5 transition-colors hover:bg-[#8B5CF6]"
        onMouseDown={divider1}
      />

      {/* ===== Middle: Editor / Session Tabs ===== */}
      <main ref={centerRef} className="panel overflow-hidden min-w-0 flex flex-col" style={{ width: isSession ? '42%' : undefined, flex: isSession ? undefined : 1 }}>
        <div className="bg-primary border-b-2 border-foreground px-5 py-3 flex items-center gap-3 shrink-0 h-[44px]">
          {isSession ? (
            <>
              <span className="inline-flex items-center bg-foreground text-background text-xs font-bold px-2 py-0.5 shrink-0">session</span>
              <span className="text-xs text-foreground/60 font-mono truncate-path">{selected}</span>
            </>
          ) : (
            <span className="text-xs text-foreground/60 font-mono truncate-path">{selected}</span>
          )}
        </div>
        {isSession ? (
          <>
            <div className="border-b border-gray-200 bg-white flex shrink-0 overflow-hidden h-[40px]">
              {['conversation.md', 'notes.md', 'decisions.md'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`tab-shrink px-5 text-sm cursor-pointer ${
                    activeTab === tab
                      ? 'font-bold bg-foreground text-background'
                      : 'font-medium text-gray-400 hover:text-gray-600'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-auto overflow-x-hidden nb-scrollbar">
              {activeTab === 'conversation.md' && <ConversationContent />}
              {activeTab === 'notes.md' && <MarkdownContent content="(notes.md 内容)" />}
              {activeTab === 'decisions.md' && <MarkdownContent content="(decisions.md 内容)" />}
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-auto overflow-x-hidden p-5 nb-scrollbar">
            <pre className="font-mono text-sm whitespace-pre-wrap text-muted-foreground">
              {`(文件内容预览区域)\n\n选择 sessions/<name>/ 会进入对话视图`}
            </pre>
          </div>
        )}
      </main>

      {/* Divider 2 */}
      <div
        className="w-[2px] cursor-col-resize bg-gray-200 shrink-0 z-5 transition-colors hover:bg-[#8B5CF6]"
        onMouseDown={divider2}
      />

      {/* ===== Right: Chat Panel ===== */}
      <aside ref={rightRef} className="panel overflow-hidden min-w-0 flex flex-col bg-white" style={{ flex: 1 }}>
        <div className="bg-primary border-b-2 border-foreground px-5 py-3 shrink-0 h-[44px] flex items-center">
          <span className="font-head text-sm">会话 Chat</span>
        </div>

        <ChatPanel />
      </aside>
    </div>
  )
}

function Tree({
  nodes,
  selected,
  onSelect,
  expanded,
  onToggle,
  depth,
}: {
  nodes: Node[]
  selected: string
  onSelect: (path: string) => void
  expanded: Set<string>
  onToggle: (path: string) => void
  depth: number
}) {
  return (
    <ul>
      {nodes.map(n => {
        const isOpen = expanded.has(n.path)
        const isSelected = selected === n.path
        const isEmpty = n.isDir && (!n.children || n.children.length === 0)
        const paddingLeft = `${depth * 24 + 16}px`

        return (
          <li key={n.path}>
            {n.isDir ? (
              <>
                <button
                  onClick={() => { onToggle(n.path); onSelect(n.path) }}
                  className={`w-full text-left text-xs px-4 py-1.5 cursor-pointer hover:bg-primary/20 flex items-center gap-1.5 ${isEmpty ? 'opacity-50' : ''}`}
                  style={{ paddingLeft }}
                >
                  <span className="inline-block text-[10px] text-gray-400 transition-transform w-3 text-center shrink-0">
                    {isOpen ? '▾' : '▸'}
                  </span>
                  <FolderIcon />
                  {isSelected ? (
                    <span className="font-bold truncate-path bg-primary px-1.5 py-0.5 border border-foreground">
                      {n.name}
                    </span>
                  ) : (
                    <span className="text-gray-700 font-medium truncate-path">{n.name}</span>
                  )}
                </button>
                {isOpen && n.children && n.children.length > 0 && (
                  <Tree
                    nodes={n.children}
                    selected={selected}
                    onSelect={onSelect}
                    expanded={expanded}
                    onToggle={onToggle}
                    depth={depth + 1}
                  />
                )}
              </>
            ) : (
              <button
                onClick={() => onSelect(n.path)}
                className={`w-full text-left text-xs px-4 py-1.5 cursor-pointer hover:bg-primary/20 flex items-center gap-1.5 ${
                  isSelected ? 'bg-primary/30' : ''
                }`}
                style={{ paddingLeft }}
              >
                <FileIcon />
                <span className="text-gray-500 truncate-path">{n.name}</span>
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="p-5">
      <pre className="font-mono text-sm whitespace-pre-wrap text-muted-foreground">{content}</pre>
    </div>
  )
}

function ConversationContent() {
  const turns = [
    {
      who: 'PM', time: '14:02',
      text: '给 user 表加 phone 字段，含迁移、API、前端表单，全部测试通过',
    },
    {
      who: 'AI', time: '14:02', text: '涉及哪几张表？需要校验格式吗（E.164）？',
      files: ['models/user.py', 'migrations/', 'api/users.py', 'frontend/UserForm.tsx'],
    },
    {
      who: 'PM', time: '14:03',
      text: '只涉及 user 和 user_audit 表，E.164 格式校验',
    },
    {
      who: 'AI', time: '14:03', text: '明白。方案如下：',
      steps: [
        '新增 migration: user + user_audit 加 phone 列',
        'API: POST /users/:id/phone — E.164 校验',
        '前端: phone input + 即时格式提示',
        '测试: unit + integration',
      ],
      tail: '开始执行？',
    },
  ]

  return (
    <>
      {turns.map((turn, i) => (
        <div key={i} className={`px-5 py-5 border-b border-gray-100 ${turn.who === 'AI' ? 'bg-gray-50/50' : ''}`}>
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`inline-flex items-center justify-center text-white text-xs font-bold px-2 py-0.5 shrink-0 ${
                turn.who === 'PM' ? 'bg-[#8B5CF6]' : 'bg-foreground'
              }`}
            >
              {turn.who}
            </span>
            <span className="text-xs text-gray-400 shrink-0">{turn.time}</span>
          </div>
          <p className="text-sm leading-relaxed" style={{ wordBreak: 'break-word' }}>{turn.text}</p>
          {turn.files && (
            <div className="mt-3 bg-white border-2 border-foreground shadow-[2px_2px_0_0_var(--border)] p-3 text-xs font-mono text-gray-600 space-y-1 overflow-hidden min-w-0">
              <div className="text-gray-400 font-bold text-xs mb-1">涉及的文件范围：</div>
              {turn.files.map(f => <div key={f}>- {f}</div>)}
            </div>
          )}
          {turn.steps && (
            <div className="mt-3 bg-white border-2 border-foreground shadow-[2px_2px_0_0_var(--border)] p-4 text-sm space-y-2 overflow-hidden min-w-0">
              {turn.steps.map((s, si) => (
                <div key={si} className="flex items-start gap-3">
                  <span className="bg-primary text-foreground text-xs font-bold px-1.5 py-0.5 border border-foreground shrink-0">
                    {si + 1}
                  </span>
                  <span style={{ wordBreak: 'break-word' }}>{s}</span>
                </div>
              ))}
            </div>
          )}
          {turn.tail && (
            <p className="text-sm mt-3 text-muted-foreground" style={{ wordBreak: 'break-word' }}>{turn.tail}</p>
          )}
        </div>
      ))}
    </>
  )
}

function NeoBranchPicker() {
  return (
    <BranchPickerPrimitive.Root hideWhenSingleBranch className="aui-neo-branch-picker">
      <BranchPickerPrimitive.Previous asChild>
        <button className="aui-neo-branch-btn"><ChevronLeft /></button>
      </BranchPickerPrimitive.Previous>
      <span className="aui-neo-branch-state">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <button className="aui-neo-branch-btn"><ChevronRight /></button>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  )
}

function NeoUserMessage() {
  return (
    <MessagePrimitive.Root className="aui-user-message-root">
      <MessagePrimitive.If hasContent>
        <div className="aui-user-message-inner">
          <UserBubble />
          <UserActionRow />
        </div>
      </MessagePrimitive.If>
      <NeoBranchPicker />
    </MessagePrimitive.Root>
  )
}

function UserBubble() {
  const msg = useMessage()
  const messageRuntime = useMessageRuntime()
  const editComposer = useEditComposer()
  const isEditing = editComposer.isEditing
  const onEditing = useContext(EditingContext)

  useEffect(() => {
    onEditing(isEditing)
  }, [isEditing, onEditing])

  const time = useMemo(() => {
    const d = msg.createdAt
    if (!d) return ''
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }, [msg.createdAt])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      messageRuntime.composer.send()
    }
    if (e.key === 'Escape') {
      messageRuntime.composer.cancel()
    }
  }, [messageRuntime.composer])

  if (isEditing) {
    return (
      <div className="aui-user-bubble aui-edit-bubble">
        <textarea
          className="aui-edit-textarea"
          value={editComposer.text}
          onChange={(e) => messageRuntime.composer.setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          autoFocus
        />
        <div className="aui-edit-actions">
          <span className="aui-edit-hint">Ctrl+Enter 发送 · Esc 取消</span>
          <div className="aui-edit-btns">
            <button
              className="aui-edit-cancel-btn"
              onClick={() => messageRuntime.composer.cancel()}
            >
              取消
            </button>
            <button
              className="aui-edit-send-btn"
              onClick={() => messageRuntime.composer.send()}
              disabled={!editComposer.canSend}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="aui-user-bubble">
      <MessagePrimitive.Content components={{ Text: MarkdownText }} />
      <div className="aui-bubble-footer">
        <span className="aui-bubble-sender user">PM</span>
        <span className="aui-bubble-dot">·</span>
        <span className="aui-bubble-time">{time}</span>
      </div>
    </div>
  )
}

function UserActionRow() {
  const messageRuntime = useMessageRuntime()
  return (
    <div className="aui-action-row">
      <div className="aui-action-bar">
        <button
          className="aui-action-btn"
          title="编辑"
          onClick={() => messageRuntime.composer.beginEdit()}
        >
          <Pencil size={14} />
        </button>
      </div>
    </div>
  )
}

function NeoAssistantMessage() {
  return (
    <MessagePrimitive.Root className="aui-assistant-message-root">
      <div className="aui-assistant-avatar">AI</div>
      <MessagePrimitive.If hasContent>
        <div className="aui-assistant-message-inner">
          <AssistantBubble />
          <AssistantActionRow />
          <NeoBranchPicker />
        </div>
      </MessagePrimitive.If>
    </MessagePrimitive.Root>
  )
}

function AssistantBubble() {
  const msg = useMessage()
  const time = useMemo(() => {
    const d = msg.createdAt
    if (!d) return ''
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }, [msg.createdAt])

  return (
    <div className="aui-assistant-bubble">
      <MessagePrimitive.Content components={{ Text: MarkdownText }} />
      <div className="aui-bubble-footer">
        <span className="aui-bubble-sender assistant">AI</span>
        <span className="aui-bubble-dot">·</span>
        <span className="aui-bubble-time">{time}</span>
      </div>
    </div>
  )
}

function AssistantActionRow() {
  const messageRuntime = useMessageRuntime()
  return (
    <div className="aui-action-row">
      <div className="aui-action-bar">
        <button
          className="aui-action-btn"
          title="复制"
          onClick={() => { void navigator.clipboard.writeText(String(messageRuntime.getState().content.map((p: any) => p.text ?? '').join(''))) }}
        >
          <Copy size={14} />
        </button>
        <button
          className="aui-action-btn"
          title="刷新"
          onClick={() => messageRuntime.reload()}
        >
          <RefreshCw size={14} />
        </button>
      </div>
    </div>
  )
}

function ChatPanel() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [editingCount, setEditingCount] = useState(0)
  const isEditing = editingCount > 0
  const onEditing = useCallback((active: boolean) => {
    setEditingCount(c => c + (active ? 1 : -1))
  }, [])

  const runtime = useLocalRuntime(mockAdapter, {
    initialMessages: INITIAL_MESSAGES,
    adapters: {
      attachments: new SimpleTextAttachmentAdapter(),
    },
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const moveFooter = () => {
      const viewport = container.querySelector('.aui-thread-viewport')
      const footer = viewport?.querySelector('.aui-thread-viewport-footer')
      const root = container.querySelector('.aui-thread-root')
      if (footer && root && footer.parentElement === viewport) {
        root.appendChild(footer)
      }
    }
    moveFooter()
    const mo = new MutationObserver(moveFooter)
    mo.observe(container, { childList: true, subtree: true })
    return () => mo.disconnect()
  }, [])

  const config = useMemo(() => ({
    welcome: {
      message: '与 AI Agent 协作',
      suggestions: [
        { prompt: '查看最近的执行进度' },
        { prompt: '分析当前 session 的问题' },
        { prompt: '总结本次对话的关键决策' },
        { prompt: '建议下一步要做什么' },
      ],
    },
    composer: { allowAttachments: true },
    components: {
      UserMessage: NeoUserMessage,
      AssistantMessage: NeoAssistantMessage,
    },
    strings: {
      composer: {
        input: { placeholder: '输入消息，Ctrl+Enter 发送...' },
        send: { tooltip: '发送' },
        addAttachment: { tooltip: '添加文件' },
        removeAttachment: { tooltip: '移除文件' },
      },
      welcome: {
        message: '与 AI Agent 协作',
      },
      editComposer: {
        send: { label: '发送' },
        cancel: { label: '取消' },
      },
    },
  } as ThreadConfig), [])

  return (
    <div ref={containerRef} className={`flex-1 min-h-0 min-w-0 flex flex-col ${isEditing ? 'hide-composer-footer' : ''}`}>
      <EditingContext.Provider value={onEditing}>
        <AssistantRuntimeProvider runtime={runtime}>
          <Thread {...config} />
        </AssistantRuntimeProvider>
      </EditingContext.Provider>
    </div>
  )
}
