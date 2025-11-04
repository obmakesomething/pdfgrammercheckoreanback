import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Script from 'next/script'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'PDF 한국어 맞춤법 검사기 - 무료 온라인 PDF 맞춤법 교정',
  description: 'PDF 파일의 한국어 맞춤법을 무료로 검사하고 교정합니다. 업로드한 PDF에 맞춤법 오류를 빨간색으로 표시하여 이메일로 전송해드립니다. 간편하고 빠른 PDF 맞춤법 검사 서비스.',
  keywords: 'PDF 맞춤법 검사, 한국어 맞춤법, PDF 교정, 맞춤법 교정, 온라인 맞춤법 검사, 무료 맞춤법 검사',
  openGraph: {
    title: 'PDF 한국어 맞춤법 검사기',
    description: 'PDF 파일의 한국어 맞춤법을 무료로 검사하고 교정합니다.',
    type: 'website',
    locale: 'ko_KR',
  },
  robots: 'index, follow',
  alternates: {
    canonical: 'https://pdfgrammercheckorean.site',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <head>
        {/* Google AdSense */}
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4224113972571264"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
        {/* Google IMA SDK for Video Ads */}
        <Script
          src="https://imasdk.googleapis.com/js/sdkloader/ima3.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  )
}
