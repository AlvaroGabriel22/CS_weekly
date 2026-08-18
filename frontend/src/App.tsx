import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { I18nProvider } from '@/i18n'
import { AppLayout } from '@/components/layout/AppLayout'
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary'

// Páginas carregadas sob demanda (mantém o bundle inicial leve)
const LoginPage = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('@/pages/RegisterPage').then(m => ({ default: m.RegisterPage })))
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPasswordPage').then(m => ({ default: m.ForgotPasswordPage })))
const HomePage = lazy(() => import('@/pages/HomePage').then(m => ({ default: m.HomePage })))
const AgendaPage = lazy(() => import('@/pages/AgendaPage').then(m => ({ default: m.AgendaPage })))
const ReportsPage = lazy(() => import('@/pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const DepartmentsPage = lazy(() => import('@/pages/DepartmentsPage').then(m => ({ default: m.DepartmentsPage })))
const DepartmentOrgPage = lazy(() => import('@/pages/DepartmentOrgPage').then(m => ({ default: m.DepartmentOrgPage })))
const ColleagueWeeklysPage = lazy(() => import('@/pages/ColleagueWeeklysPage').then(m => ({ default: m.ColleagueWeeklysPage })))
const FaqPage = lazy(() => import('@/pages/FaqPage').then(m => ({ default: m.FaqPage })))
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then(m => ({ default: m.ProfilePage })))
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    mutations: { retry: 0 },
  },
})

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
    </div>
  )
}

function ProtectedShell() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <FullScreenSpinner />
  if (!user) return <Navigate to="/login" replace />
  return (
    <AppLayout>
      <ErrorBoundary>
        <Suspense fallback={<FullScreenSpinner />}>
          <Outlet />
        </Suspense>
      </ErrorBoundary>
    </AppLayout>
  )
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <FullScreenSpinner />
  if (user) return <Navigate to="/" replace />
  return <Suspense fallback={<FullScreenSpinner />}>{children}</Suspense>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
            <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
            <Route path="/recuperar-senha" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />

            <Route element={<ProtectedShell />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/agenda" element={<AgendaPage />} />
              <Route path="/relatorios" element={<ReportsPage />} />
              <Route path="/departamentos" element={<DepartmentsPage />} />
              <Route path="/departamentos/:sector" element={<DepartmentOrgPage />} />
              <Route path="/colegas/:userId" element={<ColleagueWeeklysPage />} />
              <Route path="/faq" element={<FaqPage />} />
              <Route path="/perfil" element={<ProfilePage />} />
              <Route path="/configuracoes" element={<SettingsPage />} />
            </Route>

            {/* Rotas antigas → novas */}
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/reports" element={<Navigate to="/relatorios" replace />} />
            <Route path="/profile" element={<Navigate to="/perfil" replace />} />
            <Route path="/settings" element={<Navigate to="/configuracoes" replace />} />
            <Route path="/templates" element={<Navigate to="/relatorios" replace />} />
            <Route path="/timeline" element={<Navigate to="/agenda" replace />} />
            <Route path="/weeks" element={<Navigate to="/agenda" replace />} />
            <Route path="/files" element={<Navigate to="/agenda" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
      </I18nProvider>
    </QueryClientProvider>
  )
}
