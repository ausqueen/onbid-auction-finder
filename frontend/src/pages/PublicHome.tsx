import { Link } from 'react-router-dom'

/**
 * 비로그인 방문자가 `/`에서 보는 공개 화면.
 *
 * 이전에는 `/`가 PrivateRoute였던 탓에 비로그인 방문자와 검색엔진 크롤러가
 * 곧바로 /login으로 튕겼고, 그 결과 애드센스 심사에서 "가치가 별로 없는 콘텐츠"로
 * 반려됐다(2026-08-06). 이 컴포넌트는 로그인 없이도 서비스가 무엇인지 보이게 한다.
 *
 * 서비스 설명 본문은 index.html의 <main class="site-intro">에 정적 HTML로 두었다.
 * 자바스크립트를 실행하지 않는 크롤러도 읽을 수 있어야 하기 때문이다.
 * 여기서는 첫 화면(히어로)과 진입 버튼만 담당한다.
 */
export default function PublicHome() {
  return (
    <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-white">
      <div className="mx-auto max-w-4xl px-5 py-16 sm:py-24">
        <p className="mb-3 text-sm font-medium text-indigo-300">
          온비드 공매 · 대법원 파산 공매
        </p>
        <h1 className="mb-5 text-3xl font-bold leading-snug sm:text-4xl">
          공매 공고와 주변 시세를
          <br />
          한 화면에서 비교하세요
        </h1>
        <p className="mb-9 max-w-2xl text-base leading-relaxed text-slate-300">
          공고에 적힌 감정가와 최저입찰가만으로는 지금 그 가격이 살 만한지 알기 어렵습니다.
          온비드·대법원 공고를 수집해 유찰 이력과 국토교통부 실거래가를 나란히 놓았습니다.
        </p>

        <div className="flex flex-wrap gap-3">
          <Link
            to="/login"
            className="rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:from-indigo-600 hover:to-purple-700"
          >
            파산공매 물건 검색
          </Link>
          <Link
            to="/register"
            className="rounded-xl border border-slate-600 px-6 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
          >
            회원가입
          </Link>
          <a
            href="#service-intro"
            className="rounded-xl border border-slate-700 px-6 py-3 text-sm font-semibold text-slate-300 transition hover:bg-white/5"
          >
            서비스 알아보기
          </a>
        </div>

        <p className="mt-8 text-xs text-slate-400">
          공매·경매의 차이와 입찰 전 확인사항은 로그인 없이 아래에서 보실 수 있습니다.
        </p>
      </div>
    </div>
  )
}
