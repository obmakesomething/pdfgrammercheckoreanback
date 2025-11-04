#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
부산대 맞춤법 검사 API 새로운 엔드포인트 테스트
"""
import requests

test_text = "안녕하세요. 오늘 날씨가 되요."

# 부산대 여러 엔드포인트
endpoints = [
    'http://speller.cs.pusan.ac.kr/results',
    'http://speller.cs.pusan.ac.kr/PnuWebSpeller/',
    'http://speller.cs.pusan.ac.kr/PnuWebSpeller/lib/check.asp',
    'https://speller.cs.pusan.ac.kr/results',
    'http://164.125.7.61/results',  # IP 직접
]

print("=" * 70)
print("부산대 맞춤법 검사 API 테스트")
print("=" * 70)
print(f"테스트 문장: {test_text}\n")

for url in endpoints:
    print(f"\n[테스트] {url}")

    try:
        data = {'text1': test_text}
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=data, headers=headers, timeout=5)

        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            print(f"응답 길이: {len(response.text)}")
            print(f"응답 미리보기:\n{response.text[:500]}")

            # data 패턴 찾기
            if 'data.push' in response.text:
                print("✅ data.push 패턴 발견!")
            if 'errInfo' in response.text:
                print("✅ errInfo 발견!")

    except requests.exceptions.Timeout:
        print("❌ 타임아웃 (5초)")
    except requests.exceptions.ConnectionError:
        print("❌ 연결 실패")
    except Exception as e:
        print(f"❌ 오류: {e}")

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
