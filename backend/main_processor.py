#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 프로세서
PDF 파일을 받아 전체 맞춤법 검사 파이프라인 실행
"""
import os
import tempfile
from pdf_extractor import SimplePDFExtractor
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


class GrammarCheckProcessor:
    """PDF 맞춤법 검사 전체 프로세스 관리"""

    def __init__(self):
        self.spell_checker = SpellChecker()

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

        try:
            # 1단계: PDF 텍스트 추출
            print("\n[1/5] PDF 텍스트 추출 중...")
            extractor = SimplePDFExtractor(input_pdf_path)
            text_with_positions, raw_text = extractor.extract_text_with_positions()
            print(f"  ✓ 총 {len(text_with_positions)}자 추출 완료")
            print(f"  ✓ 텍스트 미리보기: {raw_text[:100]}...")

            # 2단계: 텍스트 전처리 (앵커 매핑)
            print("\n[2/5] 텍스트 전처리 중...")
            preprocessor = TextPreprocessor(text_with_positions, raw_text)
            cleaned_text, anchor_map = preprocessor.preprocess()
            print(f"  ✓ 전처리 완료: {len(cleaned_text)}자")
            print(f"  ✓ 앵커 맵 크기: {len(anchor_map)}개")

            # 3단계: 맞춤법 검사
            print("\n[3/5] 맞춤법 검사 중...")
            print("  (300자씩 분할하여 검사합니다)")
            errors = self.spell_checker.check(cleaned_text, max_length=300)
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
            highlighter.add_highlights(errors)

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

        for error in errors:
            # cleaned_text에서의 위치
            cleaned_start = error.get('position', 0)
            cleaned_end = cleaned_start + error.get('length', len(error['wrong']))

            # 원본 위치로 역추적
            original_indices = preprocessor.get_original_positions(
                cleaned_start, cleaned_end
            )

            if original_indices and len(original_indices) > 0:
                # 첫 번째 문자의 위치 정보 사용
                first_idx = original_indices[0]

                if first_idx < len(text_with_positions):
                    first_char_info = text_with_positions[first_idx]

                    annotation = {
                        'wrong': error['wrong'],
                        'correct': error['correct'],
                        'help': error.get('help', ''),
                        'page': first_char_info['page'],
                        'x': first_char_info.get('x'),
                        'y': first_char_info.get('y')
                    }
                    annotations.append(annotation)
            else:
                # 위치를 찾을 수 없는 경우 기본값 사용
                annotation = {
                    'wrong': error['wrong'],
                    'correct': error['correct'],
                    'help': error.get('help', ''),
                    'page': 1,
                    'x': None,
                    'y': None
                }
                annotations.append(annotation)

        return annotations


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
