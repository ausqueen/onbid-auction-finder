import { BankruptcyProperty } from '../types/bankruptcy'

const API_BASE = '/api'

function getHeaders(extraHeaders: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = { ...extraHeaders }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export async function fetchBankruptcyProperties(): Promise<BankruptcyProperty[]> {
  const res = await fetch(`${API_BASE}/bankruptcy/`, {
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to fetch bankruptcy properties')
  return res.json()
}

export async function syncBankruptcyProperties(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/bankruptcy/sync`, { 
    method: 'POST',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to trigger bankruptcy sync')
  return res.json()
}

export async function triggerFileSync(mode: 'quick' | 'full' = 'quick'): Promise<{ message: string; mode: string }> {
  const res = await fetch(`${API_BASE}/bankruptcy/file-sync?mode=${mode}`, {
    method: 'POST',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to trigger file sync')
  return res.json()
}

export async function triggerAnalyze(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/bankruptcy/analyze`, {
    method: 'POST',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to trigger AI analysis')
  return res.json()
}

export async function fetchProgress(): Promise<{
  phase: string | null
  collected: number
  analyzed: number
  total_in_db: number
  analyzed_in_db: number
  pending_analysis: number
  synced_files: number
  message: string
}> {
  const res = await fetch(`${API_BASE}/bankruptcy/progress`, {
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to fetch progress')
  return res.json()
}

export async function checkNewNotices(): Promise<{ has_new: boolean; new_count_in_page_1: number }> {
  const res = await fetch(`${API_BASE}/bankruptcy/check-new`, {
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to check new notices')
  return res.json()
}

