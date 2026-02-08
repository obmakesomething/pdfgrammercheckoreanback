import os
import sys
import unittest

# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bareun_checker import BareunSpellChecker


class _BoomCorrector:
    def correct_error(self, content: str):
        raise RuntimeError('boom')


class TestBareunCheckerExceptions(unittest.TestCase):
    def test_check_propagates_corrector_exceptions(self):
        checker = BareunSpellChecker.__new__(BareunSpellChecker)
        checker.corrector = _BoomCorrector()

        with self.assertRaises(RuntimeError):
            checker.check('hello')


if __name__ == '__main__':
    unittest.main()
