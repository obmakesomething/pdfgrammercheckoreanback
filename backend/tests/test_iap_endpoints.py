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


class TestIapEndpoints(unittest.TestCase):
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

    def test_balance_and_grant_endpoints(self):
        with _temp_cwd() as td:
            os.environ['CREDITS_DB_PATH'] = os.path.join(td, 'credits.sqlite3')
            os.environ['IAP_SKU_CREDITS_JSON'] = '{"CREDIT_5": 5}'

            app_mod = self._import_app()
            client = app_mod.app.test_client()

            resp0 = client.get('/api/credits/balance?user_id=device-1')
            self.assertEqual(resp0.status_code, 200)
            data0 = resp0.get_json()
            self.assertEqual(data0.get('status'), 'success')
            self.assertEqual(data0.get('balance'), 0)

            resp1 = client.post('/api/iap/grant', json={
                'user_id': 'device-1',
                'order_id': 'order-1',
                'sku': 'CREDIT_5',
            })
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.get_json()
            self.assertEqual(data1.get('status'), 'success')
            self.assertTrue(data1.get('granted'))
            self.assertEqual(data1.get('credits_added'), 5)
            self.assertEqual(data1.get('balance'), 5)

            # idempotent on same order_id
            resp2 = client.post('/api/iap/grant', json={
                'user_id': 'device-1',
                'order_id': 'order-1',
                'sku': 'CREDIT_5',
            })
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.get_json()
            self.assertEqual(data2.get('status'), 'success')
            self.assertFalse(data2.get('granted'))
            self.assertEqual(data2.get('credits_added'), 0)
            self.assertEqual(data2.get('balance'), 5)

            resp3 = client.get('/api/credits/balance?user_id=device-1')
            self.assertEqual(resp3.status_code, 200)
            data3 = resp3.get_json()
            self.assertEqual(data3.get('balance'), 5)


if __name__ == '__main__':
    unittest.main()

