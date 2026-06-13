import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/retroui/Card'
import { Text } from '@/components/retroui/Text'
import {
  integrationsOptions,
  extensionsOptions,
  usageOptions,
} from '@/lib/queries/config'

export default function Config() {
  const [tab, setTab] = useState<'integrations' | 'extensions' | 'usage'>('integrations')

  return (
    <div className="w-full max-w-5xl mx-auto p-4 sm:p-8">
      <Text as="h2" className="mb-6">系统配置</Text>

      <div className="flex gap-1 mb-6">
        {(['integrations', 'extensions', 'usage'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-2 cursor-pointer transition-colors ${
              tab === t
                ? 'bg-foreground text-background border-foreground'
                : 'border-transparent text-muted-foreground hover:bg-accent'
            }`}
          >
            {{ integrations: '集成', extensions: '扩展', usage: '用量' }[t]}
          </button>
        ))}
      </div>

      <Card className="block w-full">
        <Card.Content className="p-6">
          {tab === 'integrations' && <IntegrationsTab />}
          {tab === 'extensions' && <ExtensionsTab />}
          {tab === 'usage' && <UsageTab />}
        </Card.Content>
      </Card>
    </div>
  )
}

function IntegrationsTab() {
  const { data: items = [], isLoading } = useQuery(integrationsOptions)

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-6">
        服务集成状态。检测后端已配置的 API Key / Token。
      </p>

      <div className="border-2 border-foreground shadow-[4px_4px_0_0_var(--border)] bg-white">
        <table className="w-full">
          <thead>
            <tr className="bg-primary border-b-2 border-foreground">
              <th className="text-left px-5 py-3 text-sm font-head">服务</th>
              <th className="text-left px-5 py-3 text-sm font-head">Endpoint</th>
              <th className="text-center px-5 py-3 text-sm font-head">状态</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={3} className="px-5 py-8 text-center text-sm text-muted-foreground">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent mr-2" />
                  加载中...
                </td>
              </tr>
            ) : (
              items.map((it) => (
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
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ExtensionsTab() {
  const { data: plugins = [], isLoading } = useQuery(extensionsOptions)

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-6">
        已安装的插件（来自 SuperPmAgent-plugins 仓库）。
      </p>

      {isLoading ? (
        <div className="py-8 text-center text-sm text-muted-foreground">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent mr-2" />
          加载中...
        </div>
      ) : plugins.length === 0 ? (
        <div className="border-2 border-foreground shadow-[4px_4px_0_0_var(--border)] bg-white px-5 py-8 text-center">
          <p className="text-sm text-muted-foreground">暂无插件。请配置 plugin_repo_path 指向 SuperPmAgent-plugins 本地克隆。</p>
        </div>
      ) : (
        <div className="space-y-3">
          {plugins.map((p) => (
            <div key={p.path} className="border-2 border-foreground shadow-[2px_2px_0_0_var(--border)] bg-white flex items-center gap-4 px-5 py-4">
              <div className="w-8 h-8 border-2 border-border bg-primary flex items-center justify-center text-xs font-head shadow-[2px_2px_0_0_#000]">
                {p.category.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{p.name}</p>
                <p className="text-xs text-muted-foreground font-mono">{p.path}</p>
              </div>
              <span className="text-xs text-muted-foreground border-2 border-border px-2 py-0.5 font-bold bg-background">
                {p.category}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function UsageTab() {
  const { data, isLoading } = useQuery(usageOptions)

  const stats = [
    { label: 'Token 消耗总量', value: data ? data.total_tokens.toLocaleString() : '—' },
    { label: '执行总次数', value: data ? data.total_executions.toLocaleString() : '—' },
  ]

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-6">
        执行用量统计。
      </p>

      {isLoading ? (
        <div className="py-8 text-center text-sm text-muted-foreground">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent mr-2" />
          加载中...
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
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
      )}
    </div>
  )
}
