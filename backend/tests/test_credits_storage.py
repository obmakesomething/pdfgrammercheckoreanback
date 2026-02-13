import os
import sys
import tempfile
import unittest


# Allow importing modules from backend/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCreditsStorage(unittest.TestCase):
    def test_grant_iap_order_is_idempotent(self):
        from credits_storage import CreditsStorage

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'credits.sqlite3')
            storage = CreditsStorage(db_path)

            r1 = storage.grant_iap_order(
                user_id='device-1',
                order_id='order-1',
                sku='CREDIT_5',
                credits=5,
            )
            self.assertTrue(r1['granted'])
            self.assertEqual(r1['credits_added'], 5)
            self.assertEqual(r1['balance'], 5)

            r2 = storage.grant_iap_order(
                user_id='device-1',
                order_id='order-1',
                sku='CREDIT_5',
                credits=5,
            )
            self.assertFalse(r2['granted'])
            self.assertEqual(r2['credits_added'], 0)
            self.assertEqual(r2['balance'], 5)

    def test_consume_credits_is_atomic_and_can_fail(self):
        from credits_storage import CreditsStorage

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, 'credits.sqlite3')
            storage = CreditsStorage(db_path)

            storage.add_credits(user_id='device-1', credits=2, reason='seed')

            ok1 = storage.consume_credits(user_id='device-1', credits=1)
            self.assertTrue(ok1['consumed'])
            self.assertEqual(ok1['balance'], 1)

            ok2 = storage.consume_credits(user_id='device-1', credits=2)
            self.assertFalse(ok2['consumed'])
            self.assertEqual(ok2['balance'], 1)


if __name__ == '__main__':
    unittest.main()

