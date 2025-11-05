#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdfplumber를 사용한 정확한 PDF 하이라이트 모듈
틀린 단어를 PDF에서 직접 검색하여 정확한 위치에 하이라이트 추가
"""
import PyPDF2
from PyPDF2.generic import DictionaryObject, ArrayObject, FloatObject, NameObject, TextStringObject, NumberObject
from typing import List, Dict
import pdfplumber


class PDFHighlighter:
    """pdfplumber로 단어 위치를 찾고 하이라이트를 추가하는 클래스"""

    def __init__(self, input_pdf_path: str, output_pdf_path: str):
        self.input_pdf_path = input_pdf_path
        self.output_pdf_path = output_pdf_path

    def add_highlights(self, errors: List[Dict]):
        """
        틀린 단어를 PDF에서 찾아 하이라이트 추가

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
            # 1. pdfplumber로 각 오류 단어의 위치 찾기
            annotations_by_page = self._find_word_positions(errors)

            # 2. PyPDF2로 주석 추가
            self._add_annotations_to_pdf(annotations_by_page)

            print(f"✓ PDF 하이라이트 완료: {self.output_pdf_path}")
            print(f"  총 {sum(len(anns) for anns in annotations_by_page.values())}개의 하이라이트 추가")

        except Exception as e:
            print(f"PDF 하이라이트 오류: {e}")
            raise

    def _find_word_positions(self, errors: List[Dict]) -> Dict[int, List[Dict]]:
        """
        pdfplumber를 사용하여 각 오류 단어의 정확한 위치 찾기

        Returns:
            {page_num: [annotation_dict, ...], ...}
        """
        annotations_by_page = {}

        with pdfplumber.open(self.input_pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_height = float(page.height)
                page_annotations = []

                # 페이지의 모든 단어와 위치 가져오기
                words = page.extract_words()

                # 각 오류에 대해 해당 페이지에서 단어 찾기
                for error in errors:
                    wrong_word = error['wrong'].strip()

                    # 페이지에서 일치하는 단어 찾기
                    for word_obj in words:
                        word_text = word_obj['text']

                        # 단어가 일치하면 (대소문자 구분 없이)
                        if wrong_word in word_text or word_text in wrong_word:
                            # PDF 좌표계로 변환 (pdfplumber는 상단이 0, PDF는 하단이 0)
                            x0 = float(word_obj['x0'])
                            y0 = page_height - float(word_obj['bottom'])  # PDF 좌표계
                            x1 = float(word_obj['x1'])
                            y1 = page_height - float(word_obj['top'])

                            annotation = {
                                'wrong': error['wrong'],
                                'correct': error['correct'],
                                'help': error.get('help', ''),
                                'bbox': [x0, y0, x1, y1]
                            }
                            page_annotations.append(annotation)
                            break  # 첫 번째 일치만 사용 (중복 방지)

                if page_annotations:
                    annotations_by_page[page_num] = page_annotations

        return annotations_by_page

    def _add_annotations_to_pdf(self, annotations_by_page: Dict[int, List[Dict]]):
        """
        PyPDF2를 사용하여 PDF에 하이라이트 주석 추가
        """
        with open(self.input_pdf_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]

                # 해당 페이지에 추가할 주석이 있으면
                if page_num in annotations_by_page:
                    annot_list = []

                    for ann in annotations_by_page[page_num]:
                        # 하이라이트 주석 생성
                        highlight_dict = DictionaryObject()
                        highlight_dict.update({
                            NameObject("/Type"): NameObject("/Annot"),
                            NameObject("/Subtype"): NameObject("/Highlight"),
                            NameObject("/Rect"): ArrayObject([
                                FloatObject(ann['bbox'][0]),
                                FloatObject(ann['bbox'][1]),
                                FloatObject(ann['bbox'][2]),
                                FloatObject(ann['bbox'][3])
                            ]),
                            NameObject("/QuadPoints"): ArrayObject([
                                FloatObject(ann['bbox'][0]), FloatObject(ann['bbox'][3]),
                                FloatObject(ann['bbox'][2]), FloatObject(ann['bbox'][3]),
                                FloatObject(ann['bbox'][0]), FloatObject(ann['bbox'][1]),
                                FloatObject(ann['bbox'][2]), FloatObject(ann['bbox'][1])
                            ]),
                            NameObject("/Contents"): TextStringObject(
                                f"틀림: {ann['wrong']}\n올바름: {ann['correct']}\n{ann.get('help', '')}"
                            ),
                            NameObject("/C"): ArrayObject([
                                FloatObject(1), FloatObject(0), FloatObject(0)  # 빨간색
                            ]),
                            NameObject("/T"): TextStringObject("맞춤법 검사기"),
                            NameObject("/F"): NumberObject(4),  # 인쇄 가능
                        })
                        annot_list.append(highlight_dict)

                    # 페이지에 주석 추가
                    if annot_list:
                        if "/Annots" in page:
                            page["/Annots"].extend(annot_list)
                        else:
                            page[NameObject("/Annots")] = ArrayObject(annot_list)

                writer.add_page(page)

            # 출력 파일 저장
            with open(self.output_pdf_path, 'wb') as output_file:
                writer.write(output_file)


# 테스트
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("사용법: python pdf_highlighter.py <입력_pdf> <출력_pdf>")
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
    print("PDF 하이라이트 테스트")
    print("=" * 60)
    print(f"입력: {input_pdf}")
    print(f"출력: {output_pdf}")
    print(f"오류 개수: {len(test_errors)}개\n")

    highlighter = PDFHighlighter(input_pdf, output_pdf)
    highlighter.add_highlights(test_errors)

    print("\n완료!")
