'use client'

import { useEffect, useState } from 'react'

interface PriceInfo {
  char_count: number
  free_chars: number
  billable_chars: number
  price: number
  is_free: boolean
  breakdown: string
}

interface PaymentModalProps {
  isOpen: boolean
  onClose: () => void
  onPaymentSuccess: () => void
  charCount: number
  priceInfo: PriceInfo
  email: string
}

declare global {
  interface Window {
    TossPayments: any
  }
}

export default function PaymentModal({
  isOpen,
  onClose,
  onPaymentSuccess,
  charCount,
  priceInfo,
  email
}: PaymentModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tossReady, setTossReady] = useState(false)

  // 토스페이먼츠 SDK 로드
  useEffect(() => {
    if (typeof window !== 'undefined' && !window.TossPayments) {
      const script = document.createElement('script')
      script.src = 'https://js.tosspayments.com/v1/payment'
      script.async = true
      script.onload = () => setTossReady(true)
      document.body.appendChild(script)
    } else if (window.TossPayments) {
      setTossReady(true)
    }
  }, [])

  const handlePayment = async () => {
    if (!tossReady) {
      setError('결제 시스템을 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.pdfgrammercheckorean.site'

      // 1. 서버에서 결제 요청 정보 받기
      const response = await fetch(`${apiUrl}/api/payment/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: priceInfo.price,
          char_count: charCount,
          email: email
        })
      })

      const data = await response.json()

      if (data.status !== 'success') {
        throw new Error(data.message || '결제 요청 생성 실패')
      }

      const paymentData = data.payment

      // 2. 토스페이먼츠 결제창 호출
      const tossPayments = window.TossPayments(paymentData.client_key)

      await tossPayments.requestPayment('카드', {
        amount: paymentData.amount,
        orderId: paymentData.order_id,
        orderName: paymentData.order_name,
        customerEmail: paymentData.customer_email,
        successUrl: `${window.location.origin}/payment/success`,
        failUrl: `${window.location.origin}/payment/fail`,
      })

    } catch (err: any) {
      console.error('Payment error:', err)

      // 사용자가 취소한 경우
      if (err.code === 'USER_CANCEL') {
        setError('결제가 취소되었습니다.')
      } else {
        setError(err.message || '결제 처리 중 오류가 발생했습니다.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
          <h2 className="text-xl font-bold text-white">결제 안내</h2>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* 글자 수 정보 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-600">총 글자 수</span>
              <span className="font-semibold">{charCount.toLocaleString()}자</span>
            </div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-600">무료 제공</span>
              <span className="text-green-600">-{priceInfo.free_chars.toLocaleString()}자</span>
            </div>
            <div className="flex justify-between items-center border-t pt-2 mt-2">
              <span className="text-gray-600">과금 대상</span>
              <span className="font-semibold">{priceInfo.billable_chars.toLocaleString()}자</span>
            </div>
          </div>

          {/* 요금 안내 */}
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-1">결제 금액</p>
            <p className="text-4xl font-bold text-blue-600">
              {priceInfo.price.toLocaleString()}원
            </p>
            <p className="text-xs text-gray-400 mt-2">
              * 5만자 초과분에 대해 만자당 500원이 부과됩니다
            </p>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          {/* 버튼 */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 py-3 px-4 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              취소
            </button>
            <button
              onClick={handlePayment}
              disabled={isLoading || !tossReady}
              className="flex-1 py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '처리 중...' : '결제하기'}
            </button>
          </div>

          {/* 결제 수단 안내 */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
            <span>안전한 결제</span>
            <span>•</span>
            <span>토스페이먼츠</span>
          </div>
        </div>
      </div>
    </div>
  )
}
