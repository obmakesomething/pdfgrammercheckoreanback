#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 맞춤법 검사 API 테스트
"""
import requests
import json

def test_pusan_api():
    """부산대학교 맞춤법 검사기 테스트"""
    print("=" * 50)
    print("부산대학교 맞춤법 검사기 테스트")
    print("=" * 50)

    url = "http://speller.cs.pusan.ac.kr/results"

    # 테스트 텍스트 (일부러 틀린 맞춤법)
    test_text = "안녕하세요. 이것은 테스트입니다. 저는 학교에 갔어요."

    # POST 요청
    data = {
        'text1': test_text
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.text)}")
        print(f"응답 내용 (처음 500자):\n{response.text[:500]}")
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def test_naver_api():
    """네이버 맞춤법 검사기 테스트 (직접 호출)"""
    print("\n" + "=" * 50)
    print("네이버 맞춤법 검사기 테스트")
    print("=" * 50)

    url = "https://m.search.naver.com/p/csearch/ocontent/util/SpellerProxy"

    # 테스트 텍스트
    test_text = "안녕하세요. 이것은 테스트입니다. 저는 학교에 갔어요."

    # POST 요청
    data = {
        'q': test_text
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://m.search.naver.com/'
    }

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        print(f"상태 코드: {response.status_code}")
        print(f"응답 내용:\n{response.text[:500]}")
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    # 두 API 모두 테스트
    pusan_ok = test_pusan_api()
    naver_ok = test_naver_api()

    print("\n" + "=" * 50)
    print("테스트 결과")
    print("=" * 50)
    print(f"부산대: {'성공' if pusan_ok else '실패'}")
    print(f"네이버: {'성공' if naver_ok else '실패'}")
