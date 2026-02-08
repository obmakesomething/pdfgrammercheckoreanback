import os
import sys
import unittest
from unittest.mock import patch


# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main_processor


class _ExplodeSpellChecker:
    def check_paragraphs(self, paragraphs):
        raise AssertionError("SpellChecker should not be called when payment is required")


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


class TestCharPricingGate(unittest.TestCase):
    def test_processor_returns_payment_required_without_calling_bareun(self):
        # Create processor without running __init__ (avoid external Bareun init).
        processor = main_processor.GrammarCheckProcessor.__new__(main_processor.GrammarCheckProcessor)
        processor.spell_checker = _ExplodeSpellChecker()

        with patch.object(main_processor, 'SimplePDFExtractor', _DummyExtractor), \
             patch.dict(os.environ, {
                 'ENABLE_CHAR_PRICING': 'true',
                 'FREE_CHAR_LIMIT': '50000',
                 'PAID_UNIT_CHARS': '10000',
                 'PAID_UNIT_PRICE_WON': '100',
                 'PAID_CHAR_COUNT_BASIS': 'non_whitespace',
                 'PAID_CHARGE_BASIS': 'overage',
             }, clear=False):
            result = processor.process('input.pdf', 'output.pdf')

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get('success', True))
        self.assertEqual(result.get('code'), 'PAYMENT_REQUIRED')
        self.assertEqual(result.get('char_count'), 50001)
        self.assertEqual(result.get('free_char_limit'), 50000)
        self.assertEqual(result.get('unit_chars'), 10000)
        self.assertEqual(result.get('unit_price_won'), 100)
        self.assertEqual(result.get('required_units'), 1)
        self.assertEqual(result.get('price_won'), 100)


if __name__ == '__main__':
    unittest.main()

