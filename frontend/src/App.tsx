import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PropertyDetail from './pages/PropertyDetail'
import TestPage from './pages/TestPage'
import BankruptcyList from './pages/BankruptcyList'
import Navigation from './components/Navigation'
import Login from './pages/Login'
import Register from './pages/Register'
import FindAuth from './pages/FindAuth'
import AdminUserApproval from './pages/AdminUserApproval'
import MyPage from './pages/MyPage'
import PublicHome from './pages/PublicHome'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function PrivateRoute({ children, requireAdmin = false }: { children: React.ReactNode; requireAdmin?: boolean }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !user.is_superuser) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

/**
 * `/`는 공개 랜딩으로 둔다.
 * 이전엔 PrivateRoute라 비로그인 방문자·크롤러가 곧바로 /login으로 튕겼고,
 * 그 탓에 애드센스가 "가치가 별로 없는 콘텐츠"로 반려했다(2026-08-06).
 * 로그인한 사용자는 기존과 똑같이 파산공매 목록으로 보낸다.
 */
function RootRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return user ? <Navigate to="/bankruptcy" replace /> : <PublicHome />
}

function NavigationWrapper() {
  const { user } = useAuth()
  return (
    <>
      {user && <Navigation />}
      <div className="min-h-screen bg-gray-50">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/find-auth" element={<FindAuth />} />

          {/* Protected Routes */}
          <Route path="/" element={<RootRoute />} />
          <Route path="/bankruptcy" element={<PrivateRoute><BankruptcyList /></PrivateRoute>} />
          <Route path="/onbid" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/properties/:id" element={<PrivateRoute><PropertyDetail /></PrivateRoute>} />
          <Route path="/mypage" element={<PrivateRoute><MyPage /></PrivateRoute>} />
          <Route path="/admin/users" element={<PrivateRoute requireAdmin><AdminUserApproval /></PrivateRoute>} />
          <Route path="/test" element={<PrivateRoute><TestPage /></PrivateRoute>} />
        </Routes>
      </div>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <NavigationWrapper />
      </BrowserRouter>
    </AuthProvider>
  )
}

