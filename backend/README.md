# PDF 한국어 맞춤법 검사기 - 백엔드

Flask 기반 PDF 맞춤법 검사 API 서버

## 기능

- PDF 파일에서 텍스트 추출 (문자 단위 위치 정보 포함)
- 하이픈/줄바꿈으로 분리된 단어 병합 (앵커 매핑 기술)
- 한국어 맞춤법 검사 (다중 API fallback)
- PDF 주석 생성 (빨간색 하이라이트)
- 이메일 발송 (Resend API)

## 아키텍처

### 핵심 모듈

1. **pdf_extractor.py** - PDF 텍스트 추출
   - PyPDF2를 사용하여 문자 단위로 텍스트 추출
   - 각 문자의 페이지 번호 및 위치 정보 저장

2. **text_preprocessor.py** - 텍스트 전처리 및 앵커 매핑
   - 하이픈 + 줄바꿈 병합 ("안녕하세-\n요" → "안녕하세요")
   - 조사 분리 복구 ("사과 를" → "사과를")
   - 원본 위치 추적을 위한 앵커 맵 생성

3. **spell_checker.py** - 맞춤법 검사
   - 1순위: 부산대 API
   - 2순위: 네이버 API
   - 3순위: 로컬 규칙 기반
   - 300자 단위로 분할하여 검사

4. **pdf_annotator.py** - PDF 주석 생성
   - PyPDF2로 PDF에 주석 추가
   - 빨간색 하이라이트 및 코멘트

5. **email_sender.py** - 이메일 발송
   - Resend API 사용
   - PDF 첨부 및 HTML 이메일

6. **main_processor.py** - 전체 파이프라인 통합
   - 5단계 프로세스 실행
   - 오류 처리 및 로깅

7. **app.py** - Flask API 서버
   - POST /api/check-pdf - 맞춤법 검사 요청
   - GET /health - 헬스 체크
   - GET /api/test - 테스트 엔드포인트

## 설치

```bash
cd backend
pip install -r requirements.txt
```

## 환경 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집:

```env
PORT=5000
DEBUG=False
RESEND_API_KEY=re_your_api_key_here
RESEND_FROM_EMAIL=noreply@pdfgrammercheckorean.site
```

## 실행

### 개발 모드

```bash
python app.py
```

### 프로덕션 (Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API 사용법

### 1. 맞춤법 검사 요청

```bash
curl -X POST http://localhost:5000/api/check-pdf \
  -F "pdf=@test.pdf" \
  -F "email=user@example.com"
```

**응답 (성공):**

```json
{
  "status": "success",
  "message": "이메일이 발송되었습니다",
  "errors_found": 15
}
```

**응답 (오류):**

```json
{
  "status": "error",
  "message": "파일 크기는 20MB 이하여야 합니다"
}
```

### 2. 헬스 체크

```bash
curl http://localhost:5000/health
```

**응답:**

```json
{
  "status": "healthy",
  "service": "PDF Grammar Checker"
}
```

## CLI 사용법

### 단일 PDF 파일 검사

```bash
python main_processor.py input.pdf
```

결과: `input_검사완료.pdf` 생성

### 출력 파일명 지정

```bash
python main_processor.py input.pdf output.pdf
```

## 테스트

### PDF 추출 테스트

```bash
python pdf_extractor.py test.pdf
```

### 텍스트 전처리 테스트

```bash
python text_preprocessor.py
```

### 맞춤법 검사 테스트

```bash
python spell_checker.py
```

### 이메일 발송 테스트

```bash
python email_sender.py user@example.com test.pdf 5 "original.pdf"
```

## 배포 (Railway)

### 1. Railway 프로젝트 생성

```bash
railway login
railway init
```

### 2. 환경 변수 설정

Railway 대시보드에서 설정:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `PORT` (Railway가 자동 설정)

### 3. 배포

```bash
railway up
```

### 4. 도메인 연결

Railway 대시보드에서 `api.pdfgrammercheckorean.site` 도메인 연결

## 프로세스 플로우

```
1. PDF 업로드 수신
   ↓
2. 임시 파일 저장 (/tmp)
   ↓
3. PDF 텍스트 추출 (문자 + 위치)
   ↓
4. 텍스트 전처리 (앵커 매핑)
   ↓
5. 맞춤법 검사 (300자씩 분할)
   ↓
6. 앵커 역추적 (오류 위치 찾기)
   ↓
7. PDF 주석 생성
   ↓
8. 이메일 발송 (Resend)
   ↓
9. 임시 파일 삭제
   ↓
10. 응답 반환
```

## 핵심 기술: 앵커 매핑

PDF의 양끝정렬로 인해 단어가 하이픈과 줄바꿈으로 분리되는 문제를 해결:

### 문제

```
원본 PDF: "안녕하세-\n요 반갑습니다"
```

### 해결

1. **전처리**: `"안녕하세요 반갑습니다"`
2. **앵커 맵**: 전처리된 각 문자 → 원본 문자 인덱스들
3. **맞춤법 검사**: 전처리된 텍스트로 검사
4. **역추적**: 오류 위치를 앵커 맵으로 원본 위치 찾기
5. **주석**: 원본 PDF의 정확한 위치에 주석 추가

## 제한사항

- 최대 파일 크기: 20MB
- 맞춤법 검사 단위: 300자
- 외부 API 의존 (부산대, 네이버)
- PDF 좌표 추출 제한 (PyPDF2)

## 개선 필요 사항

1. **맞춤법 검사 API**
   - 현재 부산대/네이버 API 불안정
   - 대안: Kakao API, 자체 학습 모델

2. **PDF 좌표 추출**
   - PyPDF2로는 정확한 x, y 좌표 어려움
   - 대안: pdfminer.six, pypdfium2 심화

3. **비동기 처리**
   - 현재 동기 방식으로 처리 시간 김
   - 대안: Celery + Redis 큐 시스템

4. **캐싱**
   - 동일 PDF 재처리 방지
   - 대안: Redis 캐싱

## 라이선스

MIT

## 문의

기술 문의: [GitHub Issues](https://github.com/your-repo/issues)
