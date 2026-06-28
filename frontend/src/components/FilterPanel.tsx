import { useQuery } from '@tanstack/react-query'
import { SlidersHorizontal, RotateCcw } from 'lucide-react'
import { fetchRegions, fetchPropertyTypes } from '../api/client'
import type { FilterState } from '../types/property'

interface FilterPanelProps {
  filters: FilterState
  onChange: (filters: FilterState) => void
}

const DEFAULT_FILTERS: FilterState = {
  sido: '',
  property_type: '',
  min_price: '',
  max_price: '',
  safe_only: false,
  min_gap_pct: '',
  min_fail_count: '',
}

export default function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const { data: regions = [] } = useQuery({
    queryKey: ['regions'],
    queryFn: fetchRegions,
  })

  const { data: types = [] } = useQuery({
    queryKey: ['property-types'],
    queryFn: fetchPropertyTypes,
  })

  const update = (key: keyof FilterState, value: string | boolean) => {
    onChange({ ...filters, [key]: value })
  }

  const reset = () => onChange(DEFAULT_FILTERS)

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4" />
          필터
        </h3>
        <button onClick={reset} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
          <RotateCcw className="w-3 h-3" />
          초기화
        </button>
      </div>

      <div className="space-y-4">
        {/* 안전 물건만 보기 */}
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.safe_only}
            onChange={e => update('safe_only', e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm font-medium text-gray-700">안전 물건만 보기</span>
          <span className="text-xs text-gray-400">(위험키워드 없음)</span>
        </label>

        {/* 지역 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">지역 (시도)</label>
          <select
            value={filters.sido}
            onChange={e => update('sido', e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">전체 지역</option>
            {regions.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* 물건종류 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">물건종류</label>
          <select
            value={filters.property_type}
            onChange={e => update('property_type', e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">전체 종류</option>
            {types.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {/* 최저입찰가 범위 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">최저입찰가 (만원)</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="최소"
              value={filters.min_price}
              onChange={e => update('min_price', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <span className="text-gray-400 text-sm">~</span>
            <input
              type="number"
              placeholder="최대"
              value={filters.max_price}
              onChange={e => update('max_price', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* 최소 Gap% */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">최소 Gap% (시세차익률)</label>
          <input
            type="number"
            placeholder="예: 20"
            value={filters.min_gap_pct}
            onChange={e => update('min_gap_pct', e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* 최소 유찰횟수 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">최소 유찰횟수</label>
          <input
            type="number"
            placeholder="예: 2"
            value={filters.min_fail_count}
            onChange={e => update('min_fail_count', e.target.value)}
            min={0}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>
    </div>
  )
}
