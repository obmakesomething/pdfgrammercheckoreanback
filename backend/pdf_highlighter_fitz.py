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

    def __init__(self, input_pdf_path: str, output_pdf_path: str):
        self.input_pdf_path = input_pdf_path
        self.output_pdf_path = output_pdf_path

    def add_highlights(self, errors: List[Dict]):
        """
        틀린 단어를 PDF에서 찾아 빨간색 하이라이트 추가

        Args:
            errors: 오류 정보 리스트
                [
                    {
                        'wrong': '틀린 단어',
                        'correct': '올바른 단어',
                        'help': '설명'
                    },
                    ...
                ]
        """
        try:
            # PDF 열기
            doc = fitz.open(self.input_pdf_path)
            total_highlights = 0
            used_rects = set()  # 중복 하이라이트 방지

            # 각 오류에 대해
            for error in errors:
                wrong_word = error['wrong'].strip()

                # 모든 페이지에서 검색
                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # 텍스트 검색 (정확한 위치 반환)
                    text_instances = page.search_for(wrong_word)

                    # 찾은 모든 인스턴스에 하이라이트
                    for inst in text_instances:
                        # Rect를 튜플로 변환하여 중복 체크
                        rect_key = (page_num, round(inst.x0, 2), round(inst.y0, 2), round(inst.x1, 2), round(inst.y1, 2))

                        if rect_key in used_rects:
                            continue  # 이미 하이라이트된 위치는 건너뛰기

                        # 빨간색 하이라이트 추가
                        highlight = page.add_highlight_annot(inst)
                        highlight.set_colors(stroke=[1, 0, 0])  # 빨간색

                        # 주석 내용 추가
                        highlight.set_info(
                            title="맞춤법 검사기",
                            content=f"틀림: {error['wrong']}\n올바름: {error['correct']}\n\n{error.get('help', '')}"
                        )
                        highlight.update()

                        used_rects.add(rect_key)
                        total_highlights += 1
                        break  # 각 오류당 첫 번째 일치만 사용

            # PDF 저장
            doc.save(self.output_pdf_path)
            doc.close()

            print(f"✓ PDF 하이라이트 완료: {self.output_pdf_path}")
            print(f"  입력 오류: {len(errors)}개")
            print(f"  추가된 하이라이트: {total_highlights}개")

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
