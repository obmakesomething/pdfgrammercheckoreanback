'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import PDFUploader from '@/components/PDFUploader'
import AdPlayer from '@/components/AdPlayer'
import SEOContent from '@/components/SEOContent'
import PaymentModal from '@/components/PaymentModal'

interface PriceInfo {
  char_count: number
  free_chars: number
  billable_chars: number
  price: number
  is_free: boolean
  breakdown: string
}

interface AnalysisResult {
  char_count: number
  price_info: PriceInfo
  needs_payment: boolean
  file_size_mb: number
}

function HomeContent() {
  const searchParams = useSearchParams()
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [email, setEmail] = useState('')
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [agreedToPrivacy, setAgreedToPrivacy] = useState(false)
  const [showAd, setShowAd] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // 결제 관련 상태
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)

  // 결제 성공 후 돌아온 경우 처리
  useEffect(() => {
    const paymentStatus = searchParams.get('payment')
    if (paymentStatus === 'success') {
      const savedPayment = localStorage.getItem('paymentCompleted')
      if (savedPayment) {
        localStorage.removeItem('paymentCompleted')
        setMessage({
          type: 'success',
          text: '결제가 완료되었습니다! PDF 파일을 다시 업로드하여 맞춤법 검사를 진행해주세요.'
        })
      }
    }
  }, [searchParams])

  const validateEmail = (email: string) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return re.test(email)
  }

  // PDF 분석 (글자 수 확인)
  const analyzePDF = async (): Promise<AnalysisResult | null> => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.pdfgrammercheckorean.site'

    const formData = new FormData()
    formData.append('pdf', pdfFile!)

    const response = await fetch(`${apiUrl}/api/analyze-pdf`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()

    if (data.status !== 'success') {
      throw new Error(data.message || '파일 분석에 실패했습니다.')
    }

    return {
      char_count: data.char_count,
      price_info: data.price_info,
      needs_payment: data.needs_payment,
      file_size_mb: data.file_size_mb
    }
  }

  const handleSubmit = async () => {
    // Validation
    if (!pdfFile) {
      setMessage({ type: 'error', text: 'PDF 파일을 선택해주세요.' })
      return
    }

    if (!email || !validateEmail(email)) {
      setMessage({ type: 'error', text: '올바른 이메일 주소를 입력해주세요.' })
      return
    }

    if (!agreedToTerms) {
      setMessage({ type: 'error', text: '이용약관에 동의해주세요.' })
      return
    }

    if (!agreedToPrivacy) {
      setMessage({ type: 'error', text: '개인정보 처리방침에 동의해주세요.' })
      return
    }

    setMessage(null)
    setIsProcessing(true)
    setProgressMessage('📊 파일 분석 중...')

    try {
      // 1. PDF 분석 (글자 수 확인)
      const result = await analyzePDF()
      setAnalysisResult(result)
      setProgressMessage('')
      setIsProcessing(false)

      if (result?.needs_payment) {
        // 결제가 필요한 경우 결제 모달 표시
        setShowPaymentModal(true)
      } else {
        // 무료인 경우 바로 광고 표시
        setShowAd(true)
      }
    } catch (error: any) {
      console.error('Analysis error:', error)
      setProgressMessage('')
      setIsProcessing(false)
      setMessage({
        type: 'error',
        text: `❌ ${error.message || '파일 분석 중 오류가 발생했습니다.'}`
      })
    }
  }

  const handlePaymentSuccess = () => {
    setShowPaymentModal(false)
    // 결제 성공 후 광고 표시 -> 처리
    setShowAd(true)
  }

  const handleAdComplete = async () => {
    setShowAd(false)
    setIsProcessing(true)
    setMessage(null)

    try {
      // 단계 1: 업로드 시작
      setProgressMessage('📤 파일 업로드 중...')

      const formData = new FormData()
      formData.append('pdf', pdfFile!)
      formData.append('email', email)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.pdfgrammercheckorean.site'

      // 단계 2: 서버 전송
      setProgressMessage('⏳ PDF 맞춤법 검사 중...')

      const response = await fetch(`${apiUrl}/api/check-pdf`, {
        method: 'POST',
        body: formData,
      })

      setProgressMessage('') // 팝업 닫기

      if (response.ok) {
        // 헤더에서 오류 개수 추출
        const errorsCount = parseInt(response.headers.get('X-Errors-Found') || '0')

        // PDF 파일 다운로드
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${pdfFile!.name.replace('.pdf', '')}_맞춤법검사.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)

        // 오류 개수에 따라 메시지 변경
        const errorMessage = errorsCount === 0
          ? '✅ 맞춤법 오류가 발견되지 않았습니다!'
          : `✅ ${errorsCount}개의 맞춤법 오류를 발견했습니다!`

        setMessage({
          type: 'success',
          text: `${errorMessage}\n\nPDF 파일이 다운로드되었습니다.\n이메일로도 발송되었습니다.\n\n색상별 의미:\n🔵 파란색 - 띄어쓰기\n🔴 빨간색 - 맞춤법/오타\n🟡 노란색 - 문법\n🟠 주황색 - 기타\n\n주석을 클릭하면 수정 제안을 확인할 수 있습니다.`
        })

        // Reset form
        setPdfFile(null)
        setEmail('')
        setAgreedToTerms(false)
        setAgreedToPrivacy(false)
        setAnalysisResult(null)
      } else {
        const data = await response.json()
        setMessage({
          type: 'error',
          text: `❌ ${data.message || '오류가 발생했습니다. 다시 시도해주세요.'}`
        })
      }
    } catch (error) {
      console.error('Error:', error)
      setProgressMessage('')
      setMessage({
        type: 'error',
        text: '❌ 서버 연결에 실패했습니다.\n네트워크 상태를 확인한 후 다시 시도해주세요.'
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleAdError = () => {
    setShowAd(false)
    setMessage({
      type: 'error',
      text: '광고 로드에 실패했습니다. 다시 시도해주세요.'
    })
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-4xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-bold text-gray-900">
            PDF 한국어 맞춤법 검사기
          </h1>
          <p className="text-xl text-gray-600">
            PDF 파일의 맞춤법을 검사하고 색상별 주석으로 표시하여 다운로드해드립니다
          </p>
          {/* 요금 안내 */}
          <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm">
            <span>💡</span>
            <span>5만자까지 무료 | 초과시 만자당 100원</span>
          </div>
        </div>

        {/* Main Content */}
        {!showAd ? (
          <div className="bg-white rounded-2xl shadow-xl p-8 space-y-6">
            <PDFUploader
              pdfFile={pdfFile}
              setPdfFile={setPdfFile}
              email={email}
              setEmail={setEmail}
              agreedToTerms={agreedToTerms}
              setAgreedToTerms={setAgreedToTerms}
              agreedToPrivacy={agreedToPrivacy}
              setAgreedToPrivacy={setAgreedToPrivacy}
              onSubmit={handleSubmit}
              isProcessing={isProcessing}
            />

            {/* Message Display */}
            {message && (
              <div className={`p-4 rounded-lg ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-800 border border-green-200'
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}>
                <p className="whitespace-pre-line">{message.text}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <h2 className="text-2xl font-semibold text-center mb-6 text-gray-900">
              광고 시청 후 검사가 시작됩니다
            </h2>
            <AdPlayer
              onAdComplete={handleAdComplete}
              onAdError={handleAdError}
            />
          </div>
        )}

        {/* SEO Content */}
        <SEOContent />
      </div>

      {/* Progress Popup */}
      {progressMessage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
              <p className="text-xl font-semibold text-gray-900">{progressMessage}</p>
              <p className="text-sm text-gray-600">잠시만 기다려주세요...</p>
            </div>
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {analysisResult && (
        <PaymentModal
          isOpen={showPaymentModal}
          onClose={() => setShowPaymentModal(false)}
          onPaymentSuccess={handlePaymentSuccess}
          charCount={analysisResult.char_count}
          priceInfo={analysisResult.price_info}
          email={email}
        />
      )}
    </main>
  )
}

export default function Home() {
  return (
    <Suspense fallback={
      <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
      </main>
    }>
      <HomeContent />
    </Suspense>
  )
}
