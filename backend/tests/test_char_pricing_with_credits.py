import os
import sys
import tempfile
import unittest
from unittest.mock import patch


# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main_processor


class _NoopSpellChecker:
    def check_paragraphs(self, paragraphs):
        return []


class _DummyExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_paragraphs_with_positions(self):
        raw_text = 'a' * 50001
        paragraphs = [{
            'text': raw_text,
            'start_index': 0,
            'end_index': len(raw_text),
            'page': 1,
        }]
        text_with_positions = []
        return paragraphs, text_with_positions, raw_text


class TestCharPricingWithCredits(unittest.TestCase):
    def test_paid_doc_consumes_credits_and_proceeds(self):
        from credits_storage import CreditsStorage

        # Create processor without running __init__ (avoid external Bareun init).
        processor = main_processor.GrammarCheckProcessor.__new__(main_processor.GrammarCheckProcessor)
        processor.spell_checker = _NoopSpellChecker()

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'credits.sqlite3')
            storage = CreditsStorage(db_path)
            storage.add_credits(user_id='device-1', credits=1, reason='seed')

            with patch.object(main_processor, 'SimplePDFExtractor', _DummyExtractor), \
                 patch.dict(os.environ, {
                     'ENABLE_CHAR_PRICING': 'true',
                     'FREE_CHAR_LIMIT': '50000',
                     'PAID_UNIT_CHARS': '10000',
                     'PAID_UNIT_PRICE_WON': '100',
                     'PAID_CHAR_COUNT_BASIS': 'non_whitespace',
                     'PAID_CHARGE_BASIS': 'overage',
                 }, clear=False):
                result = processor.process(
                    'input.pdf',
                    'output.pdf',
                    user_id='device-1',
                    credits_storage=storage,
                )

            self.assertTrue(result.get('success'))
            self.assertEqual(result.get('errors_found'), 0)
            bal = storage.get_balance('device-1')
            self.assertEqual(bal, 0)

    def test_paid_doc_returns_payment_required_when_insufficient_credits(self):
        from credits_storage import CreditsStorage

        processor = main_processor.GrammarCheckProcessor.__new__(main_processor.GrammarCheckProcessor)
        processor.spell_checker = _NoopSpellChecker()

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'credits.sqlite3')
            storage = CreditsStorage(db_path)
            storage.add_credits(user_id='device-1', credits=0, reason='seed')

            with patch.object(main_processor, 'SimplePDFExtractor', _DummyExtractor), \
                 patch.dict(os.environ, {
                     'ENABLE_CHAR_PRICING': 'true',
                     'FREE_CHAR_LIMIT': '50000',
                     'PAID_UNIT_CHARS': '10000',
                     'PAID_UNIT_PRICE_WON': '100',
                     'PAID_CHAR_COUNT_BASIS': 'non_whitespace',
                     'PAID_CHARGE_BASIS': 'overage',
                 }, clear=False):
                result = processor.process(
                    'input.pdf',
                    'output.pdf',
                    user_id='device-1',
                    credits_storage=storage,
                )

            self.assertFalse(result.get('success', True))
            self.assertEqual(result.get('code'), 'PAYMENT_REQUIRED')
            self.assertEqual(result.get('required_units'), 1)
            self.assertEqual(result.get('credits_balance'), 0)


if __name__ == '__main__':
    unittest.main()

