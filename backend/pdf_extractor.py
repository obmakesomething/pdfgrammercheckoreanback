#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 텍스트 추출 모듈
문자 단위로 위치 정보(페이지, x, y)를 함께 추출
"""
import pypdfium2 as pdfium


class PDFTextExtractor:
    """PDF에서 텍스트와 위치 정보를 추출하는 클래스"""

    def __init__(self, pdf_path):
        """
        Args:
            pdf_path: PDF 파일 경로
        """
        self.pdf_path = pdf_path
        self.pdf = None

    def extract_text_with_positions(self):
        """
        PDF에서 문자 단위로 텍스트와 위치 정보를 추출

        Returns:
            tuple: (text_with_positions, raw_text)
                - text_with_positions: 각 문자의 위치 정보 리스트
                - raw_text: 전체 텍스트 문자열
        """
        try:
            # PDF 문서 열기
            self.pdf = pdfium.PdfDocument(self.pdf_path)
            total_pages = len(self.pdf)

            text_with_positions = []
            raw_text_parts = []
            char_index = 0

            # 각 페이지 순회
            for page_num in range(total_pages):
                page = self.pdf[page_num]
                textpage = page.get_textpage()

                # 페이지의 전체 텍스트 가져오기
                page_text = textpage.get_text_range()

                # 문자 단위로 순회하면서 위치 정보 추출
                for char_idx, char in enumerate(page_text):
                    char_info = {
                        'char': char,
                        'page': page_num + 1,  # 1부터 시작
                        'index': char_index
                    }

                    # 좌표 정보 가져오기 (가능한 경우)
                    try:
                        # 문자의 바운딩 박스 가져오기
                        # get_text_bounded는 특정 영역의 텍스트를 가져오는 메서드
                        # 여기서는 단일 문자의 위치를 추정
                        # 실제로는 textpage의 get_charbox 또는 유사 메서드 사용
                        # pypdfium2의 버전에 따라 다를 수 있음

                        # 간단한 방식: 페이지 높이와 너비 기준으로 추정
                        # 실제 구현에서는 더 정확한 방법 필요
                        char_info['x'] = None
                        char_info['y'] = None

                    except:
                        char_info['x'] = None
                        char_info['y'] = None

                    text_with_positions.append(char_info)
                    raw_text_parts.append(char)
                    char_index += 1

                # 페이지 리소스 해제
                textpage.close()
                page.close()

            # PDF 닫기
            self.pdf.close()

            raw_text = ''.join(raw_text_parts)
            return text_with_positions, raw_text

        except Exception as e:
            print(f"PDF 추출 오류: {e}")
            if self.pdf:
                self.pdf.close()
            raise

    def extract_text_simple(self):
        """
        간단한 텍스트 추출 (위치 정보 없이)

        Returns:
            str: 전체 텍스트
        """
        try:
            pdf = pdfium.PdfDocument(self.pdf_path)
            text_parts = []

            for page in pdf:
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                text_parts.append(text)
                textpage.close()
                page.close()

            pdf.close()
            return '\n'.join(text_parts)

        except Exception as e:
            print(f"PDF 추출 오류: {e}")
            raise


# 더 나은 방식: pdfplumber를 사용한 정확한 좌표 추출
class SimplePDFExtractor:
    """pdfplumber를 사용한 정확한 PDF 텍스트 및 좌표 추출"""

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_text_with_positions(self):
        """
        문자 단위로 텍스트와 정확한 위치 정보 추출 (pdfplumber 사용)

        Returns:
            tuple: (text_with_positions, raw_text)
        """
        try:
            import pdfplumber
        except ImportError:
            print("경고: pdfplumber가 설치되지 않아 PyPDF2를 사용합니다 (좌표 정보 없음)")
            return self._extract_with_pypdf2()

        text_with_positions = []
        raw_text_parts = []
        char_index = 0

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # 문자 단위로 추출 (chars에 각 문자의 좌표 정보 포함)
                    chars = page.chars

                    for char_obj in chars:
                        char = char_obj['text']

                        # pdfplumber 좌표계: 왼쪽 상단이 (0,0)
                        # PDF 좌표계: 왼쪽 하단이 (0,0)이므로 변환 필요
                        page_height = float(page.height)

                        char_info = {
                            'char': char,
                            'page': page_num + 1,
                            'x': float(char_obj['x0']),  # 문자 왼쪽 x 좌표
                            'y': page_height - float(char_obj['top']),  # PDF 좌표계로 변환
                            'index': char_index
                        }

                        text_with_positions.append(char_info)
                        raw_text_parts.append(char)
                        char_index += 1

            raw_text = ''.join(raw_text_parts)
            return text_with_positions, raw_text

        except Exception as e:
            print(f"pdfplumber 추출 오류: {e}, PyPDF2로 대체합니다")
            return self._extract_with_pypdf2()

    def _extract_with_pypdf2(self):
        """
        PyPDF2를 사용한 fallback 방식 (좌표 정보 없음)
        """
        import PyPDF2

        text_with_positions = []
        raw_text_parts = []
        char_index = 0

        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()

                # 각 문자에 페이지 정보 추가
                for char in page_text:
                    char_info = {
                        'char': char,
                        'page': page_num + 1,
                        'x': None,  # PyPDF2로는 정확한 좌표 추출 어려움
                        'y': None,
                        'index': char_index
                    }
                    text_with_positions.append(char_info)
                    raw_text_parts.append(char)
                    char_index += 1

        raw_text = ''.join(raw_text_parts)
        return text_with_positions, raw_text


# 테스트
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python pdf_extractor.py <pdf_파일_경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print("=" * 60)
    print("PDF 텍스트 추출 테스트")
    print("=" * 60)
    print(f"파일: {pdf_path}\n")

    try:
        # SimplePDFExtractor 사용
        extractor = SimplePDFExtractor(pdf_path)
        text_with_positions, raw_text = extractor.extract_text_with_positions()

        print(f"총 문자 수: {len(text_with_positions)}")
        print(f"총 텍스트 길이: {len(raw_text)}")
        print(f"\n처음 500자:\n{raw_text[:500]}")
        print(f"\n처음 10개 문자 정보:")
        for i, char_info in enumerate(text_with_positions[:10]):
            print(f"  [{i}] '{char_info['char']}' - 페이지: {char_info['page']}")

    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)
