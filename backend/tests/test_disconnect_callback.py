import os
import sys
import tempfile
import unittest
import base64
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


def _basic_auth_header(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class TestDisconnectCallback(unittest.TestCase):
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

    def test_disconnect_requires_auth_and_purges_credits(self):
        with _temp_cwd() as td:
            os.environ['CREDITS_DB_PATH'] = os.path.join(td, 'credits.sqlite3')
            os.environ['IAP_SKU_CREDITS_JSON'] = '{"CREDIT_5": 5}'
            os.environ['TOSS_DISCONNECT_BASIC_AUTH_USER'] = 'u1'
            os.environ['TOSS_DISCONNECT_BASIC_AUTH_PASS'] = 'p1'

            app_mod = self._import_app()
            client = app_mod.app.test_client()

            # Seed credits
            resp1 = client.post('/api/iap/grant', json={
                'user_id': 'device-1',
                'order_id': 'order-1',
                'sku': 'CREDIT_5',
            })
            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp1.get_json().get('balance'), 5)

            # No auth => 401
            resp2 = client.post('/api/toss/disconnect', json={'user_id': 'device-1'})
            self.assertEqual(resp2.status_code, 401)

            # Wrong auth => 401
            resp3 = client.post(
                '/api/toss/disconnect',
                json={'user_id': 'device-1'},
                headers={'Authorization': _basic_auth_header('u1', 'wrong')},
            )
            self.assertEqual(resp3.status_code, 401)

            # Correct auth => purge
            resp4 = client.post(
                '/api/toss/disconnect',
                json={'user_id': 'device-1'},
                headers={'Authorization': _basic_auth_header('u1', 'p1')},
            )
            self.assertEqual(resp4.status_code, 200)
            data4 = resp4.get_json()
            self.assertEqual(data4.get('status'), 'success')
            self.assertEqual(data4.get('purged_users'), 1)

            # Balance should be gone
            resp5 = client.get('/api/credits/balance?user_id=device-1')
            self.assertEqual(resp5.status_code, 200)
            self.assertEqual(resp5.get_json().get('balance'), 0)

            # Order id should remain idempotent (no double-grant)
            resp6 = client.post('/api/iap/grant', json={
                'user_id': 'device-1',
                'order_id': 'order-1',
                'sku': 'CREDIT_5',
            })
            self.assertEqual(resp6.status_code, 200)
            data6 = resp6.get_json()
            self.assertFalse(data6.get('granted'))
            self.assertEqual(data6.get('balance'), 0)

            # Idempotent disconnect
            resp7 = client.post(
                '/api/toss/disconnect',
                json={'user_id': 'device-1'},
                headers={'Authorization': _basic_auth_header('u1', 'p1')},
            )
            self.assertEqual(resp7.status_code, 200)
            self.assertEqual(resp7.get_json().get('purged_users'), 0)


if __name__ == '__main__':
    unittest.main()

