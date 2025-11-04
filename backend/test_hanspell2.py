#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hanspell 라이브러리 테스트 v2
"""
from hanspell import spell_checker
import traceback

print("=" * 60)
print("hanspell 라이브러리 상세 테스트")
print("=" * 60)

test_sentence = "오늘 날씨가 되요. 너무 좋아요."
print(f"\n원문: {test_sentence}")

try:
    # 맞춤법 검사 실행
    result = spell_checker.check(test_sentence)

    print(f"\nresult 타입: {type(result)}")
    print(f"result 속성들: {dir(result)}")
    print(f"\nresult 내용:")
    print(result)

    # 다양한 속성 시도
    if hasattr(result, 'result'):
        print(f"\nresult.result: {result.result}")
    if hasattr(result, 'original'):
        print(f"result.original: {result.original}")
    if hasattr(result, 'checked'):
        print(f"result.checked: {result.checked}")
    if hasattr(result, 'errors'):
        print(f"result.errors: {result.errors}")
    if hasattr(result, 'words'):
        print(f"result.words: {result.words}")

except Exception as e:
    print(f"\n오류 발생: {e}")
    print("\n전체 스택 트레이스:")
    traceback.print_exc()

# 다른 함수 시도
print("\n\n" + "=" * 60)
print("다른 방식 시도")
print("=" * 60)

try:
    from hanspell import  Speller

    speller = Speller()
    result = speller.check(test_sentence)
    print(f"Speller 결과: {result}")

except Exception as e:
    print(f"Speller 오류: {e}")
    traceback.print_exc()

# 직접 함수 확인
print("\n\n" + "=" * 60)
print("hanspell 모듈 내용 확인")
print("=" * 60)

import hanspell
print(f"hanspell 모듈 속성: {dir(hanspell)}")
print(f"\nspell_checker 속성: {dir(spell_checker)}")
