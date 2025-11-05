#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 맞춤법 검사 모듈
바른(Bareun) API를 사용한 전문 맞춤법 검사
"""
from bareun_checker import IntegratedBareunChecker
from typing import List, Dict


class SpellChecker:
    """한국어 맞춤법 검사기 (바른 API)"""

    def __init__(self):
        self.checker = IntegratedBareunChecker()

    def check(self, text: str, max_length: int = 500) -> List[Dict]:
        """
        맞춤법 검사 실행

        Args:
            text: 검사할 텍스트
            max_length: 한 번에 검사할 최대 길이 (바른 API는 긴 문장도 처리 가능)

        Returns:
            list: 오류 목록 (띄어쓰기 제안 제외, 실제 맞춤법/문법 오류만)
                [
                    {
                        'wrong': '틀린 단어',
                        'correct': '올바른 단어',
                        'help': '설명',
                        'position': 텍스트 내 위치,
                        'length': 단어 길이,
                        'category': 오류 유형
                    },
                    ...
                ]
        """
        # 바른 API는 긴 텍스트도 처리할 수 있으므로 max_length 무시
        all_errors = self.checker.check(text)

        # 띄어쓰기 제안(SPACING) 필터링 - 실제 맞춤법/문법 오류만 반환
        filtered_errors = [
            error for error in all_errors
            if error.get('category', '') != 'SPACING'
        ]

        print(f"  전체 제안: {len(all_errors)}개 → 필터링 후: {len(filtered_errors)}개 (띄어쓰기 제외)")

        return filtered_errors


# 테스트
if __name__ == "__main__":
    checker = SpellChecker()

    test_texts = [
        "안녕하세요. 이것은 테스트입니다.",
        "오늘 날씨가 되요. 너무 좋아요.",
        "안되는 것이 있으면 말해주세요.",
        "저는 학교에서 공부를 열심히 했어요.",
        "친구들과 같이 놀러 갈께요."
    ]

    print("=" * 60)
    print("맞춤법 검사 테스트")
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
                if 'position' in err:
                    print(f"    위치: {err['position']}")
        else:
            print("오류 없음")
