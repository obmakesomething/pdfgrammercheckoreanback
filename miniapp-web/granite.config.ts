import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'pdfgrammercheckorean',
  brand: {
    displayName: 'PDF 맞춤법 검사기',
    primaryColor: '#3182F6', // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
    // Public, unsigned icon URL (required for review readiness)
    icon: 'https://www.pdfgrammercheckorean.site/android-chrome-192x192.png',
  },
  web: {
    host: 'localhost',
    port: 5173,
    commands: {
      dev: 'vite',
      build: 'tsc -b && vite build',
    },
  },
  permissions: [],
  outdir: 'dist',
});
