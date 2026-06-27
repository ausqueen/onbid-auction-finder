import React, { createContext, useContext, useState, useEffect } from 'react'

interface User {
  id: number
  username: string
  name: string
  email: string
  phone: string
  is_approved: boolean
  is_superuser: boolean
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  register: (username: string, password: string, name: string, email: string, phone: string) => Promise<void>
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  const checkAuth = async () => {
    const storedToken = localStorage.getItem('token')
    if (!storedToken) {
      setUser(null)
      setToken(null)
      setLoading(false)
      return
    }

    try {
      const res = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${storedToken}`
        }
      })
      if (res.ok) {
        const userData = await res.json()
        setUser(userData)
        setToken(storedToken)
      } else {
        // 토큰 만료 또는 승인 취소 등
        logout()
      }
    } catch (err) {
      console.error('인증 확인 에러:', err)
      logout()
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkAuth()
  }, [])

  const login = async (username: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    })

    if (!res.ok) {
      const errorData = await res.json()
      throw new Error(errorData.detail || '로그인에 실패했습니다.')
    }

    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    setUser({
      id: 0, // 기본 ID (me API로 갱신 가능)
      username: data.username,
      name: data.name,
      email: '',
      phone: '',
      is_approved: data.is_approved,
      is_superuser: data.is_superuser
    })
    
    // 유저 상세 정보 추가 로드
    const userMeRes = await fetch('/api/auth/me', {
      headers: {
        'Authorization': `Bearer ${data.access_token}`
      }
    })
    if (userMeRes.ok) {
      const meData = await userMeRes.json()
      setUser(meData)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  const register = async (username: string, password: string, name: string, email: string, phone: string) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password, name, email, phone })
    })

    if (!res.ok) {
      const errorData = await res.json()
      throw new Error(errorData.detail || '회원가입 신청에 실패했습니다.')
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, register, checkAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
