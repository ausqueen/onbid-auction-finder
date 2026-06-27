import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const Login: React.FC = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const slides = [
    {
      image: '/bg_realestate1.png',
      title: '경공매 대행 전문 서비스',
      subtitle: '부동산 법원 경매 / 자산 공고 분석',
      description: '철저한 권리분석과 신속한 물건 파악으로 최상의 투자 솔루션을 제시합니다.'
    },
    {
      image: '/bg_realestate2.png',
      title: '부동산 매매 및 임대차 계약',
      subtitle: '토지 / 상가 / 주거용 신뢰 계약 매칭',
      description: '정밀한 주변 시세 비교 및 정합성 검증으로 자산 가치 향상을 돕습니다.'
    },
    {
      image: '/bg_realestate3.png',
      title: '대법원 파산 자산 매각 분석',
      subtitle: 'Gemini AI 기반 파산 공고문 실시간 해독',
      description: '복잡한 공고 내용과 인수 항목을 AI가 즉시 요약하고 분석 결과를 매핑합니다.'
    }
  ]

  const [currentSlide, setCurrentSlide] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length)
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      setError(err.message || '아이디 또는 비밀번호를 확인해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-slate-950 font-sans">
      {/* Left Side: Sliding Hero Banner (Desktop Only) */}
      <div className="hidden lg:block lg:w-3/5 relative overflow-hidden">
        {/* Background Slides */}
        {slides.map((slide, idx) => (
          <div
            key={idx}
            className={`absolute inset-0 transition-all duration-[1500ms] ease-in-out ${
              idx === currentSlide ? 'opacity-100 scale-100 z-10' : 'opacity-0 scale-105 z-0'
            }`}
          >
            <img
              src={slide.image}
              alt={slide.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-slate-900/30"></div>
          </div>
        ))}

        {/* Overlay and Banner Texts */}
        <div className="absolute inset-0 z-20 flex flex-col justify-between p-16">
          {/* Logo / Top text */}
          <div className="flex items-center space-x-3 bg-white/5 backdrop-blur-md px-4 py-2.5 rounded-xl border border-white/10 w-fit">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm shadow-md">
              COURT
            </div>
            <span className="text-white font-bold text-sm tracking-widest uppercase">
              Bankruptcy Asset Portal
            </span>
          </div>

          {/* Banner text at the bottom */}
          <div className="space-y-6">
            <div className="relative h-44 w-full">
              {slides.map((slide, idx) => (
                <div
                  key={idx}
                  className={`absolute bottom-0 left-0 right-0 transition-all duration-1000 ease-in-out transform ${
                    idx === currentSlide
                      ? 'opacity-100 translate-y-0 pointer-events-auto'
                      : 'opacity-0 translate-y-8 pointer-events-none'
                  }`}
                >
                  <span className="text-indigo-400 font-semibold text-sm uppercase tracking-widest">
                    {slide.subtitle}
                  </span>
                  <h1 className="text-4xl font-extrabold text-white leading-tight mt-2 drop-shadow-sm">
                    {slide.title}
                  </h1>
                  <p className="text-base text-gray-300 mt-3 max-w-xl font-normal leading-relaxed">
                    {slide.description}
                  </p>
                </div>
              ))}
            </div>

            {/* Custom Dots Indicator */}
            <div className="flex space-x-2.5 pt-4">
              {slides.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentSlide(idx)}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    idx === currentSlide ? 'w-8 bg-indigo-500' : 'w-2 bg-white/20 hover:bg-white/40'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Side: Login Form */}
      <div className="w-full lg:w-2/5 flex flex-col justify-center items-center px-6 sm:px-12 lg:px-20 bg-slate-900 border-l border-white/5 relative z-30">
        {/* Small visual accent */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full filter blur-[80px] -z-10 pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-purple-500/10 rounded-full filter blur-[80px] -z-10 pointer-events-none"></div>

        <div className="max-w-md w-full space-y-8">
          <div>
            {/* Mobile logo only */}
            <div className="lg:hidden mx-auto h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-500/30 mb-6">
              COURT
            </div>
            <h2 className="text-center lg:text-left text-3xl font-extrabold text-white tracking-tight">
              대법원 파산 자산 매각
            </h2>
            <p className="mt-3 text-center lg:text-left text-sm text-gray-400 font-normal">
              전문 부동산 분석 정보 제공 및 추천 계약 솔루션
            </p>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-200 px-4 py-3.5 rounded-xl text-sm text-center font-medium animate-pulse">
              {error}
            </div>
          )}

          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  아이디
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="appearance-none rounded-xl relative block w-full px-4 py-3.5 border border-white/10 placeholder-gray-600 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all focus:bg-white/10"
                  placeholder="아이디를 입력하세요"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  비밀번호
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none rounded-xl relative block w-full px-4 py-3.5 border border-white/10 placeholder-gray-600 text-white bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all focus:bg-white/10"
                  placeholder="비밀번호를 입력하세요"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <Link
                to="/find-auth"
                className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                ID / 비밀번호 찾기
              </Link>
              <Link
                to="/register"
                className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                회원가입 신청
              </Link>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3.5 px-4 border border-transparent text-sm font-semibold rounded-xl text-white bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 transform hover:-translate-y-0.5 active:translate-y-0"
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
                ) : (
                  '로그인'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
