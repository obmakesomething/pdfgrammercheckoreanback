'use client'

import { useEffect, useRef, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'

declare global {
  interface Window {
    TossPayments: any
  }
}

export default function PaymentPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [orderInfo, setOrderInfo] = useState<{
    orderId: string
    amount: number
    productName: string
    clientKey: string
  } | null>(null)
  const paymentWidgetRef = useRef<any>(null)
  const paymentMethodsWidgetRef = useRef<any>(null)

  const email = searchParams.get('email')

  useEffect(() => {
    if (!email) {
      setError('이메일 정보가 없습니다.')
      setIsLoading(false)
      return
    }

    // 주문 생성
    createOrder()
  }, [email])

  const createOrder = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.pdfgrammercheckorean.site'

      const response = await fetch(`${apiUrl}/api/payment/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (data.status === 'success') {
        setOrderInfo({
          orderId: data.order_id,
          amount: data.amount,
          productName: data.product_name,
          clientKey: data.client_key,
        })

        // 토스페이먼츠 SDK 로드
        loadTossPayments(data.client_key, data.order_id, data.amount, data.product_name)
      } else {
        setError(data.message || '주문 생성에 실패했습니다.')
        setIsLoading(false)
      }
    } catch (err) {
      console.error('Order creation error:', err)
      setError('서버 연결에 실패했습니다.')
      setIsLoading(false)
    }
  }

  const loadTossPayments = async (
    clientKey: string,
    orderId: string,
    amount: number,
    productName: string
  ) => {
    try {
      // SDK 스크립트 로드
      if (!window.TossPayments) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script')
          script.src = 'https://js.tosspayments.com/v1/payment-widget'
          script.onload = () => resolve()
          script.onerror = () => reject(new Error('토스페이먼츠 SDK 로드 실패'))
          document.head.appendChild(script)
        })
      }

      // 결제 위젯 초기화
      const tossPayments = window.TossPayments(clientKey)
      const paymentWidget = tossPayments.widgets({
        customerKey: email || 'anonymous',
      })

      paymentWidgetRef.current = paymentWidget

      // 결제 금액 설정
      await paymentWidget.setAmount({
        currency: 'KRW',
        value: amount,
      })

      // 결제 수단 위젯 렌더링
      const paymentMethodsWidget = paymentWidget.renderPaymentMethods({
        selector: '#payment-methods',
        variantKey: 'DEFAULT',
      })
      paymentMethodsWidgetRef.current = paymentMethodsWidget

      // 약관 위젯 렌더링
      paymentWidget.renderAgreement({
        selector: '#agreement',
        variantKey: 'AGREEMENT',
      })

      setIsLoading(false)
    } catch (err) {
      console.error('TossPayments load error:', err)
      setError('결제 모듈 로드에 실패했습니다.')
      setIsLoading(false)
    }
  }

  const handlePayment = async () => {
    if (!paymentWidgetRef.current || !orderInfo) {
      setError('결제 정보가 없습니다.')
      return
    }

    try {
      setIsLoading(true)

      const successUrl = `${window.location.origin}/payment/success`
      const failUrl = `${window.location.origin}/payment/fail`

      await paymentWidgetRef.current.requestPayment({
        orderId: orderInfo.orderId,
        orderName: orderInfo.productName,
        customerEmail: email,
        successUrl,
        failUrl,
      })
    } catch (err: any) {
      console.error('Payment request error:', err)
      if (err.code === 'USER_CANCEL') {
        setError('결제가 취소되었습니다.')
      } else {
        setError(err.message || '결제 요청 중 오류가 발생했습니다.')
      }
      setIsLoading(false)
    }
  }

  if (error) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="text-6xl mb-4">😢</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">오류 발생</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            홈으로 돌아가기
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-lg w-full bg-white rounded-2xl shadow-xl p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          결제하기
        </h1>

        {/* 주문 정보 */}
        {orderInfo && (
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h2 className="font-semibold text-gray-900 mb-2">주문 정보</h2>
            <div className="space-y-1 text-sm text-gray-600">
              <p>상품명: {orderInfo.productName}</p>
              <p>결제 금액: {orderInfo.amount.toLocaleString()}원</p>
              <p>이메일: {email}</p>
            </div>
          </div>
        )}

        {/* 로딩 */}
        {isLoading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">결제 모듈을 불러오는 중...</p>
          </div>
        )}

        {/* 토스페이먼츠 위젯 */}
        <div id="payment-methods" className={isLoading ? 'hidden' : 'mb-4'}></div>
        <div id="agreement" className={isLoading ? 'hidden' : 'mb-6'}></div>

        {/* 결제 버튼 */}
        {!isLoading && orderInfo && (
          <button
            onClick={handlePayment}
            className="w-full py-4 px-4 bg-blue-600 text-white rounded-lg font-semibold text-lg hover:bg-blue-700 transition"
          >
            {orderInfo.amount.toLocaleString()}원 결제하기
          </button>
        )}

        {/* 취소 버튼 */}
        <button
          onClick={() => router.push('/')}
          className="w-full mt-3 py-3 px-4 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition"
        >
          취소하고 돌아가기
        </button>
      </div>
    </main>
  )
}
