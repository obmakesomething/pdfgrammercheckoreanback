# 📝 PDF 한국어 맞춤법 검사기

AI 기반 바른(Bareun) API를 사용한 PDF 맞춤법 및 문법 검사 서비스

## 🌟 주요 기능

- **PDF 맞춤법 검사**: 업로드한 PDF 파일의 한국어 맞춤법과 문법을 자동으로 검사
- **AI 기반 정확성**: 바른(Bareun) API를 사용하여 높은 정확도의 검사 결과 제공
- **주석 추가**: 검사 결과를 PDF 파일에 주석으로 표시
- **이메일 전송**: 검사 완료된 PDF를 이메일로 자동 전송
- **완전 무료**: 회원가입 없이 무료로 사용 가능

## 🏗️ 시스템 구조

```
프론트엔드 (Vercel)          백엔드 (Railway)
    Next.js        ←→        Flask API
pdfgrammercheckorean.site   api.pdfgrammercheckorean.site
```

### 기술 스택

**프론트엔드**
- HTML5, CSS3, JavaScript
- Next.js (배포용)
- SEO 최적화 (OpenGraph, Schema.org)

**백엔드**
- Python 3.11
- Flask 2.2.5
- 바른(Bareun) API
- PyPDF2, pypdfium2
- Resend (이메일)

## 📦 설치 및 실행

### 1. 백엔드 설정

```bash
cd backend

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 서버 실행
python app.py
```

### 2. 환경 변수 설정

`.env` 파일에 다음 내용을 설정하세요:

```env
# 바른 API 설정
BAREUN_API_KEY=your_api_key_here
BAREUN_HOST=api.bareun.ai
BAREUN_PORT=443

# Resend API 설정
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=noreply@pdfgrammercheckorean.site

# Flask 설정
PORT=5000
DEBUG=False
```

### 3. 프론트엔드 실행

```bash
cd frontend

# 개발 서버 (index.html 직접 열기)
open index.html

# 또는 Next.js로 실행
npm install
npm run dev
```

## 🚀 배포

### 백엔드 (Railway)

1. Railway에 프로젝트 연결
2. 환경 변수 설정
3. `backend/` 디렉토리를 루트로 설정
4. 자동 배포

### 프론트엔드 (Vercel)

1. Vercel에 프로젝트 연결
2. `frontend/` 디렉토리를 루트로 설정
3. 환경 변수에 `NEXT_PUBLIC_API_URL` 설정
4. 자동 배포

## 📖 API 문서

### POST `/api/check-pdf`

PDF 파일의 맞춤법을 검사합니다.

**Request:**
```
multipart/form-data
- pdf: PDF 파일 (최대 20MB)
- email: 이메일 주소
```

**Response:**
```json
{
  "status": "success",
  "message": "이메일이 발송되었습니다",
  "errors_found": 171
}
```

### POST `/api/survey`

설문조사 응답을 저장합니다.

**Request:**
```json
{
  "source": "search",
  "purpose": "work",
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "설문조사가 제출되었습니다"
}
```

## 🔒 보안 및 개인정보

- 업로드된 PDF 파일은 검사 완료 후 즉시 삭제됩니다
- 이메일 주소는 결과 전송 후 즉시 삭제됩니다
- 설문조사 응답은 익명으로 저장됩니다
- HTTPS 암호화 통신 사용

## 📁 프로젝트 구조

```
pdf-grammar-checker/
├── backend/
│   ├── app.py                 # Flask API 서버
│   ├── bareun_checker.py      # 바른 API 통합
│   ├── spell_checker.py       # 맞춤법 검사기
│   ├── pdf_extractor.py       # PDF 텍스트 추출
│   ├── text_preprocessor.py   # 텍스트 전처리
│   ├── pdf_annotator.py       # PDF 주석 생성
│   ├── email_sender.py        # 이메일 발송
│   ├── main_processor.py      # 메인 처리 파이프라인
│   ├── requirements.txt       # Python 패키지
│   └── .env                   # 환경 변수 (gitignored)
│
├── frontend/
│   ├── index.html            # 메인 페이지 (SEO 최적화)
│   ├── terms.html            # 이용약관
│   ├── privacy.html          # 개인정보처리방침
│   ├── guide.html            # 사용 가이드
│   └── public/
│       ├── robots.txt        # 검색엔진 크롤링 설정
│       └── sitemap.xml       # 사이트맵
│
└── README.md
```

## 🎯 핵심 기술 구현

### 1. 앵커 매핑 (Anchor Mapping)

PDF에서 추출한 텍스트를 전처리하면서 원본 위치를 추적하는 시스템:

```python
# 하이픈으로 나뉜 단어 병합 예시
"안녕하세-\n요" → "안녕하세요"
# 위치 정보는 앵커 맵에 저장되어 나중에 역추적 가능
```

### 2. PDF 주석 생성

맞춤법 오류 위치에 자동으로 주석을 추가:

```python
# 오류 발견 → 원본 위치 역추적 → PDF 주석 추가
error = {'wrong': '되요', 'correct': '돼요', 'position': 42}
→ PDF 42번 위치에 "되요 → 돼요" 주석 추가
```

### 3. 설문조사 데이터 수집

사용자 피드백을 CSV 파일로 저장:

```python
# survey_responses.csv
timestamp,source,purpose,email
2024-11-04T14:30:00,search,work,user@example.com
```

## 🤝 기여하기

이 프로젝트는 오픈소스가 아니며, 상업적 목적으로 사용됩니다.

## 📄 라이선스

All rights reserved. © 2024 PDF Grammar Checker

## 📞 문의

- 이메일: support@pdfgrammercheckorean.site
- 개인정보 문의: privacy@pdfgrammercheckorean.site

## ⚠️ 면책조항

이 서비스는 맞춤법 검사 결과의 정확성을 보장하지 않습니다. 최종 판단은 사용자의 책임입니다.
