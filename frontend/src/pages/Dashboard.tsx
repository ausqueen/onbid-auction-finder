import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, TrendingUp, Shield, BarChart3, Loader2, Heart, Check } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'

import {
  fetchSummary,
  fetchTopProperties,
  fetchProperties,
  fetchGapDistribution,
  triggerSync,
  formatWon,
  formatDate,
} from '../api/client'
import type { FilterState } from '../types/property'
import PropertyCard from '../components/PropertyCard'
import FilterPanel from '../components/FilterPanel'
import Pagination from '../components/Pagination'

const DEFAULT_FILTERS: FilterState = {
  sido: '',
  property_type: '',
  min_price: '',
  max_price: '',
  safe_only: false,
  min_gap_pct: '',
  min_fail_count: '',
}

export default function Dashboard() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const [activeTab, setActiveTab] = useState<'top' | 'search'>('top')
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)
  const qc = useQueryClient()

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    refetchInterval: 60_000,
  })

  const { data: topData, isLoading: topLoading } = useQuery({
    queryKey: ['top-properties', filters.safe_only, filters.sido, filters.property_type],
    queryFn: () => fetchTopProperties({
      n: 20,
      safe_only: filters.safe_only || undefined,
      sido: filters.sido || undefined,
      property_type: filters.property_type || undefined,
    }),
    enabled: activeTab === 'top',
  })

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['properties', filters, page, showFavoritesOnly, showUnreadOnly],
    queryFn: () => fetchProperties({
      ...filters,
      min_price: filters.min_price ? parseInt(filters.min_price) * 10_000 : '',
      max_price: filters.max_price ? parseInt(filters.max_price) * 10_000 : '',
      favorites_only: showFavoritesOnly,
      unread_only: showUnreadOnly,
      page,
      page_size: 20,
    }),
    enabled: activeTab === 'search',
  })

  const { data: gapDist } = useQuery({
    queryKey: ['gap-distribution'],
    queryFn: fetchGapDistribution,
  })

  const syncMutation = useMutation({
    mutationFn: triggerSync,
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['summary'] })
        qc.invalidateQueries({ queryKey: ['top-properties'] })
        qc.invalidateQueries({ queryKey: ['properties'] })
      }, 3000)
    },
  })

  const filteredTopItems = (topData?.items || [])
    .filter(p => !showFavoritesOnly || p.is_favorite)
    .filter(p => !showUnreadOnly || !p.is_read)

  const filteredSearchItems = listData?.items || []

  const totalPages = listData ? Math.ceil(listData.total / 20) : 1

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">온비드 공매 추천</h1>
          <div className="flex items-center gap-3">
            {summary?.last_synced_at && (
              <span className="text-xs text-gray-400 hidden sm:block">
                마지막 동기화: {formatDate(summary.last_synced_at)}
              </span>
            )}
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="btn-primary flex items-center gap-1.5"
            >
              {syncMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              데이터 수집
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* 요약 카드 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <SummaryCard
            icon={<BarChart3 className="w-5 h-5 text-primary-500" />}
            label="전체 물건"
            value={summaryLoading ? '...' : `${(summary?.total_properties ?? 0).toLocaleString()}건`}
          />
          <SummaryCard
            icon={<Shield className="w-5 h-5 text-success-500" />}
            label="안전 물건"
            value={summaryLoading ? '...' : `${(summary?.safe_properties ?? 0).toLocaleString()}건`}
            sub={summary ? `전체의 ${((summary.safe_properties / (summary.total_properties || 1)) * 100).toFixed(0)}%` : ''}
          />
          <SummaryCard
            icon={<TrendingUp className="w-5 h-5 text-warning-500" />}
            label="평균 Gap%"
            value={summaryLoading ? '...' : `${summary?.avg_gap_pct.toFixed(1) ?? 0}%`}
          />
          <SummaryCard
            icon={<TrendingUp className="w-5 h-5 text-danger-500" />}
            label="최대 Gap%"
            value={summaryLoading ? '...' : `${summary?.top_gap_pct.toFixed(1) ?? 0}%`}
          />
        </div>

        <div className="flex gap-6">
          {/* 사이드바 필터 */}
          <aside className="w-56 flex-shrink-0 hidden lg:block">
            <FilterPanel filters={filters} onChange={f => { setFilters(f); setPage(1) }} />

            {/* Gap% 분포 차트 */}
            {gapDist && gapDist.length > 0 && (
              <div className="card p-4 mt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Gap% 분포</h3>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={gapDist} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(v) => [`${v}건`, '물건 수']} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </aside>

          {/* 메인 영역 */}
          <main className="flex-1 min-w-0">
            {/* 모바일 필터 */}
            <div className="lg:hidden mb-4">
              <FilterPanel filters={filters} onChange={f => { setFilters(f); setPage(1) }} />
            </div>

            {/* 탭 및 필터 */}
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
                <button
                  onClick={() => setActiveTab('top')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'top'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  TOP 추천
                </button>
                <button
                  onClick={() => setActiveTab('search')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'search'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  전체 검색
                </button>
              </div>

              <div className="flex gap-2">
                <button 
                  onClick={() => { setShowUnreadOnly(!showUnreadOnly); setPage(1); }}
                  className={`flex items-center px-4 py-1.5 rounded-full text-xs font-bold border transition-colors ${
                    showUnreadOnly 
                      ? 'bg-green-50 border-green-400 text-green-700 font-semibold' 
                      : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Check className="w-3.5 h-3.5 mr-1.5" />
                  {showUnreadOnly ? '미확인 물건만 보기 (ON)' : '미확인 물건 필터 (OFF)'}
                </button>
                <button 
                  onClick={() => { setShowFavoritesOnly(!showFavoritesOnly); setPage(1); }}
                  className={`flex items-center px-4 py-1.5 rounded-full text-xs font-bold border transition-colors ${
                    showFavoritesOnly 
                      ? 'bg-red-50 border-red-400 text-red-700 font-semibold' 
                      : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Heart className={`w-3.5 h-3.5 mr-1.5 ${showFavoritesOnly ? 'fill-red-500 text-red-500' : ''}`} />
                  {showFavoritesOnly ? '관심물건만 보기 (ON)' : '관심물건 필터 (OFF)'}
                </button>
              </div>
            </div>

            {/* TOP 추천 탭 */}
            {activeTab === 'top' && (
              <div>
                {topLoading ? (
                  <LoadingGrid />
                ) : !filteredTopItems.length ? (
                  <EmptyState message={showFavoritesOnly ? "관심 등록한 추천 물건이 없습니다" : "데이터를 수집하려면 상단의 '데이터 수집' 버튼을 클릭하세요"} />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredTopItems.map((p, i) => (
                      <PropertyCard key={p.id} property={p} rank={i + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 전체 검색 탭 */}
            {activeTab === 'search' && (
              <div>
                {listData && (
                  <p className="text-sm text-gray-500 mb-3">
                    총 <strong>{filteredSearchItems.length}</strong>건 {(showFavoritesOnly || showUnreadOnly) && '(필터링 됨)'}
                  </p>
                )}
                {listLoading ? (
                  <LoadingGrid />
                ) : !filteredSearchItems.length ? (
                  <EmptyState message="조건에 맞는 물건이 없습니다" />
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {filteredSearchItems.map(p => (
                        <PropertyCard key={p.id} property={p} />
                      ))}
                    </div>
                    {totalPages > 1 && (
                      <Pagination
                        currentPage={page}
                        totalPages={totalPages}
                        onPageChange={setPage}
                      />
                    )}
                  </>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}

function SummaryCard({
  icon, label, value, sub,
}: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="card p-4 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-3" />
          <div className="h-3 bg-gray-200 rounded w-1/2 mb-2" />
          <div className="h-3 bg-gray-200 rounded w-full" />
        </div>
      ))}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="card p-12 text-center">
      <p className="text-gray-400 text-sm">{message}</p>
    </div>
  )
}
