import axios from 'axios'
import type {
  PropertyListResponse,
  SummaryResponse,
  TopResponse,
  GapDistribution,
} from '../types/property'

const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

// JWT 토큰 주입 인터셉터
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})


// 숫자 포맷 헬퍼
export const formatWon = (n: number | null | undefined): string => {
  if (n == null) return '-'
  if (n >= 1_0000_0000) return `${(n / 1_0000_0000).toFixed(1)}억`
  if (n >= 1_0000) return `${Math.floor(n / 1_0000).toLocaleString()}만`
  return n.toLocaleString() + '원'
}

export const formatArea = (m2: number | null | undefined): string => {
  if (m2 == null) return '-'
  const py = m2 / 3.3058
  return `${m2.toFixed(1)}㎡ (${py.toFixed(1)}평)`
}

export const formatDate = (dt: string | null | undefined): string => {
  if (!dt) return '-'
  return new Date(dt).toLocaleDateString('ko-KR')
}

// API 함수들
export const fetchSummary = async (): Promise<SummaryResponse> => {
  const { data } = await api.get<SummaryResponse>('/analysis/summary')
  return data
}

export const fetchTopProperties = async (params?: {
  n?: number
  safe_only?: boolean
  sido?: string
  property_type?: string
}): Promise<TopResponse> => {
  const { data } = await api.get<TopResponse>('/analysis/top', { params })
  return data
}

export const fetchProperties = async (params: Record<string, unknown>): Promise<PropertyListResponse> => {
  // 빈 문자열 파라미터 제거
  const cleaned: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(params)) {
    if (v !== '' && v !== null && v !== undefined) cleaned[k] = v
  }
  const { data } = await api.get<PropertyListResponse>('/properties', { params: cleaned })
  return data
}

export const fetchProperty = async (id: number) => {
  const { data } = await api.get(`/properties/${id}`)
  return data
}

export const fetchRegions = async (): Promise<string[]> => {
  const { data } = await api.get<{ regions: string[] }>('/properties/regions/list')
  return data.regions
}

export const fetchPropertyTypes = async (): Promise<string[]> => {
  const { data } = await api.get<{ types: string[] }>('/properties/types/list')
  return data.types
}

export const fetchGapDistribution = async (): Promise<GapDistribution[]> => {
  const { data } = await api.get<{ distribution: GapDistribution[] }>('/analysis/gap-distribution')
  return data.distribution
}

export const triggerSync = async () => {
  const { data } = await api.post('/sync')
  return data
}

export const fetchSyncStatus = async () => {
  const { data } = await api.get('/sync/status')
  return data
}
