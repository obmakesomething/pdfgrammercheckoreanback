#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다양한 네이버 맞춤법 검사 API 엔드포인트 테스트
"""
import requests
import json

test_text = "안녕하세요. 오늘 날씨가 되요."

# 테스트할 엔드포인트들
endpoints = [
    {
        'name': 'SpellerProxy (모바일)',
        'url': 'https://m.search.naver.com/p/csearch/ocontent/util/SpellerProxy',
        'method': 'GET',
        'params': {'q': test_text}
    },
    {
        'name': 'spellchecker.nhn (모바일)',
        'url': 'https://m.search.naver.com/p/csearch/ocontent/spellchecker.nhn',
        'method': 'GET',
        'params': {'_callback': 'window.__jindo2_callback._spellingCheck_0', 'q': test_text}
    },
    {
        'name': 'PC 버전',
        'url': 'https://search.naver.com/p/csearch/ocontent/util/SpellerProxy',
        'method': 'POST',
        'data': {'q': test_text}
    },
    {
        'name': '부산대 API',
        'url': 'http://speller.cs.pusan.ac.kr/results',
        'method': 'POST',
        'data': {'text1': test_text}
    },
]

headers_mobile = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
    'Referer': 'https://m.search.naver.com/'
}

headers_pc = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://search.naver.com/'
}

print("=" * 70)
print("네이버 맞춤법 검사 API 엔드포인트 테스트")
print("=" * 70)
print(f"테스트 문장: {test_text}\n")

for endpoint in endpoints:
    print(f"\n[{endpoint['name']}]")
    print(f"URL: {endpoint['url']}")
    print(f"Method: {endpoint['method']}")

    try:
        if '모바일' in endpoint['name'] or 'iPhone' in str(headers_mobile):
            headers = headers_mobile
        else:
            headers = headers_pc

        if endpoint['method'] == 'GET':
            response = requests.get(
                endpoint['url'],
                params=endpoint.get('params', {}),
                headers=headers,
                timeout=10
            )
        else:
            response = requests.post(
                endpoint['url'],
                data=endpoint.get('data', {}),
                headers=headers,
                timeout=10
            )

        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            print(f"응답 길이: {len(response.text)}")
            print(f"응답 미리보기:\n{response.text[:300]}")

            # JSON 파싱 시도
            try:
                # JSONP 제거
                text = response.text
                if 'window.__jindo2_callback' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    text = text[start:end]

                data = json.loads(text)
                print(f"\nJSON 파싱 성공!")
                print(f"최상위 키: {list(data.keys())}")

                if 'message' in data:
                    print(f"message 키: {list(data['message'].keys())}")
                    if 'error' in data['message']:
                        print(f"⚠️  에러: {data['message']['error']}")
                    if 'result' in data['message']:
                        print(f"✅ result 존재!")
                        result = data['message']['result']
                        print(f"result 키: {list(result.keys())}")
                        if 'errata_count' in result:
                            print(f"오류 개수: {result['errata_count']}")

            except json.JSONDecodeError:
                print("JSON 파싱 실패 (HTML 응답일 수 있음)")
        else:
            print(f"❌ 요청 실패")

    except requests.exceptions.Timeout:
        print("❌ 타임아웃")
    except Exception as e:
        print(f"❌ 오류: {e}")

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
