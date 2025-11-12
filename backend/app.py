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
import base64
from main_processor import GrammarCheckProcessor
from email_sender import EmailSender
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 허용

# 프로세서 및 이메일 발송기 초기화
processor = GrammarCheckProcessor()
email_sender = EmailSender()


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

        # 5. 이메일 발송 (백그라운드)
        if result['success'] and result['errors_found'] > 0:
            pdf_to_send = output_pdf_path

            # 이메일 발송 시도 (실패해도 웹 응답은 정상 처리)
            try:
                print(f"\n이메일 발송 시도: {email}")
                email_success = email_sender.send_grammar_check_result(
                    to_email=email,
                    pdf_path=pdf_to_send,
                    errors_count=result['errors_found'],
                    original_filename=pdf_file.filename
                )

                if email_success:
                    print(f"✓ 이메일 발송 성공: {email}")
                else:
                    print(f"⚠ 이메일 발송 실패: {email} (웹 응답은 정상 처리)")
            except Exception as e:
                print(f"⚠ 이메일 발송 오류: {e} (웹 응답은 정상 처리)")

        # 6. JSON 응답 반환 (오류 목록 + PDF)
        if result['success']:
            # 오류가 있으면 수정된 PDF, 없으면 원본 PDF
            pdf_to_send = output_pdf_path if result['errors_found'] > 0 else input_pdf_path

            if os.path.exists(pdf_to_send):
                # PDF 파일을 base64로 인코딩
                with open(pdf_to_send, 'rb') as f:
                    pdf_bytes = f.read()
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

                # 파일 이름 생성
                base_name = os.path.splitext(pdf_file.filename)[0]
                download_name = f"{base_name}_맞춤법검사.pdf"

                # 오류 목록 가져오기
                errors_list = result.get('annotations', [])

                # JSON 응답 생성
                response_data = {
                    'status': 'success',
                    'message': f'{result["errors_found"]}개의 맞춤법 오류를 발견했습니다. 이메일로도 발송되었습니다.',
                    'errors_found': result['errors_found'],
                    'errors_highlighted': len(errors_list),
                    'errors': errors_list,
                    'pdf_data': pdf_base64,
                    'pdf_filename': download_name
                }

                # 임시 파일 삭제
                try:
                    if os.path.exists(input_pdf_path):
                        os.remove(input_pdf_path)
                    if os.path.exists(output_pdf_path):
                        os.remove(output_pdf_path)
                except Exception as e:
                    print(f"임시 파일 삭제 실패: {e}")

                return jsonify(response_data), 200
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
