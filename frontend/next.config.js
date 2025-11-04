/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.pdfgrammercheckorean.site',
    NEXT_PUBLIC_ADSENSE_ID: 'ca-pub-4224113972571264',
  },
}

module.exports = nextConfig
