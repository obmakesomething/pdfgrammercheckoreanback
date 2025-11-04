#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 한글 맞춤법 검사 모듈
py-hanspell 기반으로 수정하여 직접 구현
"""
import requests
import re
import time
from typing import List, Dict, Optional


class HanspellChecker:
    """네이버 한글 맞춤법 검사 API 래퍼"""

    def __init__(self):
        self.base_url = "https://m.search.naver.com/p/csearch/ocontent/spellchecker.nhn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://search.naver.com/',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }

    def check(self, text: str) -> List[Dict]:
        """
        맞춤법 검사 실행

        Args:
            text: 검사할 텍스트 (최대 500자)

        Returns:
            list: 오류 목록
        """
        if not text or len(text.strip()) == 0:
            return []

        # 500자 제한
        if len(text) > 500:
            text = text[:500]

        try:
            # API 호출
            params = {
                '_callback': 'window.__jindo2_callback._spellingCheck_0',
                'q': text
            }

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                print(f"  API 응답 오류: {response.status_code}")
                return []

            # JSONP 응답 파싱
            response_text = response.text

            # JSON 추출
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start < 0 or json_end <= json_start:
                print("  JSON 파싱 실패")
                return []

            json_str = response_text[json_start:json_end]

            import json
            data = json.loads(json_str)

            # 결과 파싱
            errors = []

            if 'message' not in data:
                return []

            message = data['message']

            # 오류 또는 제한 확인
            if 'error' in message:
                print(f"  API 오류: {message.get('error', 'Unknown')}")
                return []

            # 결과 파싱
            if 'result' not in message:
                return []

            result = message['result']

            # 오류 개수 확인
            error_count = result.get('errata_count', 0)

            if error_count == 0:
                return []

            # 오류 정보 추출
            if 'errata' in result:
                for err in result['errata']:
                    error_info = {
                        'wrong': err.get('orgStr', ''),
                        'correct': err.get('candWord', ''),
                        'help': err.get('help', ''),
                        'type': self._get_error_type(err.get('help', ''))
                    }
                    errors.append(error_info)

            return errors

        except requests.exceptions.Timeout:
            print("  API 타임아웃")
            return []
        except requests.exceptions.RequestException as e:
            print(f"  API 요청 실패: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"  JSON 파싱 오류: {e}")
            return []
        except Exception as e:
            print(f"  예상치 못한 오류: {e}")
            return []

    def _get_error_type(self, help_text: str) -> str:
        """도움말에서 오류 타입 추출"""
        if '맞춤법' in help_text:
            return 'spelling'
        elif '띄어쓰기' in help_text or '붙여' in help_text:
            return 'spacing'
        elif '표준어' in help_text:
            return 'standard'
        else:
            return 'grammar'

    def check_with_retry(self, text: str, max_retries: int = 2) -> List[Dict]:
        """재시도 로직 포함 맞춤법 검사"""
        for attempt in range(max_retries):
            try:
                errors = self.check(text)
                return errors
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  재시도 {attempt + 1}/{max_retries}...")
                    time.sleep(1)
                else:
                    print(f"  모든 재시도 실패")
                    return []
        return []


# 부산대 API 백업
class PusanChecker:
    """부산대 맞춤법 검사기"""

    def __init__(self):
        self.base_url = "http://speller.cs.pusan.ac.kr/results"

    def check(self, text: str) -> List[Dict]:
        """맞춤법 검사 (부산대)"""
        try:
            data = {'text1': text}
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }

            response = requests.post(
                self.base_url,
                data=data,
                headers=headers,
                timeout=8
            )

            if response.status_code != 200:
                return []

            # HTML 파싱
            errors = self._parse_html(response.text)
            return errors

        except:
            return []

    def _parse_html(self, html: str) -> List[Dict]:
        """HTML에서 오류 추출"""
        errors = []

        # data.push 패턴 찾기
        pattern = r'data\.push\(\[([^\]]+)\]\)'
        matches = re.findall(pattern, html)

        for match in matches:
            parts = [p.strip().strip('"').strip("'") for p in match.split(',')]
            if len(parts) >= 2:
                errors.append({
                    'wrong': parts[0],
                    'correct': parts[1],
                    'help': parts[2] if len(parts) > 2 else ''
                })

        return errors


# 통합 맞춤법 검사기
class IntegratedSpellChecker:
    """네이버 + 부산대 + 로컬 규칙 통합"""

    def __init__(self):
        self.naver_checker = HanspellChecker()
        self.pusan_checker = PusanChecker()

    def check(self, text: str, max_length: int = 500) -> List[Dict]:
        """
        통합 맞춤법 검사

        Args:
            text: 검사할 텍스트
            max_length: 한 번에 검사할 최대 길이

        Returns:
            list: 오류 목록
        """
        if len(text) > max_length:
            # 긴 텍스트는 분할
            chunks = self._split_text(text, max_length)
            all_errors = []

            for i, chunk_info in enumerate(chunks):
                print(f"  청크 {i+1}/{len(chunks)} 검사 중...")
                chunk_errors = self._check_single(chunk_info['text'])

                # 위치 조정
                for error in chunk_errors:
                    if 'position' in error:
                        error['position'] += chunk_info['start']

                all_errors.extend(chunk_errors)

            return all_errors
        else:
            return self._check_single(text)

    def _check_single(self, text: str) -> List[Dict]:
        """단일 텍스트 검사 (fallback 포함)"""
        # 1순위: 네이버
        errors = self.naver_checker.check_with_retry(text)

        if errors:
            print(f"    네이버 API: {len(errors)}개 오류 발견")
            return errors

        # 2순위: 부산대
        print("    네이버 실패, 부산대 시도...")
        errors = self.pusan_checker.check(text)

        if errors:
            print(f"    부산대 API: {len(errors)}개 오류 발견")
            return errors

        # 3순위: 로컬 규칙
        print("    외부 API 실패, 로컬 규칙 사용...")
        errors = self._local_check(text)

        if errors:
            print(f"    로컬 규칙: {len(errors)}개 오류 발견")

        return errors

    def _local_check(self, text: str) -> List[Dict]:
        """로컬 규칙 기반 검사"""
        errors = []

        rules = [
            # 맞춤법
            (r'\b되요\b', '되요', '돼요', "'되다'의 활용형은 '돼요'입니다"),
            (r'\b되\s+요\b', '되 요', '돼요', "붙여 써야 합니다"),
            (r'\b갈께요\b', '갈께요', '갈게요', "'게'가 올바른 표현입니다"),
            (r'\b할께요\b', '할께요', '할게요', "'게'가 올바른 표현입니다"),
            (r'\b올께요\b', '올께요', '올게요', "'게'가 올바른 표현입니다"),
            (r'\b먹을께요\b', '먹을께요', '먹을게요', "'게'가 올바른 표현입니다"),

            # 띄어쓰기 - 안 되다
            (r'\b안되', '안되', '안 돼', "'안 되다'는 띄어 씁니다"),
            (r'\b안될', '안될', '안 될', "'안 되다'는 띄어 씁니다"),
            (r'\b안되면', '안되면', '안 되면', "'안 되다'는 띄어 씁니다"),
            (r'\b안된', '안된', '안 된', "'안 되다'는 띄어 씁니다"),

            # 띄어쓰기 - 그래서, 그러나
            (r'그래서는', '그래서는', '그래서는', "붙여 쓰는 것이 맞습니다"),
            (r'그러나는', '그러나는', '그러나는', "붙여 쓰는 것이 맞습니다"),

            # 띄어쓰기 - 의존명사 (것, 줄, 수, 바)
            (r'([가-힣]+)것\b', None, None, "'것'은 의존명사로 띄어 써야 합니다"),
            (r'([가-힣]+)줄\s*알', None, None, "'줄'은 의존명사로 띄어 써야 합니다"),
            (r'할수있', '할수있', '할 수 있', "'수 있다'는 띄어 씁니다"),
            (r'할수없', '할수없', '할 수 없', "'수 없다'는 띄어 씁니다"),

            # 흔한 오타
            (r'\b왠지\b', None, None, ""),  # 맞는 표현
            (r'\b왠만하면\b', '왠만하면', '웬만하면', "'웬만하면'이 맞습니다"),
            (r'\b금방\b', None, None, ""),  # 맞는 표현
            (r'\b금새\b', '금새', '금세', "'금세'가 맞습니다"),
        ]

        for pattern, wrong, correct, help_text in rules:
            # 빈 help_text는 건너뛰기 (맞는 표현)
            if not help_text:
                continue

            matches = re.finditer(pattern, text)
            for match in matches:
                # None 값 처리 (정규식 캡처 그룹 사용 시)
                matched_text = match.group()
                if wrong is None:
                    wrong = matched_text
                if correct is None:
                    # 의존명사 패턴 처리
                    if '것' in pattern:
                        correct = matched_text[:-1] + ' 것'
                    elif '줄' in pattern:
                        correct = matched_text.replace('줄', ' 줄')
                    else:
                        correct = matched_text

                errors.append({
                    'wrong': matched_text,
                    'correct': correct,
                    'help': help_text,
                    'position': match.start(),
                    'length': len(matched_text)
                })

        return errors

    def _split_text(self, text: str, max_length: int) -> List[Dict]:
        """텍스트 분할"""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + max_length, len(text))

            # 단어 중간에서 자르지 않도록
            if end < len(text):
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space + 1

            chunks.append({
                'text': text[start:end],
                'start': start
            })
            start = end

        return chunks


# 테스트
if __name__ == "__main__":
    checker = IntegratedSpellChecker()

    test_texts = [
        "안녕하세요. 이것은 테스트입니다.",
        "오늘 날씨가 되요. 너무 좋아요.",
        "안되는 것이 있으면 말해주세요.",
        "저는 학교에서 공부를 열심히 했어요.",
        "친구들과 같이 놀러 갈께요."
    ]

    print("=" * 60)
    print("통합 맞춤법 검사 테스트")
    print("=" * 60)

    for i, text in enumerate(test_texts, 1):
        print(f"\n[테스트 {i}]")
        print(f"원문: {text}")

        errors = checker.check(text)

        if errors:
            print(f"발견된 오류: {len(errors)}개")
            for err in errors:
                print(f"  - '{err['wrong']}' → '{err['correct']}'")
                if err.get('help'):
                    print(f"    {err['help']}")
        else:
            print("오류 없음")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
