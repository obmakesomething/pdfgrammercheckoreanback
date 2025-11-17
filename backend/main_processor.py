#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 프로세서
PDF 파일을 받아 전체 맞춤법 검사 파이프라인 실행
"""
import os
import tempfile
import logging
import json
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from pdf_extractor import (
    SimplePDFExtractor,
    GoogleVisionExtractor,
    GOOGLE_VISION_AVAILABLE,
)
from text_preprocessor import TextPreprocessor
from spell_checker import SpellChecker
from pdf_annotator import PDFAnnotator
try:
    from pdf_highlighter_fitz import PDFHighlighterFitz as PDFHighlighter
    FITZ_AVAILABLE = True
except ImportError:
    from pdf_highlighter import PDFHighlighter
    FITZ_AVAILABLE = False
    print("경고: PyMuPDF가 없습니다. pdfplumber 버전 사용")


LOG_DIR = os.getenv(
    'GRAMMAR_LOG_DIR',
    os.path.join(os.path.dirname(__file__), 'logs')
)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'processor.log')

logger = logging.getLogger('GrammarCheckProcessor')
if not logger.handlers:
    handler = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

USE_GOOGLE_VISION_OCR = os.getenv('USE_GOOGLE_VISION_OCR', 'true').lower() == 'true'
FORCE_GOOGLE_VISION_OCR = os.getenv('FORCE_GOOGLE_VISION_OCR', 'false').lower() == 'true'
OCR_MIN_TEXT_LENGTH = int(os.getenv('OCR_MIN_TEXT_LENGTH', '200'))
OCR_EXCEPTION_TEXT_LENGTH = int(os.getenv('OCR_EXCEPTION_TEXT_LENGTH', '100'))


class GrammarCheckProcessor:
    """PDF 맞춤법 검사 전체 프로세스 관리"""

    def __init__(self):
        self.spell_checker = SpellChecker()
        self.logger = logger
        self.use_google_vision = USE_GOOGLE_VISION_OCR and GOOGLE_VISION_AVAILABLE
        self.force_google_vision = FORCE_GOOGLE_VISION_OCR
        self.ocr_min_text_length = max(1, OCR_MIN_TEXT_LENGTH)
        self.ocr_exception_text_length = max(1, OCR_EXCEPTION_TEXT_LENGTH)
        self.snapshot_dir = os.path.join(LOG_DIR, 'snapshots')
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def process(self, input_pdf_path: str, output_pdf_path: str = None) -> dict:
        """
        PDF 맞춤법 검사 전체 프로세스 실행

        Args:
            input_pdf_path: 입력 PDF 파일 경로
            output_pdf_path: 출력 PDF 파일 경로 (없으면 자동 생성)

        Returns:
            dict: 처리 결과
                {
                    'success': bool,
                    'errors_found': int,
                    'output_pdf': str,
                    'message': str
                }
        """
        print("\n" + "=" * 70)
        print("PDF 맞춤법 검사 시작")
        print("=" * 70)
        self.logger.info("=== Grammar check started for: %s ===", input_pdf_path)

        try:
            # 1단계: PDF 텍스트 추출 (파라그래프 단위)
            print("\n[1/5] PDF 텍스트 추출 중 (파라그래프 단위)...")
            extraction = self._extract_text_with_autodetect(input_pdf_path)
            if not extraction:
                raise RuntimeError("PDF 텍스트 추출에 실패했습니다")

            (
                paragraphs,
                text_with_positions,
                raw_text,
                used_vision,
                text_stats,
            ) = extraction

            source_label = "Google Vision OCR" if used_vision else "pdfplumber"
            print(f"  ➤ {source_label} 기반 텍스트 추출을 사용합니다")
            print(f"  ✓ 총 {len(text_with_positions)}자 추출 완료")
            print(f"  ✓ 파라그래프 개수: {len(paragraphs)}개")
            print(
                f"  ✓ 텍스트 길이: {text_stats['non_whitespace_chars']}자 "
                f"(임계값: {self.ocr_min_text_length}자)"
            )
            self.logger.info(
                "텍스트 추출 완료 | source=%s non_whitespace=%d paragraphs=%d",
                source_label,
                text_stats['non_whitespace_chars'],
                text_stats['paragraphs']
            )
            preview = raw_text[:100].replace('\n', ' ').strip()
            if preview:
                print(f"  ✓ 텍스트 미리보기: {preview}...")
                self.logger.info("텍스트 샘플: %s", preview)

            if text_stats['non_whitespace_chars'] < self.ocr_exception_text_length:
                print(
                    "  ⚠ 추출된 텍스트가 너무 적어 예외 처리합니다 "
                    f"({text_stats['non_whitespace_chars']}자 < {self.ocr_exception_text_length}자)"
                )
                self.logger.warning(
                    "텍스트 부족으로 예외 처리: chars=%d path=%s",
                    text_stats['non_whitespace_chars'],
                    input_pdf_path
                )
                return {
                    'success': False,
                    'errors_found': 0,
                    'output_pdf': None,
                    'message': (
                        "추출된 텍스트가 너무 적어 분석할 수 없습니다. "
                        "스캔 PDF라면 OCR이 가능한 버전으로 다시 업로드해주세요."
                    )
                }

            # 2단계: 텍스트 전처리 (앵커 매핑)
            print("\n[2/5] 텍스트 전처리 중...")
            preprocessor = TextPreprocessor(text_with_positions, raw_text)
            cleaned_text, anchor_map = preprocessor.preprocess()
            print(f"  ✓ 전처리 완료: {len(cleaned_text)}자")
            print(f"  ✓ 앵커 맵 크기: {len(anchor_map)}개")

            # 3단계: 맞춤법 검사 (파라그래프 단위)
            print("\n[3/5] 맞춤법 검사 중 (파라그래프 단위)...")
            errors = self.spell_checker.check_paragraphs(paragraphs)
            print(f"  ✓ 검사 완료: {len(errors)}개 오류 발견")

            if len(errors) == 0:
                print("\n  맞춤법 오류가 발견되지 않았습니다!")
                return {
                    'success': True,
                    'errors_found': 0,
                    'output_pdf': None,
                    'message': '맞춤법 오류가 발견되지 않았습니다.'
                }

            # 4단계: 앵커 역추적 (오류 위치를 원본 PDF 위치로)
            print("\n[4/5] 오류 위치 역추적 중...")
            annotations = self._create_annotations(
                errors, preprocessor, text_with_positions
            )
            print(f"  ✓ {len(annotations)}개 주석 생성")
            snapshot_file = self._save_snapshot(
                input_pdf_path,
                used_vision,
                text_stats,
                raw_text,
                cleaned_text,
                annotations
            )
            self.logger.info("스냅샷 저장: %s", snapshot_file)

            # 오류 목록 출력
            print("\n  발견된 오류들:")
            for i, ann in enumerate(annotations[:10], 1):  # 처음 10개만
                print(f"    {i}. '{ann['wrong']}' → '{ann['correct']}'")
                if ann.get('help'):
                    print(f"       ({ann['help']})")
            if len(annotations) > 10:
                print(f"    ... 외 {len(annotations) - 10}개")

            # 5단계: PDF 하이라이트 생성
            print("\n[5/5] PDF 하이라이트 생성 중...")
            if output_pdf_path is None:
                base_name = os.path.splitext(input_pdf_path)[0]
                output_pdf_path = f"{base_name}_검사완료.pdf"

            # PDFHighlighter 사용 (pdfplumber로 정확한 위치 찾기)
            highlighter = PDFHighlighter(input_pdf_path, output_pdf_path)
            try:
                highlighter.add_highlights(annotations, text_with_positions)
            except TypeError:
                highlighter.add_highlights(annotations)

            print("\n" + "=" * 70)
            print("✓ 처리 완료!")
            print("=" * 70)
            print(f"입력 파일: {input_pdf_path}")
            print(f"출력 파일: {output_pdf_path}")
            print(f"감지된 오류: {len(errors)}개")
            print(f"PDF에 표시된 오류: {len(annotations)}개")

            return {
                'success': True,
                'errors_found': len(annotations),  # 실제 PDF에 표시된 오류 개수
                'output_pdf': output_pdf_path,
                'annotations': annotations,
                'message': f'{len(annotations)}개의 맞춤법 오류를 발견했습니다.'
            }

        except Exception as e:
            print(f"\n✗ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'errors_found': 0,
                'output_pdf': None,
                'message': f'처리 중 오류 발생: {str(e)}'
            }

    def _extract_text_with_autodetect(
        self, input_pdf_path: str
    ) -> Tuple[list, list, str, bool, dict]:
        """
        기본 추출 후 텍스트가 부족하면 자동으로 Vision OCR을 재시도한다.
        Returns:
            paragraphs, text_with_positions, raw_text, used_vision, stats
        """

        def build_stats(paragraphs, raw_text):
            non_whitespace = sum(1 for c in raw_text if not c.isspace())
            return {
                'non_whitespace_chars': non_whitespace,
                'paragraphs': len(paragraphs),
            }

        try:
            simple_extractor = SimplePDFExtractor(input_pdf_path)
            paragraphs, text_with_positions, raw_text = simple_extractor.extract_paragraphs_with_positions()
            stats = build_stats(paragraphs, raw_text)
            self.logger.info(
                "pdfplumber 추출 결과 | chars=%d paragraphs=%d",
                stats['non_whitespace_chars'],
                stats['paragraphs']
            )
            need_ocr = (
                self.force_google_vision
                or stats['non_whitespace_chars'] < self.ocr_min_text_length
                or stats['paragraphs'] == 0
            )

            if need_ocr:
                reason = (
                    "강제 실행"
                    if self.force_google_vision
                    else f"텍스트 {stats['non_whitespace_chars']}자"
                )
                if not self.use_google_vision:
                    print(
                        f"  ⚠ Vision OCR 필요({reason})하지만 비활성화되어 pdfplumber 결과를 사용합니다."
                    )
                    self.logger.warning(
                        "Vision OCR 필요(%s)하지만 비활성화됨", reason
                    )
                    return paragraphs, text_with_positions, raw_text, False, stats

                print(f"  ➤ Vision OCR 재시도: {reason}")
                self.logger.info("Vision OCR 재시도 사유: %s", reason)
                try:
                    vision_extractor = GoogleVisionExtractor(input_pdf_path)
                except Exception as vision_error:
                    print(
                        f"  ⚠ Google Vision 초기화 오류: {vision_error}. pdfplumber 결과로 계속 진행합니다."
                    )
                    self.logger.exception("Google Vision 초기화 오류: %s", vision_error)
                    return paragraphs, text_with_positions, raw_text, False, stats

                paragraphs, text_with_positions, raw_text = vision_extractor.extract_paragraphs_with_positions()
                stats = build_stats(paragraphs, raw_text)
                self.logger.info(
                    "Vision OCR 추출 결과 | chars=%d paragraphs=%d",
                    stats['non_whitespace_chars'],
                    stats['paragraphs']
                )
                return paragraphs, text_with_positions, raw_text, True, stats

            return paragraphs, text_with_positions, raw_text, False, stats
        except Exception as e:
            print(f"  ✗ 기본 텍스트 추출 실패: {e}")
            self.logger.exception("텍스트 추출 실패: %s", e)
            raise

    def _create_annotations(self, errors, preprocessor, text_with_positions):
        """
        맞춤법 오류를 PDF 주석으로 변환

        Args:
            errors: 맞춤법 오류 목록
            preprocessor: TextPreprocessor 인스턴스
            text_with_positions: 원본 문자 위치 정보

        Returns:
            list: 주석 정보 목록
        """
        annotations = []
        seen_keys = set()

        for error in errors:
            # cleaned_text에서의 위치
            cleaned_start = error.get('position', 0)
            cleaned_end = cleaned_start + error.get('length', len(error['wrong']))

            # 원본 위치로 역추적
            original_indices = preprocessor.get_original_positions(
                cleaned_start, cleaned_end
            )

            if original_indices and len(original_indices) > 0:
                first_idx = original_indices[0]

                if first_idx < len(text_with_positions):
                    first_char_info = text_with_positions[first_idx]
                    char_infos = [
                        text_with_positions[idx]
                        for idx in original_indices
                        if 0 <= idx < len(text_with_positions)
                    ]
                    line_boxes = self._build_line_boxes(char_infos)

                    if not line_boxes:
                        single_box = self._aggregate_bbox(char_infos)
                        if single_box:
                            line_boxes = [single_box]

                    if not line_boxes:
                        self.logger.warning(
                            "좌표를 찾지 못해 기본 위치 사용 | word=%s page=%s",
                            error['wrong'],
                            first_char_info.get('page')
                        )
                        line_boxes = [None]

                    for box in line_boxes:
                        key = (
                            error['wrong'],
                            first_char_info['page'],
                            None if box is None else tuple(round(v, 2) for v in box)
                        )
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        annotation = {
                            'wrong': error['wrong'],
                            'correct': error['correct'],
                            'help': error.get('help', ''),
                            'category': error.get('category', 'default'),
                            'page': first_char_info['page'],
                            'x': first_char_info.get('x'),
                            'y': first_char_info.get('y'),
                            'bbox': box
                        }
                        annotations.append(annotation)
            else:
                # 위치를 찾을 수 없는 경우 기본값 사용
                annotation = {
                    'wrong': error['wrong'],
                    'correct': error['correct'],
                    'help': error.get('help', ''),
                    'category': error.get('category', 'default'),
                    'page': 1,
                    'x': None,
                    'y': None,
                    'bbox': None
                }
                annotations.append(annotation)

        return annotations

    @staticmethod
    def _aggregate_bbox(chars):
        """
        주어진 문자 리스트의 경계 박스를 계산
        """
        valid_boxes = [c.get('bbox') for c in chars if c.get('bbox')]
        if not valid_boxes:
            return None

        x0 = min(box[0] for box in valid_boxes)
        y0 = min(box[1] for box in valid_boxes)
        x1 = max(box[2] for box in valid_boxes)
        y1 = max(box[3] for box in valid_boxes)
        return [x0, y0, x1, y1]

    @staticmethod
    def _merge_boxes(boxes: List[List[float]]):
        x0 = min(box[0] for box in boxes)
        y0 = min(box[1] for box in boxes)
        x1 = max(box[2] for box in boxes)
        y1 = max(box[3] for box in boxes)
        return [x0, y0, x1, y1]

    def _build_line_boxes(self, chars: List[dict], line_threshold: float = 10.0):
        """
        문자 좌표를 라인 단위로 묶어 여러 개의 bbox를 생성
        """
        lines: List[List[List[float]]] = []
        current: List[List[float]] = []
        prev_center = None

        for info in chars:
            bbox = info.get('bbox')
            if not bbox:
                continue
            center = (bbox[1] + bbox[3]) / 2

            if prev_center is None or abs(center - prev_center) <= line_threshold:
                current.append(bbox)
            else:
                if current:
                    lines.append(current)
                current = [bbox]
            prev_center = center

        if current:
            lines.append(current)

        return [self._merge_boxes(line) for line in lines if line]

    def _save_snapshot(
        self,
        input_pdf_path: str,
        used_vision: bool,
        text_stats: dict,
        raw_text: str,
        cleaned_text: str,
        annotations: List[dict]
    ) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = os.path.splitext(os.path.basename(input_pdf_path))[0]
        filename = f"{timestamp}_{base}.json"
        path = os.path.join(self.snapshot_dir, filename)
        snapshot = {
            'input_pdf': input_pdf_path,
            'timestamp': timestamp,
            'used_vision': used_vision,
            'text_stats': text_stats,
            'raw_text_length': len(raw_text),
            'cleaned_text_length': len(cleaned_text),
            'raw_text_preview': raw_text[:1000],
            'cleaned_text_preview': cleaned_text[:1000],
            'annotations_count': len(annotations),
            'annotations': annotations,
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.exception("스냅샷 저장 실패: %s", e)
        return path


# CLI 실행
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python main_processor.py <pdf_파일_경로> [출력_파일_경로]")
        print("\n예시:")
        print("  python main_processor.py input.pdf")
        print("  python main_processor.py input.pdf output.pdf")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_pdf):
        print(f"오류: 파일을 찾을 수 없습니다: {input_pdf}")
        sys.exit(1)

    processor = GrammarCheckProcessor()
    result = processor.process(input_pdf, output_pdf)

    if result['success']:
        print(f"\n완료! 출력 파일을 확인하세요: {result['output_pdf']}")
    else:
        print(f"\n실패: {result['message']}")
        sys.exit(1)
