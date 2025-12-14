#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
결제 데이터 저장 모듈
결제 정보를 CSV 파일에 저장하고 조회
"""
import os
import csv
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict


@dataclass
class PaymentRecord:
    """결제 기록 데이터 클래스"""
    id: str
    order_id: str
    payment_key: str
    amount: int
    email: str
    product_name: str
    method: str
    status: str  # pending, completed, cancelled, failed
    created_at: str
    approved_at: Optional[str] = None
    receipt_url: Optional[str] = None
    cancel_reason: Optional[str] = None
    cancelled_at: Optional[str] = None


class PaymentStorage:
    """결제 정보 저장소 클래스"""

    def __init__(self, file_path: str = "payments.csv"):
        self.file_path = file_path
        self.fieldnames = [
            'id', 'order_id', 'payment_key', 'amount', 'email',
            'product_name', 'method', 'status', 'created_at',
            'approved_at', 'receipt_url', 'cancel_reason', 'cancelled_at'
        ]
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """CSV 파일이 없으면 헤더와 함께 생성"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def generate_order_id(self) -> str:
        """고유한 주문 ID 생성"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"ORDER_{timestamp}_{unique_id}"

    def create_payment(
        self,
        order_id: str,
        amount: int,
        email: str,
        product_name: str
    ) -> PaymentRecord:
        """
        새 결제 기록 생성 (대기 상태)

        Args:
            order_id: 주문 ID
            amount: 결제 금액
            email: 구매자 이메일
            product_name: 상품명

        Returns:
            PaymentRecord: 생성된 결제 기록
        """
        record = PaymentRecord(
            id=str(uuid.uuid4()),
            order_id=order_id,
            payment_key="",
            amount=amount,
            email=email,
            product_name=product_name,
            method="",
            status="pending",
            created_at=datetime.now().isoformat()
        )

        self._append_record(record)
        return record

    def complete_payment(
        self,
        order_id: str,
        payment_key: str,
        method: str,
        approved_at: str,
        receipt_url: Optional[str] = None
    ) -> bool:
        """
        결제 완료 처리

        Args:
            order_id: 주문 ID
            payment_key: 결제 키
            method: 결제 수단
            approved_at: 승인 시각
            receipt_url: 영수증 URL

        Returns:
            bool: 성공 여부
        """
        records = self._read_all_records()
        updated = False

        for record in records:
            if record['order_id'] == order_id:
                record['payment_key'] = payment_key
                record['method'] = method
                record['status'] = 'completed'
                record['approved_at'] = approved_at
                record['receipt_url'] = receipt_url or ''
                updated = True
                break

        if updated:
            self._write_all_records(records)

        return updated

    def cancel_payment(
        self,
        order_id: str,
        cancel_reason: str
    ) -> bool:
        """
        결제 취소 처리

        Args:
            order_id: 주문 ID
            cancel_reason: 취소 사유

        Returns:
            bool: 성공 여부
        """
        records = self._read_all_records()
        updated = False

        for record in records:
            if record['order_id'] == order_id:
                record['status'] = 'cancelled'
                record['cancel_reason'] = cancel_reason
                record['cancelled_at'] = datetime.now().isoformat()
                updated = True
                break

        if updated:
            self._write_all_records(records)

        return updated

    def fail_payment(self, order_id: str, error_message: str) -> bool:
        """
        결제 실패 처리

        Args:
            order_id: 주문 ID
            error_message: 오류 메시지

        Returns:
            bool: 성공 여부
        """
        records = self._read_all_records()
        updated = False

        for record in records:
            if record['order_id'] == order_id:
                record['status'] = 'failed'
                record['cancel_reason'] = error_message
                updated = True
                break

        if updated:
            self._write_all_records(records)

        return updated

    def get_payment_by_order_id(self, order_id: str) -> Optional[Dict]:
        """주문 ID로 결제 정보 조회"""
        records = self._read_all_records()
        for record in records:
            if record['order_id'] == order_id:
                return record
        return None

    def get_payment_by_email(self, email: str) -> List[Dict]:
        """이메일로 결제 기록 조회"""
        records = self._read_all_records()
        return [r for r in records if r['email'] == email]

    def get_completed_payments(self) -> List[Dict]:
        """완료된 결제 목록 조회"""
        records = self._read_all_records()
        return [r for r in records if r['status'] == 'completed']

    def has_valid_subscription(self, email: str) -> bool:
        """
        유효한 구독/결제가 있는지 확인

        Args:
            email: 확인할 이메일

        Returns:
            bool: 유효한 결제가 있으면 True
        """
        payments = self.get_payment_by_email(email)
        # 완료된 결제가 하나라도 있으면 True
        return any(p['status'] == 'completed' for p in payments)

    def _append_record(self, record: PaymentRecord):
        """새 기록 추가"""
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(asdict(record))

    def _read_all_records(self) -> List[Dict]:
        """모든 기록 읽기"""
        records = []
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
        return records

    def _write_all_records(self, records: List[Dict]):
        """모든 기록 다시 쓰기"""
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(records)
