# pdfgrammercheckorean (Apps in Toss web miniapp)

- `appName`: `pdfgrammercheckorean`
- Deep link: `intoss://pdfgrammercheckorean`

## What It Does

- Select a PDF
- Upload to backend: `POST /api/check-pdf`
- Save corrected PDF to device via `saveBase64Data` (Apps in Toss bridge)
  - Falls back to browser download in local dev

## Env Vars

- `VITE_API_BASE_URL` (optional)
  - Default: `https://api.pdfgrammercheckorean.site`
- `VITE_AD_GROUP_ID` (optional)
  - If set, tries to show a full-screen ad before revealing the result PDF (free docs only)

## Pricing (Current Policy)

- `<= 50,000자`: 광고 기반 무료
- `> 50,000자`: 초과분 `10,000자당 100원` = `크레딧 1개` 필요

## IAP Credits (Apps in Toss)

- 유료 문서는 **인앱결제(IAP)로 크레딧을 구매**한 뒤 다시 검사합니다.
- 서버는 `device_id`(브릿지 `getDeviceId()`)를 기준으로 크레딧 잔고를 저장합니다.

### Backend Requirements

- `POST /api/check-pdf`에 `device_id` 필드가 포함되어야 유료 문서에서 크레딧 차감이 동작합니다.
- 서버는 다음 엔드포인트를 제공합니다:
  - `GET /api/credits/balance?user_id=<device_id>`
  - `POST /api/iap/grant` (`{ user_id, order_id, sku }`)

## Commands

```bash
npm install
npm test
npm run lint
npm run build
```

Build output:
- `./pdgrammercheckorean.ait` (gitignored)

Deploy:
```bash
npm run deploy
```

## Review Notes

- Set a real app icon URL in `./granite.config.ts` before review.
- Add only the permissions you actually use (currently empty).
