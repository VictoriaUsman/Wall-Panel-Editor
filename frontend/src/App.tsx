import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { DashboardPage } from './pages/customer/DashboardPage'
import { JobPage } from './pages/customer/JobPage'
import { PipelinePage } from './pages/operator/PipelinePage'
import { CatalogPage } from './pages/operator/CatalogPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireOperator({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_operator) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  const { user } = useAuthStore()

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route path="/dashboard" element={
          <RequireAuth><DashboardPage /></RequireAuth>
        } />
        <Route path="/jobs/:jobId" element={
          <RequireAuth><JobPage /></RequireAuth>
        } />

        <Route path="/operator" element={
          <RequireOperator><PipelinePage /></RequireOperator>
        } />
        <Route path="/operator/catalog" element={
          <RequireOperator><CatalogPage /></RequireOperator>
        } />

        <Route path="/" element={
          user ? <Navigate to={user.is_operator ? '/operator' : '/dashboard'} replace />
               : <Navigate to="/login" replace />
        } />
      </Routes>
    </BrowserRouter>
  )
}
