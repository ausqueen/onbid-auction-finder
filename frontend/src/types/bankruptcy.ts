export interface BankruptcyProperty {
  id: number
  title: string
  post_date: string | null
  court_name: string | null
  notice_url: string
  asset_type: string | null
  target_property: string | null
  address?: string
  min_price: string | null
  manager_contact: string | null
  sale_deadline: string | null
  ai_summary: string | null
  is_recommended?: boolean
  is_analyzed?: boolean
  // 상세 페이지 파싱 메타데이터
  selling_agency: string | null
  phone_number: string | null
  attachment_filename: string | null
  notice_expire_date: string | null
  created_at: string
  updated_at?: string | null
  is_favorite?: boolean
  is_read?: boolean
}
