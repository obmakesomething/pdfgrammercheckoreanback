import os
import sys
import tempfile
import unittest
from contextlib import contextmanager


@contextmanager
def _temp_cwd():
    prev = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            yield td
        finally:
            os.chdir(prev)


class TestLegalPages(unittest.TestCase):
    def _import_app(self):
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        class _DummyCorrector:
            def __init__(self, apikey=None, host=None, port=None):
                self.apikey = apikey
                self.host = host
                self.port = port

        sys.modules['bareunpy'] = type(sys)('bareunpy')
        setattr(sys.modules['bareunpy'], 'Corrector', _DummyCorrector)

        os.environ.setdefault('BAREUN_API_KEY', 'test-key')

        import importlib
        if 'app' in sys.modules:
            del sys.modules['app']
        return importlib.import_module('app')

    def test_legal_terms_and_privacy_pages(self):
        with _temp_cwd():
            app_mod = self._import_app()
            client = app_mod.app.test_client()

            r1 = client.get('/legal/terms')
            self.assertEqual(r1.status_code, 200)
            self.assertIn('text/html', r1.content_type)
            self.assertIn('서비스 이용약관', r1.get_data(as_text=True))

            r2 = client.get('/legal/privacy')
            self.assertEqual(r2.status_code, 200)
            self.assertIn('text/html', r2.content_type)
            self.assertIn('개인정보 처리방침', r2.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
