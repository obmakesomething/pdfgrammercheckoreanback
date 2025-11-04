'use client'

import { ChangeEvent } from 'react'

interface PDFUploaderProps {
  pdfFile: File | null
  setPdfFile: (file: File | null) => void
  email: string
  setEmail: (email: string) => void
  onSubmit: () => void
  isProcessing: boolean
}

export default function PDFUploader({
  pdfFile,
  setPdfFile,
  email,
  setEmail,
  onSubmit,
  isProcessing
}: PDFUploaderProps) {
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]

    if (!file) return

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('PDF 파일만 업로드 가능합니다.')
      return
    }

    // Validate file size (20MB)
    const maxSize = 20 * 1024 * 1024
    if (file.size > maxSize) {
      alert('파일 크기는 20MB 이하여야 합니다.')
      return
    }

    setPdfFile(file)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]

    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('PDF 파일만 업로드 가능합니다.')
      return
    }

    const maxSize = 20 * 1024 * 1024
    if (file.size > maxSize) {
      alert('파일 크기는 20MB 이하여야 합니다.')
      return
    }

    setPdfFile(file)
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }

  return (
    <div className="space-y-6">
      {/* File Upload Area */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
          pdfFile
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 hover:border-blue-400 bg-gray-50'
        }`}
      >
        <input
          type="file"
          id="pdf-upload"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
          disabled={isProcessing}
        />
        <label
          htmlFor="pdf-upload"
          className="cursor-pointer block"
        >
          <svg
            className="mx-auto h-16 w-16 text-gray-400 mb-4"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {pdfFile ? (
            <div className="text-green-600">
              <p className="text-lg font-semibold">{pdfFile.name}</p>
              <p className="text-sm">({(pdfFile.size / 1024 / 1024).toFixed(2)} MB)</p>
              <p className="text-sm mt-2">다른 파일을 선택하려면 클릭하세요</p>
            </div>
          ) : (
            <div className="text-gray-600">
              <p className="text-lg font-semibold">PDF 파일을 드래그하거나 클릭하여 선택</p>
              <p className="text-sm mt-2">최대 20MB</p>
            </div>
          )}
        </label>
      </div>

      {/* Email Input */}
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
          이메일 주소
        </label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="example@email.com"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          disabled={isProcessing}
        />
        <p className="text-xs text-gray-500 mt-2">
          검사 완료된 PDF 파일을 이메일로 받으실 수 있습니다
        </p>
      </div>

      {/* Submit Button */}
      <button
        onClick={onSubmit}
        disabled={isProcessing || !pdfFile || !email}
        className={`w-full py-4 px-6 rounded-lg font-semibold text-white text-lg transition-all ${
          isProcessing || !pdfFile || !email
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 active:scale-95'
        }`}
      >
        {isProcessing ? '처리 중...' : '맞춤법 검사하기'}
      </button>
    </div>
  )
}
