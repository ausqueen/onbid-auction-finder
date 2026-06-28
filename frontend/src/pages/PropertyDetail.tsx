import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, AlertTriangle, CheckCircle, Leaf, MapPin, TrendingUp, Heart } from 'lucide-react'
import { fetchProperty, formatWon, formatArea, formatDate } from '../api/client'
import GapBadge from '../components/GapBadge'
import type { Property } from '../types/property'
import { useAuth } from '../contexts/AuthContext'

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const { token } = useAuth()
  const [isFav, setIsFav] = useState(false)

  const { data: property, isLoading, isError } = useQuery<Property>({
    queryKey: ['property', id],
    queryFn: () => fetchProperty(Number(id)),
    enabled: !!id,
  })

  useEffect(() => {
    if (property) {
      setIsFav(!!property.is_favorite)
    }
  }, [property])

  const handleFavoriteToggle = async () => {
    if (!token || !property) return
    try {
      const url = `/api/users/me/favorites/properties/${property.id}`
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (isError || !property) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">물건을 불러올 수 없습니다</p>
          <Link to="/onbid" className="btn-primary">대시보드로 돌아가기</Link>
        </div>
      </div>
    )
  }

  const a = property.analysis

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <Link to="/onbid" className="text-gray-500 hover:text-gray-700 shrink-0">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-base font-semibold text-gray-900 truncate">{property.address}</h1>
          </div>

          <button
            onClick={handleFavoriteToggle}
            className="p-2 hover:bg-gray-100 rounded-full transition transform hover:scale-110 shrink-0"
            title={isFav ? '관심 해제' : '관심 등록'}
          >
            <Heart className={`w-5 h-5 ${isFav ? 'text-red-500 fill-red-500' : 'text-gray-400'}`} />
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 왼쪽: 물건 정보 */}
          <div className="md:col-span-2 space-y-4">
            {/* 기본 정보 */}
            <div className="card p-5">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {property.property_type}
                    </span>
                    {property.fail_count > 0 && (
                      <span className="text-sm bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        {property.fail_count}회 유찰
                      </span>
                    )}
                  </div>
                  <h2 className="text-lg font-bold text-gray-900 flex items-center gap-1">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    {property.address}
                  </h2>
                  <p className="text-xs text-gray-400 mt-0.5">공고번호: {property.notice_no}</p>
                </div>
                {a?.gap_pct != null && a.gap_pct > 0 && (
                  <GapBadge gapPct={a.gap_pct} size="lg" />
                )}
              </div>

              <dl className="grid grid-cols-2 gap-4">
                <InfoItem label="최저입찰가" value={formatWon(property.min_bid_price)} emphasis />
                <InfoItem label="감정평가액" value={formatWon(property.appraisal_value)} />
                <InfoItem label="면적" value={formatArea(property.area_m2)} />
                {property.land_category && (
                  <InfoItem label="지목" value={property.land_category} />
                )}
                <InfoItem label="입찰 시작" value={formatDate(property.bid_start_dt)} />
                <InfoItem label="입찰 마감" value={formatDate(property.bid_end_dt)} />
              </dl>
            </div>

            {/* 분석 결과 */}
            {a && (
              <div className="card p-5">
                <h3 className="font-semibold text-gray-900 mb-4">가격 분석</h3>
                <dl className="grid grid-cols-2 gap-4 mb-4">
                  <InfoItem label="추정 시세" value={formatWon(a.market_price)} />
                  <InfoItem
                    label="시세차익(Gap)"
                    value={a.gap_amount != null && a.gap_amount > 0 ? formatWon(a.gap_amount) : '-'}
                    positive
                  />
                  <InfoItem label="Gap%" value={a.gap_pct != null ? `${a.gap_pct.toFixed(1)}%` : '-'} positive />
                  <InfoItem label="취득세 추정" value={formatWon(a.acquisition_tax)} />
                  <InfoItem
                    label="종합 점수"
                    value={a.score != null ? `${a.score.toFixed(1)}점` : '-'}
                  />
                </dl>

                {a.market_price != null && property.min_bid_price != null && (
                  <ProfitCalculator
                    minBidPrice={property.min_bid_price}
                    marketPrice={a.market_price}
                    acquisitionTax={a.acquisition_tax ?? 0}
                    tenantDeposit={a.tenant_deposit ?? 0}
                    isSafe={a.is_safe}
                  />
                )}
              </div>
            )}

            {/* 물건 설명 */}
            {property.description && (
              <div className="card p-5">
                <h3 className="font-semibold text-gray-900 mb-3">공고 내용</h3>
                <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
                  {property.description}
                </p>
              </div>
            )}
          </div>

          {/* 오른쪽: 위험 분석 + 링크 */}
          <div className="space-y-4">
            {/* 위험 분석 */}
            {a && (
              <div className="card p-4">
                <h3 className="font-semibold text-gray-900 mb-3">권리 분석</h3>

                <RiskItem
                  ok={a.is_safe}
                  okLabel="안전 물건"
                  failLabel="위험 물건"
                  icon={a.is_safe
                    ? <CheckCircle className="w-4 h-4 text-success-500" />
                    : <AlertTriangle className="w-4 h-4 text-danger-500" />
                  }
                />

                {a.risk_keywords.length > 0 && (
                  <div className="mt-2 p-2 bg-red-50 rounded-lg">
                    <p className="text-xs font-medium text-red-700 mb-1">감지된 위험 키워드</p>
                    <div className="flex flex-wrap gap-1">
                      {a.risk_keywords.map(kw => (
                        <span key={kw} className="badge bg-red-100 text-red-700">{kw}</span>
                      ))}
                    </div>
                  </div>
                )}

                {a.is_blind_land && (
                  <div className="mt-2 flex items-center gap-2 p-2 bg-orange-50 rounded-lg">
                    <MapPin className="w-4 h-4 text-orange-500" />
                    <span className="text-sm text-orange-700">맹지 의심 (진입로 없음)</span>
                  </div>
                )}

                {a.needs_farm_cert && (
                  <div className="mt-2 flex items-center gap-2 p-2 bg-yellow-50 rounded-lg">
                    <Leaf className="w-4 h-4 text-yellow-600" />
                    <div>
                      <p className="text-sm text-yellow-700 font-medium">농취증 필요</p>
                      <p className="text-xs text-yellow-600">농지취득자격증명 제출 필수</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="card p-4">
              <h3 className="font-semibold text-gray-900 mb-3">바로가기</h3>
              <button
                onClick={(e) => {
                  e.preventDefault()
                  navigator.clipboard.writeText(property.notice_no)
                  alert(`물건관리번호(${property.notice_no})가 복사되었습니다.\n새 탭으로 열리는 온비드 검색창에 붙여넣기(Ctrl+V)하여 검색하세요!`)
                  window.open(`https://www.onbid.co.kr/op/com/unisrch/intgSrch.do?searchKeyword=${property.notice_no}`, '_blank')
                }}
                className="w-full flex items-center justify-between p-3 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors cursor-pointer text-left"
              >
                <span className="text-sm font-medium text-primary-700">차세대 온비드 공고 검색하기 (번호 복사)</span>
                <ExternalLink className="w-4 h-4 text-primary-500" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoItem({
  label, value, emphasis, positive,
}: { label: string; value: string; emphasis?: boolean; positive?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 mb-0.5">{label}</dt>
      <dd className={`text-sm font-semibold ${emphasis ? 'text-gray-900 text-base' : positive ? 'text-success-600' : 'text-gray-700'}`}>
        {value}
      </dd>
    </div>
  )
}

function RiskItem({
  ok, okLabel, failLabel, icon,
}: { ok: boolean; okLabel: string; failLabel: string; icon: React.ReactNode }) {
  return (
    <div className={`flex items-center gap-2 p-2 rounded-lg ${ok ? 'bg-green-50' : 'bg-red-50'}`}>
      {icon}
      <span className={`text-sm font-medium ${ok ? 'text-success-700' : 'text-danger-700'}`}>
        {ok ? okLabel : failLabel}
      </span>
    </div>
  )
}

function ProfitCalculator({
  minBidPrice,
  marketPrice,
  acquisitionTax,
  tenantDeposit,
  isSafe,
}: {
  minBidPrice: number
  marketPrice: number
  acquisitionTax: number
  tenantDeposit: number
  isSafe: boolean
}) {
  // 부대비용: 등록세(낙찰가의 0.2%) + 법무사비용(50만 고정) + 인지세/잡비(낙찰가의 0.3%)
  const registrationTax = Math.round(minBidPrice * 0.002)
  const legalFee = 500_000
  const miscFee = Math.round(minBidPrice * 0.003)
  const additionalCosts = registrationTax + legalFee + miscFee

  const totalInvestment = minBidPrice + tenantDeposit + acquisitionTax + additionalCosts
  const netProfit = marketPrice - totalInvestment
  const roiPct = totalInvestment > 0 ? (netProfit / totalInvestment) * 100 : 0

  const [open, setOpen] = useState(false)

  const isProfit = netProfit > 0

  return (
    <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary-600" />
          <span className="text-sm font-semibold text-gray-800">투자 수익 상세 분석</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold ${isProfit ? 'text-success-600' : 'text-danger-600'}`}>
            {isProfit ? '+' : ''}{formatWon(netProfit)} ({roiPct.toFixed(1)}%)
          </span>
          <span className="text-xs text-gray-400">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div className="p-4 bg-white space-y-1 text-sm">
          {/* 투자금 항목 */}
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">총 투자금 구성</p>

          <CostRow label="낙찰가(최저입찰가 기준)" value={minBidPrice} />
          {tenantDeposit > 0 && (
            <CostRow label="인수 보증금 (임차인)" value={tenantDeposit} highlight />
          )}
          {!isSafe && tenantDeposit === 0 && (
            <div className="flex justify-between py-1 px-2 bg-red-50 rounded text-red-700">
              <span>인수 보증금 (미파악)</span>
              <span className="font-semibold animate-pulse">? 원</span>
            </div>
          )}
          <CostRow label="취득세" value={acquisitionTax} />
          <div className="border-t border-dashed border-gray-200 my-2" />
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">부대비용</p>
          <CostRow label="등록세 (낙찰가×0.2%)" value={registrationTax} indent />
          <CostRow label="법무사비용 (고정)" value={legalFee} indent />
          <CostRow label="인지세/잡비 (낙찰가×0.3%)" value={miscFee} indent />

          <div className="border-t border-gray-300 my-2" />
          <div className="flex justify-between py-1 font-bold text-gray-900">
            <span>총 투자금{!isSafe && tenantDeposit === 0 ? ' (+α)' : ''}</span>
            <span>{formatWon(totalInvestment)}{!isSafe && tenantDeposit === 0 ? ' +α' : ''}</span>
          </div>

          {/* 수익 계산 */}
          <div className="mt-3 border-t border-gray-200 pt-3 space-y-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">수익 분석</p>
            <CostRow label="추정 시세" value={marketPrice} />
            <div className="flex justify-between py-1 text-gray-600">
              <span>(-) 총 투자금</span>
              <span>- {formatWon(totalInvestment)}</span>
            </div>
            <div className={`flex justify-between py-2 px-3 rounded-lg font-bold text-base ${isProfit ? 'bg-green-50 text-success-700' : 'bg-red-50 text-danger-700'}`}>
              <span>예상 순수익</span>
              <span>{isProfit ? '+' : ''}{formatWon(netProfit)}</span>
            </div>
            <div className={`flex justify-between py-1 px-3 rounded text-sm font-semibold ${isProfit ? 'text-success-600' : 'text-danger-600'}`}>
              <span>투자 수익률(ROI)</span>
              <span>{roiPct.toFixed(2)}%</span>
            </div>
          </div>

          {!isSafe && (
            <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
              ⚠️ 위험 물건입니다. 인수금이 추가로 발생할 경우 수익이 감소하거나 손실이 발생할 수 있습니다.
              {tenantDeposit === 0 && (
                <> 손익분기 허용 추가인수금: <strong>{formatWon(Math.max(0, netProfit))}</strong> 이내</>
              )}
            </div>
          )}

          <p className="text-xs text-gray-400 mt-2">
            * 부대비용(등록세·법무사·잡비)은 간이 추정치입니다. 실제 비용과 차이가 있을 수 있습니다.
          </p>
        </div>
      )}
    </div>
  )
}

function CostRow({
  label, value, highlight, indent,
}: {
  label: string
  value: number
  highlight?: boolean
  indent?: boolean
}) {
  return (
    <div className={`flex justify-between py-0.5 ${indent ? 'pl-4 text-gray-500' : 'text-gray-700'} ${highlight ? 'font-semibold text-amber-700' : ''}`}>
      <span>{label}</span>
      <span>{formatWon(value)}</span>
    </div>
  )
}
