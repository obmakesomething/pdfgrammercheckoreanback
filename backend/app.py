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
import re
import logging
from main_processor import GrammarCheckProcessor
from email_sender import EmailSender
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS 설정 - 환경 변수에서 허용된 도메인 가져오기
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'https://pdfgrammercheckorean.site,http://localhost:3000')
origins_list = [origin.strip() for origin in allowed_origins.split(',')]
CORS(app, origins=origins_list)


def is_valid_email(email: str) -> bool:
    """이메일 주소 유효성 검사"""
    if not email or len(email) > 254:
        return False
    # 기본적인 이메일 형식 검증
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def sanitize_filename(filename: str) -> str:
    """파일명에서 위험한 문자 제거"""
    if not filename:
        return 'document'
    # 경로 구분자 및 위험한 문자 제거
    filename = os.path.basename(filename)
    # 허용된 문자만 유지 (한글, 영문, 숫자, 공백, 점, 하이픈, 언더스코어)
    filename = re.sub(r'[^\w\s\-\.\uAC00-\uD7A3]', '', filename)
    # 연속된 점 방지
    filename = re.sub(r'\.{2,}', '.', filename)
    return filename if filename else 'document'


def escape_csv_field(field: str) -> str:
    """CSV 인젝션 방지를 위한 필드 이스케이프"""
    if not field:
        return ''
    field = str(field)
    # 위험한 문자로 시작하는 경우 앞에 작은따옴표 추가
    if field.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + field
    return field


def cleanup_temp_files(*file_paths):
    """임시 파일들 안전하게 삭제"""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {file_path} - {e}")


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

        # 이메일 유효성 검사
        if not is_valid_email(email):
            return jsonify({
                'status': 'error',
                'message': '유효하지 않은 이메일 주소입니다'
            }), 400

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

        # 파일명 sanitization
        safe_filename = sanitize_filename(pdf_file.filename)

        logger.info("=" * 60)
        logger.info(f"새로운 요청: {safe_filename}")
        logger.info(f"파일 크기: {file_size / 1024 / 1024:.2f} MB")
        logger.info("=" * 60)

        # 2. 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_id = str(uuid.uuid4())
        input_pdf_path = os.path.join(temp_dir, f"{file_id}_input.pdf")
        output_pdf_path = os.path.join(temp_dir, f"{file_id}_output.pdf")

        pdf_file.save(input_pdf_path)
        logger.info(f"임시 파일 저장: {input_pdf_path}")

        # 3. 맞춤법 검사 실행
        result = processor.process(input_pdf_path, output_pdf_path)

        # 4. 이메일을 CSV에 저장 (CSV 인젝션 방지)
        try:
            csv_file = 'user_emails.csv'
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'email', 'filename', 'errors_found'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'email': escape_csv_field(email),
                    'filename': escape_csv_field(safe_filename),
                    'errors_found': result['errors_found']
                })
            logger.info("사용자 데이터 저장 완료")
        except Exception as e:
            logger.error(f"사용자 데이터 저장 실패: {e}")

        # 5. PDF 파일 반환 (다운로드)
        if result['success']:
            # 오류가 있으면 수정된 PDF, 없으면 원본 PDF
            pdf_to_send = output_pdf_path if result['errors_found'] > 0 else input_pdf_path

            if os.path.exists(pdf_to_send):
                # 파일 이름 생성 (sanitized 파일명 사용)
                base_name = os.path.splitext(safe_filename)[0]
                download_name = f"{base_name}_맞춤법검사.pdf"

                # 파일 내용을 메모리로 읽어서 응답 생성 후 즉시 정리
                with open(pdf_to_send, 'rb') as f:
                    pdf_content = f.read()

                # 임시 파일 즉시 정리
                cleanup_temp_files(input_pdf_path, output_pdf_path)

                # 메모리에서 응답 생성
                from io import BytesIO
                response = send_file(
                    BytesIO(pdf_content),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=download_name
                )
                # 오류 개수를 헤더에 추가
                response.headers['X-Errors-Found'] = str(result['errors_found'])
                # CORS 헤더 - 허용된 origin만 반환
                origin = request.headers.get('Origin', '')
                if origin in origins_list:
                    response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Expose-Headers'] = 'X-Errors-Found'
                return response
            else:
                cleanup_temp_files(input_pdf_path, output_pdf_path)
                return jsonify({
                    'status': 'error',
                    'message': 'PDF 파일 생성에 실패했습니다'
                }), 500
        else:
            # 임시 파일 삭제
            cleanup_temp_files(input_pdf_path, output_pdf_path)
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 500

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 예외 발생 시에도 임시 파일 정리 시도
        try:
            if 'input_pdf_path' in locals():
                cleanup_temp_files(input_pdf_path, output_pdf_path)
        except:
            pass

        return jsonify({
            'status': 'error',
            'message': f'서버 오류가 발생했습니다'
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

        # 설문조사 데이터 저장
        timestamp = datetime.datetime.now().isoformat()

        # CSV 인젝션 방지 적용
        survey_log = {
            'timestamp': timestamp,
            'source': escape_csv_field(source),
            'purpose': escape_csv_field(purpose),
            'email': escape_csv_field(email)
        }

        logger.info(f"설문조사 응답 수신")

        # CSV 파일로 저장
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
        logger.error(f"설문조사 저장 오류: {e}")
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

    logger.info("=" * 60)
    logger.info("PDF 맞춤법 검사 API 서버 시작")
    logger.info("=" * 60)
    logger.info(f"포트: {port}")
    logger.info(f"디버그 모드: {debug}")
    logger.info(f"허용된 Origins: {origins_list}")
    logger.info("=" * 60)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
