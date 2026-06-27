import { useState, useEffect } from 'react'
import { Building2, MapPin, RotateCcw, Calendar, ExternalLink, Heart, Check } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Property } from '../types/property'
import GapBadge from './GapBadge'
import RiskBadge from './RiskBadge'
import { formatWon, formatArea, formatDate } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

interface PropertyCardProps {
  property: Property
  rank?: number
}

export default function PropertyCard({ property: p, rank }: PropertyCardProps) {
  const { token } = useAuth()
  const [isFav, setIsFav] = useState(!!p.is_favorite)
  const [isRead, setIsRead] = useState(!!p.is_read)
  const a = p.analysis

  useEffect(() => {
    setIsRead(!!p.is_read)
  }, [p.is_read])

  const handleReadToggle = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!token) return

    try {
      const url = `/api/properties/${p.id}/read`
      const method = isRead ? 'DELETE' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setIsRead(!isRead)
      }
    } catch (err) {
      console.error('읽음 토글 실패:', err)
    }
  }

  const hasTenantRisk = a?.risk_keywords?.some(k => k.includes('대항력') || k.includes('유치권') || k.includes('임차'))
  const hasUnknownDeposit = hasTenantRisk && (!a?.tenant_deposit || a.tenant_deposit === 0)

  const handleFavoriteToggle = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!token) return

    try {
      const url = `/api/users/me/favorites/properties/${p.id}`
      const method = isFav ? 'DELETE' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setIsFav(!isFav)
      }
    } catch (err) {
      console.error('하트 토글 실패:', err)
    }
  }

  return (
    <div className={`card p-4 transition-all relative ${isRead ? 'bg-gray-200 border-gray-400' : 'hover:shadow-md bg-white border-gray-200'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {rank && (
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary-600 text-white text-xs font-bold flex items-center justify-center">
              {rank}
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1 pr-8">
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium">
                {p.property_type}
              </span>
              {p.fail_count > 0 && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                  <RotateCcw className="w-3 h-3" />
                  {p.fail_count}회 유찰
                </span>
              )}
              <RiskBadge analysis={a} />
            </div>
            <p className="text-sm font-medium text-gray-900 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <span className="truncate">{p.address}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {a?.gap_pct != null && a.gap_pct > 0 && !hasUnknownDeposit && (
            <GapBadge gapPct={a.gap_pct} size="md" hasDeposit={!!a.tenant_deposit && a.tenant_deposit > 0} />
          )}
          <button
            onClick={handleReadToggle}
            className={`p-1.5 rounded-full transition transform hover:scale-110 border cursor-pointer ${
              isRead 
                ? 'bg-green-50 border-green-200 text-green-600' 
                : 'bg-white border-gray-200 text-gray-400 hover:bg-gray-50'
            }`}
            title={isRead ? '확인 취소' : '확인 완료'}
          >
            <Check className={`w-4 h-4 ${isRead ? 'stroke-[3px]' : ''}`} />
          </button>
          <button
            onClick={handleFavoriteToggle}
            className="p-1.5 hover:bg-gray-100 rounded-full transition transform hover:scale-110"
            title={isFav ? '관심 해제' : '관심 등록'}
          >
            <Heart className={`w-4 h-4 ${isFav ? 'text-red-500 fill-red-500' : 'text-gray-400'}`} />
          </button>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <span className="text-gray-500 text-xs">최저입찰가</span>
          <p className="font-semibold text-gray-900">{formatWon(p.min_bid_price)}</p>
        </div>
        
        {/* 인수금 표시 (시세평가 포함 요소) */}
        {!a?.is_safe ? (
          <div>
            <span className="text-gray-500 text-xs text-danger-600 font-bold">비용 합산 (인수금 등)</span>
            <p className="font-semibold text-danger-600">
              {a?.tenant_deposit && a.tenant_deposit > 0 ? `+${formatWon(a.tenant_deposit)}` : '미파악'}
              <span className="animate-pulse ml-1 text-danger-500">(+α)</span>
            </p>
          </div>
        ) : (
          <div>
            <span className="text-gray-500 text-xs">예상 인수금</span>
            <p className="font-semibold text-gray-400">없음 (안전)</p>
          </div>
        )}

        {a?.market_price && (
          <div>
            <span className="text-gray-500 text-xs">추정 시세</span>
            <p className="font-semibold text-gray-700">{formatWon(a.market_price)}</p>
          </div>
        )}

        {a?.market_price != null && (
          <div>
            <span className="text-gray-500 text-xs font-bold text-success-600">순 시세차익 (시세-입찰가-인수금)</span>
            <p className="font-bold text-success-600">
              {formatWon(Math.max(0, a.market_price - p.min_bid_price - (a.tenant_deposit || 0) - (a.acquisition_tax || 0)))}
            </p>
          </div>
        )}

        {p.area_m2 && (
          <div>
            <span className="text-gray-500 text-xs">면적</span>
            <p className="font-medium text-gray-700">{formatArea(p.area_m2)}</p>
          </div>
        )}
        {a?.acquisition_tax && (
          <div>
            <span className="text-gray-500 text-xs">취득세 추정</span>
            <p className="font-medium text-gray-600">{formatWon(a.acquisition_tax)}</p>
          </div>
        )}
        
        {/* 알파(+α) 한도액 가이드라인 표시 */}
        {!a?.is_safe && a?.market_price && p.min_bid_price && (
          <div className="col-span-2 bg-red-50 p-2.5 rounded-md mt-1 border border-red-100">
            <p className="text-danger-700 text-[11px] font-bold mb-0.5 flex items-center gap-1">
              ⚠️ 투자 손익분기 한도액 추산
            </p>
            <p className="text-danger-600 text-[12px] leading-tight">
              현재 확인된 인수금 <b>{formatWon(a.tenant_deposit || 0)}</b> 외에 추가로 발생할 수 있는 <b>불명확한 인수금(α)</b>이 
              <br/>
              <b>{formatWon(a.market_price - p.min_bid_price - (a.tenant_deposit || 0) - (a.acquisition_tax || 0))} 이내</b>여야만 시세 대비 수익성(본전 이상)이 있습니다.
            </p>
          </div>
        )}
        {p.bid_end_dt && (
          <div className={!a?.is_safe ? "col-span-2 mt-1" : ""}>
            <span className="text-gray-500 text-xs flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              입찰 마감
            </span>
            <p className="font-medium text-gray-700">{formatDate(p.bid_end_dt)}</p>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <Link
          to={`/properties/${p.id}`}
          className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center gap-1"
        >
          <Building2 className="w-3.5 h-3.5" />
          상세 보기
        </Link>
        <button
          onClick={(e) => {
            e.preventDefault()
            navigator.clipboard.writeText(p.notice_no)
            alert(`물건관리번호(${p.notice_no})가 복사되었습니다.\n새 탭으로 열리는 온비드 검색창에 붙여넣기(Ctrl+V)하여 검색하세요!`)
            window.open(`https://www.onbid.co.kr/op/com/unisrch/intgSrch.do?searchKeyword=${p.notice_no}`, '_blank')
          }}
          className="text-gray-500 hover:text-gray-700 text-xs flex items-center gap-1 cursor-pointer"
        >
          온비드로 이동 (번호 복사)
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
