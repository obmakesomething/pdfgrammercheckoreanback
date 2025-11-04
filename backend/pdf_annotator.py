#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 주석 생성 모듈
맞춤법 오류 위치에 빨간색 하이라이트 주석 추가
"""
import PyPDF2
from PyPDF2.generic import DictionaryObject, ArrayObject, FloatObject, NameObject, TextStringObject, NumberObject
from typing import List, Dict


class PDFAnnotator:
    """PDF에 맞춤법 오류 주석을 추가하는 클래스"""

    def __init__(self, input_pdf_path: str, output_pdf_path: str):
        """
        Args:
            input_pdf_path: 입력 PDF 파일 경로
            output_pdf_path: 출력 PDF 파일 경로
        """
        self.input_pdf_path = input_pdf_path
        self.output_pdf_path = output_pdf_path

    def add_annotations(self, annotations: List[Dict]):
        """
        PDF에 주석 추가

        Args:
            annotations: 주석 정보 리스트
                [
                    {
                        'wrong': '틀린 단어',
                        'correct': '올바른 단어',
                        'help': '설명',
                        'page': 페이지 번호 (1부터 시작),
                        'x': x 좌표,
                        'y': y 좌표
                    },
                    ...
                ]
        """
        try:
            # PDF 읽기
            with open(self.input_pdf_path, 'rb') as input_file:
                reader = PyPDF2.PdfReader(input_file)
                writer = PyPDF2.PdfWriter()

                # 각 페이지 복사
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]

                    # 해당 페이지의 주석들 필터링
                    page_annotations = [
                        ann for ann in annotations
                        if ann.get('page', 1) == page_num + 1
                    ]

                    # 주석 추가
                    for ann in page_annotations:
                        self._add_highlight_annotation(page, ann)

                    writer.add_page(page)

                # 출력 파일 저장
                with open(self.output_pdf_path, 'wb') as output_file:
                    writer.write(output_file)

            print(f"✓ PDF 주석이 생성되었습니다: {self.output_pdf_path}")
            print(f"  총 {len(annotations)}개의 오류에 주석을 추가했습니다.")

        except Exception as e:
            print(f"PDF 주석 추가 오류: {e}")
            raise

    def _add_highlight_annotation(self, page, annotation: Dict):
        """
        페이지에 하이라이트 주석 추가

        Args:
            page: PDF 페이지 객체
            annotation: 주석 정보
        """
        try:
            # 페이지 크기 가져오기
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            # 주석 위치 (기본값 설정)
            x = annotation.get('x', 100)
            y = annotation.get('y', page_height - 100)

            # x, y가 None인 경우 기본값 사용
            if x is None:
                x = 100
            if y is None:
                y = page_height - 100

            # 단어 길이에 따라 하이라이트 크기 조정
            word_length = len(annotation.get('wrong', '오류'))
            width = max(50, word_length * 10)  # 최소 50, 글자당 10pt
            height = 15

            # 텍스트 주석 생성 (Text Annotation)
            annotation_dict = DictionaryObject()
            annotation_dict.update({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/FreeText"),
                NameObject("/Rect"): ArrayObject([
                    FloatObject(x),
                    FloatObject(y - height),
                    FloatObject(x + width),
                    FloatObject(y)
                ]),
                NameObject("/Contents"): TextStringObject(
                    f"틀림: {annotation['wrong']}\n올바름: {annotation['correct']}\n{annotation.get('help', '')}"
                ),
                NameObject("/C"): ArrayObject([FloatObject(1), FloatObject(0), FloatObject(0)]),  # 빨간색
                NameObject("/T"): TextStringObject("맞춤법 검사기"),
                NameObject("/DA"): TextStringObject("/Helv 10 Tf 1 0 0 rg"),  # 폰트 및 색상
                NameObject("/F"): NumberObject(4),  # 플래그: 인쇄 가능
            })

            # 페이지에 주석 추가
            if "/Annots" in page:
                page["/Annots"].append(annotation_dict)
            else:
                page[NameObject("/Annots")] = ArrayObject([annotation_dict])

        except Exception as e:
            print(f"  주석 추가 실패 ({annotation.get('wrong', '?')}): {e}")

    def create_simple_annotation(self, annotations: List[Dict]):
        """
        간단한 텍스트 주석 추가 (FreeText 대신 Text 사용)
        """
        try:
            with open(self.input_pdf_path, 'rb') as input_file:
                reader = PyPDF2.PdfReader(input_file)
                writer = PyPDF2.PdfWriter()

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_annotations = [
                        ann for ann in annotations
                        if ann.get('page', 1) == page_num + 1
                    ]

                    # 페이지에 주석 목록 준비
                    annot_list = []

                    for i, ann in enumerate(page_annotations):
                        # 각 오류마다 텍스트 주석 생성
                        media_box = page.mediabox
                        page_height = float(media_box.height)

                        # y 좌표 계산 (위에서부터 배치)
                        y_pos = page_height - 50 - (i * 30)

                        annot_dict = DictionaryObject()
                        annot_dict.update({
                            NameObject("/Type"): NameObject("/Annot"),
                            NameObject("/Subtype"): NameObject("/Text"),
                            NameObject("/Rect"): ArrayObject([
                                FloatObject(50),
                                FloatObject(y_pos),
                                FloatObject(70),
                                FloatObject(y_pos + 20)
                            ]),
                            NameObject("/Contents"): TextStringObject(
                                f"{ann['wrong']} → {ann['correct']}\n{ann.get('help', '')}"
                            ),
                            NameObject("/Name"): NameObject("/Comment"),
                            NameObject("/C"): ArrayObject([
                                FloatObject(1), FloatObject(0), FloatObject(0)
                            ]),
                            NameObject("/T"): TextStringObject("맞춤법"),
                        })
                        annot_list.append(annot_dict)

                    # 주석 추가
                    if annot_list:
                        if "/Annots" in page:
                            page["/Annots"].extend(annot_list)
                        else:
                            page[NameObject("/Annots")] = ArrayObject(annot_list)

                    writer.add_page(page)

                with open(self.output_pdf_path, 'wb') as output_file:
                    writer.write(output_file)

            print(f"✓ 간단한 주석 PDF 생성 완료: {self.output_pdf_path}")

        except Exception as e:
            print(f"간단한 주석 추가 오류: {e}")
            raise


# 테스트
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("사용법: python pdf_annotator.py <입력_pdf> <출력_pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    # 테스트 주석
    test_annotations = [
        {
            'wrong': '되요',
            'correct': '돼요',
            'help': "'되다'의 활용형은 '돼요'입니다",
            'page': 1,
            'x': 100,
            'y': 700
        },
        {
            'wrong': '안되는',
            'correct': '안 되는',
            'help': "'안 되다'는 띄어 씁니다",
            'page': 1,
            'x': 100,
            'y': 650
        }
    ]

    print("=" * 60)
    print("PDF 주석 추가 테스트")
    print("=" * 60)
    print(f"입력: {input_pdf}")
    print(f"출력: {output_pdf}")
    print(f"주석 개수: {len(test_annotations)}개\n")

    annotator = PDFAnnotator(input_pdf, output_pdf)
    annotator.create_simple_annotation(test_annotations)

    print("\n완료!")
