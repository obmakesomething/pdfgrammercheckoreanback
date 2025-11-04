#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 테스트 스크립트
"""
import requests

# API URL
API_URL = 'http://localhost:5000/api/check-pdf'

# 테스트할 PDF 파일
PDF_PATH = '/Users/daeyounglee/pdf-grammar-checker/05.11 리서치 정리 (2).pdf'

# 테스트 이메일 (실제 발송하지 않음)
TEST_EMAIL = 'test@example.com'

print("=" * 60)
print("API 테스트 시작")
print("=" * 60)
print(f"PDF: {PDF_PATH}")
print(f"이메일: {TEST_EMAIL}")
print()

try:
    # 파일 열기
    with open(PDF_PATH, 'rb') as f:
        files = {'pdf': f}
        data = {'email': TEST_EMAIL}

        print("API 요청 중...")
        response = requests.post(API_URL, files=files, data=data, timeout=300)

        print(f"\n상태 코드: {response.status_code}")
        print(f"응답: {response.json()}")

        if response.status_code == 200:
            result = response.json()
            print("\n✓ 성공!")
            print(f"  발견된 오류: {result.get('errors_found', 0)}개")
        else:
            print("\n✗ 실패!")

except FileNotFoundError:
    print(f"✗ 파일을 찾을 수 없습니다: {PDF_PATH}")
except requests.exceptions.ConnectionError:
    print("✗ 서버에 연결할 수 없습니다. Flask 서버가 실행 중인지 확인하세요.")
except Exception as e:
    print(f"✗ 오류: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
