import os
import sys
import unittest

# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Minimal dotenv stub so importing bareun_checker does not require external deps.
if 'dotenv' not in sys.modules:
    sys.modules['dotenv'] = type(sys)('dotenv')
setattr(sys.modules['dotenv'], 'load_dotenv', lambda *args, **kwargs: None)

from bareun_checker import IntegratedBareunChecker


class _BoomBareun:
    def check(self, _text: str):
        raise RuntimeError('bareun unavailable')


class _OkFallback:
    def __init__(self, errors):
        self._errors = errors

    def check(self, _text: str):
        return self._errors


class _BoomFallback:
    def check(self, _text: str):
        raise RuntimeError('fallback unavailable')


class TestIntegratedBareunFallback(unittest.TestCase):
    def test_uses_fallback_when_bareun_fails(self):
        checker = IntegratedBareunChecker.__new__(IntegratedBareunChecker)
        checker.bareun = _BoomBareun()
        checker.fallback = _OkFallback([
            {
                'wrong': '되요',
                'correct': '돼요',
                'help': '로컬 폴백',
                'position': 0,
                'length': 2,
            }
        ])

        errors = checker.check('오늘 날씨가 되요')

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['wrong'], '되요')
        self.assertEqual(errors[0]['correct'], '돼요')

    def test_returns_empty_when_both_primary_and_fallback_fail(self):
        checker = IntegratedBareunChecker.__new__(IntegratedBareunChecker)
        checker.bareun = _BoomBareun()
        checker.fallback = _BoomFallback()

        errors = checker.check('테스트')

        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
