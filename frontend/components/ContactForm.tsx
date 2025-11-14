'use client'

import { useState } from 'react'

export default function ContactForm() {
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!message.trim()) {
      setStatus({ type: 'error', text: '문의 내용을 입력해주세요.' })
      return
    }

    setIsSubmitting(true)
    setStatus(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message.trim(),
          email: email.trim() || '익명'
        })
      })

      if (response.ok) {
        setStatus({ type: 'success', text: '✅ 문의가 접수되었습니다. 빠르게 확인하겠습니다.' })
        setMessage('')
        setEmail('')
      } else {
        const data = await response.json()
        throw new Error(data.message || '문의 전송 실패')
      }
    } catch (err) {
      setStatus({ type: 'error', text: '❌ 문의 전송에 실패했습니다. 잠시 후 다시 시도해주세요.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">📩 문의하기</h2>
        <p className="text-gray-600">
          서비스 관련 궁금한 점이나 제안이 있으면 언제든 보내주세요
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="contact-message" className="block text-sm font-medium text-gray-700 mb-2">
            문의 내용 <span className="text-red-500">*</span>
          </label>
          <textarea
            id="contact-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="요청 사항, 버그 제보, 제안 등을 자유롭게 남겨주세요..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            rows={5}
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label htmlFor="contact-email" className="block text-sm font-medium text-gray-700 mb-2">
            이메일 (선택)
          </label>
          <input
            id="contact-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="답변을 받고 싶은 이메일 (선택사항)"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            disabled={isSubmitting}
          />
        </div>

        {status && (
          <div className={`p-4 rounded-lg ${status.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {status.text}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold"
        >
          {isSubmitting ? '전송 중...' : '문의 보내기'}
        </button>
      </form>
    </div>
  )
}
