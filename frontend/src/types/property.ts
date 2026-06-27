export interface MarketPrice {
  source: string
  price: number
  price_per_m2: number | null
  deal_date: string | null
}

export interface AnalysisResult {
  market_price: number | null
  gap_amount: number | null
  gap_pct: number | null
  acquisition_tax: number | null
  risk_keywords: string[]
  is_blind_land: boolean
  needs_farm_cert: boolean
  is_safe: boolean
  score: number | null
  tenant_deposit?: number
  analyzed_at: string | null
}

export interface Property {
  id: number
  notice_no: string
  address: string
  sido: string | null
  sigungu: string | null
  property_type: string
  land_category: string | null
  area_m2: number | null
  appraisal_value: number | null
  min_bid_price: number
  fail_count: number
  bid_start_dt: string | null
  bid_end_dt: string | null
  description: string | null
  notice_url: string | null
  image_url: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  analysis: AnalysisResult | null
  market_prices: MarketPrice[]
  is_favorite?: boolean
  is_read?: boolean
}

export interface PropertyListResponse {
  total: number
  page: number
  page_size: number
  items: Property[]
}

export interface SummaryResponse {
  total_properties: number
  safe_properties: number
  avg_gap_pct: number
  top_gap_pct: number
  avg_score: number
  last_synced_at: string | null
  type_distribution: Record<string, number>
  sido_distribution: Record<string, number>
}

export interface TopResponse {
  count: number
  items: Property[]
}

export interface GapDistribution {
  label: string
  count: number
}

export interface FilterState {
  sido: string
  property_type: string
  min_price: string
  max_price: string
  safe_only: boolean
  min_gap_pct: string
  min_fail_count: string
}
