import { TOSS_DEEP_LINK } from '@/lib/deeplink'

export default function PaymentSuccessPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl p-8 space-y-5">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-red-600">서비스 종료</p>
          <h1 className="text-3xl font-bold text-gray-900">웹 서비스는 종료되었습니다</h1>
          <p className="text-gray-600">
            이제 Toss 앱에서 미니앱으로 이용해주세요.
          </p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm text-gray-700">아래 버튼을 눌러 Toss로 이동할 수 있습니다.</p>
          <a
            href={TOSS_DEEP_LINK}
            className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-white font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all"
          >
            Toss에서 열기
          </a>
          <p className="mt-3 text-xs text-gray-500 break-all">딥링크: {TOSS_DEEP_LINK}</p>
        </div>

        <p className="text-xs text-gray-500">
          자동으로 열리지 않으면, Toss 앱 설치 여부를 확인 후 다시 시도해주세요.
        </p>
      </div>
    </main>
  )
}
