#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API 서버
PDF 맞춤법 검사 API 제공
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import uuid
import csv
import datetime
import hashlib
import time
import json
from main_processor import GrammarCheckProcessor
from email_sender import EmailSender
from pricing import pricing_calculator
from toss_payments import toss_payments
from pdf_extractor import SimplePDFExtractor
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 허용

# 프로세서 및 이메일 발송기 초기화
processor = GrammarCheckProcessor()
email_sender = EmailSender()

# 에러 코드 정의
ERROR_CODES = {
    'FILE_TOO_LARGE': '파일 크기가 너무 큽니다 (최대 20MB)',
    'TOO_MANY_CHARS': '글자 수가 너무 많습니다',
    'PDF_READ_FAILED': 'PDF 파일을 읽을 수 없습니다. 파일이 손상되었거나 암호화되어 있을 수 있습니다.',
    'NO_TEXT_FOUND': 'PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.',
    'PAYMENT_REQUIRED': '결제가 필요합니다',
    'PROCESSING_FAILED': '처리 중 오류가 발생했습니다'
}

# 제한 설정
MAX_FILE_SIZE_MB = 20
MAX_CHAR_LIMIT = 500000  # 50만자 제한

# PDF 분석 세션 저장소 (메모리 기반, 1시간 만료)
# 보안: 결제 요청 시 char_count 조작 방지
class PDFAnalysisSessionStore:
    """PDF 분석 결과를 저장하여 결제 검증에 사용"""

    def __init__(self, expiry_seconds=3600):
        self._store = {}  # {session_id: {char_count, file_hash, timestamp, email}}
        self.expiry_seconds = expiry_seconds

    def create_session(self, char_count: int, file_hash: str, email: str = None) -> str:
        """분석 세션 생성 및 ID 반환"""
        self._cleanup_expired()
        session_id = str(uuid.uuid4())
        self._store[session_id] = {
            'char_count': char_count,
            'file_hash': file_hash,
            'email': email,
            'timestamp': time.time()
        }
        print(f"[세션] 생성: {session_id[:8]}... (글자수: {char_count:,}, 해시: {file_hash[:16]}...)")
        return session_id

    def get_session(self, session_id: str) -> dict:
        """세션 데이터 조회 (없거나 만료 시 None)"""
        self._cleanup_expired()
        session = self._store.get(session_id)
        if session and (time.time() - session['timestamp']) < self.expiry_seconds:
            return session
        return None

    def invalidate_session(self, session_id: str):
        """세션 무효화 (결제 완료 후)"""
        if session_id in self._store:
            del self._store[session_id]
            print(f"[세션] 무효화: {session_id[:8]}...")

    def _cleanup_expired(self):
        """만료된 세션 정리"""
        now = time.time()
        expired = [sid for sid, data in self._store.items()
                   if (now - data['timestamp']) >= self.expiry_seconds]
        for sid in expired:
            del self._store[sid]

# 세션 저장소 인스턴스
pdf_session_store = PDFAnalysisSessionStore()

# 결제 토큰 저장소 (결제 완료 후 PDF 처리 권한 부여)
class PaymentTokenStore:
    """결제 완료 토큰 저장소"""

    def __init__(self, expiry_seconds=3600):
        self._store = {}  # {token: {order_id, amount, char_count, timestamp}}
        self.expiry_seconds = expiry_seconds

    def create_token(self, order_id: str, amount: int, char_count: int, file_hash: str = None) -> str:
        """결제 완료 토큰 생성"""
        self._cleanup_expired()
        token = str(uuid.uuid4())
        self._store[token] = {
            'order_id': order_id,
            'amount': amount,
            'char_count': char_count,
            'file_hash': file_hash,
            'timestamp': time.time(),
            'used': False
        }
        print(f"[결제토큰] 생성: {token[:8]}... (주문: {order_id})")
        return token

    def validate_and_use_token(self, token: str) -> dict:
        """토큰 검증 및 사용 (1회용)"""
        self._cleanup_expired()
        data = self._store.get(token)
        if not data:
            return None
        if data['used']:
            return None
        if (time.time() - data['timestamp']) >= self.expiry_seconds:
            return None
        # 토큰 사용 처리
        self._store[token]['used'] = True
        print(f"[결제토큰] 사용: {token[:8]}...")
        return data

    def _cleanup_expired(self):
        """만료된 토큰 정리"""
        now = time.time()
        expired = [t for t, data in self._store.items()
                   if (now - data['timestamp']) >= self.expiry_seconds]
        for t in expired:
            del self._store[t]

payment_token_store = PaymentTokenStore()


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'service': 'PDF Grammar Checker'
    }), 200


@app.route('/api/check-pdf', methods=['POST'])
def check_pdf():
    """
    PDF 맞춤법 검사 API 엔드포인트

    Request:
        - multipart/form-data
        - pdf: PDF 파일
        - email: 이메일 주소
        - free_mode: 'true'이면 5만자까지만 무료로 검사 (선택)
        - payment_token: 결제 완료 토큰 (유료 결제 시)
        - order_id: 주문 ID (유료 결제 시)

    Response:
        PDF 파일 또는 에러 JSON
    """
    try:
        # 1. 요청 검증
        if 'pdf' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'PDF 파일이 없습니다'
            }), 400

        if 'email' not in request.form:
            return jsonify({
                'status': 'error',
                'message': '이메일 주소가 없습니다'
            }), 400

        pdf_file = request.files['pdf']
        email = request.form['email']
        free_mode = request.form.get('free_mode', 'false').lower() == 'true'
        payment_token = request.form.get('payment_token')
        order_id = request.form.get('order_id')

        # 결제 토큰 검증 (유료 처리용)
        payment_data = None
        if payment_token:
            payment_data = payment_token_store.validate_and_use_token(payment_token)
            if not payment_data:
                return jsonify({
                    'status': 'error',
                    'error_code': 'INVALID_PAYMENT_TOKEN',
                    'message': '유효하지 않거나 이미 사용된 결제 토큰입니다.'
                }), 400
            print(f"[처리] 결제 토큰 확인: {payment_token[:8]}... (주문: {order_id})")

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
        print(f"[API] /api/check-pdf 요청")
        print(f"{'=' * 60}")
        print(f"  파일명: {pdf_file.filename}")
        print(f"  이메일: {email}")
        print(f"  파일 크기: {file_size / 1024 / 1024:.2f} MB")
        print(f"  무료 모드: {free_mode}")
        print(f"{'=' * 60}")

        # 2. 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        input_pdf_path = os.path.join(temp_dir, f"{file_id}_input.pdf")
        output_pdf_path = os.path.join(temp_dir, f"{file_id}_output.pdf")

        pdf_file.save(input_pdf_path)
        print(f"[저장] 임시 파일: {input_pdf_path}")

        # 3. 글자 수 확인
        try:
            extractor = SimplePDFExtractor(input_pdf_path)
            text_with_positions, raw_text = extractor.extract_text_with_positions()
            char_count = len(raw_text.strip())
            print(f"[분석] 총 글자 수: {char_count:,}자")
        except Exception as e:
            print(f"[오류] PDF 텍스트 추출 실패: {e}")
            return jsonify({
                'status': 'error',
                'error_code': 'PDF_READ_FAILED',
                'message': ERROR_CODES['PDF_READ_FAILED']
            }), 400

        # 4. 글자 수 제한 및 결제 체크
        FREE_LIMIT = 50000
        is_paid = payment_data is not None

        if char_count > FREE_LIMIT and not free_mode and not is_paid:
            # 결제가 필요한 경우 (유료 결제 안 됨, 무료 모드 아님)
            price_info = pricing_calculator.calculate_price(char_count)
            print(f"[결제필요] {char_count:,}자 > {FREE_LIMIT:,}자 (무료한도)")
            print(f"[결제필요] 예상 금액: {price_info['price']:,}원")

            return jsonify({
                'status': 'payment_required',
                'error_code': 'PAYMENT_REQUIRED',
                'message': f'글자 수가 무료 한도({FREE_LIMIT:,}자)를 초과했습니다.',
                'char_count': char_count,
                'free_limit': FREE_LIMIT,
                'price_info': price_info,
                'options': {
                    'pay': f'{price_info["price"]:,}원 결제 후 전체 검사',
                    'free_mode': f'무료로 처음 {FREE_LIMIT:,}자만 검사 (free_mode=true)'
                }
            }), 402

        # 5. 맞춤법 검사 실행
        # - 무료 모드: 5만자까지만
        # - 결제 완료: 전체 검사
        # - 5만자 이하: 전체 검사
        max_chars = None
        if free_mode and char_count > FREE_LIMIT:
            max_chars = FREE_LIMIT
            print(f"[무료모드] {FREE_LIMIT:,}자까지만 검사합니다 (전체: {char_count:,}자)")
        elif is_paid:
            print(f"[유료처리] 결제 확인됨, 전체 {char_count:,}자 검사")

        print(f"[처리] 맞춤법 검사 시작...")
        result = processor.process(input_pdf_path, output_pdf_path, max_chars=max_chars)
        print(f"[처리] 검사 완료 - 오류 {result['errors_found']}개 발견")

        # 6. 이메일을 CSV에 저장
        try:
            csv_file = 'user_emails.csv'
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'email', 'filename', 'char_count', 'errors_found', 'free_mode'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'email': email,
                    'filename': pdf_file.filename,
                    'char_count': char_count,
                    'errors_found': result['errors_found'],
                    'free_mode': free_mode
                })
            print(f"[저장] 이메일 기록 완료: {email}")
        except Exception as e:
            print(f"[오류] 이메일 저장 실패: {e}")

        # 7. 이메일 발송 및 PDF 파일 반환
        if result['success']:
            # 오류가 있으면 수정된 PDF, 없으면 원본 PDF
            pdf_to_send = output_pdf_path if result['errors_found'] > 0 else input_pdf_path

            if os.path.exists(pdf_to_send):
                # 파일 이름 생성
                base_name = os.path.splitext(pdf_file.filename)[0]
                download_name = f"{base_name}_맞춤법검사.pdf"

                # 이메일 발송
                email_success = False
                email_error_msg = None
                try:
                    print(f"[이메일] 발송 시작: {email}")
                    email_success = email_sender.send_grammar_check_result(
                        to_email=email,
                        pdf_path=pdf_to_send,
                        errors_count=result['errors_found'],
                        original_filename=pdf_file.filename
                    )
                    if email_success:
                        print(f"[이메일] ✓ 발송 성공: {email}")
                    else:
                        print(f"[이메일] ✗ 발송 실패: {email}")
                        email_error_msg = '이메일 발송에 실패했습니다'
                except Exception as e:
                    print(f"[이메일] ✗ 발송 중 오류: {e}")
                    email_error_msg = str(e)

                print(f"[응답] PDF 파일 반환: {download_name}")
                response = send_file(
                    pdf_to_send,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=download_name
                )
                # 응답 헤더에 정보 추가
                response.headers['X-Errors-Found'] = str(result['errors_found'])
                response.headers['X-Char-Count'] = str(char_count)
                response.headers['X-Free-Mode'] = str(free_mode)
                response.headers['X-Email-Sent'] = str(email_success)
                if email_error_msg:
                    response.headers['X-Email-Error'] = email_error_msg
                # CORS 헤더 명시적으로 추가
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'X-Errors-Found, X-Char-Count, X-Free-Mode, X-Email-Sent, X-Email-Error'
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




@app.route('/api/analyze-pdf', methods=['POST'])
def analyze_pdf():
    """
    PDF 분석 API - 글자 수 확인 및 가격 계산

    Request:
        - multipart/form-data
        - pdf: PDF 파일

    Response:
        {
            'status': 'success' | 'error',
            'char_count': int,
            'price_info': {...},
            'needs_payment': bool
        }
    """
    try:
        if 'pdf' not in request.files:
            return jsonify({
                'status': 'error',
                'error_code': 'NO_FILE',
                'message': 'PDF 파일이 없습니다'
            }), 400

        pdf_file = request.files['pdf']

        if pdf_file.filename == '':
            return jsonify({
                'status': 'error',
                'error_code': 'NO_FILE',
                'message': '파일이 선택되지 않았습니다'
            }), 400

        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({
                'status': 'error',
                'error_code': 'INVALID_FILE',
                'message': 'PDF 파일만 업로드 가능합니다'
            }), 400

        # 파일 크기 검증
        pdf_file.seek(0, os.SEEK_END)
        file_size = pdf_file.tell()
        pdf_file.seek(0)

        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return jsonify({
                'status': 'error',
                'error_code': 'FILE_TOO_LARGE',
                'message': ERROR_CODES['FILE_TOO_LARGE']
            }), 400

        # 파일 해시 계산 (보안용)
        pdf_content = pdf_file.read()
        file_hash = hashlib.sha256(pdf_content).hexdigest()
        pdf_file.seek(0)

        # 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        temp_pdf_path = os.path.join(temp_dir, f"{file_id}_analyze.pdf")
        pdf_file.save(temp_pdf_path)

        print(f"\n[분석] PDF 분석 시작: {pdf_file.filename}")
        print(f"[분석] 파일 해시: {file_hash[:16]}...")

        try:
            # PDF에서 글자 수 추출
            extractor = SimplePDFExtractor(temp_pdf_path)
            text_with_positions, raw_text = extractor.extract_text_with_positions()
            char_count = len(raw_text.strip())

            print(f"[분석] 총 글자 수: {char_count:,}자")

            if char_count == 0:
                return jsonify({
                    'status': 'error',
                    'error_code': 'NO_TEXT_FOUND',
                    'message': ERROR_CODES['NO_TEXT_FOUND']
                }), 400

            if char_count > MAX_CHAR_LIMIT:
                return jsonify({
                    'status': 'error',
                    'error_code': 'TOO_MANY_CHARS',
                    'message': f'{ERROR_CODES["TOO_MANY_CHARS"]} (최대 {MAX_CHAR_LIMIT:,}자, 현재 {char_count:,}자)'
                }), 400

            # 가격 계산
            price_info = pricing_calculator.calculate_price(char_count)
            needs_payment = not price_info['is_free']

            # 결제가 필요한 경우 세션 생성 (보안)
            session_id = None
            order_id = None
            if needs_payment:
                session_id = pdf_session_store.create_session(
                    char_count=char_count,
                    file_hash=file_hash
                )
                order_id = f"order_{session_id[:12]}"
                print(f"[분석] 결제 필요: {price_info['price']:,}원 (세션: {session_id[:8]}...)")

            response_data = {
                'status': 'success',
                'char_count': char_count,
                'price_info': price_info,
                'needs_payment': needs_payment,
                'file_size_mb': round(file_size / 1024 / 1024, 2)
            }

            # 결제가 필요한 경우 추가 필드
            if needs_payment:
                response_data['amount'] = price_info['price']
                response_data['session_id'] = session_id
                response_data['order_id'] = order_id
                response_data['file_hash'] = file_hash

            return jsonify(response_data), 200

        except Exception as e:
            print(f"[오류] PDF 분석 실패: {e}")
            return jsonify({
                'status': 'error',
                'error_code': 'PDF_READ_FAILED',
                'message': ERROR_CODES['PDF_READ_FAILED']
            }), 400

        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    except Exception as e:
        print(f"분석 API 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'error_code': 'SERVER_ERROR',
            'message': f'서버 오류: {str(e)}'
        }), 500


@app.route('/api/pricing', methods=['GET'])
def get_pricing():
    """요금 정보 조회 API"""
    return jsonify({
        'status': 'success',
        'pricing': pricing_calculator.get_price_info()
    }), 200


@app.route('/api/payment/request', methods=['POST'])
def create_payment_request():
    """
    결제 요청 생성 API

    Request:
        - application/json
        - session_id: 분석 세션 ID (필수, 보안 검증용)
        - amount: 결제 금액
        - email: 고객 이메일

    Response:
        결제 요청 정보 (프론트엔드에서 토스페이먼츠 SDK에 전달)
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        amount = data.get('amount')
        email = data.get('email')

        if not all([session_id, amount, email]):
            return jsonify({
                'status': 'error',
                'message': '필수 항목이 누락되었습니다 (session_id, amount, email 필요)'
            }), 400

        # 세션 검증 (보안: 클라이언트가 char_count 조작 불가)
        session = pdf_session_store.get_session(session_id)
        if not session:
            print(f"[결제] 세션 없음 또는 만료: {session_id[:8] if session_id else 'None'}...")
            return jsonify({
                'status': 'error',
                'error_code': 'SESSION_EXPIRED',
                'message': '분석 세션이 만료되었습니다. PDF를 다시 분석해주세요.'
            }), 400

        # 서버에 저장된 char_count로 가격 계산 (조작 방지)
        char_count = session['char_count']
        expected_price = pricing_calculator.calculate_price(char_count)

        if expected_price['price'] != amount:
            print(f"[결제] 금액 불일치: 요청={amount}, 예상={expected_price['price']}")
            return jsonify({
                'status': 'error',
                'error_code': 'PRICE_MISMATCH',
                'message': '결제 금액이 일치하지 않습니다. PDF를 다시 분석해주세요.'
            }), 400

        # 결제 요청 정보 생성
        order_id = f"order_{session_id[:12]}"
        payment_request = toss_payments.create_payment_request(
            amount=amount,
            order_name=f'PDF 맞춤법 검사 ({char_count:,}자)',
            customer_email=email,
            char_count=char_count,
            order_id=order_id
        )

        print(f"[결제] 요청 생성: {order_id}, {amount:,}원, {email}")

        return jsonify({
            'status': 'success',
            'payment': payment_request,
            'order_id': order_id
        }), 200

    except Exception as e:
        print(f"[오류] 결제 요청 생성 실패: {e}")
        return jsonify({
            'status': 'error',
            'message': f'결제 요청 생성 실패: {str(e)}'
        }), 500


@app.route('/api/payment/confirm', methods=['POST'])
def confirm_payment():
    """
    결제 승인 API (토스페이먼츠 콜백 후 서버에서 호출)

    Request:
        - application/json
        - paymentKey: 토스페이먼츠 결제 키
        - orderId: 주문 ID
        - amount: 결제 금액
        - session_id: 분석 세션 ID (선택, 보안 강화용)

    Response:
        {
            'success': bool,
            'payment_token': str (결제 완료 토큰, check-pdf에서 사용)
        }
    """
    try:
        data = request.get_json()
        payment_key = data.get('paymentKey')
        order_id = data.get('orderId')
        amount = data.get('amount')
        session_id = data.get('session_id')  # 선택적

        if not all([payment_key, order_id, amount]):
            return jsonify({
                'status': 'error',
                'success': False,
                'message': '필수 항목이 누락되었습니다 (paymentKey, orderId, amount)'
            }), 400

        # 세션이 제공된 경우 검증
        char_count = None
        file_hash = None
        if session_id:
            session = pdf_session_store.get_session(session_id)
            if session:
                char_count = session['char_count']
                file_hash = session.get('file_hash')
                # 세션의 금액과 일치하는지 확인
                expected_price = pricing_calculator.calculate_price(char_count)
                if expected_price['price'] != amount:
                    print(f"[결제확인] 금액 불일치: 요청={amount}, 세션={expected_price['price']}")

        print(f"[결제확인] 승인 요청: {order_id}, {amount:,}원")

        # 결제 승인 요청
        result = toss_payments.confirm_payment(payment_key, order_id, amount)

        if result['success']:
            # 결제 성공 로깅
            print(f"[결제확인] ✓ 승인 성공: {order_id}, {amount:,}원")

            # 결제 토큰 생성 (PDF 처리 권한)
            payment_token = payment_token_store.create_token(
                order_id=order_id,
                amount=amount,
                char_count=char_count,
                file_hash=file_hash
            )

            # 분석 세션 무효화
            if session_id:
                pdf_session_store.invalidate_session(session_id)

            # 결제 내역 CSV 저장
            try:
                csv_file = 'payment_history.csv'
                file_exists = os.path.exists(csv_file)

                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'timestamp', 'order_id', 'payment_key', 'amount', 'status', 'payment_token'
                    ])
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow({
                        'timestamp': datetime.datetime.now().isoformat(),
                        'order_id': order_id,
                        'payment_key': payment_key,
                        'amount': amount,
                        'status': 'confirmed',
                        'payment_token': payment_token[:8] + '...'
                    })
            except Exception as e:
                print(f"[오류] 결제 내역 저장 실패: {e}")

            return jsonify({
                'status': 'success',
                'success': True,
                'message': '결제가 완료되었습니다',
                'payment_token': payment_token,
                'order_id': order_id
            }), 200
        else:
            print(f"[결제확인] ✗ 승인 실패: {result.get('error_message')}")
            return jsonify({
                'status': 'error',
                'success': False,
                'message': result.get('error_message', '결제 승인 실패'),
                'error_code': result.get('error_code')
            }), 400

    except Exception as e:
        print(f"[오류] 결제 승인 실패: {e}")
        return jsonify({
            'status': 'error',
            'success': False,
            'message': f'결제 승인 실패: {str(e)}'
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
        email = data.get('email', 'anonymous')

        if not source or not purpose:
            return jsonify({
                'status': 'error',
                'message': '필수 항목이 누락되었습니다'
            }), 400

        # 설문조사 데이터 저장 (현재는 로그만 출력, 추후 DB 저장)
        import datetime
        timestamp = datetime.datetime.now().isoformat()

        survey_log = {
            'timestamp': timestamp,
            'source': source,
            'purpose': purpose,
            'email': email
        }

        print(f"\n[설문조사 응답] {survey_log}")

        # CSV 파일로 저장 (간단한 로깅)
        import csv
        import os

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
