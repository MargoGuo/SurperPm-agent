/**
 * API client — all backend calls go through here.
 * Vite dev proxies /api → http://localhost:8000.
 */

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (res.status === 401) {
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new ApiError(401, 'unauthorized')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, text)
  }
  return res.json()
}

export interface User {
  username: string
  repo: string
  avatar_url?: string
}

export interface Repo {
  name: string
  owner: string
  private: boolean
  desc: string
  updated: string
  stars: number
}

export interface GoalRun {
  id: string
  status: 'running' | 'done' | 'failed'
  goal_text: string
  logs: string[]
  started_at: string
  finished_at: string | null
  cost_usd: number
}

export const api = {
  auth: {
    me: () => request<User>('/auth/me'),
    login: (pat: string, repo: string, anthropic_key?: string) =>
      request<{ ok: boolean; username: string; repo: string; profile_missing: boolean }>(
        '/auth/login',
        { method: 'POST', body: JSON.stringify({ pat, repo, anthropic_key }) },
      ),
    logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
    githubAuthorize: () =>
      request<{ url: string }>('/auth/github/authorize'),
    githubRepos: () =>
      request<Repo[]>('/auth/github/repos'),
    githubComplete: (data: { repo: string; anthropic_key?: string }) =>
      request<{ ok: boolean; username: string; repo: string; profile_missing: boolean }>(
        '/auth/github/complete',
        { method: 'POST', body: JSON.stringify(data) },
      ),
  },
  setup: {
    state: () => request<{ completed: boolean; step: number }>('/setup/state'),
    saveStep: (data: unknown) =>
      request('/setup/save-step', { method: 'POST', body: JSON.stringify(data) }),
    finish: () => request<{ ok: boolean; cli: string }>('/setup/finish', { method: 'POST' }),
  },
  knowledge: {
    tree: () => request('/knowledge/tree'),
    file: (path: string) => request(`/knowledge/file?path=${encodeURIComponent(path)}`),
    saveFile: (data: unknown) =>
      request('/knowledge/file', { method: 'PUT', body: JSON.stringify(data) }),
    chat: (data: unknown) =>
      request('/knowledge/session/chat', { method: 'POST', body: JSON.stringify(data) }),
  },
  goal: {
    submit: (data: { goal_text: string }) =>
      request<{ id: string; status: string }>('/goal/submit', { method: 'POST', body: JSON.stringify(data) }),
    list: () => request<GoalRun[]>('/goal/list'),
    get: (id: string) => request<GoalRun>(`/goal/${id}`),
    pause: (id: string) => request(`/goal/${id}/pause`, { method: 'POST' }),
    resume: (id: string) => request(`/goal/${id}/resume`, { method: 'POST' }),
  },
}
