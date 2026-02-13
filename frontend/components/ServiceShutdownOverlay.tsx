'use client'

import { useEffect, useState } from 'react'
import { openDeepLink, TOSS_DEEP_LINK, TOSS_INSTALL_URL } from '@/lib/deeplink'

const AUTO_OPEN_DELAY_MS = 1600
const COUNTDOWN_START = Math.ceil(AUTO_OPEN_DELAY_MS / 1000)

export default function ServiceShutdownOverlay() {
  const [secondsLeft, setSecondsLeft] = useState(COUNTDOWN_START)
  const [copied, setCopied] = useState(false)
  const [autoTried, setAutoTried] = useState(false)

  useEffect(() => {
    const openTimer = window.setTimeout(() => {
      openDeepLink(TOSS_DEEP_LINK)
      setAutoTried(true)
    }, AUTO_OPEN_DELAY_MS)

    const countdownTimer = window.setInterval(() => {
      setSecondsLeft((s) => (s > 0 ? s - 1 : 0))
    }, 1000)

    return () => {
      window.clearTimeout(openTimer)
      window.clearInterval(countdownTimer)
    }
  }, [])

  const handleOpen = () => {
    openDeepLink(TOSS_DEEP_LINK)
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(TOSS_DEEP_LINK)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  const progressPercent = Math.max(
    0,
    Math.min(100, ((COUNTDOWN_START - secondsLeft) / Math.max(COUNTDOWN_START, 1)) * 100)
  )

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/85 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="서비스 종료 안내"
    >
      <div className="relative w-full max-w-xl overflow-hidden rounded-3xl border border-white/20 bg-gradient-to-br from-slate-900 via-[#0d1f3b] to-[#102b52] text-white shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
        <div className="pointer-events-none absolute -left-20 -top-16 h-56 w-56 rounded-full bg-cyan-300/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />

        <div className="relative px-7 py-7">
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-rose-200/50 bg-rose-100/90 px-3 py-1 text-xs font-bold tracking-wide text-rose-700">
              WEB 종료
            </span>
            <span className="rounded-full border border-cyan-200/40 bg-cyan-100/90 px-3 py-1 text-xs font-bold tracking-wide text-cyan-800">
              Apps in Toss 전환
            </span>
          </div>

          <h1 className="text-3xl font-black leading-tight tracking-tight">
            Toss 미니앱으로
            <br />
            자동 이동합니다
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-blue-100">
            웹 버전은 더 이상 운영하지 않습니다. PDF 맞춤법 검사는 Apps in Toss
            <span className="mx-1 rounded bg-white/15 px-1 py-0.5 font-semibold text-white">
              pdfgrammercheckorean
            </span>
            미니앱에서 이용해 주세요.
          </p>
        </div>

        <div className="relative border-t border-white/15 bg-white/95 px-7 py-6 text-slate-800">
          <p className="text-sm font-semibold text-slate-900">앱으로 열기</p>
          <p className="mt-1 text-sm text-slate-600">
            자동으로 열리지 않으면 버튼으로 다시 시도해 주세요.
          </p>

          <div className="mt-3 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {secondsLeft > 0
              ? `${secondsLeft}초 후 자동 이동을 시도합니다`
              : autoTried
                ? '자동 이동을 시도했습니다'
                : '자동 이동 준비 중'}
          </p>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={handleOpen}
              className="rounded-xl bg-gradient-to-r from-sky-600 to-blue-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-blue-600/25 transition hover:from-sky-700 hover:to-blue-800"
            >
              앱인토스로 열기
            </button>
            <a
              href={TOSS_INSTALL_URL}
              target="_blank"
              rel="noreferrer"
              className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-center text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Toss 앱 설치
            </a>
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Deep Link</p>
            <p className="mt-1 break-all font-mono text-xs text-slate-700">{TOSS_DEEP_LINK}</p>
            <button
              type="button"
              onClick={handleCopy}
              className="mt-2 inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              {copied ? '복사 완료' : '딥링크 복사'}
            </button>
          </div>

          <p className="mt-4 text-[11px] text-slate-500">
            앱이 설치되어 있지 않거나 딥링크 차단 환경에서는 설치 후 다시 열어주세요.
          </p>
        </div>
      </div>
    </div>
  )
}
