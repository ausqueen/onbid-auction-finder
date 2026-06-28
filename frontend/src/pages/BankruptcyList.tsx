import React, { useEffect, useState, useRef } from 'react'
import {
  RefreshCw, AlertCircle, FileText, ExternalLink, Calendar,
  MapPin, Briefcase, Star, Cpu, Clock, ChevronsLeft, ChevronsRight,
  Phone, Building, FileWarning, CalendarX, Check, Paperclip, Info, Search, X,
  Heart
} from 'lucide-react'
import { BankruptcyProperty } from '../types/bankruptcy'
import { fetchBankruptcyProperties, syncBankruptcyProperties, triggerFileSync, triggerAnalyze, fetchProgress, checkNewNotices } from '../api/bankruptcyClient'
import AddressMap from '../components/AddressMap'
import { useAuth } from '../contexts/AuthContext'

interface ProgressInfo {
  phase: string | null
  collected: number
  analyzed: number
  total_in_db: number
  analyzed_in_db: number
  pending_analysis: number
  synced_files: number
  message: string
}

export default function BankruptcyList() {

  /**
   * 최저 매각 가격 포맷:
   * - 순수 숫자("3000000") → "3,000,000원"
   * - 숫자+한글("3000000원") → "3,000,000원"
   * - 이미 콤마 포함("3,000,000원") → "3,000,000원" (그대로)
   * - 그 외 문자열 → 그대로 반환
   */
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
  // address가 없을 때 target_property에서 한국 주소 패턴 추출 (카카오맵 fallback)
  function extractAddressFromText(text: string | null | undefined): string | null {
    if (!text) return null;
    // Try to match full road address with optional lot number (e.g., 대전 중구 목동 33-91)
    const lotPattern = /([가-힣]+(?:특별시|광역시|특별자치시|도|특별자치도)\s+[가-힣]+[시군구]\s+[가-힣]+(?:동|읍|면)?\s*\d+(?:-\d+)?)/;
    const mLot = text.match(lotPattern);
    if (mLot) return mLot[1].trim();

    // General road address pattern (without lot number)
    const roadPattern = /([가-힣]+(?:특별시|광역시|특별자치시|도|특별자치도)\s+[가-힣]+[시군구]\s+[^,\n\(]{5,50})/;
    const mRoad = text.match(roadPattern);
    if (mRoad) return mRoad[1].trim();

    // Short city pattern fallback
    const shortPattern = /(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]{5,60}(?:로|길|동|읍|면)\s*\d*/;
    const mShort = text.match(shortPattern);
    if (mShort) return mShort[0].trim();

    return null;
  }

  const { token } = useAuth()
  const [properties, setProperties] = useState<BankruptcyProperty[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<ProgressInfo | null>(null)
  const [hasNewData, setHasNewData] = useState<boolean>(false)

  const [searchQuery, setSearchQuery] = useState<string>('')
  const [searchType, setSearchType] = useState<'통합검색' | '주소' | '채무자' | '파산관재인'>('통합검색')

  const [activeTab, setActiveTab] = useState<string>('전체')
  const [showRecommendedOnly, setShowRecommendedOnly] = useState<boolean>(false)
  const [showFavoritesOnly, setShowFavoritesOnly] = useState<boolean>(false)
  const [showUnreadOnly, setShowUnreadOnly] = useState<boolean>(false)

  const toggleFavorite = async (id: number, isFav: boolean) => {
    if (!token) return
    try {
      const url = `/api/users/me/favorites/bankruptcy/${id}`
      const method = isFav ? 'DELETE' : 'POST'
      const res = await fetch(url, {
        method: method,
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setProperties(prev => prev.map(p => p.id === id ? { ...p, is_favorite: !isFav } : p))
      }
    } catch (err) {
      console.error('하트 토글 실패:', err)
    }
  }

  const toggleRead = async (id: number, isRead: boolean) => {
    if (!token) return
    try {
      const url = `/api/bankruptcy/${id}/read`
      const method = isRead ? 'DELETE' : 'POST'
      const res = await fetch(url, {
        method: method,
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setProperties(prev => prev.map(p => p.id === id ? { ...p, is_read: !isRead } : p))
      }
    } catch (err) {
      console.error('읽음 토글 실패:', err)
    }
  }

  const handleDownloadClick = (id: number, isRead: boolean) => {
    if (!isRead) {
      toggleRead(id, false)
    }
  }

  const [currentPage, setCurrentPage] = useState<number>(1)
  const ITEMS_PER_PAGE = 10
  const PAGES_PER_GROUP = 5

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const prevPhaseRef = useRef<string | null>(null)
  const listTopRef = useRef<HTMLDivElement>(null)

  // 페이지 변경 시 맨 위로 스크롤
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [currentPage])

  useEffect(() => {
    loadData(true)
    loadProgress()
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [activeTab, showRecommendedOnly, showFavoritesOnly, searchQuery, searchType])

  useEffect(() => {
    const isWorking = progress?.phase === 'collecting' || progress?.phase === 'analyzing' || progress?.phase === 'file_syncing'
    const justFinished =
      (prevPhaseRef.current === 'collecting' || prevPhaseRef.current === 'analyzing' || prevPhaseRef.current === 'file_syncing') &&
      !isWorking

    if (justFinished) {
      loadData(false)
    }
    prevPhaseRef.current = progress?.phase ?? null

    if (isWorking) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(() => {
          loadProgress()
        }, 10000)
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [progress?.phase])

  // 10분 주기 백그라운드 폴링 (미분석 건 및 신규 공고 확인)
  useEffect(() => {
    let mounted = true
    const checkStatus = async () => {
      if (!mounted) return
      try {
        const p = await fetchProgress()
        if (mounted) setProgress(p)
        const currentlyWorking = p.phase === 'collecting' || p.phase === 'analyzing'
        if (!currentlyWorking) {
          const res = await checkNewNotices()
          if (mounted) setHasNewData(res.has_new)
        }
      } catch (e) {}
    }

    // 초기 진입 시 약간 지연 후 백그라운드 체크
    const initTimer = setTimeout(checkStatus, 3000)
    // 1시간 주기 (3,600,050 ms)
    const interval = setInterval(checkStatus, 60 * 60 * 1000)

    return () => {
      mounted = false
      clearTimeout(initTimer)
      clearInterval(interval)
    }
  }, [])


  const loadData = async (showSpinner = false) => {
    try {
      if (showSpinner) setIsLoading(true)
      const data = await fetchBankruptcyProperties()
      setProperties(data)
    } catch (err: any) {
      setError(err.message || '데이터를 불러오는데 실패했습니다.')
    } finally {
      if (showSpinner) setIsLoading(false)
    }
  }

  const loadProgress = async () => {
    try {
      const p = await fetchProgress()
      setProgress(p)
    } catch {
      // 진행률 오류는 무시
    }
  }

  const handleSync = async () => {
    try {
      setIsSyncing(true)
      await syncBankruptcyProperties()
      setHasNewData(false)
      setProgress(prev => ({ ...(prev || {} as ProgressInfo), phase: 'collecting', message: '목록 수집 시작됨...' }))
      setTimeout(() => { loadProgress() }, 2000)
    } catch (err) {
      alert('수집 시작 실패')
    } finally {
      setIsSyncing(false)
    }
  }

  const handleFileSync = async (mode: 'quick' | 'full' = 'quick') => {
    try {
      await triggerFileSync(mode)
      setProgress(prev => ({ ...(prev || {} as ProgressInfo), phase: 'file_syncing', message: `파일 동기화 시작됨 (${mode})...` }))
      setTimeout(() => { loadProgress() }, 2000)
    } catch (err) {
      alert('파일 동기화 시작 실패')
    }
  }

  const handleAnalyze = async () => {
    try {
      setIsAnalyzing(true)
      await triggerAnalyze()
      setProgress(prev => ({ ...(prev || {} as ProgressInfo), phase: 'analyzing', message: 'AI 분석 시작됨...' }))
    } catch (err) {
      alert('AI 분석 시작 실패')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const filteredProperties = properties.filter((p) => {
    const matchTab = activeTab === '전체' ? true : p.asset_type === activeTab
    const matchRec = showRecommendedOnly ? p.is_recommended === true : true
    const matchFav = showFavoritesOnly ? p.is_favorite === true : true
    const matchUnread = showUnreadOnly ? !p.is_read : true
    let matchSearch = true
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      if (searchType === '주소') {
        // address 필드 + target_property 텍스트 모두 검색
        const addrMatch = !!(p.address && p.address.toLowerCase().includes(q))
        const targetMatch = !!(p.target_property && p.target_property.toLowerCase().includes(q))
        matchSearch = addrMatch || targetMatch
      } else if (searchType === '채무자') {
        matchSearch = extractDebtor(p.selling_agency).toLowerCase().includes(q)
      } else if (searchType === '파산관재인') {
        matchSearch = extractTrustee(p.selling_agency).toLowerCase().includes(q)
      } else {
        // 통합검색: address + target_property + title + selling_agency 전체
        const addr = (p.address || '').toLowerCase()
        const target = (p.target_property || '').toLowerCase()
        const titleStr = (p.title || '').toLowerCase()
        const agency = (p.selling_agency || '').toLowerCase()
        matchSearch = addr.includes(q) || target.includes(q) || titleStr.includes(q) || agency.includes(q)
      }
    }
    return matchTab && matchRec && matchFav && matchUnread && matchSearch
  })

  // 페이징 계산
  const totalItems = filteredProperties.length
  const totalPages = Math.max(1, Math.ceil(totalItems / ITEMS_PER_PAGE))
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const currentItems = filteredProperties.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  const currentGroupIndex = Math.floor((currentPage - 1) / PAGES_PER_GROUP)
  const startPage = currentGroupIndex * PAGES_PER_GROUP + 1
  const endPage = Math.min(startPage + PAGES_PER_GROUP - 1, totalPages)
  
  const pageNumbers = []
  for (let i = startPage; i <= endPage; i++) {
    pageNumbers.push(i)
  }

  const tabs = ['전체', '부동산', '유체동산', '채권', '기타']

  const isWorking = progress?.phase === 'collecting' || progress?.phase === 'analyzing'
  const pendingCount = progress?.pending_analysis ?? 0
  const totalInDb = progress?.total_in_db ?? properties.length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 flex items-center">
            ⚖️ 대법원 파산 자산 매각
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            대법원 전체 공고를 스크래핑하고 AI가 분석한 주요 매각 요약 정보입니다.
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex gap-2 flex-wrap">
          <button
            onClick={handleSync}
            disabled={isSyncing || isWorking || !hasNewData}
            title={hasNewData ? '신규 공고를 수집합니다' : '이미 최신 상태입니다 (10분 주기 자동 확인)'}
            className={`flex items-center px-4 py-2 text-white rounded-md transition-colors shadow-sm text-sm font-medium ${
              !hasNewData && !isSyncing && !isWorking
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300'
            }`}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? '시작 중...' : hasNewData ? '신규 데이터 수집 활성화됨' : '최신 데이터 유지 중'}
          </button>
          <button
            onClick={() => handleFileSync('quick')}
            disabled={isWorking}
            title="로컬 파일 없는 항목만 법원 사이트에서 재다운로드 (빠름)"
            className="flex items-center px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-700 disabled:bg-teal-300 transition-colors shadow-sm text-sm font-medium"
          >
            <Paperclip className="w-4 h-4 mr-2" />
            파일 동기화 (빠른)
          </button>
          <button
            onClick={() => handleFileSync('full')}
            disabled={isWorking}
            title="전체 항목 대상 — 파일명·파일크기 변경 감지 후 재다운로드 (느림)"
            className="flex items-center px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:bg-orange-300 transition-colors shadow-sm text-sm font-medium"
          >
            <Paperclip className="w-4 h-4 mr-2" />
            파일 동기화 (전체)
          </button>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || isWorking || pendingCount === 0}
            className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-purple-300 transition-colors shadow-sm text-sm font-medium"
            title={pendingCount === 0 ? '분석 대기 항목 없음' : `미분석 ${pendingCount}건 AI 분석 시작`}
          >
            <Cpu className={`w-4 h-4 mr-2 ${isAnalyzing ? 'animate-pulse' : ''}`} />
            {isAnalyzing ? '시작 중...' : `AI 분석 시작 (${pendingCount}건 대기)`}
          </button>
        </div>
      </div>

      {/* 진행률 배너 */}
      {isWorking && progress && (
        <div className="mb-5 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
          <Clock className="w-5 h-5 text-blue-500 animate-spin shrink-0" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-blue-800">
              {progress.phase === 'collecting' ? '📋 목록 수집 진행 중'
                : progress.phase === 'file_syncing' ? '📎 파일 동기화 진행 중'
                : '🤖 AI 분석 진행 중'}
              {' — '}
              {progress.message}
            </div>
            <div className="text-xs text-blue-600 mt-0.5">
              DB 누계: {totalInDb}건 | 분석 완료: {progress.analyzed_in_db}건 | 미분석: {pendingCount}건
              {progress.synced_files >= 0 && ` | 로컬 파일: ${progress.synced_files}건`}
            </div>
          </div>
          <span className="text-xs text-blue-500 bg-blue-100 px-2 py-1 rounded-full">자동 갱신 중</span>
        </div>
      )}

      {/* 대기 항목 안내 (작업 없을 때) */}
      {!isWorking && pendingCount > 0 && (
        <div className="mb-5 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <Cpu className="w-5 h-5 text-amber-500 shrink-0" />
          <div className="text-sm text-amber-800">
            <strong>{pendingCount}건</strong>이 AI 분석 대기 중입니다. "AI 분석 시작" 버튼을 눌러 분석하세요.
            <span className="ml-2 text-xs text-amber-600">(분당 약 8건 처리, 완료까지 최대 {Math.ceil(pendingCount / 8)}분 소요)</span>
          </div>
        </div>
      )}

      {/* DB 요약 */}
      <div className="mb-4 text-sm text-gray-500">
        전체 {totalInDb}건 수집됨 / AI 분석 완료 {(progress?.analyzed_in_db ?? 0)}건 / 필터된 항목 {totalItems}건
      </div>

      {/* 검색 바 */}
      <div className="mb-5 flex gap-2 items-center">
        <div className="relative">
          <select
            id="search-type-select"
            value={searchType}
            onChange={(e) => setSearchType(e.target.value as typeof searchType)}
            className="appearance-none h-10 pl-3 pr-8 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer font-medium"
          >
            <option value="통합검색">통합검색</option>
            <option value="주소">주소</option>
            <option value="채무자">채무자</option>
            <option value="파산관재인">파산관재인</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-gray-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <input
            id="search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              searchType === '주소' ? '물건 주소 검색...' :
              searchType === '채무자' ? '채무자 회사명 검색...' :
              searchType === '파산관재인' ? '파산관재인 이름 검색...' :
              '주소, 채무자, 파산관재인 통합 검색...'
            }
            className="w-full h-10 pl-9 pr-9 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        {searchQuery && (
          <span className="text-xs text-blue-600 font-semibold bg-blue-50 px-2 py-1 rounded-full whitespace-nowrap border border-blue-200">
            {totalItems}건 검색됨
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 border-b border-gray-200">
        <div className="flex space-x-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 px-6 font-medium text-sm border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="py-3 md:py-0 flex items-center space-x-2">
          <button 
            onClick={() => setShowUnreadOnly(!showUnreadOnly)}
            className={`flex items-center px-4 py-1.5 rounded-full text-sm font-bold border transition-colors ${
              showUnreadOnly 
                ? 'bg-green-50 border-green-400 text-green-700' 
                : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Check className="w-4 h-4 mr-1.5" />
            {showUnreadOnly ? '미확인 물건만 보기 (ON)' : '미확인 물건 필터 (OFF)'}
          </button>
          <button 
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            className={`flex items-center px-4 py-1.5 rounded-full text-sm font-bold border transition-colors ${
              showFavoritesOnly 
                ? 'bg-red-50 border-red-400 text-red-700' 
                : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Heart className={`w-4 h-4 mr-1.5 ${showFavoritesOnly ? 'fill-red-500 text-red-500' : ''}`} />
            {showFavoritesOnly ? '관심물건만 보기 (ON)' : '관심물건 필터 (OFF)'}
          </button>
          <button 
            onClick={() => setShowRecommendedOnly(!showRecommendedOnly)}
            className={`flex items-center px-4 py-1.5 rounded-full text-sm font-bold border transition-colors ${
              showRecommendedOnly 
                ? 'bg-yellow-50 border-yellow-400 text-yellow-700' 
                : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Star className={`w-4 h-4 mr-1.5 ${showRecommendedOnly ? 'fill-yellow-500 text-yellow-500' : ''}`} />
            {showRecommendedOnly ? '추천물건만 보기 (ON)' : '전체보기 (OFF)'}
          </button>
        </div>
      </div>

      {isLoading && <div className="text-center py-20 text-gray-500">데이터를 불러오는 중입니다...</div>}
      
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6 text-red-700 flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}

      {!isLoading && !error && (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-2">
            {currentItems.length === 0 ? (
              <div className="col-span-full text-center py-20 text-gray-500 bg-gray-50 rounded-lg">조회된 매각 물건이 없습니다.</div>
            ) : (
              currentItems.map((prop) => {
                const isUnanalyzable = prop.is_analyzed && !prop.ai_summary &&
                  prop.attachment_filename != null &&
                  !prop.attachment_filename.toLowerCase().endsWith('.pdf')
                // 파일 확장자 추출 (예: ".hwp" → "HWP")
                const attachExt = prop.attachment_filename
                  ? (prop.attachment_filename.split('.').pop() || '').toUpperCase()
                  : ''
                // "내용 없음", null, undefined, 빈 문자열 모두 유효하지 않은 가격으로 처리
                const INVALID_PRICE_VALUES = ['내용 없음', '내용없음', '-', '']
                const hasValidPrice = !!(prop.min_price && !INVALID_PRICE_VALUES.includes(prop.min_price.trim()))
                return (
                  <div key={prop.id} className={`rounded-xl shadow-sm overflow-hidden transition-all border flex flex-col relative ${prop.is_read ? 'bg-gray-200 border-gray-400' : 'hover:shadow-lg bg-white border-gray-200'}`}>
                    
                     {/* 확인 완료 버튼 */}
                    <button
                      onClick={() => toggleRead(prop.id, !!prop.is_read)}
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
                      onClick={() => toggleFavorite(prop.id, !!prop.is_favorite)}
                      className="absolute top-4 right-4 z-10 p-1.5 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full shadow-sm transition hover:scale-110 border border-gray-105"
                      title={prop.is_favorite ? '관심 해제' : '관심 등록'}
                    >
                      <Heart className={`w-4 h-4 ${prop.is_favorite ? 'text-red-500 fill-red-500' : 'text-gray-400'}`} />
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

                      {/* ── 콘텐츠 분기: 분석불가파일 / AI분석완료 / 미분석 ── */}
                      {isUnanalyzable ? (
                        <>
                          {/* 공고 메타데이터 정보 박스 */}
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

                          {/* 분석불가 파일 경고 */}
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
                          {/* 대상물건 요약 */}
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
                            
                            {/* 공고 메타데이터 인라인 표시 */}
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
                                    <span>
                                      {attachExt === 'PDF'
                                        ? "원본 공고(PDF) 내에 최저 매각 가격이 불분명하여 자동 추출이 어렵습니다. 원본 공고를 직접 확인하시기 바랍니다."
                                        : `첨부파일이 ${attachExt || '해당'} 형식으로 자동 추출이 불가합니다. 원본 공고 내 첨부파일을 직접 다운로드하여 확인하시기 바랍니다.`}
                                    </span>
                                  </div>
                                )}
                              </div>
                              <div>
                                <div className="text-xs text-blue-600 uppercase tracking-widest font-bold">매각 기일</div>
                                <div className="font-medium mt-0.5 text-gray-800">{prop.sale_deadline || '미정'}</div>
                              </div>
                            </div>
                          </div>
                          <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-100 mb-4 text-sm">
                            <strong className="text-indigo-900 block mb-1">Gemini AI 종합 분석</strong>
                            <span className="text-indigo-800">{prop.ai_summary}</span>
                          </div>
                        </>
                      ) : (
                        <div className="text-sm text-gray-400 italic mb-4 bg-gray-50 p-3 rounded-lg">
                          {prop.is_analyzed
                            ? 'AI 문서 분석 내용이 없습니다. (첨부파일 없음)'
                            : '⏳ AI 분석 대기 중입니다. "AI 분석 시작" 버튼을 눌러 분석할 수 있습니다.'}
                        </div>
                      )}

                    </div>

                    <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 grid grid-cols-2 items-center gap-4">
                      <div className="flex items-center text-xs text-gray-500 space-x-1">
                        <Briefcase className="w-4 h-4 text-gray-400" />
                        <span>관재인: {prop.manager_contact || '미상'}</span>
                      </div>
                      <div className="text-right">
                        <a 
                          href={prop.notice_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-500 transition-colors"
                        >
                          원본 공고 보기 <ExternalLink className="w-4 h-4 ml-1" />
                        </a>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-10 flex justify-center items-center space-x-1">
              {/* 맨 처음 */}
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                title="첫 페이지"
                className="w-9 h-9 flex items-center justify-center border border-gray-300 rounded text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>

              {/* 이전 그룹 */}
              <button
                onClick={() => setCurrentPage(Math.max(1, startPage - PAGES_PER_GROUP))}
                disabled={startPage === 1}
                className="px-3 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                이전
              </button>
              
              {pageNumbers.map(num => (
                <button
                  key={num}
                  onClick={() => setCurrentPage(num)}
                  className={`w-10 h-10 rounded flex items-center justify-center text-sm font-medium transition-colors ${
                    currentPage === num
                      ? 'bg-blue-600 text-white border border-blue-600'
                      : 'border border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                  }`}
                >
                  {num}
                </button>
              ))}

              {/* 다음 그룹 */}
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, endPage + 1))}
                disabled={endPage === totalPages}
                className="px-3 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                다음
              </button>

              {/* 맨 끝 */}
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                title="마지막 페이지"
                className="w-9 h-9 flex items-center justify-center border border-gray-300 rounded text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>

              {/* 현재 위치 텍스트 */}
              <span className="ml-2 text-xs text-gray-400">
                {currentPage} / {totalPages}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
