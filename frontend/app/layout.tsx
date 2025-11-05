import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Script from 'next/script'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'PDF 한국어 맞춤법 검사기 - 무료 온라인 PDF 맞춤법 교정',
  description: 'PDF 파일의 한국어 맞춤법을 무료로 검사하고 교정합니다. 업로드한 PDF에 맞춤법 오류를 빨간색으로 표시하여 이메일로 전송해드립니다. 간편하고 빠른 PDF 맞춤법 검사 서비스.',
  keywords: 'PDF 맞춤법 검사, 한국어 맞춤법, PDF 교정, 맞춤법 교정, 온라인 맞춤법 검사, 무료 맞춤법 검사',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-96x96.png', sizes: '96x96', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    other: [
      { url: '/android-chrome-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/android-chrome-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
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
        <link rel="manifest" href="/site.webmanifest" />
        <meta name="theme-color" content="#667eea" />

        {/* Google Analytics (GA4) */}
        <Script
          async
          src="https://www.googletagmanager.com/gtag/js?id=G-PJFYER4MDV"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-PJFYER4MDV');
          `}
        </Script>

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
