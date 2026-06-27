import { useEffect, useState, useRef } from 'react'
import { Map, MapMarker, useKakaoLoader } from 'react-kakao-maps-sdk'
import { MapPin } from 'lucide-react'

// 1. 네이버 지도 렌더링 컴포넌트
function NaverMapContainer({ coords }: { coords: { lat: number; lng: number } }) {
  const mapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mapRef.current) return

    const naver = (window as any).naver
    if (!naver || !naver.maps) return

    const centerCoords = new naver.maps.LatLng(coords.lat, coords.lng)
    const mapOptions = {
      center: centerCoords,
      zoom: 16,
      minZoom: 10,
      zoomControl: true,
      zoomControlOptions: {
        position: naver.maps.Position.TOP_RIGHT
      }
    }

    const map = new naver.maps.Map(mapRef.current, mapOptions)
    new naver.maps.Marker({
      position: centerCoords,
      map: map,
    })
  }, [coords])

  return (
    <div className="w-full h-40 rounded-lg overflow-hidden border border-gray-200 shadow-sm relative">
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}

// 2. 카카오 지도 렌더링 컴포넌트
function KakaoMapContainer({ coords }: { coords: { lat: number; lng: number } }) {
  return (
    <div className="w-full h-40 rounded-lg overflow-hidden border border-gray-200 shadow-sm relative">
      <Map center={coords} style={{ width: '100%', height: '100%' }} level={3}>
        <MapMarker position={coords} />
      </Map>
    </div>
  )
}

// 3. 지도를 실제로 그리는 자식 컴포넌트 (Naver/Kakao Geocoder 활용)
interface AddressMapContentProps {
  address: string
  kakaoKey: string
  naverKey: string
  naverScriptLoaded: boolean
}

function AddressMapContent({ address, kakaoKey, naverKey, naverScriptLoaded }: AddressMapContentProps) {
  const [kakaoLoading, kakaoError] = useKakaoLoader({
    appkey: kakaoKey,
    libraries: ["services"]
  })

  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!address) return

    let isMounted = true
    setLoading(true)
    setError(null)

    // 1. 네이버 지오코더 사용 시도
    const tryNaverGeocode = () => {
      const naver = (window as any).naver
      if (naver && naver.maps && naver.maps.Service && naver.maps.Service.geocode) {
        try {
          naver.maps.Service.geocode({ query: address }, (status: any, response: any) => {
            if (!isMounted) return
            if (status === naver.maps.Service.Status.OK && response.v2.addresses.length > 0) {
              const item = response.v2.addresses[0]
              setCoords({
                lat: Number(item.y),
                lng: Number(item.x)
              })
              setLoading(false)
            } else {
              tryKakaoGeocode()
            }
          })
          return true
        } catch (err) {
          console.error("Naver geocode error:", err)
        }
      }
      return false
    }

    // 2. 카카오 지오코더 폴백
    const tryKakaoGeocode = () => {
      try {
        const kakao = (window as any).kakao
        if (kakao && kakao.maps && kakao.maps.services && kakao.maps.services.Geocoder) {
          const geocoder = new kakao.maps.services.Geocoder()
          geocoder.addressSearch(address, (result: any, status: any) => {
            if (!isMounted) return
            if (status === kakao.maps.services.Status.OK && result.length > 0) {
              setCoords({
                lat: Number(result[0].y),
                lng: Number(result[0].x)
              })
              setLoading(false)
            } else {
              const places = new kakao.maps.services.Places()
              places.keywordSearch(address, (res: any, stat: any) => {
                if (!isMounted) return
                if (stat === kakao.maps.services.Status.OK && res.length > 0) {
                  setCoords({
                    lat: Number(res[0].y),
                    lng: Number(res[0].x)
                  })
                  setLoading(false)
                } else {
                  setError('주소 위치를 찾을 수 없습니다.')
                  setLoading(false)
                }
              })
            }
          })
        } else {
          setError('지도 라이브러리가 로드되지 않았습니다.')
          setLoading(false)
        }
      } catch (err: any) {
        setError(err.message || '지도 서비스 초기화 실패')
        setLoading(false)
      }
    }

    // 네이버 스크립트가 로드되어 있으면 네이버 우선 사용
    if (naverScriptLoaded) {
      if (tryNaverGeocode()) return
    }

    // 카카오 로딩이 완료된 상태면 카카오 사용
    if (!kakaoLoading && !kakaoError) {
      tryKakaoGeocode()
    } else if (kakaoError) {
      // 카카오 에러 시 네이버 재시도 (혹시 위에서 준비 안됐을 때를 위해)
      if (!tryNaverGeocode()) {
        setError('지도 라이브러리를 사용할 수 없습니다.')
        setLoading(false)
      }
    }

    return () => {
      isMounted = false
    }
  }, [address, naverScriptLoaded, kakaoLoading, kakaoError])

  if (loading || (!coords && !error)) {
    return (
      <div className="w-full h-40 mt-2 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-center text-sm text-gray-500">
        지도 정보를 불러오는 중...
      </div>
    )
  }

  if (error && !coords) {
    return (
      <div className="w-full h-40 mt-2 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-center text-sm text-red-500 font-medium p-4">
        {error}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 w-full mt-2">
      {/* 1. 네이버맵 크게보기 */}
      <div className="flex justify-end">
        <a
          href={`https://map.naver.com/v5/search/${encodeURIComponent(address)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#03C75A] hover:bg-[#02B34F] text-white text-xs font-bold rounded-md transition-colors shadow-sm border border-[#02B34F]"
        >
          <MapPin className="w-3.5 h-3.5" />
          네이버맵 크게보기
        </a>
      </div>

      {/* 2. 네이버요약맵 */}
      {coords && <NaverMapContainer coords={coords} />}

      {/* 3. 카카오맵 크게보기 */}
      <div className="flex justify-end">
        <a
          href={`https://map.kakao.com/link/search/${encodeURIComponent(address)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#FEE500] hover:bg-[#F4DC00] text-[#391B1B] text-xs font-bold rounded-md transition-colors shadow-sm border border-[#F4DC00]"
        >
          <MapPin className="w-3.5 h-3.5" />
          카카오맵 크게보기
        </a>
      </div>

      {/* 4. 카카오요약맵 또는 에러 표시 */}
      {kakaoError ? (
        <div className="w-full h-40 bg-red-50 border border-red-200 rounded-lg flex flex-col items-center justify-center text-xs text-red-600 font-medium text-center p-3">
          <span>카카오맵 로드 실패 (API 키 또는 플랫폼 도메인 등록 확인 필요)</span>
          <span className="text-[10px] mt-1 font-mono text-red-500">
            {kakaoError instanceof Error ? kakaoError.message : String(kakaoError)}
          </span>
        </div>
      ) : (
        coords && <KakaoMapContainer coords={coords} />
      )}
    </div>
  )
}

// 4. 외부에서 로드하는 메인 래퍼 컴포넌트
export default function AddressMap({ address }: { address: string }) {
  const [kakaoKey, setKakaoKey] = useState<string | null>(null)
  const [naverKey, setNaverKey] = useState<string | null>(null)
  const [keyError, setKeyError] = useState<string | null>(null)
  const [naverScriptLoaded, setNaverScriptLoaded] = useState(false)

  useEffect(() => {
    // 백엔드로부터 카카오 및 네이버 API 키 조회
    Promise.all([
      fetch('/api/config/kakao').then(res => res.json()),
      fetch('/api/config/naver').then(res => res.json())
    ])
      .then(([kakaoData, naverData]) => {
        if (kakaoData.kakao_js_api_key && naverData.naver_client_id) {
          setKakaoKey(kakaoData.kakao_js_api_key)
          setNaverKey(naverData.naver_client_id)
        } else {
          setKeyError('지도 API 키가 올바르게 설정되어 있지 않습니다. backend/.env 설정을 확인해 주세요.')
        }
      })
      .catch((err) => {
        console.error(err)
        setKeyError('API 키 정보를 가져오는 도중 오류가 발생했습니다.')
      })
  }, [])

  useEffect(() => {
    if (!naverKey) return

    const scriptId = 'naver-maps-script'
    if ((window as any).naver && (window as any).naver.maps) {
      setNaverScriptLoaded(true)
      return
    }

    let script = document.getElementById(scriptId) as HTMLScriptElement
    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.type = 'text/javascript'
      script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${naverKey}&submodules=geocoder`
      document.head.appendChild(script)
    }

    const handleLoad = () => setNaverScriptLoaded(true)
    script.addEventListener('load', handleLoad)

    return () => {
      script.removeEventListener('load', handleLoad)
    }
  }, [naverKey])

  if (keyError) {
    return (
      <div className="w-full h-auto mt-2 bg-yellow-50 border border-yellow-200 rounded-lg flex flex-col items-center justify-center text-sm text-yellow-700 font-medium text-center p-4">
        <span>지도 설정 필요</span>
        <span className="text-xs mt-1 font-normal text-yellow-600">{keyError}</span>
      </div>
    )
  }

  if (!kakaoKey || !naverKey || !naverScriptLoaded) {
    return (
      <div className="w-full h-40 mt-2 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-center text-sm text-gray-400">
        지도 모듈 초기화 중...
      </div>
    )
  }

  return (
    <AddressMapContent
      address={address}
      kakaoKey={kakaoKey}
      naverKey={naverKey}
      naverScriptLoaded={naverScriptLoaded}
    />
  )
}
