#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyMuPDF (fitz)를 사용한 정확한 PDF 하이라이트 모듈
텍스트 검색 또는 전달받은 좌표를 사용하여 하이라이트 추가
"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional


class PDFHighlighterFitz:
    """PyMuPDF를 사용하여 정확한 하이라이트를 추가하는 클래스"""

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

    def add_highlights(self, annotations: List[Dict], text_positions: List[Dict] = None):
        """
        전달받은 주석 정보를 기반으로 PDF에 하이라이트 추가
        """
        try:
            doc = fitz.open(self.input_pdf_path)
            total_highlights = 0
            used_texts = set()

            for annotation in annotations:
                wrong_word = (annotation.get('wrong') or '').strip()
                category = annotation.get('category', 'default')
                color = self.COLORS.get(category, self.COLORS['default'])

                page_index = max(0, int(annotation.get('page', 1)) - 1)
                if page_index >= len(doc):
                    continue

                page = doc[page_index]
                rect = self._rect_from_annotation(page, annotation)

                if rect is None and wrong_word:
                    key = (page_index, wrong_word)
                    if key in used_texts:
                        continue
                    rect = self._search_rect(page, wrong_word)
                    used_texts.add(key)

                if rect is None:
                    continue

                highlight = page.add_highlight_annot(rect)
                highlight.set_colors(stroke=color)
                highlight.set_info(
                    title=f"맞춤법 검사기",
                    content=f"틀림: {annotation.get('wrong', '')}\n"
                            f"올바름: {annotation.get('correct', '')}\n\n"
                            f"{annotation.get('help', '')}"
                )
                highlight.update()
                total_highlights += 1

            if text_positions:
                self._write_text_layer(doc, text_positions)

            doc.save(self.output_pdf_path)
            doc.close()

            print(f"✓ PDF 하이라이트 완료: {self.output_pdf_path}")
            print(f"  입력 오류: {len(annotations)}개")
            print(f"  추가된 하이라이트: {total_highlights}개")

        except Exception as e:
            print(f"PDF 하이라이트 오류: {e}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _rect_from_annotation(page, annotation) -> Optional[fitz.Rect]:
        bbox = annotation.get('bbox')
        if bbox and len(bbox) == 4:
            x0, y0, x1, y1 = bbox
            height = page.rect.height
            rect = fitz.Rect(
                x0,
                height - y1,
                x1,
                height - y0
            ) & page.rect
            if rect.is_valid and not rect.is_empty:
                return rect

        x = annotation.get('x')
        y = annotation.get('y')
        if x is None or y is None:
            return None

        padding = 8
        height = page.rect.height
        rect = fitz.Rect(
            x - padding,
            height - (y + padding),
            x + padding,
            height - (y - padding)
        ) & page.rect
        if rect.is_empty or not rect.is_valid:
            return None
        return rect

    @staticmethod
    def _search_rect(page, text: str) -> Optional[fitz.Rect]:
        matches = page.search_for(text)
        if not matches:
            return None
        return matches[0]

    def _write_text_layer(self, doc: fitz.Document, text_positions: List[Dict]):
        by_page: Dict[int, List[Dict]] = {}
        for info in text_positions:
            if not info.get('bbox'):
                continue
            page = info.get('page')
            if page is None:
                continue
            by_page.setdefault(int(page), []).append(info)

        for page_index in range(len(doc)):
            page_number = page_index + 1
            chars = by_page.get(page_number)
            if not chars:
                continue

            page = doc[page_index]
            lines = self._build_lines(chars)
            for line_text, bbox in lines:
                if not line_text.strip():
                    continue
                x0, y0, x1, y1 = bbox
                page_height = page.rect.height
                rect = fitz.Rect(
                    x0,
                    page_height - y1,
                    x1,
                    page_height - y0
                ) & page.rect
                if rect.is_empty or not rect.is_valid:
                    continue
                font_size = max(6, min(18, rect.height))
                try:
                    page.insert_textbox(
                        rect,
                        line_text,
                        fontname="helv",
                        fontsize=font_size,
                        color=(0, 0, 0),
                        overlay=True,
                        opacity=0
                    )
                except Exception:
                    continue

    @staticmethod
    def _build_lines(chars: List[Dict], line_threshold: float = 6.0):
        sorted_chars = sorted(
            chars,
            key=lambda c: (
                -((c['bbox'][1] + c['bbox'][3]) / 2),
                c['bbox'][0]
            )
        )

        lines = []
        current_boxes = []
        current_text = []
        prev_center = None

        def flush():
            nonlocal current_boxes, current_text
            if not current_boxes:
                current_text = []
                return None
            text = ''.join(current_text)
            x0 = min(box[0] for box in current_boxes)
            y0 = min(box[1] for box in current_boxes)
            x1 = max(box[2] for box in current_boxes)
            y1 = max(box[3] for box in current_boxes)
            bbox = [x0, y0, x1, y1]
            result = (text, bbox)
            current_boxes = []
            current_text = []
            return result

        for info in sorted_chars:
            char = info.get('char', '')
            bbox = info.get('bbox')
            if char == '\n':
                res = flush()
                if res:
                    lines.append(res)
                prev_center = None
                continue

            if bbox:
                center = (bbox[1] + bbox[3]) / 2
                if prev_center is None or abs(center - prev_center) <= line_threshold:
                    current_boxes.append(bbox)
                    current_text.append(char)
                else:
                    res = flush()
                    if res:
                        lines.append(res)
                    current_boxes.append(bbox)
                    current_text.append(char)
                prev_center = center
            else:
                current_text.append(char)

        res = flush()
        if res:
            lines.append(res)

        return lines


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("사용법: python pdf_highlighter_fitz.py <입력_pdf> <출력_pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    sample = [{
        'wrong': '되요',
        'correct': '돼요',
        'help': "'되다'의 활용형은 '돼요'입니다",
        'page': 1,
        'bbox': [100, 100, 150, 120]
    }]

    highlighter = PDFHighlighterFitz(input_pdf, output_pdf)
    highlighter.add_highlights(sample)
