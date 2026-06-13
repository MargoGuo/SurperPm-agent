import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import '@fontsource/archivo-black/400.css'
import '@fontsource-variable/space-grotesk'

import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Config from './pages/Config'
import Goal from './pages/Goal'
import Knowledge from './pages/Knowledge'
import Login from './pages/Login'
import LoginOAuth from './pages/LoginOAuth'
import SetupNew from './pages/SetupNew'

import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginOAuth />} />
          <Route path="/login-pat" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/goal" replace />} />
              <Route path="/setup" element={<SetupNew />} />
              <Route path="/config" element={<Config />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/goal" element={<Goal />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>,
)
