import { useState } from 'react'
import axios from 'axios'
import { CheckCircle, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

const api = axios.create({ baseURL: '/api', timeout: 20000 })

type Status = 'idle' | 'loading' | 'success' | 'error'

interface TestResult {
  status: Status
  data: unknown
  elapsed?: number
}

const TESTS = [
  {
    id: 'config',
    label: '⚙️ 환경변수 / API 키 확인',
    desc: '.env 설정 및 API 키 마스킹 출력',
    fn: () => api.get('/test/config'),
  },
  {
    id: 'onbid',
    label: '🏠 온비드 API 연결 테스트',
    desc: '온비드 공매물건 목록 API 실제 호출 (5건)',
    fn: () => api.get('/test/onbid'),
  },
  {
    id: 'molit',
    label: '📊 국토부 실거래가 API 테스트',
    desc: '서울 아파트 최근 거래 데이터 조회 (5건)',
    fn: () => api.get('/test/molit'),
  },
  {
    id: 'mock',
    label: '🔬 분석 파이프라인 테스트 (목업)',
    desc: '목업 5개 물건으로 Gap%·위험도·점수 계산',
    fn: () => api.get('/test/mock-sync'),
  },
  {
    id: 'pipeline',
    label: '🚀 전체 파이프라인 (DB 동기화)',
    desc: '온비드 수집 → 시세 분석 → DB 저장 → TOP 5 반환',
    fn: () => api.get('/test/full-pipeline'),
  },
]

export default function TestPage() {
  const [results, setResults] = useState<Record<string, TestResult>>({})
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const run = async (id: string, fn: () => Promise<unknown>) => {
    setResults(r => ({ ...r, [id]: { status: 'loading', data: null } }))
    const t0 = Date.now()
    try {
      const res = await fn() as { data: unknown }
      setResults(r => ({
        ...r,
        [id]: { status: 'success', data: res.data, elapsed: Date.now() - t0 },
      }))
      setExpanded(e => ({ ...e, [id]: true }))
    } catch (e: unknown) {
      const err = e as { response?: { data: unknown }; message?: string }
      setResults(r => ({
        ...r,
        [id]: {
          status: 'error',
          data: err.response?.data ?? err.message ?? '알 수 없는 오류',
          elapsed: Date.now() - t0,
        },
      }))
      setExpanded(e => ({ ...e, [id]: true }))
    }
  }

  const runAll = async () => {
    for (const t of TESTS) {
      await run(t.id, t.fn)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          <div>
            <h1 className="text-base font-bold text-gray-900">🧪 API 테스트 페이지</h1>
            <p className="text-xs text-gray-400">온비드 공매 추천 서비스</p>
          </div>
          <div className="flex gap-2">
            <a href="/" className="btn-secondary text-xs">← 대시보드</a>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-xs"
            >
              Swagger UI ↗
            </a>
            <button onClick={runAll} className="btn-primary text-xs">
              전체 테스트 실행
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-3">
        {/* 연결 정보 */}
        <div className="card p-4 bg-blue-50 border-blue-200">
          <p className="text-xs font-semibold text-blue-800 mb-2">연결 정보</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-blue-700">
            <div>🔵 백엔드: <code className="bg-blue-100 px-1 rounded">http://localhost:8000</code></div>
            <div>🟢 프론트: <code className="bg-blue-100 px-1 rounded">http://localhost:5173</code></div>
            <div>📖 Swagger: <code className="bg-blue-100 px-1 rounded">http://localhost:8000/docs</code></div>
            <div>🗄️ DB: <code className="bg-blue-100 px-1 rounded">SQLite (onbid.db)</code></div>
          </div>
        </div>

        {/* 테스트 카드 */}
        {TESTS.map(t => {
          const result = results[t.id]
          const isExpanded = expanded[t.id]

          return (
            <div key={t.id} className="card overflow-hidden">
              <div className="p-4 flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusIcon status={result?.status ?? 'idle'} />
                    <span className="font-medium text-sm text-gray-900">{t.label}</span>
                    {result?.elapsed != null && (
                      <span className="text-xs text-gray-400">{result.elapsed}ms</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 ml-6">{t.desc}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => run(t.id, t.fn)}
                    disabled={result?.status === 'loading'}
                    className="btn-primary text-xs py-1.5 px-3 disabled:opacity-50"
                  >
                    {result?.status === 'loading' ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : '실행'}
                  </button>
                  {result?.data != null && (
                    <button
                      onClick={() => setExpanded(e => ({ ...e, [t.id]: !e[t.id] }))}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      {isExpanded
                        ? <ChevronUp className="w-4 h-4" />
                        : <ChevronDown className="w-4 h-4" />}
                    </button>
                  )}
                </div>
              </div>

              {isExpanded && result?.data != null && (
                <div className={`border-t px-4 py-3 ${result.status === 'error' ? 'bg-red-50 border-red-100' : 'bg-gray-50 border-gray-100'}`}>
                  <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )
        })}

        {/* API 엔드포인트 목록 */}
        <div className="card p-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">📋 전체 API 엔드포인트</p>
          <div className="space-y-1">
            {[
              ['GET', '/api/test/config', '환경변수 확인'],
              ['GET', '/api/test/onbid', '온비드 API 테스트'],
              ['GET', '/api/test/molit', '국토부 API 테스트'],
              ['GET', '/api/test/mock-sync', '목업 분석 파이프라인'],
              ['GET', '/api/test/full-pipeline', '전체 DB 동기화'],
              ['GET', '/api/properties', '물건 목록 (필터)'],
              ['GET', '/api/properties/{id}', '물건 상세'],
              ['GET', '/api/analysis/top', 'TOP 추천'],
              ['GET', '/api/analysis/summary', '통계 요약'],
              ['GET', '/api/analysis/gap-distribution', 'Gap% 분포'],
              ['POST', '/api/sync', '수동 동기화'],
              ['GET', '/api/sync/status', '동기화 상태'],
            ].map(([method, path, desc]) => (
              <div key={path} className="flex items-center gap-2 text-xs">
                <span className={`font-mono font-bold w-10 ${method === 'POST' ? 'text-orange-600' : 'text-blue-600'}`}>
                  {method}
                </span>
                <code className="text-gray-600 font-mono flex-1">{path}</code>
                <span className="text-gray-400">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusIcon({ status }: { status: Status }) {
  if (status === 'loading') return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
  if (status === 'success') return <CheckCircle className="w-4 h-4 text-green-500" />
  if (status === 'error') return <XCircle className="w-4 h-4 text-red-500" />
  return <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
}
