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
- `> 50,000자`: 초과분 `10,000자당 100원` (백엔드가 `402 payment_required`로 응답)

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
