import io
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def _temp_cwd():
    prev = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            yield td
        finally:
            os.chdir(prev)


class TestCheckPdfEndpoint(unittest.TestCase):
    def _import_app(self):
        # Allow importing modules from backend/
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        # Stub bareunpy so importing app doesn't create real network clients.
        # (app.py initializes BareunSpellChecker at import time.)
        class _DummyCorrector:
            def __init__(self, apikey=None, host=None, port=None):
                self.apikey = apikey
                self.host = host
                self.port = port

        sys.modules['bareunpy'] = type(sys)('bareunpy')
        setattr(sys.modules['bareunpy'], 'Corrector', _DummyCorrector)

        # Ensure required env var exists for BareunSpellChecker init.
        os.environ.setdefault('BAREUN_API_KEY', 'test-key')

        # Import backend/app.py as module "app"
        import importlib
        if 'app' in sys.modules:
            del sys.modules['app']
        return importlib.import_module('app')

    def test_check_pdf_allows_missing_email(self):
        with _temp_cwd() as td:
            app_mod = self._import_app()

            fixed_uuid = app_mod.uuid.UUID('00000000-0000-0000-0000-000000000000')

            def _fake_process(input_path, output_path):
                return {
                    'success': True,
                    'errors_found': 0,
                    'output_pdf': None,
                    'message': 'ok',
                }

            client = app_mod.app.test_client()
            pdf_bytes = b'%PDF-1.4\n%EOF\n'

            with patch.object(app_mod.uuid, 'uuid4', return_value=fixed_uuid), \
                 patch.object(app_mod.tempfile, 'gettempdir', return_value=td), \
                 patch.object(app_mod.processor, 'process', side_effect=_fake_process):
                resp = client.post(
                    '/api/check-pdf',
                    data={
                        'pdf': (io.BytesIO(pdf_bytes), 'test.pdf'),
                        # intentionally no email
                    },
                    content_type='multipart/form-data',
                )

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data, pdf_bytes)

    def test_check_pdf_does_not_write_user_email_csv_by_default(self):
        with _temp_cwd() as td:
            app_mod = self._import_app()

            fixed_uuid = app_mod.uuid.UUID('00000000-0000-0000-0000-000000000000')

            def _fake_process(input_path, output_path):
                # Create a dummy output so the handler can return it.
                with open(output_path, 'wb') as f:
                    f.write(b'%PDF-1.4\n%FAKE\n')
                return {
                    'success': True,
                    'errors_found': 1,
                    'output_pdf': output_path,
                    'message': 'ok',
                }

            client = app_mod.app.test_client()

            with patch.object(app_mod.uuid, 'uuid4', return_value=fixed_uuid), \
                 patch.object(app_mod.tempfile, 'gettempdir', return_value=td), \
                 patch.object(app_mod.processor, 'process', side_effect=_fake_process):
                resp = client.post(
                    '/api/check-pdf',
                    data={
                        'pdf': (io.BytesIO(b'%PDF-1.4\n%EOF\n'), 'test.pdf'),
                        'email': 'test@example.com',
                    },
                    content_type='multipart/form-data',
                )

            self.assertEqual(resp.status_code, 200)
            self.assertFalse(os.path.exists(os.path.join(td, 'user_emails.csv')))

    def test_check_pdf_cleans_up_temp_files_on_success(self):
        with _temp_cwd() as td:
            app_mod = self._import_app()

            fixed_uuid = app_mod.uuid.UUID('00000000-0000-0000-0000-000000000000')

            def _fake_process(input_path, output_path):
                return {
                    'success': True,
                    'errors_found': 0,
                    'output_pdf': None,
                    'message': 'ok',
                }

            client = app_mod.app.test_client()
            pdf_bytes = b'%PDF-1.4\n%EOF\n'

            with patch.object(app_mod.uuid, 'uuid4', return_value=fixed_uuid), \
                 patch.object(app_mod.tempfile, 'gettempdir', return_value=td), \
                 patch.object(app_mod.processor, 'process', side_effect=_fake_process):
                resp = client.post(
                    '/api/check-pdf',
                    data={
                        'pdf': (io.BytesIO(pdf_bytes), 'test.pdf'),
                    },
                    content_type='multipart/form-data',
                )

            self.assertEqual(resp.status_code, 200)

            file_id = str(fixed_uuid)
            input_pdf_path = os.path.join(td, f"{file_id}_input.pdf")
            output_pdf_path = os.path.join(td, f"{file_id}_output.pdf")

            self.assertFalse(os.path.exists(input_pdf_path))
            self.assertFalse(os.path.exists(output_pdf_path))


if __name__ == '__main__':
    unittest.main()

