#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hanspell API 직접 호출 테스트
"""
import requests
import json

print("=" * 60)
print("네이버 맞춤법 검사 API 직접 호출")
print("=" * 60)

# 네이버 맞춤법 검사 API URL
url = "https://m.search.naver.com/p/csearch/ocontent/spellchecker.nhn"

test_sentence = "오늘 날씨가 되요. 너무 좋아요."
print(f"\n원문: {test_sentence}\n")

# 요청 파라미터
params = {
    '_callback': 'window.__jindo2_callback._spellingCheck_0',
    'q': test_sentence
}

# 헤더
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Referer': 'https://m.search.naver.com/'
}

try:
    # API 호출
    response = requests.get(url, params=params, headers=headers, timeout=10)

    print(f"상태 코드: {response.status_code}")
    print(f"\n응답 내용:\n{response.text}\n")

    # JSONP 응답 파싱
    response_text = response.text
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1

    if json_start >= 0 and json_end > json_start:
        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)

        print(f"JSON 데이터:")
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 결과 파싱
        if 'message' in data:
            message = data['message']
            print(f"\nmessage 키들: {message.keys()}")

            if 'result' in message:
                result = message['result']
                print(f"\nresult 내용:")
                print(json.dumps(result, ensure_ascii=False, indent=2))

                # 오류 정보
                if 'errata_count' in result:
                    error_count = result['errata_count']
                    print(f"\n오류 개수: {error_count}")

                    if error_count > 0 and 'errata' in result:
                        print("\n틀린 부분들:")
                        for err in result['errata']:
                            print(f"  - {err.get('orgStr', '?')} → {err.get('candWord', '?')}")
                            print(f"    도움말: {err.get('help', '없음')}")
            else:
                print(f"\n'result' 키가 없음. message 구조:")
                print(json.dumps(message, ensure_ascii=False, indent=2))

except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
