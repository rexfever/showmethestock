#!/usr/bin/env python3
"""
간단한 V2 스캐너 테스트
"""
import os
import sys
sys.path.insert(0, '/Users/rexsmac/workspace/stock-finder/backend')

def test_v2_imports():
    """V2 모듈 import 테스트"""
    print("🔍 V2 모듈 import 테스트")
    
    try:
        from scanner_v2.config_v2 import scanner_v2_config
        print(f"✅ V2 설정 로드: ohlcv_count={scanner_v2_config.ohlcv_count}")
    except Exception as e:
        print(f"❌ V2 설정 로드 실패: {e}")
        return False
    
    try:
        from scanner_v2 import ScannerV2
        print("✅ ScannerV2 클래스 import 성공")
    except Exception as e:
        print(f"❌ ScannerV2 import 실패: {e}")
        return False
    
    try:
        from scanner_v2.core.indicator_calculator import IndicatorCalculator
        print("✅ IndicatorCalculator import 성공")
    except Exception as e:
        print(f"❌ IndicatorCalculator import 실패: {e}")
        return False
    
    try:
        from scanner_v2.core.filter_engine import FilterEngine
        print("✅ FilterEngine import 성공")
    except Exception as e:
        print(f"❌ FilterEngine import 실패: {e}")
        return False
    
    try:
        from scanner_v2.core.scorer import Scorer
        print("✅ Scorer import 성공")
    except Exception as e:
        print(f"❌ Scorer import 실패: {e}")
        return False
    
    return True

def test_v2_scanner_creation():
    """V2 스캐너 생성 테스트"""
    print("\n🔧 V2 스캐너 생성 테스트")
    
    try:
        from scanner_v2 import ScannerV2
        from scanner_v2.config_v2 import scanner_v2_config
        from market_analyzer import market_analyzer
        
        scanner = ScannerV2(scanner_v2_config, market_analyzer)
        print("✅ V2 스캐너 생성 성공")
        return scanner
    except Exception as e:
        print(f"❌ V2 스캐너 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_single_stock_scan():
    """단일 종목 스캔 테스트"""
    print("\n📊 단일 종목 스캔 테스트")
    
    scanner = test_v2_scanner_creation()
    if not scanner:
        return False
    
    try:
        # 삼성전자로 테스트
        result = scanner.scan_one("005930", "20241101")
        if result:
            print(f"✅ 스캔 성공: {result.name} (점수: {result.score})")
            return True
        else:
            print("📭 스캔 결과 없음 (필터링됨)")
            return True
    except Exception as e:
        print(f"❌ 스캔 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 V2 스캐너 간단 테스트 시작")
    
    # 1. Import 테스트
    if not test_v2_imports():
        print("❌ Import 테스트 실패")
        sys.exit(1)
    
    # 2. 스캐너 생성 테스트
    if not test_v2_scanner_creation():
        print("❌ 스캐너 생성 테스트 실패")
        sys.exit(1)
    
    # 3. 단일 종목 스캔 테스트
    if not test_single_stock_scan():
        print("❌ 스캔 테스트 실패")
        sys.exit(1)
    
    print("✅ 모든 테스트 통과!")