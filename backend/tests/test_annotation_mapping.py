import os
import sys
import unittest
import logging

# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from text_preprocessor import TextPreprocessor
from main_processor import GrammarCheckProcessor


class TestAnnotationMapping(unittest.TestCase):
    def _make_text_positions(self, raw_text: str):
        positions = []
        for i, ch in enumerate(raw_text):
            bbox = [float(i), 0.0, float(i + 1), 1.0] if ch not in ('\n',) else None
            positions.append({
                'char': ch,
                'page': 1,
                'index': i,
                'x': float(i),
                'y': 0.0,
                'bbox': bbox,
            })
        return positions

    def test_create_annotations_accepts_raw_positions(self):
        # raw_text -> cleaned_text differs due to '-\n' removal.
        raw_text = 'a-\nb'
        text_positions = self._make_text_positions(raw_text)

        preprocessor = TextPreprocessor(text_positions, raw_text)
        cleaned_text, _ = preprocessor.preprocess()
        self.assertEqual(cleaned_text, 'ab')

        # Create a processor without invoking __init__ (avoids external Bareun init).
        processor = GrammarCheckProcessor.__new__(GrammarCheckProcessor)
        processor.logger = logging.getLogger('test')

        # This position is in RAW coordinates (index 3 points to 'b' in raw_text).
        errors = [{
            'wrong': 'b',
            'correct': 'B',
            'position': 3,
            'length': 1,
            'category': 'SPELL',
        }]

        annotations = processor._create_annotations(errors, preprocessor, text_positions)
        self.assertEqual(len(annotations), 1)
        ann = annotations[0]

        # We expect the annotation to resolve to the bbox of 'b' (raw index 3).
        self.assertEqual(ann['page'], 1)
        self.assertIsNotNone(ann.get('bbox'))

    def test_create_annotations_accepts_cleaned_positions(self):
        raw_text = 'a-\nb'
        text_positions = self._make_text_positions(raw_text)

        preprocessor = TextPreprocessor(text_positions, raw_text)
        cleaned_text, _ = preprocessor.preprocess()
        self.assertEqual(cleaned_text, 'ab')

        processor = GrammarCheckProcessor.__new__(GrammarCheckProcessor)
        processor.logger = logging.getLogger('test')

        # This position is in CLEANED coordinates (index 1 points to 'b' in 'ab').
        errors = [{
            'wrong': 'b',
            'correct': 'B',
            'position': 1,
            'length': 1,
            'category': 'SPELL',
        }]

        annotations = processor._create_annotations(errors, preprocessor, text_positions)
        self.assertEqual(len(annotations), 1)
        ann = annotations[0]
        self.assertEqual(ann['page'], 1)
        self.assertIsNotNone(ann.get('bbox'))


if __name__ == '__main__':
    unittest.main()
