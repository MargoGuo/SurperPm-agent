import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import '@fontsource/archivo-black/400.css'
import '@fontsource-variable/space-grotesk'

import { AuthProvider } from './context/AuthContext'
import { QueryProvider } from './providers/query-provider'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import { WorkspaceLayout } from './components/layout/workspace-layout'
import Config from './pages/Config'
import Goal from './pages/Goal'
import Knowledge from './pages/Knowledge'
import Login from './pages/Login'
import LoginOAuth from './pages/LoginOAuth'
import SetupNew from './pages/SetupNew'
import GoalsPage from './pages/workspace/Goals'
import DiscussPage from './pages/workspace/Discuss'
import KnowledgePage from './pages/workspace/Knowledge'
import SettingsPage from './pages/workspace/Settings'

import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginOAuth />} />
            <Route path="/login-pat" element={<Login />} />
            <Route element={<ProtectedRoute />}>
              {/* Legacy routes */}
              <Route element={<Layout />}>
                <Route path="/setup" element={<SetupNew />} />
                <Route path="/config" element={<Config />} />
                <Route path="/knowledge" element={<Knowledge />} />
                <Route path="/goal" element={<Goal />} />
              </Route>
              {/* v2 workspace routes */}
              <Route path="/workspace/:slug" element={<WorkspaceLayout />}>
                <Route index element={<Navigate to="goals" replace />} />
                <Route path="goals" element={<GoalsPage />} />
                <Route path="discuss" element={<DiscussPage />} />
                <Route path="knowledge" element={<KnowledgePage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Route>
            <Route path="/" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryProvider>
  </React.StrictMode>,
)
