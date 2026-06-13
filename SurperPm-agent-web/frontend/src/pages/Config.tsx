import { useState } from 'react'
import { Button } from '@/components/retroui/Button'
import { Card } from '@/components/retroui/Card'
import { Text } from '@/components/retroui/Text'

const ITEMS = [
  { name: 'GitHub PAT', endpoint: 'https://api.github.com', key: '••••••••', connected: true },
  { name: '模型 endpoint', endpoint: 'https://api.anthropic.com', key: '', connected: false },
  { name: 'LAP', endpoint: '', key: '', connected: false },
]

export default function Config() {
  const [tab, setTab] = useState<'integrations' | 'usage'>('integrations')

  return (
    <div className="w-full max-w-5xl mx-auto p-4 sm:p-8">
      <Text as="h2" className="mb-6">系统配置</Text>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6">
        <button
          onClick={() => setTab('integrations')}
          className={`px-4 py-2 text-sm font-medium border-2 cursor-pointer transition-colors ${
            tab === 'integrations'
              ? 'bg-foreground text-background border-foreground'
              : 'border-transparent text-muted-foreground hover:bg-accent'
          }`}
        >
          集成
        </button>
        <button
          onClick={() => setTab('usage')}
          className={`px-4 py-2 text-sm font-medium border-2 cursor-pointer transition-colors ${
            tab === 'usage'
              ? 'bg-foreground text-background border-foreground'
              : 'border-transparent text-muted-foreground hover:bg-accent'
          }`}
        >
          用量
        </button>
      </div>

      {/* Content wrapper card */}
      <Card className="block w-full">
        <Card.Content className="p-6">
          {tab === 'integrations' ? <IntegrationsTab /> : <UsageTab />}
        </Card.Content>
      </Card>
    </div>
  )
}

function IntegrationsTab() {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-6">
        所有 endpoint + key。条目跟随仓库的{' '}
        <code className="px-1.5 py-0.5 text-xs underline decoration-[#8B5CF6] decoration-2 underline-offset-4">
          .SuperPmAgent.toml
        </code>{' '}
        模板配置。模型 endpoint 不绑定具体厂商。
      </p>

      {/* Table */}
      <div className="border-2 border-foreground shadow-[4px_4px_0_0_var(--border)] bg-white mb-6">
        <table className="w-full">
          <thead>
            <tr className="bg-primary border-b-2 border-foreground">
              <th className="text-left px-5 py-3 text-sm font-head">服务</th>
              <th className="text-left px-5 py-3 text-sm font-head">Endpoint</th>
              <th className="text-left px-5 py-3 text-sm font-head">Key</th>
              <th className="text-center px-5 py-3 text-sm font-head">状态</th>
              <th className="px-5 py-3 text-sm font-head">
                <div className="flex justify-end">操作</div>
              </th>
            </tr>
          </thead>
          <tbody>
            {ITEMS.map((it) => (
              <tr
                key={it.name}
                className={`border-b border-gray-100 hover:bg-primary/30 transition-colors ${
                  !it.connected ? 'bg-gray-50' : ''
                }`}
              >
                <td className="px-5 py-4 font-medium text-sm">{it.name}</td>
                <td className={`px-5 py-4 font-mono text-xs ${it.connected ? 'text-muted-foreground' : 'text-gray-400'}`}>
                  {it.endpoint || <span className="text-gray-400">(未配置)</span>}
                </td>
                <td className={`px-5 py-4 font-mono text-xs ${it.connected ? 'text-muted-foreground' : 'text-gray-400'}`}>
                  {it.key || <span className="text-gray-400">(未配置)</span>}
                </td>
                <td className="px-5 py-4 text-center">
                  {it.connected ? (
                    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span className="text-green-500">●</span> 已连接
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
                      ○ 未配置
                    </span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <div className="flex justify-end">
                    <Button variant="outline" size="sm">编辑</Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Button className="font-head">＋ 新增服务</Button>
    </div>
  )
}

function UsageTab() {
  const stats = [
    { label: '模型 Token (in)', value: '1,240,000' },
    { label: '模型 Token (out)', value: '320,000' },
    { label: '活跃 Goal', value: '3' },
    { label: '蒸馏 PR (待审)', value: '2' },
  ]

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-6">
        本月用量。占位数据，真实数据 W2 接通后展示。
      </p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="border-2 border-foreground shadow-[4px_4px_0_0_var(--border)] bg-white">
            <div className="bg-primary border-b-2 border-foreground px-5 py-2">
              <span className="text-sm font-head">{s.label}</span>
            </div>
            <div className="px-5 py-4">
              <span className="text-2xl font-head tabular-nums">{s.value}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="border-2 border-foreground shadow-[4px_4px_0_0_var(--border)] bg-white">
        <div className="bg-primary border-b-2 border-foreground px-5 py-2">
          <span className="text-sm font-head">本月趋势</span>
        </div>
        <div className="px-5 py-10 text-center">
          <p className="text-sm text-muted-foreground">图表区域 — W2 接通后展示</p>
        </div>
      </div>
    </div>
  )
}
