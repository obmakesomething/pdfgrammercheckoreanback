#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
과금 시스템 모듈
글자 수 기반 요금 계산
"""
import math

# 과금 설정
FREE_CHAR_LIMIT = 50000  # 무료 글자 수 (5만자)
PRICE_PER_10K_CHARS = 100  # 만자당 100원


class PricingCalculator:
    """글자 수 기반 요금 계산기"""

    def __init__(self):
        self.free_limit = FREE_CHAR_LIMIT
        self.price_per_unit = PRICE_PER_10K_CHARS
        self.unit_size = 10000  # 만자 단위

    def calculate_price(self, char_count: int) -> dict:
        """
        글자 수에 따른 요금 계산

        Args:
            char_count: 총 글자 수

        Returns:
            dict: {
                'char_count': int,
                'free_chars': int,
                'billable_chars': int,
                'price': int,
                'is_free': bool,
                'breakdown': str
            }
        """
        if char_count <= self.free_limit:
            return {
                'char_count': char_count,
                'free_chars': char_count,
                'billable_chars': 0,
                'price': 0,
                'is_free': True,
                'breakdown': f'{char_count:,}자 (무료 범위 내)'
            }

        billable_chars = char_count - self.free_limit
        # 만자 단위로 올림 계산 (부분 단위도 과금)
        # 예: 50,001자 → 1원, 59,999자 → 100원, 60,000자 → 100원, 60,001자 → 200원
        units = math.ceil(billable_chars / self.unit_size)
        price = units * self.price_per_unit

        return {
            'char_count': char_count,
            'free_chars': self.free_limit,
            'billable_chars': billable_chars,
            'units': units,
            'price': price,
            'is_free': False,
            'breakdown': f'{char_count:,}자 중 {self.free_limit:,}자 무료, {billable_chars:,}자 과금 ({units}만자 × {self.price_per_unit}원 = {price:,}원)'
        }

    def needs_payment(self, char_count: int) -> bool:
        """결제가 필요한지 확인"""
        return char_count > self.free_limit

    def get_price_info(self) -> dict:
        """요금 정보 반환"""
        return {
            'free_limit': self.free_limit,
            'price_per_unit': self.price_per_unit,
            'unit_size': self.unit_size,
            'description': f'{self.free_limit:,}자까지 무료, 이후 {self.unit_size:,}자당 {self.price_per_unit}원'
        }


# 싱글톤 인스턴스
pricing_calculator = PricingCalculator()


if __name__ == "__main__":
    # 테스트
    calc = PricingCalculator()

    test_cases = [10000, 50000, 60000, 100000, 150000]

    print("=" * 60)
    print("과금 계산 테스트")
    print("=" * 60)
    print(f"무료 한도: {calc.free_limit:,}자")
    print(f"과금 단위: {calc.unit_size:,}자당 {calc.price_per_unit}원")
    print("=" * 60)

    for chars in test_cases:
        result = calc.calculate_price(chars)
        print(f"\n{chars:,}자:")
        print(f"  - 무료: {'예' if result['is_free'] else '아니오'}")
        print(f"  - 요금: {result['price']:,}원")
        print(f"  - 상세: {result['breakdown']}")
