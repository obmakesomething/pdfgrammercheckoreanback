#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
토스페이먼츠 결제 연동 모듈
https://docs.tosspayments.com/
"""
import os
import base64
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()


class TossPayments:
    """토스페이먼츠 결제 처리 클래스"""

    def __init__(self):
        self.client_key = os.getenv('TOSS_CLIENT_KEY')
        self.secret_key = os.getenv('TOSS_SECRET_KEY')
        self.api_url = 'https://api.tosspayments.com/v1'

        if not self.client_key or not self.secret_key:
            print("경고: 토스페이먼츠 API 키가 설정되지 않았습니다")

    def _get_auth_header(self) -> dict:
        """Basic 인증 헤더 생성"""
        credentials = f"{self.secret_key}:"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }

    def create_payment_request(
        self,
        amount: int,
        order_name: str,
        customer_email: str,
        char_count: int
    ) -> dict:
        """
        결제 요청 정보 생성 (프론트엔드에서 사용)

        Args:
            amount: 결제 금액 (원)
            order_name: 주문명
            customer_email: 고객 이메일
            char_count: 검사할 글자 수

        Returns:
            dict: 결제 요청에 필요한 정보
        """
        order_id = f"PDFGC_{uuid.uuid4().hex[:16]}"

        return {
            'client_key': self.client_key,
            'amount': amount,
            'order_id': order_id,
            'order_name': order_name,
            'customer_email': customer_email,
            'success_url': os.getenv('TOSS_SUCCESS_URL', 'https://pdfgrammercheckorean.site/payment/success'),
            'fail_url': os.getenv('TOSS_FAIL_URL', 'https://pdfgrammercheckorean.site/payment/fail'),
            'metadata': {
                'char_count': char_count,
                'email': customer_email
            }
        }

    def confirm_payment(self, payment_key: str, order_id: str, amount: int) -> dict:
        """
        결제 승인 요청 (서버에서 호출)

        Args:
            payment_key: 토스페이먼츠에서 발급한 결제 키
            order_id: 주문 ID
            amount: 결제 금액

        Returns:
            dict: 결제 승인 결과
        """
        if not self.secret_key:
            return {
                'success': False,
                'error': '토스페이먼츠 API 키가 설정되지 않았습니다'
            }

        try:
            response = requests.post(
                f'{self.api_url}/payments/confirm',
                headers=self._get_auth_header(),
                json={
                    'paymentKey': payment_key,
                    'orderId': order_id,
                    'amount': amount
                }
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'payment_key': data.get('paymentKey'),
                    'order_id': data.get('orderId'),
                    'status': data.get('status'),
                    'approved_at': data.get('approvedAt'),
                    'receipt_url': data.get('receipt', {}).get('url'),
                    'data': data
                }
            else:
                error_data = response.json()
                return {
                    'success': False,
                    'error_code': error_data.get('code'),
                    'error_message': error_data.get('message')
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_payment(self, payment_key: str, cancel_reason: str) -> dict:
        """
        결제 취소

        Args:
            payment_key: 결제 키
            cancel_reason: 취소 사유

        Returns:
            dict: 취소 결과
        """
        try:
            response = requests.post(
                f'{self.api_url}/payments/{payment_key}/cancel',
                headers=self._get_auth_header(),
                json={'cancelReason': cancel_reason}
            )

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': response.json()}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_payment(self, payment_key: str) -> dict:
        """
        결제 조회

        Args:
            payment_key: 결제 키

        Returns:
            dict: 결제 정보
        """
        try:
            response = requests.get(
                f'{self.api_url}/payments/{payment_key}',
                headers=self._get_auth_header()
            )

            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': response.json()}

        except Exception as e:
            return {'success': False, 'error': str(e)}


# 싱글톤 인스턴스
toss_payments = TossPayments()


if __name__ == "__main__":
    from pricing import pricing_calculator

    # 테스트
    print("=" * 60)
    print("토스페이먼츠 결제 테스트")
    print("=" * 60)

    toss = TossPayments()

    # 결제 요청 정보 생성 테스트
    test_chars = 80000
    price_info = pricing_calculator.calculate_price(test_chars)

    if not price_info['is_free']:
        payment_request = toss.create_payment_request(
            amount=price_info['price'],
            order_name=f'PDF 맞춤법 검사 ({test_chars:,}자)',
            customer_email='test@example.com',
            char_count=test_chars
        )

        print(f"\n결제 요청 정보:")
        print(f"  - 주문 ID: {payment_request['order_id']}")
        print(f"  - 금액: {payment_request['amount']:,}원")
        print(f"  - 주문명: {payment_request['order_name']}")
    else:
        print(f"\n{test_chars:,}자는 무료 범위입니다.")
