#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 프로세서
PDF 파일을 받아 전체 맞춤법 검사 파이프라인 실행
"""
import os
import tempfile
import math
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

    def _get_char_pricing_config(self):
        """Character-based monetization policy (Apps in Toss).

        Defaults:
        - <= 50,000 chars: free (ad-based)
        - > 50,000 chars: charge 100 KRW per 10,000 chars (overage)

        All knobs are env-configurable to allow quick iteration without code changes.
        """
        def _env_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return str(raw).strip().lower() in ('1', 'true', 'yes', 'y', 'on')

        def _env_int(name: str, default: int, min_value: int) -> int:
            raw = os.getenv(name)
            if raw is None or str(raw).strip() == '':
                return default
            try:
                value = int(str(raw).strip())
                return max(min_value, value)
            except Exception:
                return default

        enabled = _env_bool('ENABLE_CHAR_PRICING', True)
        free_char_limit = _env_int('FREE_CHAR_LIMIT', 50000, 0)
        unit_chars = _env_int('PAID_UNIT_CHARS', 10000, 1)
        unit_price_won = _env_int('PAID_UNIT_PRICE_WON', 100, 0)

        # What to count: total characters vs non-whitespace (default).
        count_basis = (os.getenv('PAID_CHAR_COUNT_BASIS') or 'non_whitespace').strip().lower()
        if count_basis not in ('total', 'non_whitespace'):
            count_basis = 'non_whitespace'

        # What to charge: only overage beyond free limit vs total size when paid.
        charge_basis = (os.getenv('PAID_CHARGE_BASIS') or 'overage').strip().lower()
        if charge_basis not in ('overage', 'total'):
            charge_basis = 'overage'

        return {
            'enabled': enabled,
            'free_char_limit': free_char_limit,
            'unit_chars': unit_chars,
            'unit_price_won': unit_price_won,
            'count_basis': count_basis,
            'charge_basis': charge_basis,
        }

    def _count_chars_for_pricing(self, raw_text: str, count_basis: str) -> int:
        if not raw_text:
            return 0
        if count_basis == 'total':
            return len(raw_text)
        # default: non-whitespace
        return sum(1 for ch in raw_text if not ch.isspace())

    def _quote_char_pricing(self, char_count: int, cfg: dict) -> dict:
        """Return a quote dict; caller decides whether to enforce payment."""
        free_char_limit = int(cfg.get('free_char_limit', 0) or 0)
        unit_chars = int(cfg.get('unit_chars', 10000) or 10000)
        unit_price_won = int(cfg.get('unit_price_won', 0) or 0)
        charge_basis = str(cfg.get('charge_basis') or 'overage')

        charge_chars = 0
        if charge_basis == 'total':
            charge_chars = char_count
        else:
            charge_chars = max(0, char_count - free_char_limit)

        required_units = 0
        if charge_chars > 0:
            required_units = int(math.ceil(charge_chars / float(unit_chars)))

        return {
            'char_count': char_count,
            'free_char_limit': free_char_limit,
            'unit_chars': unit_chars,
            'unit_price_won': unit_price_won,
            'required_units': required_units,
            'price_won': required_units * unit_price_won,
            'count_basis': cfg.get('count_basis'),
            'charge_basis': charge_basis,
        }

    def process(
        self,
        input_pdf_path: str,
        output_pdf_path: str = None,
        *,
        user_id: str = None,
        credits_storage=None,
    ) -> dict:
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
            reserved = None
            credits_to_consume = 0

            # 1단계: PDF 텍스트 추출 (파라그래프 단위)
            print("\n[1/5] PDF 텍스트 추출 중 (파라그래프 단위)...")
            extractor = SimplePDFExtractor(input_pdf_path)
            paragraphs, text_with_positions, raw_text = extractor.extract_paragraphs_with_positions()
            print(f"  ✓ 총 {len(text_with_positions)}자 추출 완료")
            print(f"  ✓ 파라그래프 개수: {len(paragraphs)}개")
            # Avoid logging raw user content (PII/privacy).
            print(f"  ✓ 텍스트 길이: {len(raw_text)}자")

            # Character-based monetization gate (Ads vs paywall).
            pricing_cfg = self._get_char_pricing_config()
            char_count = self._count_chars_for_pricing(raw_text or '', pricing_cfg.get('count_basis'))
            quote = self._quote_char_pricing(char_count, pricing_cfg)

            pricing_enabled = bool(pricing_cfg.get('enabled'))
            free_char_limit = int(quote.get('free_char_limit', 0) or 0)
            credits_to_consume = int(quote.get('required_units', 0) or 0)
            is_paid_doc = pricing_enabled and char_count > free_char_limit and credits_to_consume > 0

            if is_paid_doc:
                balance = 0
                if user_id and credits_storage:
                    try:
                        balance = int(credits_storage.get_balance(user_id))
                    except Exception:
                        balance = 0

                if balance < credits_to_consume:
                    msg = (
                        f"무료 한도({free_char_limit}자)를 초과했습니다. "
                        f"초과분 10,000자당 {quote.get('unit_price_won')}원 결제가 필요합니다."
                    )
                    print(f"  ⚠ {msg} (chars={char_count})")
                    return {
                        'success': False,
                        'errors_found': 0,
                        'output_pdf': None,
                        'message': msg,
                        'code': 'PAYMENT_REQUIRED',
                        'credits_balance': balance,
                        **quote,
                    }

                try:
                    reserved = credits_storage.consume_credits(user_id, credits_to_consume)
                except Exception:
                    reserved = None

                if not reserved or not reserved.get('consumed'):
                    bal2 = balance
                    if user_id and credits_storage:
                        try:
                            bal2 = int(credits_storage.get_balance(user_id))
                        except Exception:
                            bal2 = balance
                    msg = (
                        f"무료 한도({free_char_limit}자)를 초과했습니다. "
                        f"초과분 10,000자당 {quote.get('unit_price_won')}원 결제가 필요합니다."
                    )
                    print(f"  ⚠ {msg} (chars={char_count})")
                    return {
                        'success': False,
                        'errors_found': 0,
                        'output_pdf': None,
                        'message': msg,
                        'code': 'PAYMENT_REQUIRED',
                        'credits_balance': bal2,
                        **quote,
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
                    'message': '맞춤법 오류가 발견되지 않았습니다.',
                    'char_count': char_count,
                    'credits_used': credits_to_consume if is_paid_doc else 0,
                    'credits_balance': reserved.get('balance') if reserved else None,
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
                'message': f'{len(annotations)}개의 맞춤법 오류를 발견했습니다.',
                'char_count': char_count,
                'credits_used': credits_to_consume if is_paid_doc else 0,
                'credits_balance': reserved.get('balance') if reserved else None,
            }

        except Exception as e:
            # Refund reserved credits on failure.
            try:
                if reserved and reserved.get('consumed') and user_id and credits_storage and credits_to_consume > 0:
                    credits_storage.add_credits(user_id=user_id, credits=credits_to_consume, reason='refund')
            except Exception:
                pass
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

        cleaned_text = getattr(preprocessor, 'cleaned_text', '') or ''
        raw_text = getattr(preprocessor, 'raw_text', '') or ''

        for error in errors:
            wrong = (error.get('wrong') or '')
            pos = int(error.get('position', 0) or 0)
            length = int(error.get('length', len(wrong)) or len(wrong))

            # Determine what coordinate system `pos` is in.
            # - If we spell-check preprocessed text, pos refers to `cleaned_text`.
            # - If we spell-check extracted raw text/paragraphs, pos refers to `raw_text`.
            mode = None
            if wrong and pos >= 0:
                end = pos + len(wrong)
                if end <= len(cleaned_text) and cleaned_text[pos:end] == wrong:
                    mode = 'cleaned'
                elif end <= len(raw_text) and raw_text[pos:end] == wrong:
                    mode = 'raw'

            cleaned_start = pos
            cleaned_end = pos + max(0, length)

            # Map to raw indices (text_with_positions indices).
            original_indices = []
            if mode == 'raw':
                original_indices = list(
                    range(
                        cleaned_start,
                        min(cleaned_end, len(text_with_positions))
                    )
                )
            else:
                # Default: treat as cleaned positions.
                original_indices = preprocessor.get_original_positions(
                    cleaned_start, cleaned_end
                )
                # If mapping fails, fall back to treating the position as raw.
                if not original_indices:
                    original_indices = list(
                        range(
                            cleaned_start,
                            min(cleaned_end, len(text_with_positions))
                        )
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
