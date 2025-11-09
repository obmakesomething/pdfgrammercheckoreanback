#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyMuPDF (fitz)를 사용한 정확한 PDF 하이라이트 모듈
텍스트 검색 기능을 사용하여 정확한 위치에 하이라이트 추가
"""
import fitz  # PyMuPDF
from typing import List, Dict


class PDFHighlighterFitz:
    """PyMuPDF를 사용하여 정확한 하이라이트를 추가하는 클래스"""

    # 카테고리별 색상 정의 (RGB, 0-1 범위)
    COLORS = {
        'SPACING': [0, 0.5, 1],      # 파란색 - 띄어쓰기
        'SPELL': [1, 0, 0],          # 빨간색 - 맞춤법
        'GRAMMAR': [1, 0.8, 0],      # 노란색 - 문법
        'TYPO': [1, 0, 0],           # 빨간색 - 오타
        'default': [1, 0.4, 0]       # 주황색 - 기타
    }

    def __init__(self, input_pdf_path: str, output_pdf_path: str):
        self.input_pdf_path = input_pdf_path
        self.output_pdf_path = output_pdf_path

    def add_highlights(self, errors: List[Dict]):
        """
        틀린 단어를 PDF에서 찾아 카테고리별 색상으로 하이라이트 추가

        Args:
            errors: 오류 정보 리스트
                [
                    {
                        'wrong': '틀린 단어',
                        'correct': '올바른 단어',
                        'help': '설명',
                        'category': 'SPACING' | 'SPELL' | 'GRAMMAR' 등
                    },
                    ...
                ]
        """
        try:
            # PDF 열기
            doc = fitz.open(self.input_pdf_path)
            total_highlights = 0
            used_texts = set()  # 이미 하이라이트한 텍스트 추적 (중복 방지)

            # 각 오류에 대해
            for error in errors:
                wrong_word = error['wrong'].strip()
                category = error.get('category', 'default')

                # 이미 처리한 텍스트는 건너뛰기 (중복 방지)
                if wrong_word in used_texts:
                    continue

                # 카테고리별 색상 선택
                color = self.COLORS.get(category, self.COLORS['default'])

                # 모든 페이지에서 검색
                found = False
                for page_num in range(len(doc)):
                    if found:
                        break

                    page = doc[page_num]

                    # 텍스트 검색 (정확한 위치 반환)
                    text_instances = page.search_for(wrong_word)

                    # 첫 번째 일치 항목만 하이라이트
                    if text_instances:
                        inst = text_instances[0]

                        # 텍스트의 실제 바운딩 박스를 구하기 위해 글자별 위치 확인
                        # inst는 Rect(x0, y0, x1, y1) 형태
                        # 패딩을 크게 줄여서 텍스트에 딱 맞게 조정
                        padding = 3

                        # 패딩 적용 후 유효성 검증
                        y0_adjusted = inst.y0 + padding
                        y1_adjusted = inst.y1 - padding

                        # 사각형이 너무 작아지는 것 방지 (최소 높이 1픽셀)
                        if y1_adjusted <= y0_adjusted:
                            # 패딩 없이 원본 사용
                            y0_adjusted = inst.y0
                            y1_adjusted = inst.y1

                        # 좌표 유효성 검증 (NaN, 무한대 체크)
                        try:
                            adjusted_rect = fitz.Rect(
                                inst.x0,
                                y0_adjusted,
                                inst.x1,
                                y1_adjusted
                            )

                            # 페이지 경계 내에 있는지 확인
                            page_rect = page.rect
                            if not (adjusted_rect.x0 >= 0 and adjusted_rect.x1 <= page_rect.width and
                                    adjusted_rect.y0 >= 0 and adjusted_rect.y1 <= page_rect.height and
                                    adjusted_rect.is_valid):
                                # 페이지 경계 내로 클리핑
                                adjusted_rect = adjusted_rect & page_rect

                            # 여전히 유효하지 않으면 건너뛰기
                            if not adjusted_rect.is_valid or adjusted_rect.is_empty:
                                print(f"  경고: '{wrong_word}' 하이라이트 건너뜀 (유효하지 않은 좌표)")
                                continue

                        except (ValueError, RuntimeError) as e:
                            print(f"  경고: '{wrong_word}' 하이라이트 건너뜀 (좌표 오류: {e})")
                            continue

                        # 하이라이트 추가 (조정된 사각형 사용)
                        highlight = page.add_highlight_annot(adjusted_rect)
                        highlight.set_colors(stroke=color)

                        # 주석 내용 추가
                        category_name = {
                            'SPACING': '띄어쓰기',
                            'SPELL': '맞춤법',
                            'GRAMMAR': '문법',
                            'TYPO': '오타'
                        }.get(category, '기타')

                        highlight.set_info(
                            title=f"맞춤법 검사기 ({category_name})",
                            content=f"틀림: {error['wrong']}\n올바름: {error['correct']}\n\n{error.get('help', '')}"
                        )
                        highlight.update()

                        used_texts.add(wrong_word)
                        total_highlights += 1
                        found = True

            # PDF 저장
            doc.save(self.output_pdf_path)
            doc.close()

            print(f"✓ PDF 하이라이트 완료: {self.output_pdf_path}")
            print(f"  입력 오류: {len(errors)}개")
            print(f"  추가된 하이라이트: {total_highlights}개 (중복 제거)")

        except Exception as e:
            print(f"PDF 하이라이트 오류: {e}")
            import traceback
            traceback.print_exc()
            raise


# 테스트
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("사용법: python pdf_highlighter_fitz.py <입력_pdf> <출력_pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    # 테스트 오류
    test_errors = [
        {
            'wrong': '되요',
            'correct': '돼요',
            'help': "'되다'의 활용형은 '돼요'입니다"
        },
        {
            'wrong': '안되는',
            'correct': '안 되는',
            'help': "'안 되다'는 띄어 씁니다"
        }
    ]

    print("=" * 60)
    print("PDF 하이라이트 테스트 (PyMuPDF)")
    print("=" * 60)
    print(f"입력: {input_pdf}")
    print(f"출력: {output_pdf}")
    print(f"오류 개수: {len(test_errors)}개\n")

    highlighter = PDFHighlighterFitz(input_pdf, output_pdf)
    highlighter.add_highlights(test_errors)

    print("\n완료!")
