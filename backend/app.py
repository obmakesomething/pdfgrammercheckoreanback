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

        if 'email' not in request.form:
            return jsonify({
                'status': 'error',
                'message': '이메일 주소가 없습니다'
            }), 400

        pdf_file = request.files['pdf']
        email = request.form['email']

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
        print(f"이메일: {email}")
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

        # 4. 이메일을 CSV에 저장
        try:
            csv_file = 'user_emails.csv'
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'email', 'filename', 'errors_found'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'email': email,
                    'filename': pdf_file.filename,
                    'errors_found': result['errors_found']
                })
            print(f"이메일 저장 완료: {email}")
        except Exception as e:
            print(f"이메일 저장 실패: {e}")

        # 5. 이메일 발송 및 PDF 파일 반환
        if result['success']:
            # 오류가 있으면 수정된 PDF, 없으면 원본 PDF
            pdf_to_send = output_pdf_path if result['errors_found'] > 0 else input_pdf_path

            if os.path.exists(pdf_to_send):
                # 파일 이름 생성
                base_name = os.path.splitext(pdf_file.filename)[0]
                download_name = f"{base_name}_맞춤법검사.pdf"

                # 이메일 발송
                try:
                    email_success = email_sender.send_grammar_check_result(
                        to_email=email,
                        pdf_path=pdf_to_send,
                        errors_count=result['errors_found'],
                        original_filename=pdf_file.filename
                    )
                    if email_success:
                        print(f"✓ 이메일 발송 성공: {email}")
                    else:
                        print(f"✗ 이메일 발송 실패: {email}")
                except Exception as email_error:
                    print(f"✗ 이메일 발송 중 오류: {email_error}")

                response = send_file(
                    pdf_to_send,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=download_name
                )
                # 오류 개수를 헤더에 추가
                response.headers['X-Errors-Found'] = str(result['errors_found'])
                # CORS 헤더 명시적으로 추가
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Expose-Headers'] = 'X-Errors-Found'
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

        # 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        temp_pdf_path = os.path.join(temp_dir, f"{file_id}_analyze.pdf")
        pdf_file.save(temp_pdf_path)

        try:
            # PDF에서 글자 수 추출
            extractor = SimplePDFExtractor(temp_pdf_path)
            text_with_positions, raw_text = extractor.extract_text_with_positions()
            char_count = len(raw_text.strip())

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

            return jsonify({
                'status': 'success',
                'char_count': char_count,
                'price_info': price_info,
                'needs_payment': not price_info['is_free'],
                'file_size_mb': round(file_size / 1024 / 1024, 2)
            }), 200

        except Exception as e:
            print(f"PDF 분석 오류: {e}")
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
        - amount: 결제 금액
        - char_count: 글자 수
        - email: 고객 이메일

    Response:
        결제 요청 정보 (프론트엔드에서 토스페이먼츠 SDK에 전달)
    """
    try:
        data = request.get_json()
        amount = data.get('amount')
        char_count = data.get('char_count')
        email = data.get('email')

        if not all([amount, char_count, email]):
            return jsonify({
                'status': 'error',
                'message': '필수 항목이 누락되었습니다'
            }), 400

        # 가격 검증
        expected_price = pricing_calculator.calculate_price(char_count)
        if expected_price['price'] != amount:
            return jsonify({
                'status': 'error',
                'message': '결제 금액이 일치하지 않습니다'
            }), 400

        # 결제 요청 정보 생성
        payment_request = toss_payments.create_payment_request(
            amount=amount,
            order_name=f'PDF 맞춤법 검사 ({char_count:,}자)',
            customer_email=email,
            char_count=char_count
        )

        return jsonify({
            'status': 'success',
            'payment': payment_request
        }), 200

    except Exception as e:
        print(f"결제 요청 생성 오류: {e}")
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

    Response:
        결제 승인 결과
    """
    try:
        data = request.get_json()
        payment_key = data.get('paymentKey')
        order_id = data.get('orderId')
        amount = data.get('amount')

        if not all([payment_key, order_id, amount]):
            return jsonify({
                'status': 'error',
                'message': '필수 항목이 누락되었습니다'
            }), 400

        # 결제 승인 요청
        result = toss_payments.confirm_payment(payment_key, order_id, amount)

        if result['success']:
            # 결제 성공 로깅
            print(f"✓ 결제 성공: {order_id}, {amount:,}원")

            # 결제 내역 CSV 저장
            try:
                csv_file = 'payment_history.csv'
                file_exists = os.path.exists(csv_file)

                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'timestamp', 'order_id', 'payment_key', 'amount', 'status'
                    ])
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow({
                        'timestamp': datetime.datetime.now().isoformat(),
                        'order_id': order_id,
                        'payment_key': payment_key,
                        'amount': amount,
                        'status': 'confirmed'
                    })
            except Exception as e:
                print(f"결제 내역 저장 실패: {e}")

            return jsonify({
                'status': 'success',
                'message': '결제가 완료되었습니다',
                'data': result
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error_message', '결제 승인 실패'),
                'error_code': result.get('error_code')
            }), 400

    except Exception as e:
        print(f"결제 승인 오류: {e}")
        return jsonify({
            'status': 'error',
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
