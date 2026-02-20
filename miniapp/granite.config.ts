import { appsInToss } from '@apps-in-toss/framework/plugins';
import { router } from '@granite-js/plugin-router';
import { hermes } from '@granite-js/plugin-hermes';
import { defineConfig } from '@granite-js/react-native/config';

export default defineConfig({
  scheme: 'intoss',
  appName: 'pdfgrammercheckorean',
  plugins: [
    appsInToss({
      brand: {
        // NOTE: appsInToss 콘솔에 노출될 이름 (한글 권장)
        displayName: 'PDF 맞춤법 검사기',
        primaryColor: '#3182F6',
        // Public, unsigned icon URL (review-ready)
        icon: 'https://www.pdfgrammercheckorean.site/android-chrome-192x192.png',
      },
      permissions: [],
    }),
    router(),
    hermes(),
  ],
});
