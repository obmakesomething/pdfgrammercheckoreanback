#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hanspell 라이브러리 테스트
"""
from hanspell import spell_checker

print("=" * 60)
print("hanspell 라이브러리 테스트")
print("=" * 60)

# 테스트 문장들 (일부러 틀린 맞춤법)
test_sentences = [
    "안녕하세요. 이것은 테스트입니다.",
    "오늘 날씨가 되요. 너무 좋아요.",
    "안되는 것이 있으면 말해주세요.",
    "저는 학교에서 공부를 열심이 했어요.",
    "친구들과 같이 놀러 갔어요."
]

for i, sentence in enumerate(test_sentences, 1):
    print(f"\n[테스트 {i}]")
    print(f"원문: {sentence}")

    try:
        # 맞춤법 검사 실행
        result = spell_checker.check(sentence)

        print(f"수정된 문장: {result.checked}")
        print(f"오류 개수: {result.errors}")

        if result.words:
            print("틀린 단어들:")
            for wrong, correct in result.words.items():
                print(f"  - {wrong} → {correct}")
        else:
            print("오류 없음")

    except Exception as e:
        print(f"오류 발생: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
