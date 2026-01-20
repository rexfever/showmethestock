#!/usr/bin/env python3
"""스캐너 V2 테스트"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner_v2 import ScannerV2
from config import config
from market_analyzer import market_analyzer

def test_scanner_v2():
    """스캐너 V2 기본 테스트"""
    print("=" * 60)
    print("스캐너 V2 테스트")
    print("=" * 60)
    
    # 스캐너 초기화
    scanner = ScannerV2(config, market_analyzer)
    
    # 테스트 종목
    test_codes = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, NAVER
    
    print(f"\n테스트 종목: {test_codes}")
    print(f"스캔 날짜: 20251027\n")
    
    results = []
    for code in test_codes:
        result = scanner.scan_one(code, "20251027")
        if result:
            results.append(result)
            print(f"✅ {code} ({result.name}): 점수 {result.score}, 전략 {result.strategy}")
        else:
            print(f"❌ {code}: 필터링됨")
    
    print(f"\n총 {len(results)}개 종목 매칭")
    return results

if __name__ == '__main__':
    test_scanner_v2()

