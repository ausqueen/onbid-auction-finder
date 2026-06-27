import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Navigation() {
  const location = useLocation()
  const { user, logout } = useAuth()
  
  const isActive = (path: string) => {
    return location.pathname === path ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-300 hover:bg-gray-700/50 hover:text-white'
  }

  return (
    <nav className="bg-slate-900 border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center text-white font-extrabold text-lg tracking-tight mr-8 cursor-pointer hover:text-indigo-400 transition-colors">
                🏛 OnBid & 파산공매
              </div>
              <div className="flex items-center space-x-2">
                <Link to="/" className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${isActive('/')}`}>
                  법원 파산 매각 현황
                </Link>
                <Link to="/onbid" className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${isActive('/onbid')}`}>
                  온비드 공매 추천
                </Link>
                {user?.is_superuser && (
                  <Link to="/admin/users" className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${isActive('/admin/users')}`}>
                    회원 승인 관리
                  </Link>
                )}
              </div>
            </div>

            {/* 사용자 정보 및 로그아웃 버튼 */}
            {user && (
              <div className="flex items-center space-x-4">
                <Link to="/mypage" className={`px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-750 transition-all ${
                  location.pathname === '/mypage'
                    ? 'bg-indigo-600 text-white border-transparent'
                    : 'bg-slate-800 text-gray-300 hover:bg-slate-700 hover:text-white border-slate-700'
                }`}>
                  마이페이지
                </Link>
                <span className="text-gray-300 text-sm font-medium hidden sm:inline-block">
                  <strong className="text-white font-semibold">{user.name}</strong> 님
                </span>
                <button
                  onClick={logout}
                  className="bg-slate-800 hover:bg-red-900/40 text-gray-300 hover:text-red-200 border border-slate-700 hover:border-red-900/50 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all"
                >
                  로그아웃
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

