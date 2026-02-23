'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

function PaymentFailPageContent() {
  const searchParams = useSearchParams()

  const code = searchParams.get('code')
  const message = searchParams.get('message')
  const orderId = searchParams.get('orderId')

  const getErrorMessage = (code: string | null, message: string | null): string => {
    if (message) {
      return decodeURIComponent(message)
    }

    switch (code) {
      case 'PAY_PROCESS_CANCELED':
        return '결제가 취소되었습니다.'
      case 'PAY_PROCESS_ABORTED':
        return '결제가 중단되었습니다.'
      case 'REJECT_CARD_COMPANY':
        return '카드사에서 결제를 거절했습니다.'
      case 'INVALID_CARD_NUMBER':
        return '유효하지 않은 카드 번호입니다.'
      case 'EXCEED_MAX_DAILY_PAYMENT_COUNT':
        return '일일 최대 결제 횟수를 초과했습니다.'
      case 'EXCEED_MAX_PAYMENT_AMOUNT':
        return '최대 결제 금액을 초과했습니다.'
      case 'NOT_SUPPORTED_CARD_TYPE':
        return '지원하지 않는 카드 유형입니다.'
      default:
        return '결제 처리 중 오류가 발생했습니다.'
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-red-50 to-rose-100">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-6">
          <div className="text-6xl mb-4">😢</div>
          <h1 className="text-2xl font-bold text-gray-900">결제 실패</h1>
          <p className="text-gray-600 mt-2">{getErrorMessage(code, message)}</p>
        </div>

        {/* 오류 정보 */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">오류 정보</h2>
          <div className="space-y-2 text-sm">
            {code && (
              <div className="flex justify-between">
                <span className="text-gray-600">오류 코드</span>
                <span className="text-gray-900 font-mono text-xs">{code}</span>
              </div>
            )}
            {orderId && (
              <div className="flex justify-between">
                <span className="text-gray-600">주문번호</span>
                <span className="text-gray-900 font-mono text-xs">{orderId}</span>
              </div>
            )}
          </div>
        </div>

        {/* 안내 메시지 */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-yellow-800">
            결제가 완료되지 않았습니다. 결제 정보를 확인하신 후 다시 시도해주세요.
            문제가 계속되면 고객센터로 문의해주세요.
          </p>
        </div>

        {/* 버튼들 */}
        <div className="space-y-3">
          <Link
            href="/"
            className="block w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition text-center"
          >
            다시 시도하기
          </Link>
          <Link
            href="/"
            className="block w-full py-3 px-4 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition text-center"
          >
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    </main>
  )
}

function PaymentFailPageFallback() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-red-50 to-rose-100">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-rose-600 mx-auto mb-4"></div>
        <p className="text-gray-600">결제 상태를 확인하는 중...</p>
      </div>
    </main>
  )
}

export default function PaymentFailPage() {
  return (
    <Suspense fallback={<PaymentFailPageFallback />}>
      <PaymentFailPageContent />
    </Suspense>
  )
}
