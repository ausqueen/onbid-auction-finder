import { AlertTriangle, Leaf, MapPin } from 'lucide-react'
import type { AnalysisResult } from '../types/property'

interface RiskBadgeProps {
  analysis: AnalysisResult | null
}

export default function RiskBadge({ analysis }: RiskBadgeProps) {
  if (!analysis) return null

  const badges: JSX.Element[] = []

  if (!analysis.is_safe && analysis.risk_keywords.length > 0) {
    badges.push(
      <span key="risk" className="badge bg-red-100 text-red-700" title={analysis.risk_keywords.join(', ')}>
        <AlertTriangle className="w-3 h-3" />
        위험
      </span>
    )
  }

  if (analysis.is_blind_land) {
    badges.push(
      <span key="blind" className="badge bg-orange-100 text-orange-700">
        <MapPin className="w-3 h-3" />
        맹지
      </span>
    )
  }

  if (analysis.needs_farm_cert) {
    badges.push(
      <span key="farm" className="badge bg-yellow-100 text-yellow-700">
        <Leaf className="w-3 h-3" />
        농취증
      </span>
    )
  }

  if (badges.length === 0) {
    return (
      <span className="badge bg-green-100 text-green-700">
        안전
      </span>
    )
  }

  return <div className="flex flex-wrap gap-1">{badges}</div>
}
