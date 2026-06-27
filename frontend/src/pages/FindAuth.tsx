import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

const FindAuth: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'id' | 'password'>('id')
  
  // ID 찾기 폼
  const [idName, setIdName] = useState('')
  const [idEmail, setIdEmail] = useState('')
  const [idPhone, setIdPhone] = useState('')
  const [foundId, setFoundId] = useState<string | null>(null)
  
  // 비밀번호 찾기 폼
  const [pwUsername, setPwUsername] = useState('')
  const [pwName, setPwName] = useState('')
  const [pwEmail, setPwEmail] = useState('')
  const [pwPhone, setPwPhone] = useState('')
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleFindId = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setFoundId(null)
    setLoading(true)

    try {
      const res = await fetch('/api/auth/find-id', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: idName, email: idEmail, phone: idPhone })
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || '일치하는 사용자 정보를 찾을 수 없습니다.')
      }

      const data = await res.json()
      setFoundId(data.username)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFindPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setTempPassword(null)
    setLoading(true)

    try {
      const res = await fetch('/api/auth/find-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: pwUsername, name: pwName, email: pwEmail, phone: pwPhone })
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || '일치하는 사용자 정보를 찾을 수 없습니다.')
      }

      const data = await res.json()
      setTempPassword(data.temp_password)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white/10 backdrop-blur-xl p-8 rounded-2xl border border-white/10 shadow-2xl transition-all duration-300 hover:border-white/20">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-white tracking-tight">
            ID / 비밀번호 찾기
          </h2>
          
          {/* 탭 버튼 */}
          <div className="flex mt-6 bg-white/5 p-1 rounded-lg border border-white/10">
            <button
              onClick={() => {
                setActiveTab('id')
                setError('')
                setFoundId(null)
                setTempPassword(null)
              }}
              className={`w-1/2 py-2 text-sm font-semibold rounded-md transition-all ${
                activeTab === 'id'
                  ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              아이디 찾기
            </button>
            <button
              onClick={() => {
                setActiveTab('password')
                setError('')
                setFoundId(null)
                setTempPassword(null)
              }}
              className={`w-1/2 py-2 text-sm font-semibold rounded-md transition-all ${
                activeTab === 'password'
                  ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              비밀번호 찾기
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-200 px-4 py-3 rounded-lg text-sm text-center">
            {error}
          </div>
        )}

        {/* 1. 아이디 찾기 탭 */}
        {activeTab === 'id' && (
          <div>
            {!foundId ? (
              <form className="space-y-4" onSubmit={handleFindId}>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    이름
                  </label>
                  <input
                    type="text"
                    required
                    value={idName}
                    onChange={(e) => setIdName(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="이름 입력"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    이메일 주소
                  </label>
                  <input
                    type="email"
                    required
                    value={idEmail}
                    onChange={(e) => setIdEmail(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="등록된 이메일"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    연락처
                  </label>
                  <input
                    type="text"
                    required
                    value={idPhone}
                    onChange={(e) => setIdPhone(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="등록된 연락처 (010-0000-0000)"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 focus:outline-none shadow-lg disabled:opacity-50 transition-all transform hover:-translate-y-0.5"
                >
                  {loading ? '찾는 중...' : '아이디 찾기'}
                </button>
              </form>
            ) : (
              <div className="space-y-6 text-center">
                <div className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-200 px-6 py-4 rounded-xl">
                  <p className="text-gray-300 text-sm mb-2">입력한 정보와 일치하는 아이디는 다음과 같습니다.</p>
                  <p className="text-2xl font-extrabold text-white tracking-wide">{foundId}</p>
                </div>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full py-2.5 px-4 rounded-lg text-white font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 shadow-lg"
                >
                  로그인하러 가기
                </button>
              </div>
            )}
          </div>
        )}

        {/* 2. 비밀번호 찾기 탭 */}
        {activeTab === 'password' && (
          <div>
            {!tempPassword ? (
              <form className="space-y-4" onSubmit={handleFindPassword}>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    아이디
                  </label>
                  <input
                    type="text"
                    required
                    value={pwUsername}
                    onChange={(e) => setPwUsername(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="아이디 입력"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    이름
                  </label>
                  <input
                    type="text"
                    required
                    value={pwName}
                    onChange={(e) => setPwName(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="이름 입력"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    이메일 주소
                  </label>
                  <input
                    type="email"
                    required
                    value={pwEmail}
                    onChange={(e) => setPwEmail(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="등록된 이메일"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                    연락처
                  </label>
                  <input
                    type="text"
                    required
                    value={pwPhone}
                    onChange={(e) => setPwPhone(e.target.value)}
                    className="appearance-none rounded-lg block w-full px-3 py-2 border border-white/10 placeholder-gray-500 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all"
                    placeholder="등록된 연락처 (010-0000-0000)"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 focus:outline-none shadow-lg disabled:opacity-50 transition-all transform hover:-translate-y-0.5"
                >
                  {loading ? '재발급 중...' : '임시 비밀번호 발급'}
                </button>
              </form>
            ) : (
              <div className="space-y-6 text-center">
                <div className="bg-purple-500/10 border border-purple-500/20 text-purple-200 px-6 py-4 rounded-xl">
                  <p className="text-gray-300 text-sm mb-2">임시 비밀번호가 생성되었습니다.</p>
                  <p className="text-2xl font-mono font-extrabold text-white tracking-widest select-all">{tempPassword}</p>
                  <p className="text-xs text-red-300 mt-3">로그인 후 반드시 비밀번호를 변경해 주세요.</p>
                </div>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full py-2.5 px-4 rounded-lg text-white font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 shadow-lg"
                >
                  로그인하러 가기
                </button>
              </div>
            )}
          </div>
        )}

        <div className="text-center text-sm pt-2">
          <Link
            to="/login"
            className="font-medium text-gray-400 hover:text-gray-300 transition-colors"
          >
            로그인 화면으로 돌아가기
          </Link>
        </div>
      </div>
    </div>
  )
}

export default FindAuth
