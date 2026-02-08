'use client'

import { useEffect, useState } from 'react'
import { openDeepLink, TOSS_DEEP_LINK } from '@/lib/deeplink'

export default function ServiceShutdownOverlay() {
  const [secondsLeft, setSecondsLeft] = useState(2)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    // Try to open the miniapp shortly after page load.
    const openTimer = window.setTimeout(() => {
      openDeepLink(TOSS_DEEP_LINK)
    }, 1200)

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
      // If clipboard is blocked, the link is still visible for manual copy.
      setCopied(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="서비스 종료 안내"
    >
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100">
          <p className="text-sm font-semibold text-red-600">서비스 종료</p>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">
            웹 서비스는 종료되었습니다
          </h1>
          <p className="mt-2 text-gray-600">
            이제 Toss 앱에서 미니앱으로 이용하실 수 있습니다.
          </p>
        </div>

        <div className="px-6 py-5 space-y-4">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm font-semibold text-gray-900">앱으로 이동</p>
            <p className="mt-1 text-sm text-gray-600">
              자동으로 열리지 않으면 아래 버튼을 눌러주세요.
            </p>
            <p className="mt-2 text-xs text-gray-500">
              {secondsLeft > 0 ? `${secondsLeft}초 후 자동 이동 시도` : '자동 이동을 시도했습니다'}
            </p>

            <div className="mt-4 flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={handleOpen}
                className="flex-1 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-white font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all"
              >
                Toss에서 열기
              </button>
              <button
                type="button"
                onClick={handleCopy}
                className="rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-800 font-semibold hover:bg-gray-50 transition-all"
              >
                {copied ? '복사됨' : '링크 복사'}
              </button>
            </div>

            <div className="mt-4 rounded-lg bg-white border border-gray-200 p-3">
              <p className="text-xs text-gray-500">딥링크</p>
              <p className="mt-1 text-sm font-mono text-gray-800 break-all">{TOSS_DEEP_LINK}</p>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            Toss 앱이 설치되어 있어야 합니다. 설치되어 있지 않다면 설치 후 다시 시도해주세요.
          </p>
        </div>
      </div>
    </div>
  )
}
