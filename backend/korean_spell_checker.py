#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 맞춤법 검사 모듈
네이버 맞춤법 검사기 API를 사용하는 간단한 wrapper
"""
import requests
import json
import re
from urllib.parse import quote

class KoreanSpellChecker:
    """한국어 맞춤법 검사기"""

    def __init__(self):
        # 부산대 API 엔드포인트 (구버전)
        self.pusan_url = "http://speller.cs.pusan.ac.kr/results"
        # 포털다음 맞춤법 검사 API
        self.daum_url = "https://dic.daum.net/grammar_checker.do"

    def check_pusan(self, text):
        """부산대 맞춤법 검사기 사용"""
        try:
            data = {'text1': text}
            response = requests.post(
                self.pusan_url,
                data=data,
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code == 200:
                return self._parse_pusan_response(response.text)
            else:
                return None
        except Exception as e:
            print(f"부산대 API 오류: {e}")
            return None

    def _parse_pusan_response(self, html):
        """부산대 API 응답 파싱"""
        errors = []

        # HTML에서 오류 정보 추출 (정규식 사용)
        # 실제 응답 형식에 따라 조정 필요
        error_pattern = r'data\s*=\s*({.*?});'
        matches = re.findall(error_pattern, html, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if 'errInfo' in data:
                    for err in data['errInfo']:
                        errors.append({
                            'wrong': err.get('orgStr', ''),
                            'correct': err.get('candWord', ''),
                            'help': err.get('help', '')
                        })
            except:
                pass

        return errors

    def check_simple(self, text):
        """간단한 맞춤법 검사 (로컬 규칙 기반)"""
        errors = []

        # 기본적인 맞춤법 규칙들
        rules = [
            {
                'wrong': r'되요\b',
                'correct': '돼요',
                'help': "'되다'의 활용형은 '돼요'입니다"
            },
            {
                'wrong': r'안되',
                'correct': '안 돼',
                'help': "'안 되다'는 띄어 씁니다"
            },
            {
                'wrong': r'만들어요',
                'correct': '만들어요',  # 정확함
                'help': ''
            },
        ]

        for rule in rules:
            pattern = rule['wrong']
            matches = re.finditer(pattern, text)
            for match in matches:
                if rule['help']:  # help가 있으면 실제 오류
                    errors.append({
                        'wrong': match.group(),
                        'correct': rule['correct'],
                        'help': rule['help'],
                        'position': match.start(),
                        'length': len(match.group())
                    })

        return errors

    def check(self, text, method='simple'):
        """
        맞춤법 검사 실행

        Args:
            text: 검사할 텍스트
            method: 'pusan', 'simple' 중 선택

        Returns:
            list: 오류 목록
        """
        if method == 'pusan':
            return self.check_pusan(text)
        else:
            return self.check_simple(text)


# 테스트
if __name__ == "__main__":
    checker = KoreanSpellChecker()

    # 테스트 텍스트
    test_texts = [
        "안녕하세요. 이거는 테스트예요.",
        "오늘 날씨가 좋아요. 밖에 나가고 싶어요.",
        "이 문서를 작성했어요. 검토 부탁드려요."
    ]

    print("=" * 60)
    print("한국어 맞춤법 검사 테스트")
    print("=" * 60)

    for i, text in enumerate(test_texts, 1):
        print(f"\n[테스트 {i}]")
        print(f"원문: {text}")

        # 간단한 검사
        errors = checker.check(text, method='simple')
        if errors:
            print(f"발견된 오류: {len(errors)}개")
            for err in errors:
                print(f"  - {err['wrong']} → {err['correct']}")
                print(f"    ({err['help']})")
        else:
            print("오류 없음")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
