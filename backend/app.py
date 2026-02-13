#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API 서버
PDF 맞춤법 검사 API 제공
"""
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import os
import base64
import hmac
import tempfile
import uuid
import csv
import datetime
from urllib.parse import quote
from main_processor import GrammarCheckProcessor
from email_sender import EmailSender
from toss_payments import TossPayments
from payment_storage import PaymentStorage
from credits_storage import CreditsStorage
from dotenv import load_dotenv
import json
import re
from typing import Optional, Tuple

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
# CORS: Toss 콘솔 테스트(브라우저 fetch)에서 Basic Auth/credentials 옵션이 켜져도
# "Failed to fetch"로 막히지 않도록 credentials 허용.
CORS(app, supports_credentials=True)  # CORS 허용

# 프로세서 및 이메일 발송기 초기화
processor = GrammarCheckProcessor()
email_sender = EmailSender()

# 결제 시스템 초기화
toss_payments = TossPayments()
payment_storage = PaymentStorage()

# Credits storage (Apps in Toss IAP)
credits_db_path = os.getenv('CREDITS_DB_PATH', os.path.join('data', 'credits.sqlite3'))
credits_storage = CreditsStorage(credits_db_path)

# 상품 정보 (환경변수에서 가져오거나 기본값 사용)
PRODUCT_AMOUNT = int(os.getenv('PRODUCT_AMOUNT', '3900'))  # 기본 3,900원
PRODUCT_NAME = os.getenv('PRODUCT_NAME', 'PDF 맞춤법 검사 프리미엄')

def _get_iap_sku_credits_map() -> dict:
    raw = (os.getenv('IAP_SKU_CREDITS_JSON') or '').strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _infer_credits_from_sku(sku: str) -> int:
    """Fallback: infer credits from SKU name like CREDIT_5 -> 5."""
    if not sku:
        return 0
    m = re.search(r'(\\d+)', sku)
    if not m:
        return 1
    try:
        return max(1, int(m.group(1)))
    except Exception:
        return 1


def _credits_for_sku(sku: str) -> int:
    mapping = _get_iap_sku_credits_map()
    if sku in mapping:
        try:
            return max(0, int(mapping[sku]))
        except Exception:
            return 0
    return _infer_credits_from_sku(sku)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def _expected_disconnect_basic_auth() -> Optional[Tuple[str, str]]:
    user = (os.getenv('TOSS_DISCONNECT_BASIC_AUTH_USER') or '').strip()
    pw = (os.getenv('TOSS_DISCONNECT_BASIC_AUTH_PASS') or '').strip()
    if not user and not pw:
        return None
    return (user, pw)


def _parse_basic_auth(authorization: Optional[str]) -> Optional[Tuple[str, str]]:
    if not authorization:
        return None

    # Some consoles may provide only "user:pass" or only "<base64(user:pass)>"
    # as the header value. Accept those as well to reduce integration friction.
    raw = authorization.strip()
    if raw and ' ' not in raw:
        if ':' in raw:
            u, p = raw.split(':', 1)
            return (u, p)
        try:
            decoded = base64.b64decode(raw).decode('utf-8')
        except Exception:
            decoded = None
        if decoded and ':' in decoded:
            u, p = decoded.split(':', 1)
            return (u, p)

    parts = authorization.split(' ', 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != 'basic':
        return None
    token = parts[1].strip()
    if not token:
        return None
    # Some webhook providers may (incorrectly) send "Basic user:pass" without base64.
    # Be tolerant: if it contains a colon, treat it as plaintext.
    if ':' in token:
        u, p = token.split(':', 1)
        return (u, p)
    try:
        decoded = base64.b64decode(token).decode('utf-8')
    except Exception:
        return None
    if ':' in decoded:
        u, p = decoded.split(':', 1)
        return (u, p)
    return (decoded, '')


def _verify_basic_auth(authorization: Optional[str], expected_user: str, expected_pass: str) -> bool:
    parsed = _parse_basic_auth(authorization)
    if not parsed:
        return False
    user, pw = parsed
    return hmac.compare_digest(user, expected_user) and hmac.compare_digest(pw, expected_pass)


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Grammar Checker'
    }), 200


def _legal_html_page(title: str, body_html: str, updated_at: str) -> str:
    # Minimal, self-contained HTML page for Apps in Toss review docs.
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex, nofollow" />
    <title>{title} | PDF 맞춤법 검사기</title>
    <style>
      :root {{
        --bg: #f6f7fb;
        --card: #ffffff;
        --text: #111827;
        --muted: #6b7280;
        --accent: #2563eb;
        --border: #e5e7eb;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans KR", Helvetica, Arial, "Apple Color Emoji",
          "Segoe UI Emoji";
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
      }}
      .wrap {{
        max-width: 920px;
        margin: 0 auto;
        padding: 24px;
      }}
      .card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 8px 18px rgba(17, 24, 39, 0.06);
      }}
      h1 {{
        margin: 0 0 6px 0;
        font-size: 28px;
        letter-spacing: -0.02em;
      }}
      .meta {{
        margin: 0 0 18px 0;
        color: var(--muted);
        font-size: 13px;
      }}
      h2 {{
        margin: 26px 0 10px 0;
        font-size: 18px;
        color: var(--accent);
      }}
      p {{ margin: 10px 0; }}
      ul {{ margin: 10px 0 10px 22px; }}
      li {{ margin: 6px 0; }}
      .note {{
        margin: 14px 0;
        padding: 12px 14px;
        border-left: 4px solid var(--accent);
        background: #eff6ff;
        border-radius: 10px;
      }}
      code {{
        background: #f3f4f6;
        padding: 0 6px;
        border-radius: 6px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.95em;
      }}
      a {{ color: var(--accent); }}
      .footer {{
        margin-top: 22px;
        color: var(--muted);
        font-size: 12px;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>{title}</h1>
        <p class="meta">최종 수정일: {updated_at}</p>
        {body_html}
        <p class="footer">본 문서는 Apps in Toss 미니앱(앱명: <code>pdfgrammercheckorean</code>) 서비스 운영을 위한 고지 문서입니다.</p>
      </div>
    </div>
  </body>
</html>
"""


@app.route('/legal/terms', methods=['GET'])
def legal_terms():
    updated_at = os.getenv('LEGAL_LAST_UPDATED', '2026년 2월 9일')
    contact_email = os.getenv('LEGAL_CONTACT_EMAIL', os.getenv('RESEND_FROM_EMAIL', 'noreply@pdfgrammercheckorean.site'))

    body = f"""
        <h2>1. 목적</h2>
        <p>본 약관은 PDF 맞춤법 검사기(이하 “서비스”)의 이용 조건 및 절차, 서비스 제공자와 이용자의 권리/의무/책임사항을 규정합니다.</p>

        <h2>2. 서비스 내용</h2>
        <ul>
          <li>이용자가 업로드한 PDF에서 텍스트를 추출하여 한국어 맞춤법/문법 검사를 수행합니다.</li>
          <li>검사 결과는 오류 표시(하이라이트/주석)가 포함된 PDF로 제공될 수 있습니다.</li>
        </ul>

        <h2>3. 유료/무료 정책</h2>
        <div class="note">
          <p><strong>무료 구간</strong>: 문서당 문자수(공백 제외 기준)가 <code>50,000자 이하</code>인 경우 무료로 제공되며, 일부 화면에서 광고가 노출될 수 있습니다.</p>
          <p><strong>유료 구간</strong>: <code>50,000자 초과</code> 문서는 초과분에 대해 <code>10,000자당 100원</code> 기준으로 크레딧이 차감됩니다. (예: 초과분 1~10,000자 = 1크레딧)</p>
        </div>
        <p>유료 결제는 Apps in Toss 인앱결제(IAP)로 제공되는 크레딧 구매 형태로 진행됩니다.</p>

        <h2>4. 이용자의 의무</h2>
        <ul>
          <li>타인의 권리를 침해하는 문서, 불법/유해 콘텐츠 업로드 등 관련 법령을 위반하는 행위를 하지 않아야 합니다.</li>
          <li>서비스의 정상 동작을 방해하는 행위(과도한 요청, 취약점 악용 등)를 하지 않아야 합니다.</li>
        </ul>

        <h2>5. 파일 처리 및 보안</h2>
        <ul>
          <li>업로드된 PDF는 처리에 필요한 기간 동안만 서버에 임시 저장되며, 처리 완료 후 즉시 삭제를 원칙으로 합니다.</li>
          <li>서비스는 기능 제공을 위해 외부 맞춤법 API로 텍스트를 전송할 수 있습니다(개인정보 최소화).</li>
        </ul>

        <h2>6. 면책</h2>
        <ul>
          <li>검사 결과의 정확성은 보장되지 않으며, 최종 판단과 책임은 이용자에게 있습니다.</li>
          <li>천재지변/장애/점검 등 불가항력 사유로 인한 서비스 중단에 대해 책임을 지지 않습니다.</li>
        </ul>

        <h2>7. 문의</h2>
        <p>서비스 관련 문의: <a href="mailto:{contact_email}">{contact_email}</a></p>
    """

    html = _legal_html_page('서비스 이용약관', body, updated_at)
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


@app.route('/legal/privacy', methods=['GET'])
def legal_privacy():
    updated_at = os.getenv('LEGAL_LAST_UPDATED', '2026년 2월 9일')
    contact_email = os.getenv('LEGAL_CONTACT_EMAIL', os.getenv('RESEND_FROM_EMAIL', 'noreply@pdfgrammercheckorean.site'))

    body = f"""
        <h2>1. 수집하는 정보</h2>
        <p>서비스는 기능 제공을 위해 다음 정보를 처리할 수 있습니다.</p>
        <ul>
          <li><strong>기기 식별자(가명 처리)</strong>: 크레딧 잔액/차감 처리 및 결제 내역 중복 처리 방지</li>
          <li><strong>IAP 주문 정보</strong>: order id, 상품 SKU(중복 결제 방지 및 크레딧 지급)</li>
          <li><strong>서비스 로그</strong>: 오류 진단/부정 이용 방지 목적의 최소 로그(개인정보 최소화)</li>
        </ul>
        <p>서비스는 원칙적으로 이름/이메일/성별 등 실명 기반 개인정보를 입력받지 않습니다.</p>

        <h2>2. 업로드 파일 처리</h2>
        <div class="note">
          <ul>
            <li>업로드된 PDF는 처리 중에만 임시 저장되며 처리 완료 후 즉시 삭제를 원칙으로 합니다.</li>
            <li>PDF에서 추출된 텍스트는 맞춤법 검사를 위해 외부 API로 전송될 수 있습니다.</li>
            <li>서비스 제공 목적 외로 문서 내용을 저장/판매/공유하지 않습니다.</li>
          </ul>
        </div>

        <h2>3. 제3자 제공/처리위탁</h2>
        <p>서비스 제공을 위해 다음과 같은 외부 서비스가 사용될 수 있습니다.</p>
        <ul>
          <li>맞춤법 검사: 바른(Bareun) API 등</li>
          <li>인프라: Railway(서버 호스팅)</li>
          <li>결제/광고: Apps in Toss 제공 IAP/광고 기능</li>
        </ul>

        <h2>4. 보유 및 파기</h2>
        <ul>
          <li>업로드된 파일: 처리 완료 후 즉시 삭제를 원칙으로 합니다.</li>
          <li>크레딧/결제 중복 방지용 식별 정보 및 주문 ID: 서비스 운영/정산 및 부정 이용 방지를 위해 필요한 기간 동안 보관될 수 있습니다.</li>
        </ul>

        <h2>5. 이용자 권리</h2>
        <ul>
          <li>연결 끊기(회원 탈퇴) 시 서비스는 보유 중인 크레딧 관련 정보를 삭제할 수 있습니다.</li>
          <li>개인정보 관련 문의는 아래 이메일로 접수할 수 있습니다.</li>
        </ul>

        <h2>6. 문의</h2>
        <p>개인정보 관련 문의: <a href="mailto:{contact_email}">{contact_email}</a></p>
    """

    html = _legal_html_page('개인정보 처리방침', body, updated_at)
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


@app.route('/api/credits/balance', methods=['GET'])
def credits_balance():
    user_id = (request.args.get('user_id') or '').strip()
    if not user_id:
        return jsonify({
            'status': 'error',
            'message': 'user_id가 필요합니다',
        }), 400

    try:
        balance = int(credits_storage.get_balance(user_id))
    except Exception:
        balance = 0

    return jsonify({
        'status': 'success',
        'balance': balance,
    }), 200


@app.route('/api/iap/grant', methods=['POST'])
def iap_grant():
    data = request.get_json(silent=True) or {}
    user_id = (data.get('user_id') or '').strip()
    order_id = (data.get('order_id') or '').strip()
    sku = (data.get('sku') or '').strip()

    if not user_id or not order_id or not sku:
        return jsonify({
            'status': 'error',
            'message': 'user_id, order_id, sku가 필요합니다',
        }), 400

    credits = _credits_for_sku(sku)
    if credits <= 0:
        return jsonify({
            'status': 'error',
            'message': '유효하지 않은 sku입니다',
        }), 400

    result = credits_storage.grant_iap_order(
        user_id=user_id,
        order_id=order_id,
        sku=sku,
        credits=credits,
    )

    return jsonify({
        'status': 'success',
        'granted': bool(result.get('granted')),
        'credits_added': int(result.get('credits_added', 0) or 0),
        'balance': int(result.get('balance', 0) or 0),
    }), 200


@app.route('/api/toss/disconnect', methods=['POST', 'GET'])
def toss_disconnect():
    """
    Apps in Toss "연결 끊기(회원 탈퇴)" 콜백 엔드포인트.

    - 콘솔에서 설정한 Basic Auth 자격증명을 검증합니다.
    - 전달된 사용자 식별자(user_id/device_id/userKey 등)로 credits 데이터를 삭제합니다.
    """
    expected = _expected_disconnect_basic_auth()
    allow_insecure = _env_flag('ALLOW_INSECURE_DISCONNECT_NO_AUTH', default=False)

    if expected:
        exp_user, exp_pass = expected
        if not _verify_basic_auth(request.headers.get('Authorization'), exp_user, exp_pass):
            resp = jsonify({
                'status': 'error',
                'message': 'unauthorized',
            })
            resp.status_code = 401
            resp.headers['WWW-Authenticate'] = 'Basic realm="toss-disconnect"'
            return resp
    else:
        if not allow_insecure:
            # Secure-by-default: require auth in prod.
            return jsonify({
                'status': 'error',
                'message': 'disconnect callback auth not configured',
            }), 500

    payload = {}
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        if not payload:
            payload = {k: v for k, v in request.form.items()}

    args = {k: v for k, v in request.args.items()}

    # Do not log payload values (privacy). Optional debug prints only keys.
    if _env_flag('DEBUG_DISCONNECT_CALLBACK_KEYS', default=False):
        try:
            print(f"[disconnect] method={request.method} keys={list(payload.keys())} query_keys={list(args.keys())}")
        except Exception:
            pass

    def _pick(d: dict, key: str):
        if not isinstance(d, dict):
            return None
        v = d.get(key)
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    # Try common keys used by Apps in Toss / integrations.
    candidate_keys = [
        'user_id', 'userId',
        'device_id', 'deviceId',
        'userKey', 'user_key',
        'memberId', 'member_id',
    ]

    candidates = []
    for k in candidate_keys:
        v = _pick(payload, k)
        if v:
            candidates.append(v)
    for parent in ('data', 'user', 'member'):
        nested = payload.get(parent) if isinstance(payload, dict) else None
        if isinstance(nested, dict):
            for k in candidate_keys:
                v = _pick(nested, k)
                if v:
                    candidates.append(v)
    for k in candidate_keys:
        v = _pick(args, k)
        if v:
            candidates.append(v)

    # Also accept some header-based identifiers (rare).
    for hk in ('X-User-Id', 'X-Device-Id', 'X-User-Key', 'X-Toss-User-Key'):
        hv = (request.headers.get(hk) or '').strip()
        if hv:
            candidates.append(hv)

    # Deduplicate (preserve order)
    seen = set()
    user_ids = []
    for c in candidates:
        if not c:
            continue
        c2 = c[:256]  # avoid unbounded input
        if c2 in seen:
            continue
        seen.add(c2)
        user_ids.append(c2)

    purged = 0
    debug_details = _env_flag('DEBUG_DISCONNECT_CALLBACK_KEYS', default=False)
    details = []
    for uid in user_ids:
        try:
            res = credits_storage.purge_user(uid, keep_iap_order_ids=True)
            changed = int(res.get('credits_deleted', 0) or 0) + int(res.get('ledger_deleted', 0) or 0) + int(res.get('orders_changed', 0) or 0)
            if changed > 0:
                purged += 1
            if debug_details:
                details.append({
                    'credits_deleted': res.get('credits_deleted', 0),
                    'ledger_deleted': res.get('ledger_deleted', 0),
                    'orders_changed': res.get('orders_changed', 0),
                })
        except Exception:
            # Be idempotent/resilient: do not fail the callback on storage errors.
            continue

    response = {
        'status': 'success',
        'purged_users': purged,
    }
    if debug_details:
        response['details'] = details

    return jsonify(response), 200


@app.route('/api/check-pdf', methods=['POST'])
def check_pdf():
    """
    PDF 맞춤법 검사 API 엔드포인트

    Request:
        - multipart/form-data
        - pdf: PDF 파일
        - email: 이메일 주소

    Response:
        {
            'status': 'success' | 'error',
            'message': str,
            'errors_found': int
        }
    """
    try:
        # 1. 요청 검증
        if 'pdf' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'PDF 파일이 없습니다'
            }), 400

        pdf_file = request.files['pdf']
        # Email is optional (we're moving to miniapp flows and should avoid collecting PII by default).
        email = (request.form.get('email') or '').strip()
        # Pseudonymous device id for credits. Optional.
        user_id = (request.form.get('device_id') or '').strip()
        if not user_id:
            user_id = None

        # 파일명 검증
        if pdf_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '파일이 선택되지 않았습니다'
            }), 400

        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({
                'status': 'error',
                'message': 'PDF 파일만 업로드 가능합니다'
            }), 400

        # 파일 크기 검증 (20MB)
        pdf_file.seek(0, os.SEEK_END)
        file_size = pdf_file.tell()
        pdf_file.seek(0)

        if file_size > 20 * 1024 * 1024:  # 20MB
            return jsonify({
                'status': 'error',
                'message': '파일 크기는 20MB 이하여야 합니다'
            }), 400

        print(f"\n{'=' * 60}")
        print(f"새로운 요청: {pdf_file.filename}")
        if email:
            print("이메일: (provided)")
        else:
            print("이메일: (none)")
        print(f"파일 크기: {file_size / 1024 / 1024:.2f} MB")
        print(f"{'=' * 60}")

        # 2. 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        input_pdf_path = os.path.join(temp_dir, f"{file_id}_input.pdf")
        output_pdf_path = os.path.join(temp_dir, f"{file_id}_output.pdf")

        pdf_file.save(input_pdf_path)
        print(f"임시 파일 저장: {input_pdf_path}")

        # 3. 맞춤법 검사 실행
        result = processor.process(
            input_pdf_path,
            output_pdf_path,
            user_id=user_id,
            credits_storage=credits_storage,
        )

        # 3-1. 결제 필요(무료 한도 초과) 응답
        if result.get('code') == 'PAYMENT_REQUIRED':
            # 임시 파일 삭제
            try:
                if os.path.exists(input_pdf_path):
                    os.remove(input_pdf_path)
                if os.path.exists(output_pdf_path):
                    os.remove(output_pdf_path)
            except Exception as e:
                print(f"임시 파일 삭제 실패: {e}")

            return jsonify({
                'status': 'payment_required',
                'message': result.get('message') or '결제가 필요합니다.',
                'char_count': result.get('char_count', 0),
                'free_char_limit': result.get('free_char_limit', 0),
                'unit_chars': result.get('unit_chars', 0),
                'unit_price_won': result.get('unit_price_won', 0),
                'required_units': result.get('required_units', 0),
                'price_won': result.get('price_won', 0),
                'credits_balance': result.get('credits_balance', 0),
            }), 402

        # 4. (Optional) store request metadata.
        # Default off to avoid collecting/storing PII in server files (Apps in Toss review readiness).
        enable_email_csv = str(os.getenv('ENABLE_USER_EMAIL_CSV', '')).lower() in ('1', 'true', 'yes')
        if enable_email_csv and email:
            try:
                csv_file = 'user_emails.csv'
                file_exists = os.path.exists(csv_file)

                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=['timestamp', 'email', 'filename', 'errors_found']
                    )
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow({
                        'timestamp': datetime.datetime.now().isoformat(),
                        'email': email,
                        'filename': pdf_file.filename,
                        'errors_found': result['errors_found']
                    })
                print("이메일 저장 완료")
            except Exception as e:
                print(f"이메일 저장 실패: {e}")

        # 5. PDF 파일 반환 (다운로드)
        if result['success']:
            # 오류가 있으면 수정된 PDF, 없으면 원본 PDF
            pdf_to_send = output_pdf_path if result['errors_found'] > 0 else input_pdf_path

            if os.path.exists(pdf_to_send):
                # 파일 이름 생성
                base_name = os.path.splitext(pdf_file.filename)[0]
                download_name = f"{base_name}_맞춤법검사.pdf"

                # 파일 읽기
                with open(pdf_to_send, 'rb') as f:
                    pdf_data = f.read()

                # Response 생성
                response = make_response(pdf_data)
                response.headers['Content-Type'] = 'application/pdf'

                # Content-Disposition 헤더 설정 (RFC 5987 형식으로 한글 파일명 지원)
                # ASCII 안전한 파일명과 UTF-8 인코딩된 파일명 모두 제공
                ascii_filename = "grammar_checked.pdf"
                encoded_filename = quote(download_name)
                response.headers['Content-Disposition'] = (
                    f"attachment; filename=\"{ascii_filename}\"; "
                    f"filename*=UTF-8''{encoded_filename}"
                )

                # 오류 개수를 헤더에 추가
                response.headers['X-Errors-Found'] = str(result['errors_found'])
                # Character count (for UI/debugging; does not expose content).
                if 'char_count' in result and result.get('char_count') is not None:
                    response.headers['X-Char-Count'] = str(result.get('char_count'))
                # CORS 헤더 명시적으로 추가
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'X-Errors-Found, X-Char-Count, Content-Disposition'

                # Clean up temp files after reading into memory.
                try:
                    if os.path.exists(input_pdf_path):
                        os.remove(input_pdf_path)
                    if os.path.exists(output_pdf_path):
                        os.remove(output_pdf_path)
                except Exception as e:
                    print(f"임시 파일 삭제 실패: {e}")

                return response
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'PDF 파일 생성에 실패했습니다'
                }), 500
        else:
            # 임시 파일 삭제
            try:
                if os.path.exists(input_pdf_path):
                    os.remove(input_pdf_path)
                if os.path.exists(output_pdf_path):
                    os.remove(output_pdf_path)
            except Exception as e:
                print(f"임시 파일 삭제 실패: {e}")

            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 500

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'서버 오류: {str(e)}'
        }), 500




@app.route('/api/survey', methods=['POST'])
def submit_survey():
    """
    설문조사 제출 API

    Request:
        - application/json
        - source: 유입 경로 (search, sns, recommend, other)
        - purpose: 사용 목적 (work, study, personal, other)
        - email: 이메일 (선택)

    Response:
        {'status': 'success', 'message': '설문조사가 제출되었습니다'}
    """
    try:
        data = request.get_json()

        source = data.get('source')
        purpose = data.get('purpose')
        email = (data.get('email') or '').strip()

        if not source or not purpose:
            return jsonify({
                'status': 'error',
                'message': '필수 항목이 누락되었습니다'
            }), 400

        # 설문조사 데이터 저장 (PII 최소화)
        import datetime
        timestamp = datetime.datetime.now().isoformat()

        survey_log = {
            'timestamp': timestamp,
            'source': source,
            'purpose': purpose,
            'email': email or 'anonymous'
        }

        # Avoid logging raw email.
        print(f"\n[설문조사 응답] timestamp={timestamp} source={source} purpose={purpose} email={'provided' if email else 'none'}")

        # CSV 저장은 기본 비활성화 (ephemeral FS + PII 이슈)
        enable_survey_csv = str(os.getenv('ENABLE_SURVEY_CSV', '')).lower() in ('1', 'true', 'yes')
        if enable_survey_csv:
            import csv
            csv_file = 'survey_responses.csv'
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'source', 'purpose', 'email'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow(survey_log)

        return jsonify({
            'status': 'success',
            'message': '설문조사가 제출되었습니다'
        }), 200

    except Exception as e:
        print(f"설문조사 저장 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': '설문조사 제출 중 오류가 발생했습니다'
        }), 500


# ==================== 결제 API ====================

@app.route('/api/payment/create', methods=['POST'])
def create_payment():
    """
    결제 생성 API - 주문 정보 생성

    Request:
        - application/json
        - email: 구매자 이메일

    Response:
        {
            'status': 'success',
            'order_id': str,
            'amount': int,
            'product_name': str
        }
    """
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({
                'status': 'error',
                'message': '이메일 주소가 필요합니다.'
            }), 400

        # 주문 ID 생성
        order_id = payment_storage.generate_order_id()

        # 결제 기록 생성 (대기 상태)
        payment_storage.create_payment(
            order_id=order_id,
            amount=PRODUCT_AMOUNT,
            email=email,
            product_name=PRODUCT_NAME
        )

        print(f"\n[결제 생성] order_id: {order_id}, email: {email}, amount: {PRODUCT_AMOUNT}")

        return jsonify({
            'status': 'success',
            'order_id': order_id,
            'amount': PRODUCT_AMOUNT,
            'product_name': PRODUCT_NAME,
            'client_key': os.getenv('TOSS_CLIENT_KEY', '')
        }), 200

    except Exception as e:
        print(f"결제 생성 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': f'결제 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/payment/confirm', methods=['POST'])
def confirm_payment():
    """
    결제 승인 API - 토스페이먼츠 결제 승인 요청

    Request:
        - application/json
        - paymentKey: 결제 키
        - orderId: 주문 ID
        - amount: 결제 금액

    Response:
        {
            'status': 'success' | 'error',
            'message': str,
            'receipt_url': str (성공 시)
        }
    """
    try:
        data = request.get_json()

        payment_key = data.get('paymentKey')
        order_id = data.get('orderId')
        amount = data.get('amount')

        # 필수 파라미터 검증
        if not all([payment_key, order_id, amount]):
            return jsonify({
                'status': 'error',
                'message': '필수 파라미터가 누락되었습니다.'
            }), 400

        # 금액 검증 (서버에서 저장한 금액과 일치하는지)
        saved_payment = payment_storage.get_payment_by_order_id(order_id)
        if not saved_payment:
            return jsonify({
                'status': 'error',
                'message': '유효하지 않은 주문입니다.'
            }), 400

        if int(saved_payment['amount']) != int(amount):
            return jsonify({
                'status': 'error',
                'message': '결제 금액이 일치하지 않습니다.'
            }), 400

        print(f"\n[결제 승인 요청] order_id: {order_id}, amount: {amount}")

        # 토스페이먼츠 결제 승인 요청
        result = toss_payments.confirm_payment(
            payment_key=payment_key,
            order_id=order_id,
            amount=int(amount)
        )

        if result.success:
            # 결제 완료 처리
            payment_storage.complete_payment(
                order_id=order_id,
                payment_key=payment_key,
                method=result.method or '',
                approved_at=result.approved_at or datetime.datetime.now().isoformat(),
                receipt_url=result.receipt_url
            )

            print(f"[결제 승인 완료] order_id: {order_id}")

            return jsonify({
                'status': 'success',
                'message': '결제가 완료되었습니다.',
                'order_id': order_id,
                'amount': result.amount,
                'method': result.method,
                'approved_at': result.approved_at,
                'receipt_url': result.receipt_url
            }), 200
        else:
            # 결제 실패 처리
            payment_storage.fail_payment(order_id, result.error_message or '결제 실패')

            print(f"[결제 승인 실패] order_id: {order_id}, error: {result.error_message}")

            return jsonify({
                'status': 'error',
                'code': result.error_code,
                'message': result.error_message
            }), 400

    except Exception as e:
        print(f"결제 승인 오류: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'결제 승인 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/payment/cancel', methods=['POST'])
def cancel_payment():
    """
    결제 취소 API

    Request:
        - application/json
        - orderId: 주문 ID
        - cancelReason: 취소 사유

    Response:
        {'status': 'success' | 'error', 'message': str}
    """
    try:
        data = request.get_json()

        order_id = data.get('orderId')
        cancel_reason = data.get('cancelReason', '고객 요청')

        if not order_id:
            return jsonify({
                'status': 'error',
                'message': '주문 ID가 필요합니다.'
            }), 400

        # 저장된 결제 정보 조회
        saved_payment = payment_storage.get_payment_by_order_id(order_id)
        if not saved_payment:
            return jsonify({
                'status': 'error',
                'message': '유효하지 않은 주문입니다.'
            }), 400

        if saved_payment['status'] != 'completed':
            return jsonify({
                'status': 'error',
                'message': '취소할 수 없는 결제 상태입니다.'
            }), 400

        # 토스페이먼츠 결제 취소 요청
        result = toss_payments.cancel_payment(
            payment_key=saved_payment['payment_key'],
            cancel_reason=cancel_reason
        )

        if result.success:
            payment_storage.cancel_payment(order_id, cancel_reason)
            return jsonify({
                'status': 'success',
                'message': '결제가 취소되었습니다.'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'code': result.error_code,
                'message': result.error_message
            }), 400

    except Exception as e:
        print(f"결제 취소 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': f'결제 취소 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/payment/status/<order_id>', methods=['GET'])
def get_payment_status(order_id):
    """
    결제 상태 조회 API

    Response:
        {
            'status': 'success',
            'payment': {
                'order_id': str,
                'amount': int,
                'status': str,
                ...
            }
        }
    """
    try:
        payment = payment_storage.get_payment_by_order_id(order_id)

        if not payment:
            return jsonify({
                'status': 'error',
                'message': '결제 정보를 찾을 수 없습니다.'
            }), 404

        return jsonify({
            'status': 'success',
            'payment': {
                'order_id': payment['order_id'],
                'amount': int(payment['amount']),
                'product_name': payment['product_name'],
                'payment_status': payment['status'],
                'method': payment.get('method', ''),
                'approved_at': payment.get('approved_at', ''),
                'receipt_url': payment.get('receipt_url', '')
            }
        }), 200

    except Exception as e:
        print(f"결제 상태 조회 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': f'결제 상태 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """
    결제 검증 API - 이메일로 유효한 결제가 있는지 확인

    Request:
        - application/json
        - email: 확인할 이메일

    Response:
        {
            'status': 'success',
            'has_valid_payment': bool
        }
    """
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({
                'status': 'error',
                'message': '이메일 주소가 필요합니다.'
            }), 400

        has_payment = payment_storage.has_valid_subscription(email)

        return jsonify({
            'status': 'success',
            'has_valid_payment': has_payment
        }), 200

    except Exception as e:
        print(f"결제 검증 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': f'결제 검증 중 오류가 발생했습니다: {str(e)}'
        }), 500


# ==================== 기존 API ====================

@app.route('/api/test', methods=['GET'])
def test():
    """테스트 엔드포인트"""
    return jsonify({
        'message': 'API가 정상적으로 작동 중입니다',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print("\n" + "=" * 60)
    print("PDF 맞춤법 검사 API 서버 시작")
    print("=" * 60)
    print(f"포트: {port}")
    print(f"디버그 모드: {debug}")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
