'use client'

import { useState } from 'react'
import PDFUploader from '@/components/PDFUploader'
import AdPlayer from '@/components/AdPlayer'
import SEOContent from '@/components/SEOContent'

export default function Home() {
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [email, setEmail] = useState('')
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [agreedToPrivacy, setAgreedToPrivacy] = useState(false)
  const [showAd, setShowAd] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')
  const [errorsFound, setErrorsFound] = useState<number | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleSubmit = () => {
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

    // Show ad
    setMessage(null)
    setShowAd(true)
  }

  const validateEmail = (email: string) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return re.test(email)
  }

  const handleAdComplete = async () => {
    setShowAd(false)
    setIsProcessing(true)
    setMessage(null)
    setErrorsFound(null)

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
          text: `${errorMessage}\n\nPDF 파일이 다운로드되었습니다.\n\n색상별 의미:\n🔵 파란색 - 띄어쓰기\n🔴 빨간색 - 맞춤법/오타\n🟡 노란색 - 문법\n🟠 주황색 - 기타\n\n주석을 클릭하면 수정 제안을 확인할 수 있습니다.`
        })

        // Reset form
        setPdfFile(null)
        setEmail('')
        setAgreedToTerms(false)
        setAgreedToPrivacy(false)
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
    </main>
  )
}
