#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 텍스트 추출 모듈
Google Vision OCR + pdfplumber fallback
"""
import io
import json
import os

import pypdfium2 as pdfium

try:
    from google.cloud import vision
    from google.oauth2 import service_account
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    vision = None
    service_account = None
    GOOGLE_VISION_AVAILABLE = False


class PDFTextExtractor:
    """기본 PDF 텍스트 추출 (pypdfium2)"""

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.pdf = None

    def extract_text_with_positions(self):
        try:
            self.pdf = pdfium.PdfDocument(self.pdf_path)
            total_pages = len(self.pdf)

            text_with_positions = []
            raw_text_parts = []
            char_index = 0

            for page_num in range(total_pages):
                page = self.pdf[page_num]
                textpage = page.get_textpage()
                page_text = textpage.get_text_range()

                for char in page_text:
                    char_info = {
                        'char': char,
                        'page': page_num + 1,
                        'index': char_index,
                        'x': None,
                        'y': None
                    }
                    text_with_positions.append(char_info)
                    raw_text_parts.append(char)
                    char_index += 1

                textpage.close()
                page.close()

            self.pdf.close()
            raw_text = ''.join(raw_text_parts)
            return text_with_positions, raw_text

        except Exception as e:
            print(f"PDF 추출 오류: {e}")
            if self.pdf:
                self.pdf.close()
            raise

    def extract_text_simple(self):
        try:
            pdf = pdfium.PdfDocument(self.pdf_path)
            text_parts = []

            for page in pdf:
                textpage = page.get_textpage()
                text_parts.append(textpage.get_text_range())
                textpage.close()
                page.close()

            pdf.close()
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"PDF 추출 오류: {e}")
            raise


class SimplePDFExtractor:
    """pdfplumber 기반 텍스트 + 좌표 추출"""

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_paragraphs_with_positions(self):
        text_with_positions, raw_text = self.extract_text_with_positions()
        paragraphs = self._split_into_paragraphs(text_with_positions, raw_text)
        return paragraphs, text_with_positions, raw_text

    @staticmethod
    def _split_into_paragraphs(text_with_positions, raw_text):
        paragraphs = []
        current_para = []
        current_start = 0

        for i, char in enumerate(raw_text):
            current_para.append(char)

            if i > 0:
                if char == '\n' and raw_text[i-1] == '\n':
                    para_text = ''.join(current_para).strip()
                    if para_text:
                        paragraphs.append({
                            'text': para_text,
                            'start_index': current_start,
                            'end_index': i,
                            'page': text_with_positions[current_start]['page'] if current_start < len(text_with_positions) else 1
                        })
                    current_para = []
                    current_start = i + 1
                elif len(current_para) >= 300 and char == '\n' and raw_text[i-1] in '.?!':
                    para_text = ''.join(current_para).strip()
                    if para_text:
                        paragraphs.append({
                            'text': para_text,
                            'start_index': current_start,
                            'end_index': i,
                            'page': text_with_positions[current_start]['page'] if current_start < len(text_with_positions) else 1
                        })
                    current_para = []
                    current_start = i + 1

        if current_para:
            para_text = ''.join(current_para).strip()
            if para_text:
                paragraphs.append({
                    'text': para_text,
                    'start_index': current_start,
                    'end_index': len(raw_text),
                    'page': text_with_positions[current_start]['page'] if current_start < len(text_with_positions) else 1
                })

        return paragraphs

    def extract_text_with_positions(self):
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
                    chars = page.chars
                    page_height = float(page.height)

                    for char_obj in chars:
                        char = char_obj['text']
                        char_info = {
                            'char': char,
                            'page': page_num + 1,
                            'x': float(char_obj['x0']),
                            'y': page_height - float(char_obj['top']),
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
        import PyPDF2

        text_with_positions = []
        raw_text_parts = []
        char_index = 0

        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ''
                for char in page_text:
                    char_info = {
                        'char': char,
                        'page': page_num + 1,
                        'x': None,
                        'y': None,
                        'index': char_index
                    }
                    text_with_positions.append(char_info)
                    raw_text_parts.append(char)
                    char_index += 1

        raw_text = ''.join(raw_text_parts)
        return text_with_positions, raw_text


class GoogleVisionExtractor(SimplePDFExtractor):
    """Google Cloud Vision Document OCR"""

    def __init__(self, pdf_path, scale=2.0):
        super().__init__(pdf_path)
        if not GOOGLE_VISION_AVAILABLE:
            raise ImportError("google-cloud-vision 패키지가 설치되지 않았습니다")

        self.scale = scale
        self.client = self._create_client()

    def _create_client(self):
        cred_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        credentials = None

        try:
            if cred_json:
                info = json.loads(cred_json)
                credentials = service_account.Credentials.from_service_account_info(info)
                print("Google Vision: 서비스 계정 JSON(환경 변수)으로 인증합니다.")
            elif cred_path and os.path.exists(cred_path):
                credentials = service_account.Credentials.from_service_account_file(cred_path)
                print(f"Google Vision: 서비스 계정 파일({cred_path})로 인증합니다.")
            else:
                print("Google Vision: 별도 자격 증명 없이 기본 ADC를 사용합니다.")
        except Exception as cred_error:
            print(f"Google Vision 자격 증명 로딩 실패: {cred_error}")

        if credentials:
            return vision.ImageAnnotatorClient(credentials=credentials)
        return vision.ImageAnnotatorClient()

    def extract_text_with_positions(self):
        pdf = pdfium.PdfDocument(self.pdf_path)

        text_with_positions = []
        raw_text_parts = []
        char_index = 0

        for page_num in range(len(pdf)):
            page = pdf[page_num]
            bitmap = page.render(scale=self.scale)
            pil_image = bitmap.to_pil()

            image_bytes = io.BytesIO()
            pil_image.save(image_bytes, format='PNG')
            image_content = image_bytes.getvalue()

            bitmap.close()
            page.close()

            image = vision.Image(content=image_content)
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                raise RuntimeError(f"Vision API 오류: {response.error.message}")

            annotations = response.full_text_annotation
            if not annotations or not annotations.pages:
                continue

            for annotation_page in annotations.pages:
                for block in annotation_page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            for symbol in word.symbols:
                                char = symbol.text or ''
                                if not char:
                                    continue

                                x, y = self._get_symbol_center(symbol)
                                char_info = {
                                    'char': char,
                                    'page': page_num + 1,
                                    'x': x,
                                    'y': y,
                                    'index': char_index
                                }
                                text_with_positions.append(char_info)
                                raw_text_parts.append(char)
                                char_index += 1

                                break_type = None
                                if symbol.property and symbol.property.detected_break:
                                    break_type = symbol.property.detected_break.type_

                                if break_type in (
                                    vision.TextAnnotation.DetectedBreak.Type.SPACE,
                                    vision.TextAnnotation.DetectedBreak.Type.EOL_SURE_SPACE
                                ):
                                    text_with_positions.append({
                                        'char': ' ',
                                        'page': page_num + 1,
                                        'x': None,
                                        'y': None,
                                        'index': char_index
                                    })
                                    raw_text_parts.append(' ')
                                    char_index += 1
                                elif break_type == vision.TextAnnotation.DetectedBreak.Type.LINE_BREAK:
                                    text_with_positions.append({
                                        'char': '\n',
                                        'page': page_num + 1,
                                        'x': None,
                                        'y': None,
                                        'index': char_index
                                    })
                                    raw_text_parts.append('\n')
                                    char_index += 1

            text_with_positions.append({
                'char': '\n',
                'page': page_num + 1,
                'x': None,
                'y': None,
                'index': char_index
            })
            raw_text_parts.append('\n')
            char_index += 1

        pdf.close()
        raw_text = ''.join(raw_text_parts)
        return text_with_positions, raw_text

    def extract_paragraphs_with_positions(self):
        text_with_positions, raw_text = self.extract_text_with_positions()
        paragraphs = self._split_into_paragraphs(text_with_positions, raw_text)
        return paragraphs, text_with_positions, raw_text

    @staticmethod
    def _get_symbol_center(symbol):
        if not symbol.bounding_box or not symbol.bounding_box.vertices:
            return None, None

        xs = [v.x for v in symbol.bounding_box.vertices if v.x is not None]
        ys = [v.y for v in symbol.bounding_box.vertices if v.y is not None]

        if not xs or not ys:
            return None, None

        return sum(xs) / len(xs), sum(ys) / len(ys)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python pdf_extractor.py <pdf_파일_경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        if GOOGLE_VISION_AVAILABLE and os.getenv('USE_GOOGLE_VISION_OCR', 'true').lower() == 'true':
            extractor = GoogleVisionExtractor(pdf_path)
            print("Google Vision OCR로 텍스트를 추출합니다")
        else:
            extractor = SimplePDFExtractor(pdf_path)
            print("pdfplumber 기반 텍스트를 추출합니다")

        paragraphs, text_with_positions, raw_text = extractor.extract_paragraphs_with_positions()
        print(f"총 문자 수: {len(text_with_positions)}")
        print(f"총 텍스트 길이: {len(raw_text)}")
        print(f"파라그래프 수: {len(paragraphs)}")
    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)
