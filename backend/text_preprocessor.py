#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텍스트 전처리 모듈
하이픈 병합, 줄바꿈 처리, 조사 병합 등을 수행하며
원본 위치(앵커) 정보를 유지
"""
import re


class TextPreprocessor:
    """텍스트 전처리 및 앵커 매핑 클래스"""

    def __init__(self, text_with_positions, raw_text):
        """
        Args:
            text_with_positions: PDF에서 추출한 문자별 위치 정보
            raw_text: 전체 원본 텍스트
        """
        self.text_with_positions = text_with_positions
        self.raw_text = raw_text
        self.cleaned_text = ""
        self.anchor_map = {}  # cleaned_text의 인덱스 -> 원본 인덱스들

    def preprocess(self):
        """
        전처리 실행

        Returns:
            tuple: (cleaned_text, anchor_map)
        """
        # 0단계: PDF 노이즈 제거 (NEW)
        text, mapping = self._clean_pdf_noise(self.raw_text)

        # 1단계: 하이픈 + 줄바꿈 병합
        text, mapping = self._merge_hyphen_newlines(text, mapping)

        # 2단계: 단순 줄바꿈으로 분리된 단어 병합
        text, mapping = self._merge_word_breaks(text, mapping)

        # 3단계: 조사 분리 복구
        text, mapping = self._merge_particles(text, mapping)

        # 4단계: 문장 종결 후 줄바꿈을 공백으로
        text, mapping = self._normalize_sentence_breaks(text, mapping)

        # 5단계: 연속된 공백 정리 (NEW)
        text, mapping = self._normalize_spaces(text, mapping)

        self.cleaned_text = text
        self.anchor_map = mapping

        return self.cleaned_text, self.anchor_map

    def _clean_pdf_noise(self, text):
        """
        0단계: PDF에서 자주 발생하는 노이즈 제거
        - 불필요한 제어 문자 제거
        - 이상한 유니코드 문자 정리
        - 페이지 번호 패턴 제거
        """
        result = []
        mapping = {}
        cleaned_idx = 0
        i = 0

        while i < len(text):
            char = text[i]

            # 제어 문자 제거 (줄바꿈, 탭, 캐리지리턴은 유지)
            if ord(char) < 32 and char not in ['\n', '\t', '\r']:
                i += 1
                continue

            # NULL 바이트 제거
            if char == '\x00':
                i += 1
                continue

            # PDF에서 자주 나타나는 특수 마커 제거 (예: \uf0b7 = bullet point)
            if '\uf000' <= char <= '\uf0ff':
                # 불릿 포인트는 공백으로 대체
                result.append(' ')
                mapping[cleaned_idx] = [i]
                cleaned_idx += 1
                i += 1
                continue

            # 정상 문자는 유지
            result.append(char)
            mapping[cleaned_idx] = [i]
            cleaned_idx += 1
            i += 1

        return ''.join(result), mapping

    def _merge_hyphen_newlines(self, text, mapping):
        """
        패턴 A: 하이픈 + 줄바꿈 병합
        예: "안녕하세-\n요" -> "안녕하세요"
        """
        result = []
        new_mapping = {}
        cleaned_idx = 0
        i = 0

        while i < len(text):
            # 하이픈 + 줄바꿈 패턴 감지
            if i + 1 < len(text) and text[i] == '-' and text[i + 1] == '\n':
                # 하이픈과 줄바꿈 제거, 연결
                i += 2  # '-'와 '\n' 건너뛰기
                continue
            else:
                result.append(text[i])
                new_mapping[cleaned_idx] = mapping.get(i, [i])
                cleaned_idx += 1
                i += 1

        return ''.join(result), new_mapping

    def _merge_word_breaks(self, text, mapping):
        """
        패턴 B: 줄바꿈으로 분리된 한글 단어 병합
        예: "반갑\n습니다" -> "반갑습니다"
        """
        result = []
        new_mapping = {}
        cleaned_idx = 0
        i = 0

        while i < len(text):
            # 한글 + 줄바꿈 + 한글 패턴
            if i + 2 < len(text):
                if self._is_korean(text[i]) and text[i + 1] == '\n' and self._is_korean(text[i + 2]):
                    # 문장 종결이 아닌 경우만 병합
                    if not self._is_sentence_end(text, i):
                        result.append(text[i])
                        # 현재 cleaned_idx에 원본 i를 매핑
                        if cleaned_idx in new_mapping:
                            new_mapping[cleaned_idx].extend(mapping.get(i, [i]))
                        else:
                            new_mapping[cleaned_idx] = mapping.get(i, [i])
                        cleaned_idx += 1
                        # 줄바꿈 건너뛰기
                        i += 2
                        continue

            # 일반 문자
            result.append(text[i])
            if cleaned_idx in new_mapping:
                new_mapping[cleaned_idx].extend(mapping.get(i, [i]))
            else:
                new_mapping[cleaned_idx] = mapping.get(i, [i])
            cleaned_idx += 1
            i += 1

        return ''.join(result), new_mapping

    def _merge_particles(self, text, mapping):
        """
        패턴 C: 조사 분리 복구
        예: "사과 를" -> "사과를"
        """
        particles = ['이', '가', '을', '를', '은', '는', '와', '과', '의', '에', '도', '만',
                     '에서', '부터', '까지', '로', '으로']

        result = []
        new_mapping = {}
        cleaned_idx = 0
        i = 0

        while i < len(text):
            # 한글 + 공백 + 조사 패턴
            if i + 2 < len(text):
                if self._is_korean(text[i]) and text[i + 1] == ' ':
                    # 다음에 조사가 오는지 확인
                    for particle in particles:
                        end_idx = i + 2 + len(particle)
                        if end_idx <= len(text):
                            if text[i + 2:end_idx] == particle:
                                # 조사 발견, 공백 제거하고 병합
                                result.append(text[i])
                                new_mapping[cleaned_idx] = mapping.get(i, [i])
                                cleaned_idx += 1

                                # 공백 건너뛰기
                                # 조사 추가
                                for j in range(len(particle)):
                                    result.append(particle[j])
                                    new_mapping[cleaned_idx] = mapping.get(i + 2 + j, [i + 2 + j])
                                    cleaned_idx += 1

                                i = end_idx
                                break
                    else:
                        # 조사가 아님, 일반 처리
                        result.append(text[i])
                        new_mapping[cleaned_idx] = mapping.get(i, [i])
                        cleaned_idx += 1
                        i += 1
                else:
                    result.append(text[i])
                    new_mapping[cleaned_idx] = mapping.get(i, [i])
                    cleaned_idx += 1
                    i += 1
            else:
                result.append(text[i])
                new_mapping[cleaned_idx] = mapping.get(i, [i])
                cleaned_idx += 1
                i += 1

        return ''.join(result), new_mapping

    def _normalize_sentence_breaks(self, text, mapping):
        """
        패턴 D: 문장 종결 후 줄바꿈을 공백으로
        예: "문장 끝.\n새 문장" -> "문장 끝. 새 문장"
        """
        result = []
        new_mapping = {}
        cleaned_idx = 0

        for i, char in enumerate(text):
            if char == '\n':
                # 이전 문자가 문장 종결 부호인지 확인
                if i > 0 and text[i - 1] in '.!?':
                    # 줄바꿈을 공백으로
                    result.append(' ')
                    new_mapping[cleaned_idx] = mapping.get(i, [i])
                    cleaned_idx += 1
                elif i > 0 and self._is_korean(text[i - 1]):
                    # 일반 줄바꿈도 공백으로 (단락 구분 유지)
                    result.append(' ')
                    new_mapping[cleaned_idx] = mapping.get(i, [i])
                    cleaned_idx += 1
            else:
                result.append(char)
                new_mapping[cleaned_idx] = mapping.get(i, [i])
                cleaned_idx += 1

        return ''.join(result), new_mapping

    def _is_korean(self, char):
        """한글인지 확인"""
        return '가' <= char <= '힣' or 'ㄱ' <= char <= 'ㅎ' or 'ㅏ' <= char <= 'ㅣ'

    def _normalize_spaces(self, text, mapping):
        """
        패턴 E: 연속된 공백을 하나로 정리
        예: "안녕   하세요" -> "안녕 하세요"
        """
        result = []
        new_mapping = {}
        cleaned_idx = 0
        i = 0

        while i < len(text):
            char = text[i]

            # 공백이 연속되는 경우
            if char == ' ':
                # 첫 공백은 추가
                result.append(char)
                new_mapping[cleaned_idx] = mapping.get(i, [i])
                cleaned_idx += 1
                i += 1

                # 연속된 공백은 건너뛰기
                while i < len(text) and text[i] == ' ':
                    i += 1
            else:
                result.append(char)
                new_mapping[cleaned_idx] = mapping.get(i, [i])
                cleaned_idx += 1
                i += 1

        return ''.join(result), new_mapping

    def _is_sentence_end(self, text, pos):
        """문장 종결 위치인지 확인"""
        # 앞쪽에 마침표, 느낌표, 물음표가 있는지
        for i in range(max(0, pos - 3), pos):
            if text[i] in '.!?':
                return True
        return False

    def get_original_positions(self, cleaned_start, cleaned_end):
        """
        전처리된 텍스트의 위치를 원본 위치로 역추적

        Args:
            cleaned_start: 전처리된 텍스트에서의 시작 인덱스
            cleaned_end: 전처리된 텍스트에서의 종료 인덱스

        Returns:
            list: 원본 text_with_positions의 인덱스 리스트
        """
        original_indices = []

        for i in range(cleaned_start, cleaned_end):
            if i in self.anchor_map:
                original_indices.extend(self.anchor_map[i])

        return original_indices


# 테스트
if __name__ == "__main__":
    # 테스트 데이터
    test_text = "안녕하세-\n요 반갑\n습니다. 사과 를 먹었습니다.\n새로운 문장입니다."

    # 간단한 text_with_positions 생성
    text_with_positions = []
    for i, char in enumerate(test_text):
        text_with_positions.append({
            'char': char,
            'page': 1,
            'x': i * 10,
            'y': 100,
            'index': i
        })

    print("=" * 60)
    print("텍스트 전처리 테스트")
    print("=" * 60)
    print(f"원본 텍스트:\n{repr(test_text)}\n")

    # 전처리 실행
    preprocessor = TextPreprocessor(text_with_positions, test_text)
    cleaned_text, anchor_map = preprocessor.preprocess()

    print(f"전처리된 텍스트:\n{repr(cleaned_text)}\n")
    print(f"앵커 맵 (첫 20개):")
    for i, (k, v) in enumerate(list(anchor_map.items())[:20]):
        print(f"  cleaned[{k}] = '{cleaned_text[k]}' -> original{v}")

    # 역추적 테스트
    print(f"\n역추적 테스트:")
    test_word = "안녕하세요"
    if test_word in cleaned_text:
        start = cleaned_text.index(test_word)
        end = start + len(test_word)
        original_indices = preprocessor.get_original_positions(start, end)
        print(f"  '{test_word}' (cleaned[{start}:{end}])")
        print(f"  -> 원본 인덱스: {original_indices}")
