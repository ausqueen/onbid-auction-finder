import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface ManagedUser {
  id: number
  username: string
  name: string
  email: string
  phone: string
  is_approved: boolean
  is_superuser: boolean
  created_at: string
}

const AdminUserApproval: React.FC = () => {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { token, user: currentUser } = useAuth()

  const fetchUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/admin/users', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        throw new Error('사용자 목록을 불러오는 데 실패했습니다.')
      }
      const data = await res.json()
      setUsers(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token) {
      fetchUsers()
    }
  }, [token])

  const handleApprove = async (id: number) => {
    try {
      const res = await fetch(`/api/admin/users/${id}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || '승인 처리 실패')
      }
      fetchUsers()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const handleReject = async (id: number) => {
    if (!window.confirm('이 사용자를 정말 삭제/반려하시겠습니까?')) return

    try {
      const res = await fetch(`/api/admin/users/${id}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || '삭제 처리 실패')
      }
      fetchUsers()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const handleToggleSuperuser = async (id: number) => {
    if (!window.confirm('이 사용자의 관리자 권한 설정을 변경하시겠습니까?')) return

    try {
      const res = await fetch(`/api/admin/users/${id}/toggle-superuser`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || '권한 변경 실패')
      }
      fetchUsers()
    } catch (err: any) {
      alert(err.message)
    }
  }

  // 가입 대기 회원과 기존 회원 분류
  const pendingUsers = users.filter((u) => !u.is_approved)
  const approvedUsers = users.filter((u) => u.is_approved)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-gray-200 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">회원 가입 승인 및 권한 관리</h1>
          <p className="text-sm text-gray-500 mt-1">시스템 이용 신청 회원들의 상태를 변경하고 관리자 권한을 부여할 수 있습니다.</p>
        </div>
        <button
          onClick={fetchUsers}
          className="mt-4 md:mt-0 flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 transition shadow-sm"
        >
          새로고침
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <div className="space-y-10">
          
          {/* 1. 가입 대기 회원 */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                가입 대기 목록
                <span className="bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full font-medium">
                  {pendingUsers.length}건
                </span>
              </h2>
            </div>
            
            {pendingUsers.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">
                현재 승인 대기 중인 회원가입 요청이 없습니다.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">아이디</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">이름</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">이메일</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">연락처</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">신청일</th>
                      <th className="px-6 py-3 text-center font-semibold text-gray-500 uppercase tracking-wider">작업</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {pendingUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{u.username}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-700">{u.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.email}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.phone}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                          {new Date(u.created_at).toLocaleDateString('ko-KR')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center space-x-2">
                          <button
                            onClick={() => handleApprove(u.id)}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-md text-xs font-semibold shadow-sm transition"
                          >
                            승인
                          </button>
                          <button
                            onClick={() => handleReject(u.id)}
                            className="bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 px-3 py-1.5 rounded-md text-xs font-semibold transition"
                          >
                            반려
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 2. 승인 완료 및 기존 회원 */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4">
              <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                전체 승인 회원 목록
                <span className="bg-indigo-600 text-white text-xs px-2 py-0.5 rounded-full font-medium">
                  {approvedUsers.length}명
                </span>
              </h2>
            </div>
            
            {approvedUsers.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">
                승인된 회원이 없습니다.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">아이디</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">이름</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">이메일</th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">연락처</th>
                      <th className="px-6 py-3 text-center font-semibold text-gray-500 uppercase tracking-wider">권한</th>
                      <th className="px-6 py-3 text-center font-semibold text-gray-500 uppercase tracking-wider">작업</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {approvedUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900 flex items-center gap-1.5">
                          {u.username}
                          {u.is_superuser && (
                            <span className="bg-purple-100 text-purple-800 text-xs px-1.5 py-0.5 rounded-md font-bold">
                              관리자
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-700">{u.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.email}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.phone}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          {u.username === 'root' ? (
                            <span className="text-gray-400 text-xs font-semibold">변경불가 (root)</span>
                          ) : (
                            <button
                              onClick={() => handleToggleSuperuser(u.id)}
                              disabled={u.id === currentUser?.id}
                              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition border ${
                                u.is_superuser
                                  ? 'bg-purple-50 hover:bg-purple-100 text-purple-700 border-purple-200'
                                  : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-300'
                              }`}
                            >
                              {u.is_superuser ? '일반전환' : '관리자임명'}
                            </button>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          {u.username === 'root' || u.id === currentUser?.id ? (
                            <span className="text-gray-400 text-xs font-semibold">-</span>
                          ) : (
                            <button
                              onClick={() => handleReject(u.id)}
                              className="bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 px-3 py-1.5 rounded-md text-xs font-semibold transition"
                            >
                              탈퇴/반려
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  )
}

export default AdminUserApproval
