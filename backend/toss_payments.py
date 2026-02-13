#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
토스페이먼츠 결제 모듈
결제 승인 및 검증 처리
"""
import os
import base64
import requests
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaymentResult:
    """결제 결과 데이터 클래스"""
    success: bool
    payment_key: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[int] = None
    method: Optional[str] = None
    approved_at: Optional[str] = None
    receipt_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TossPayments:
    """토스페이먼츠 결제 처리 클래스"""

    BASE_URL = "https://api.tosspayments.com/v1"

    def __init__(self):
        self.secret_key = os.getenv('TOSS_SECRET_KEY', '')
        if not self.secret_key:
            print("[경고] TOSS_SECRET_KEY 환경변수가 설정되지 않았습니다.")

    def _get_auth_header(self) -> dict:
        """인증 헤더 생성"""
        # 토스페이먼츠는 시크릿키:를 Base64로 인코딩
        credentials = f"{self.secret_key}:"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }

    def confirm_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int
    ) -> PaymentResult:
        """
        결제 승인 요청

        Args:
            payment_key: 토스페이먼츠에서 발급한 결제 키
            order_id: 주문 ID
            amount: 결제 금액

        Returns:
            PaymentResult: 결제 결과
        """
        if not self.secret_key:
            return PaymentResult(
                success=False,
                error_code="NO_SECRET_KEY",
                error_message="토스페이먼츠 시크릿 키가 설정되지 않았습니다."
            )

        url = f"{self.BASE_URL}/payments/confirm"

        payload = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )

            data = response.json()

            if response.status_code == 200:
                return PaymentResult(
                    success=True,
                    payment_key=data.get('paymentKey'),
                    order_id=data.get('orderId'),
                    amount=data.get('totalAmount'),
                    method=data.get('method'),
                    approved_at=data.get('approvedAt'),
                    receipt_url=data.get('receipt', {}).get('url')
                )
            else:
                return PaymentResult(
                    success=False,
                    error_code=data.get('code', 'UNKNOWN_ERROR'),
                    error_message=data.get('message', '결제 승인에 실패했습니다.')
                )

        except requests.exceptions.Timeout:
            return PaymentResult(
                success=False,
                error_code="TIMEOUT",
                error_message="결제 승인 요청 시간이 초과되었습니다."
            )
        except requests.exceptions.RequestException as e:
            return PaymentResult(
                success=False,
                error_code="REQUEST_ERROR",
                error_message=f"결제 승인 요청 중 오류가 발생했습니다: {str(e)}"
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                error_code="UNKNOWN_ERROR",
                error_message=f"알 수 없는 오류가 발생했습니다: {str(e)}"
            )

    def get_payment(self, payment_key: str) -> PaymentResult:
        """
        결제 정보 조회

        Args:
            payment_key: 결제 키

        Returns:
            PaymentResult: 결제 정보
        """
        if not self.secret_key:
            return PaymentResult(
                success=False,
                error_code="NO_SECRET_KEY",
                error_message="토스페이먼츠 시크릿 키가 설정되지 않았습니다."
            )

        url = f"{self.BASE_URL}/payments/{payment_key}"

        try:
            response = requests.get(
                url,
                headers=self._get_auth_header(),
                timeout=30
            )

            data = response.json()

            if response.status_code == 200:
                return PaymentResult(
                    success=True,
                    payment_key=data.get('paymentKey'),
                    order_id=data.get('orderId'),
                    amount=data.get('totalAmount'),
                    method=data.get('method'),
                    approved_at=data.get('approvedAt'),
                    receipt_url=data.get('receipt', {}).get('url')
                )
            else:
                return PaymentResult(
                    success=False,
                    error_code=data.get('code', 'UNKNOWN_ERROR'),
                    error_message=data.get('message', '결제 정보 조회에 실패했습니다.')
                )

        except Exception as e:
            return PaymentResult(
                success=False,
                error_code="REQUEST_ERROR",
                error_message=f"결제 정보 조회 중 오류가 발생했습니다: {str(e)}"
            )

    def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str,
        cancel_amount: Optional[int] = None
    ) -> PaymentResult:
        """
        결제 취소

        Args:
            payment_key: 결제 키
            cancel_reason: 취소 사유
            cancel_amount: 취소 금액 (부분 취소 시)

        Returns:
            PaymentResult: 취소 결과
        """
        if not self.secret_key:
            return PaymentResult(
                success=False,
                error_code="NO_SECRET_KEY",
                error_message="토스페이먼츠 시크릿 키가 설정되지 않았습니다."
            )

        url = f"{self.BASE_URL}/payments/{payment_key}/cancel"

        payload = {"cancelReason": cancel_reason}
        if cancel_amount:
            payload["cancelAmount"] = cancel_amount

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_auth_header(),
                timeout=30
            )

            data = response.json()

            if response.status_code == 200:
                return PaymentResult(
                    success=True,
                    payment_key=data.get('paymentKey'),
                    order_id=data.get('orderId'),
                    amount=data.get('totalAmount')
                )
            else:
                return PaymentResult(
                    success=False,
                    error_code=data.get('code', 'UNKNOWN_ERROR'),
                    error_message=data.get('message', '결제 취소에 실패했습니다.')
                )

        except Exception as e:
            return PaymentResult(
                success=False,
                error_code="REQUEST_ERROR",
                error_message=f"결제 취소 중 오류가 발생했습니다: {str(e)}"
            )
