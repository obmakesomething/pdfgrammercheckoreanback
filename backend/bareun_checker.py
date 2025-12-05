#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
바른(Bareun) API를 사용한 한국어 맞춤법 검사 모듈
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

try:
    from bareunpy import Corrector
    BAREUN_AVAILABLE = True
except ImportError:
    BAREUN_AVAILABLE = False
    print("경고: bareunpy 라이브러리가 설치되지 않았습니다")


class BareunSpellChecker:
    """바른 API를 사용한 맞춤법 검사기"""

    def __init__(self, api_key: str = None, host: str = None, port: int = None):
        """
        Args:
            api_key: 바른 API 키 (없으면 환경 변수에서 가져옴)
            host: 바른 서버 호스트 (기본: api.bareun.ai)
            port: 바른 서버 포트 (기본: 443)
        """
        if not BAREUN_AVAILABLE:
            raise ImportError("bareunpy가 설치되지 않았습니다: pip install bareunpy")

        self.api_key = api_key or os.getenv('BAREUN_API_KEY')
        if not self.api_key:
            raise ValueError("BAREUN_API_KEY가 설정되지 않았습니다")

        # 바른 서버 설정
        self.host = host or os.getenv('BAREUN_HOST', 'api.bareun.ai')
        self.port = port or int(os.getenv('BAREUN_PORT', '443'))

        # Corrector 초기화
        try:
            self.corrector = Corrector(
                apikey=self.api_key,
                host=self.host,
                port=self.port
            )
            print(f"✓ 바른 API 초기화 완료 ({self.host}:{self.port})")
        except Exception as e:
            print(f"✗ 바른 API 초기화 실패: {e}")
            raise

    def check(self, text: str) -> List[Dict]:
        """
        맞춤법 검사 실행

        Args:
            text: 검사할 텍스트

        Returns:
            list: 오류 목록
                [
                    {
                        'wrong': '틀린 부분',
                        'correct': '올바른 표현',
                        'help': '설명',
                        'position': 텍스트 내 위치,
                        'length': 길이,
                        'category': 'SPACING', 'GRAMMER' 등
                    },
                    ...
                ]
        """
        if not text or len(text.strip()) == 0:
            return []

        try:
            # 바른 API 호출
            response = self.corrector.correct_error(content=text)

            # 응답 파싱
            errors = self._parse_response(response, text)
            return errors

        except Exception as e:
            print(f"바른 API 오류: {e}")
            return []

    def _parse_response(self, response, original_text: str) -> List[Dict]:
        """바른 API 응답 파싱"""
        errors = []

        if not hasattr(response, 'revised_blocks'):
            return errors

        for block in response.revised_blocks:
            # 원문과 교정문이 다른 경우만
            if block.origin.content != block.revised:
                # 주요 교정 정보
                error = {
                    'wrong': block.origin.content,
                    'correct': block.revised,
                    'position': block.origin.begin_offset,
                    'length': len(block.origin.content),
                    'help': '',
                    'category': ''
                }

                # revision 정보가 있으면 상세 정보 추가
                if block.revisions and len(block.revisions) > 0:
                    first_revision = block.revisions[0]

                    # 카테고리 (SPACING, GRAMMER, TYPO 등)
                    if hasattr(first_revision, 'category'):
                        error['category'] = str(first_revision.category)

                    # 도움말 ID
                    if hasattr(first_revision, 'help_id'):
                        help_id = first_revision.help_id

                        # helps 맵에서 도움말 찾기
                        if hasattr(response, 'helps') and help_id in response.helps:
                            help_info = response.helps[help_id]
                            error['help'] = help_info.comment

                errors.append(error)

        return errors

    def check_multiple(self, texts: List[str]) -> List[List[Dict]]:
        """여러 텍스트를 한 번에 검사"""
        try:
            responses = self.corrector.correct_error_list(contents=texts)

            results = []
            for response, text in zip(responses, texts):
                errors = self._parse_response(response, text)
                results.append(errors)

            return results

        except Exception as e:
            print(f"바른 API 오류: {e}")
            return [[] for _ in texts]


# 통합 맞춤법 검사기 (바른 API만 사용)
class IntegratedBareunChecker:
    """바른 API 기반 맞춤법 검사기"""

    def __init__(self):
        # 바른 API 초기화
        self.bareun = BareunSpellChecker()
        print("✓ 바른 API 사용 가능")

    def check(self, text: str) -> List[Dict]:
        """맞춤법 검사 (바른 API만 사용)"""
        try:
            errors = self.bareun.check(text)
            if errors:
                print(f"  바른 API: {len(errors)}개 오류 발견")
            return errors
        except Exception as e:
            print(f"  바른 API 오류: {e}")
            raise  # 오류 발생 시 예외를 상위로 전파


# 테스트
if __name__ == "__main__":
    import sys

    test_texts = [
        "안녕하세요. 이것은 테스트입니다.",
        "오늘 날씨가 되요. 너무 좋아요.",
        "줄기가 얇아서 시들을 것 같은 꽃에물을 주었더니 고은 꽃이 피었다.",
        "어제도 너무더워서잠이오지를않았다.그런데, 오늘은 더심하네요.",
    ]

    print("=" * 70)
    print("바른 API 맞춤법 검사 테스트")
    print("=" * 70)

    try:
        checker = IntegratedBareunChecker()

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
                    if err.get('category'):
                        print(f"    카테고리: {err['category']}")
            else:
                print("오류 없음")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)
