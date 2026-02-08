import os
import sys
import unittest
from unittest.mock import patch

# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pdf_highlighter_fitz


class _DummyPage:
    def add_highlight_annot(self, rect):
        raise ValueError('bad quads entry')


class _DummyDoc:
    def __init__(self):
        self._pages = [_DummyPage()]
        self.saved_path = None
        self.closed = False

    def __len__(self):
        return len(self._pages)

    def __getitem__(self, idx):
        return self._pages[idx]

    def save(self, path):
        self.saved_path = path

    def close(self):
        self.closed = True


class TestPDFHighlighterFitzRobust(unittest.TestCase):
    def test_add_highlights_does_not_raise_on_bad_quads(self):
        dummy_doc = _DummyDoc()

        errors = [{
            'wrong': '되요',
            'correct': '돼요',
            'help': '...',
            'category': 'SPELL',
            'page': 1,
            'bbox': [0, 0, 1, 1],
        }]

        highlighter = pdf_highlighter_fitz.PDFHighlighterFitz('in.pdf', 'out.pdf')

        with patch.object(pdf_highlighter_fitz.fitz, 'open', return_value=dummy_doc):
            # Force a non-None rect so we hit add_highlight_annot.
            with patch.object(pdf_highlighter_fitz.PDFHighlighterFitz, '_rect_from_annotation', return_value=object()):
                highlighter.add_highlights(errors, text_positions=None)

        self.assertEqual(dummy_doc.saved_path, 'out.pdf')
        self.assertTrue(dummy_doc.closed)


if __name__ == '__main__':
    unittest.main()
