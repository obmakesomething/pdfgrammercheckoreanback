const TOSS_DEEP_LINK = 'intoss://pdfgrammercheckorean'

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#071226]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-20 top-16 h-80 w-80 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="absolute -right-20 bottom-10 h-96 w-96 rounded-full bg-blue-600/20 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-5xl items-center px-6 py-16">
        <div className="w-full rounded-3xl border border-white/15 bg-white/10 p-8 backdrop-blur-sm sm:p-12">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">
            SERVICE MIGRATION
          </p>
          <h1 className="mt-3 text-4xl font-black leading-tight text-white sm:text-5xl">
            PDF 맞춤법 검사는
            <br />
            이제 Apps in Toss 전용입니다
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-blue-100 sm:text-base">
            기존 웹 서비스는 종료되었고, 현재는 Toss 미니앱에서만 사용할 수 있습니다.
            화면 상단의 안내 모달이 자동으로 앱 이동을 시도합니다.
          </p>

          <a
            href={TOSS_DEEP_LINK}
            className="mt-8 inline-flex items-center justify-center rounded-2xl border border-cyan-300/30 bg-cyan-400/15 px-6 py-3 text-sm font-bold text-cyan-100 transition hover:bg-cyan-300/20"
          >
            수동으로 앱 열기
          </a>
        </div>
      </div>
    </main>
  )
}
