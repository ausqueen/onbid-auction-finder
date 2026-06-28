import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { formatWon, formatArea } from '../api/client'
import PropertyCard from '../components/PropertyCard'
import type { Property } from '../types/property'
import type { BankruptcyProperty } from '../types/bankruptcy'
import { Star, Cpu, MapPin, Calendar, FileText, Building, CalendarX, Phone, FileWarning, Heart, Paperclip, ExternalLink, Check } from 'lucide-react'
import AddressMap from '../components/AddressMap'

const MyPage: React.FC = () => {
  function formatPrice(raw: string | null | undefined): string {
    if (!raw) return '-'
    const trimmed = raw.trim()
    if (/^\d+$/.test(trimmed)) {
      return Number(trimmed).toLocaleString('ko-KR') + '원'
    }
    const m = trimmed.match(/^([\d,]+)(.*)/)
    if (m) {
      const numPart = m[1].replace(/,/g, '')
      const suffix = m[2]
      if (/^\d+$/.test(numPart)) {
        return Number(numPart).toLocaleString('ko-KR') + suffix
      }
    }
    return trimmed
  }

  function extractDebtor(agency: string | null): string {
    if (!agency) return ''
    const m = agency.match(/채무자\s+(.+?)(?:의\s*파산관재인|$)/)
    return m ? m[1].trim() : ''
  }
  function extractTrustee(agency: string | null): string {
    if (!agency) return ''
    const m = agency.match(/파산관재인\s+(.+)/)
    return m ? m[1].trim() : ''
  }
  function extractAddressFromText(text: string | null | undefined): string | null {
    if (!text) return null;
    const lotPattern = /([가-힣]+(?:특별시|광역시|특별자치시|도|특별자치도)\s+[가-힣]+[시군구]\s+[가-힣]+(?:동|읍|면)?\s*\d+(?:-\d+)?)/;
    const mLot = text.match(lotPattern);
    if (mLot) return mLot[1].trim();

    const roadPattern = /([가-힣]+(?:특별시|광역시|특별자치시|도|특별자치도)\s+[가-힣]+[시군구]\s+[^,\n\(]{5,50})/;
    const mRoad = text.match(roadPattern);
    if (mRoad) return mRoad[1].trim();

    const shortPattern = /(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]{5,60}(?:로|길|동|읍|면)\s*\d*/;
    const mShort = text.match(shortPattern);
    if (mShort) return mShort[0].trim();

    return null;
  }
  const { user, token, checkAuth } = useAuth()
  
  // 탭 제어 ('profile' | 'fav_bankrupt' | 'fav_onbid')
  const [activeTab, setActiveTab] = useState<'profile' | 'fav_bankrupt' | 'fav_onbid'>('profile')

  // 프로필 정보 수정 폼
  const [name, setName] = useState(user?.name || '')
  const [email, setEmail] = useState(user?.email || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [profileMsg, setProfileMsg] = useState('')
  const [profileErr, setProfileErr] = useState('')

  // 비밀번호 변경 폼
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [pwMsg, setPwMsg] = useState('')
  const [pwErr, setPwErr] = useState('')

  // 관심 물건 목록 데이터
  const [favoriteProps, setFavoriteProps] = useState<Property[]>([])
  const [favoriteBankrupts, setFavoriteBankrupts] = useState<BankruptcyProperty[]>([])
  const [loadingFavs, setLoadingFavs] = useState(false)

  // 컴포넌트 첫 로드 시 유저 데이터로 프로필 폼 동기화
  useEffect(() => {
    if (user) {
      setName(user.name)
      setEmail(user.email)
      setPhone(user.phone)
    }
  }, [user])

  // 즐겨찾기 리스트 로드
  const fetchFavorites = async (loadAll = false) => {
    if (!token) return
    setLoadingFavs(true)
    try {
      if (loadAll) {
        // 첫 진입 시 전체 즐겨찾기를 로드하여 탭 숫자를 업데이트함
        const [onbidRes, bankruptRes] = await Promise.all([
          fetch('/api/users/me/favorites/properties', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/users/me/favorites/bankruptcy', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ])

        if (onbidRes.ok) {
          const data = await onbidRes.json()
          setFavoriteProps(data)
        }
        if (bankruptRes.ok) {
          const data = await bankruptRes.json()
          setFavoriteBankrupts(data)
        }
      } else {
        if (activeTab === 'fav_onbid') {
          const res = await fetch('/api/users/me/favorites/properties', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (res.ok) {
            const data = await res.json()
            setFavoriteProps(data)
          }
        } else if (activeTab === 'fav_bankrupt') {
          const res = await fetch('/api/users/me/favorites/bankruptcy', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (res.ok) {
            const data = await res.json()
            setFavoriteBankrupts(data)
          }
        }
      }
    } catch (err) {
      console.error('즐겨찾기 조회 실패:', err)
    } finally {
      setLoadingFavs(false)
    }
  }

  useEffect(() => {
    if (token) {
      fetchFavorites(true)
    }
  }, [token])

  useEffect(() => {
    if (activeTab !== 'profile') {
      fetchFavorites(false)
    }
  }, [activeTab])

  // 프로필 수정 처리
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileMsg('')
    setProfileErr('')

    try {
      const res = await fetch('/api/users/me/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name, email, phone })
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || '수정에 실패했습니다.')
      }

      setProfileMsg('개인 정보가 안전하게 변경되었습니다.')
      // AuthContext 상태 갱신
      await checkAuth()
    } catch (err: any) {
      setProfileErr(err.message)
    }
  }

  // 비밀번호 변경 처리
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwMsg('')
    setPwErr('')

    if (newPassword !== confirmNewPassword) {
      setPwErr('새 비밀번호가 일치하지 않습니다.')
      return
    }

    try {
      const res = await fetch('/api/users/me/change-password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || '비밀번호 변경 실패')
      }

      setPwMsg('비밀번호가 성공적으로 변경되었습니다.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (err: any) {
      setPwErr(err.message)
    }
  }

  // 관심 등록 해제 (하트 토글 해제)
  const handleRemoveFavorite = async (type: 'onbid' | 'bankruptcy', id: number) => {
    try {
      const url = type === 'onbid' 
        ? `/api/users/me/favorites/properties/${id}`
        : `/api/users/me/favorites/bankruptcy/${id}`

      const res = await fetch(url, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.ok) {
        // 클라이언트 목록에서 제거
        if (type === 'onbid') {
          setFavoriteProps(favoriteProps.filter(item => item.id !== id))
        } else {
          setFavoriteBankrupts(favoriteBankrupts.filter(item => item.id !== id))
        }
      }
    } catch (err) {
      console.error('해제 실패:', err)
    }
  }

  const handleToggleRead = async (id: number, isRead: boolean) => {
    if (!token) return
    try {
      const url = `/api/bankruptcy/${id}/read`
      const method = isRead ? 'DELETE' : 'POST'
      const res = await fetch(url, {
        method: method,
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setFavoriteBankrupts(prev => prev.map(p => p.id === id ? { ...p, is_read: !isRead } : p))
      }
    } catch (err) {
      console.error('읽음 토글 실패:', err)
    }
  }

  const handleDownloadClick = (id: number, isRead: boolean) => {
    if (!isRead) {
      handleToggleRead(id, false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="pb-6 border-b border-gray-200 mb-8">
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">마이페이지</h1>
        <p className="text-sm text-gray-500 mt-1">개인 정보를 변경하고 관심 등록한 매각 자산들을 모아볼 수 있습니다.</p>
      </div>

      {/* 탭 헤더 */}
      <div className="flex border-b border-gray-200 mb-8">
        <button
          onClick={() => setActiveTab('profile')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'profile'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          내 정보 관리
        </button>
        <button
          onClick={() => setActiveTab('fav_bankrupt')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'fav_bankrupt'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          관심 파산 공고 ({favoriteBankrupts.length})
        </button>
        <button
          onClick={() => setActiveTab('fav_onbid')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'fav_onbid'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          관심 공매 물건 ({favoriteProps.length})
        </button>
      </div>

      {/* 1. 내 정보 관리 탭 */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* 가입 정보 및 프로필 수정 */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-lg font-bold text-gray-800 mb-6 pb-2 border-b border-gray-100">프로필 편집</h2>
            
            {profileMsg && <div className="bg-green-50 text-green-700 p-3 rounded-lg text-sm mb-4">{profileMsg}</div>}
            {profileErr && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">{profileErr}</div>}

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">아이디</label>
                <input
                  type="text"
                  disabled
                  value={user?.username || ''}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-gray-500 bg-gray-50 text-sm focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">이름 (실명)</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">이메일 주소</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">연락처 (전화번호)</label>
                <input
                  type="text"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm transition"
              >
                변경 내용 저장
              </button>
            </form>
          </div>

          {/* 비밀번호 변경 */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-lg font-bold text-gray-800 mb-6 pb-2 border-b border-gray-100">비밀번호 변경</h2>

            {pwMsg && <div className="bg-green-50 text-green-700 p-3 rounded-lg text-sm mb-4">{pwMsg}</div>}
            {pwErr && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">{pwErr}</div>}

            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">현재 비밀번호</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="현재 비밀번호를 입력하세요"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">새 비밀번호</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="최소 4자 이상"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">새 비밀번호 확인</label>
                <input
                  type="password"
                  required
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="새 비밀번호 재입력"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm transition"
              >
                비밀번호 수정
              </button>
            </form>
          </div>

        </div>
      )}

      {/* 2. 관심 파산 공고 탭 */}
      {activeTab === 'fav_bankrupt' && (
        <div>
          {loadingFavs ? (
            <div className="flex justify-center py-16">
              <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600"></div>
            </div>
          ) : favoriteBankrupts.length === 0 ? (
            <div className="text-center py-20 text-gray-400 bg-white rounded-xl border border-gray-200">
              관심 등록된 파산 매각 공고가 없습니다.<br />
              파산 공고 리스트에서 하트를 누르면 여기에 저장됩니다.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {favoriteBankrupts.map((prop) => {
                const isUnanalyzable = prop.is_analyzed && !prop.ai_summary &&
                  prop.attachment_filename != null &&
                  !prop.attachment_filename.toLowerCase().endsWith('.pdf')
                
                const attachExt = prop.attachment_filename
                  ? (prop.attachment_filename.split('.').pop() || '').toUpperCase()
                  : ''

                const INVALID_PRICE_VALUES = ['내용 없음', '내용없음', '-', '']
                const hasValidPrice = !!(prop.min_price && !INVALID_PRICE_VALUES.includes(prop.min_price.trim()))
                
                return (
                  <div key={prop.id} className={`rounded-xl shadow-md overflow-hidden transition-all border flex flex-col relative ${prop.is_read ? 'bg-gray-200 border-gray-400' : 'hover:shadow-lg bg-white border-gray-200'}`}>
                    
                    {/* 확인 완료 버튼 */}
                    <button
                      onClick={() => handleToggleRead(prop.id, !!prop.is_read)}
                      className={`absolute top-4 right-12 z-10 p-1.5 rounded-full shadow-sm transition hover:scale-110 border cursor-pointer ${
                        prop.is_read 
                          ? 'bg-green-50 border-green-200 text-green-600' 
                          : 'bg-white bg-opacity-80 border-gray-200 text-gray-400 hover:bg-opacity-100 hover:bg-gray-50'
                      }`}
                      title={prop.is_read ? '확인 취소' : '확인 완료'}
                    >
                      <Check className={`w-4 h-4 ${prop.is_read ? 'stroke-[3px]' : ''}`} />
                    </button>

                    {/* 하트 관심버튼 */}
                    <button
                      onClick={() => handleRemoveFavorite('bankruptcy', prop.id)}
                      className="absolute top-4 right-4 z-10 p-1.5 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full shadow-sm transition hover:scale-110 border border-gray-100"
                      title="관심 해제"
                    >
                      <Heart className="w-4 h-4 text-red-500 fill-red-500" />
                    </button>

                    <div className="px-6 py-5 border-b border-gray-100 flex-grow pt-8">
                      {/* 배지 목록 (우측 하트 버튼과의 충돌 방지를 위해 pr-10 설정) */}
                      <div className="flex items-center gap-2 flex-wrap mb-3 pr-10">
                        {prop.is_recommended && (
                          <span className="inline-flex items-center bg-yellow-400 text-yellow-900 text-xs font-black px-2 py-0.5 rounded shadow-sm">
                            <Star className="w-3.5 h-3.5 fill-yellow-900 mr-1" /> 강력 추천
                          </span>
                        )}
                        {prop.asset_type && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
                            {prop.asset_type}
                          </span>
                        )}
                        {!prop.is_analyzed && (
                          <span className="inline-flex items-center bg-gray-100 text-gray-500 text-xs px-2 py-0.5 rounded-full border border-gray-200">
                            <Cpu className="w-3 h-3 mr-1" /> AI 분석 대기
                          </span>
                        )}
                      </div>

                      <div className="flex justify-between items-start mb-2">
                        <h3 className="text-lg font-bold text-gray-900 leading-tight">
                          {prop.title}
                        </h3>
                      </div>
                      
                      <div className="flex items-center text-sm text-gray-500 mb-4 space-x-4">
                        <span className="flex items-center"><MapPin className="w-4 h-4 mr-1 text-gray-400"/> {prop.court_name}</span>
                        <span className="flex items-center"><Calendar className="w-4 h-4 mr-1 text-gray-400"/> {prop.post_date || '-'}</span>
                      </div>

                      {/* 콘텐츠 분기 */}
                      {isUnanalyzable ? (
                        <>
                          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-3">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5" /> 공고 정보
                            </h4>
                            <div className="grid grid-cols-1 gap-2 text-sm">
                              {prop.selling_agency && (
                                <div className="flex items-start gap-2">
                                  <Building className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-slate-400 block">매각기관</span>
                                    <span className="text-slate-700 font-medium leading-snug">{prop.selling_agency}</span>
                                  </div>
                                </div>
                              )}
                              {prop.court_name && (
                                <div className="flex items-start gap-2">
                                  <MapPin className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-slate-400 block">관할법원</span>
                                    <span className="text-slate-700 font-medium">{prop.court_name}</span>
                                  </div>
                                </div>
                              )}
                              <div className="grid grid-cols-2 gap-2 mt-1">
                                {prop.post_date && (
                                  <div className="flex items-start gap-2">
                                    <Calendar className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                                    <div>
                                      <span className="text-xs text-slate-400 block">작성일</span>
                                      <span className="text-slate-700 font-medium">{prop.post_date}</span>
                                    </div>
                                  </div>
                                )}
                                {prop.notice_expire_date && (
                                  <div className="flex items-start gap-2">
                                    <CalendarX className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                                    <div>
                                      <span className="text-xs text-slate-400 block">공고만료일</span>
                                      <span className="text-red-600 font-semibold">{prop.notice_expire_date}</span>
                                    </div>
                                  </div>
                                )}
                              </div>
                              {prop.phone_number && (
                                <div className="flex items-start gap-2 mt-1">
                                  <Phone className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-slate-400 block">전화번호</span>
                                    <a href={`tel:${prop.phone_number}`} className="text-blue-600 font-medium hover:underline">{prop.phone_number}</a>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex items-start gap-2.5 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-3">
                            <FileWarning className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                            <div className="text-sm w-full">
                              <span className="font-semibold text-amber-800">{attachExt} 첨부파일 — AI 분석 불가</span>
                              <p className="text-amber-700 mt-0.5 leading-snug">
                                첨부파일이 <code className="bg-amber-100 px-1 rounded text-xs font-mono">.{attachExt.toLowerCase()}</code> 형식으로 자동 분석이 지원되지 않습니다.
                                상세 내용은 <strong>원본 공고</strong>에서 직접 확인해 주세요.
                              </p>
                              <div className="mt-2 border-t border-amber-200 pt-2">
                                <span className="text-xs text-amber-600 block mb-1">첨부파일 다운로드:</span>
                                {(() => {
                                  const attachList = (prop as any).attachments && (prop as any).attachments.length > 0
                                    ? (prop as any).attachments
                                    : prop.attachment_filename ? [{ filename: prop.attachment_filename }] : [];
                                  
                                  return attachList.map((att: any, idx: number) => (
                                    <a
                                      key={idx}
                                      href={`/api/bankruptcy/${prop.id}/download?filename=${encodeURIComponent(att.filename)}&token=${token}`}
                                      onClick={() => handleDownloadClick(prop.id, !!prop.is_read)}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-amber-750 hover:text-amber-900 text-xs font-mono font-medium underline inline-flex items-center gap-1 mt-1 mr-3 break-all"
                                      title="클릭하여 파일 다운로드"
                                    >
                                      <span>📎</span>
                                      <span>{att.filename}</span>
                                      <ExternalLink className="w-3 h-3 opacity-70" />
                                    </a>
                                  ));
                                })()}
                              </div>
                            </div>
                          </div>
                        </>
                      ) : prop.ai_summary ? (
                        <>
                          <div className="bg-blue-50 bg-opacity-50 p-4 rounded-lg mb-3">
                            <h4 className="text-sm font-semibold text-blue-900 mb-2 flex items-center">
                              <FileText className="w-4 h-4 mr-2 text-blue-600"/>
                              대상물건 요약
                            </h4>
                            <p className="text-sm text-gray-700 whitespace-pre-line mb-3">{prop.target_property}</p>
                            {(() => {
                              const mapAddr = (prop.address && prop.address !== '내용 없음')
                                ? prop.address
                                : extractAddressFromText(prop.target_property)
                              return mapAddr ? <AddressMap address={mapAddr} /> : null
                            })()}
                            
                            <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm border-t border-blue-100 pt-3">
                              {prop.selling_agency && (
                                <div className="flex items-start gap-1.5 col-span-2">
                                  <Building className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-blue-400 block">매각기관</span>
                                    <span className="text-gray-700 font-medium text-xs">{prop.selling_agency}</span>
                                  </div>
                                </div>
                              )}
                              {prop.court_name && (
                                <div className="flex items-start gap-1.5 col-span-2">
                                  <MapPin className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-blue-400 block">관할법원</span>
                                    <span className="text-gray-700 font-medium text-xs">{prop.court_name}</span>
                                  </div>
                                </div>
                              )}
                              {prop.post_date && (
                                <div className="flex items-start gap-1.5">
                                  <Calendar className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-blue-400 block">작성일</span>
                                    <span className="text-gray-700 font-medium text-xs">{prop.post_date}</span>
                                  </div>
                                </div>
                              )}
                              {prop.notice_expire_date && (
                                <div className="flex items-start gap-1.5">
                                  <CalendarX className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-blue-400 block">공고만료일</span>
                                    <span className="text-red-600 font-semibold text-xs">{prop.notice_expire_date}</span>
                                  </div>
                                </div>
                              )}
                              {prop.phone_number && (
                                <div className="flex items-start gap-1.5">
                                  <Phone className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                                  <div>
                                    <span className="text-xs text-blue-400 block">전화번호</span>
                                    <a href={`tel:${prop.phone_number}`} className="text-blue-600 font-medium text-xs hover:underline">{prop.phone_number}</a>
                                  </div>
                                </div>
                              )}
                              {prop.attachment_filename && (
                                <div className="flex items-start gap-1.5 col-span-2">
                                  <Paperclip className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0" />
                                  <div className="w-full">
                                    <span className="text-xs text-blue-400 block mb-1">첨부파일</span>
                                    <div className="flex flex-col gap-1.5">
                                      {(() => {
                                        const attachList = (prop as any).attachments && (prop as any).attachments.length > 0
                                          ? (prop as any).attachments
                                          : [{ filename: prop.attachment_filename }];
                                        
                                        return attachList.map((att: any, idx: number) => (
                                          <a
                                            key={idx}
                                            href={`/api/bankruptcy/${prop.id}/download?filename=${encodeURIComponent(att.filename)}&token=${token}`}
                                            onClick={() => handleDownloadClick(prop.id, !!prop.is_read)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-blue-600 hover:text-blue-800 text-xs font-mono font-medium underline inline-flex items-center gap-1 break-all"
                                            title="클릭하여 파일 다운로드"
                                          >
                                            <span>{att.filename}</span>
                                            <ExternalLink className="w-3 h-3 opacity-70" />
                                          </a>
                                        ));
                                      })()}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>

                            <div className="mt-3 grid grid-cols-2 gap-3 text-sm border-t border-blue-100 pt-3">
                              <div>
                                <div className="text-xs text-blue-600 uppercase tracking-widest font-bold">최저 매각 가격</div>
                                {hasValidPrice ? (
                                  <div className="font-medium mt-0.5 text-gray-800">{formatPrice(prop.min_price)}</div>
                                ) : (
                                  <div className="mt-0.5 text-amber-700 text-xs leading-snug flex items-start gap-1">
                                    <FileWarning className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-500" />
                                    <span>정확한 금액은 첨부파일 참조</span>
                                  </div>
                                )}
                              </div>
                              <div>
                                <div className="text-xs text-blue-600 uppercase tracking-widest font-bold">매각 기일</div>
                                <div className="font-medium mt-0.5 text-gray-800">{prop.sale_deadline || '-'}</div>
                              </div>
                            </div>
                          </div>

                          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
                            <h4 className="text-sm font-semibold text-indigo-900 mb-2 flex items-center">
                              <Cpu className="w-4 h-4 mr-2 text-indigo-600"/>
                              Gemini AI 종합 분석
                            </h4>
                            <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{prop.ai_summary}</p>
                          </div>
                        </>
                      ) : (
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-sm text-gray-500">
                          AI가 해당 공고문을 정밀 분석하고 있습니다. 완료 시 요약과 투자의견이 노출됩니다.
                        </div>
                      )}
                    </div>

                    <div className="bg-gray-50 px-6 py-4 flex items-center justify-between border-t border-gray-100">
                      <a
                        href={prop.notice_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary py-1.5 text-xs font-bold flex items-center gap-1"
                      >
                        <ExternalLink className="w-3.5 h-3.5" /> 대법원 원본 공고
                      </a>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 3. 관심 공매 물건 탭 */}
      {activeTab === 'fav_onbid' && (
        <div>
          {loadingFavs ? (
            <div className="flex justify-center py-16">
              <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-600"></div>
            </div>
          ) : favoriteProps.length === 0 ? (
            <div className="text-center py-20 text-gray-400 bg-white rounded-xl border border-gray-200">
              관심 등록된 온비드 공매 물건이 없습니다.<br />
              추천 목록에서 하트를 누르면 여기에 저장됩니다.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {favoriteProps.map((item) => (
                <PropertyCard key={item.id} property={item} />
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  )
}

export default MyPage
