#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API 서버
PDF 맞춤법 검사 API 제공
"""
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import os
import tempfile
import uuid
import csv
import datetime
from urllib.parse import quote
from main_processor import GrammarCheckProcessor
from email_sender import EmailSender
from toss_payments import TossPayments
from payment_storage import PaymentStorage
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 허용

# 프로세서 및 이메일 발송기 초기화
processor = GrammarCheckProcessor()
email_sender = EmailSender()

# 결제 시스템 초기화
toss_payments = TossPayments()
payment_storage = PaymentStorage()

# 상품 정보 (환경변수에서 가져오거나 기본값 사용)
PRODUCT_AMOUNT = int(os.getenv('PRODUCT_AMOUNT', '3900'))  # 기본 3,900원
PRODUCT_NAME = os.getenv('PRODUCT_NAME', 'PDF 맞춤법 검사 프리미엄')


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
        result = processor.process(input_pdf_path, output_pdf_path)

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
                # CORS 헤더 명시적으로 추가
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'X-Errors-Found, Content-Disposition'

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
