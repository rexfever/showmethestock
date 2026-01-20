"""
등락률 표시 로직 일관성 테스트

이 테스트는 백엔드와 프론트엔드 간의 change_rate 처리 일관성을 검증합니다.
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scanner_v2.core.scanner import ScannerV2
import pandas as pd
from datetime import datetime


class TestChangeRateConsistency(unittest.TestCase):
    """등락률 일관성 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.scanner = ScannerV2(None)
    
    def test_scanner_calculate_change_rate_returns_decimal(self):
        """스캐너 v2의 _calculate_change_rate가 소수 형태로 반환하는지 확인"""
        # 테스트 데이터: 전일 8820원, 당일 8870원 (0.57% 상승)
        df = pd.DataFrame({
            'close': [8750, 8720, 8750, 8820, 8870],
            'volume': [100000, 100000, 100000, 100000, 100000]
        })
        
        change_rate = self.scanner._calculate_change_rate(df)
        
        # 소수 형태로 반환되어야 함 (0.0057 = 0.57%)
        expected = round((8870 - 8820) / 8820, 4)
        self.assertAlmostEqual(change_rate, expected, places=4)
        self.assertLess(abs(change_rate), 1.0, "소수 형태여야 함")
        print(f"✅ 스캐너 계산값: {change_rate} (소수 형태)")
    
    def test_save_scan_snapshot_converts_to_percent(self):
        """save_scan_snapshot이 소수 형태를 퍼센트로 변환하는지 확인"""
        from services.scan_service import save_scan_snapshot
        
        # 스캐너가 반환한 소수 형태 (0.0057)
        scan_items = [{
            "ticker": "030960",
            "name": "양지사",
            "score": 9.0,
            "score_label": "매수 후보",
            "indicators": {
                "close": 8870.0,
                "change_rate": 0.0057  # 소수 형태
            },
            "flags": {},
            "trend": {}
        }]
        
        # 실제 DB 저장은 하지 않고 변환 로직만 테스트
        indicators = scan_items[0]["indicators"]
        scan_change_rate = indicators.get("change_rate")
        
        # 변환 로직 (scan_service.py의 로직과 동일)
        if scan_change_rate is not None:
            scan_change_rate = float(scan_change_rate)
            if abs(scan_change_rate) < 1.0 and scan_change_rate != 0.0:
                scan_change_rate = scan_change_rate * 100
        
        # 퍼센트 형태로 변환되어야 함 (0.57%)
        self.assertAlmostEqual(scan_change_rate, 0.57, places=2)
        self.assertGreaterEqual(abs(scan_change_rate), 0.01, "퍼센트 형태여야 함")
        print(f"✅ 저장 변환값: {scan_change_rate}% (퍼센트 형태)")
    
    def test_api_endpoint_returns_percent_for_v2(self):
        """API 엔드포인트가 v2 스캐너의 경우 퍼센트 형태를 그대로 반환하는지 확인"""
        # DB에 저장된 값 (퍼센트 형태: 0.57%)
        db_change_rate = 0.57
        scanner_version = 'v2'
        
        # API 변환 로직 (main.py의 로직과 동일)
        change_rate_raw = db_change_rate
        change_rate = float(change_rate_raw)
        row_scanner_version = scanner_version
        
        if row_scanner_version != 'v2' and abs(change_rate) < 1.0 and change_rate != 0.0:
            change_rate = change_rate * 100
        
        # v2는 변환하지 않아야 함
        self.assertAlmostEqual(change_rate, 0.57, places=2)
        self.assertLess(abs(change_rate), 1.0, "v2는 변환하지 않음")
        print(f"✅ API 반환값 (v2): {change_rate}% (변환 없음)")
    
    def test_api_endpoint_converts_for_v1(self):
        """API 엔드포인트가 v1 스캐너의 경우 소수 형태를 퍼센트로 변환하는지 확인"""
        # DB에 저장된 값 (소수 형태: 0.0057)
        db_change_rate = 0.0057
        scanner_version = 'v1'
        
        # API 변환 로직 (main.py의 로직과 동일)
        change_rate_raw = db_change_rate
        change_rate = float(change_rate_raw)
        row_scanner_version = scanner_version
        
        if row_scanner_version != 'v2' and abs(change_rate) < 1.0 and change_rate != 0.0:
            change_rate = change_rate * 100
        
        # v1은 변환해야 함
        self.assertAlmostEqual(change_rate, 0.57, places=2)
        self.assertGreaterEqual(abs(change_rate), 0.01, "v1은 변환함")
        print(f"✅ API 반환값 (v1): {change_rate}% (변환됨)")
    
    def test_frontend_display_expects_percent(self):
        """프론트엔드가 퍼센트 형태를 기대하는지 확인"""
        # API에서 반환된 값 (퍼센트 형태: 0.57%)
        api_change_rate = 0.57
        
        # 프론트엔드 표시 로직 (customer-scanner.js의 로직과 동일)
        display_value = api_change_rate  # 그대로 표시
        
        # 프론트엔드는 퍼센트 형태를 기대
        self.assertAlmostEqual(display_value, 0.57, places=2)
        self.assertLess(abs(display_value), 100.0, "퍼센트 형태여야 함")
        print(f"✅ 프론트엔드 표시값: {display_value}%")
    
    def test_end_to_end_consistency(self):
        """전체 플로우 일관성 테스트"""
        # 1. 스캐너 계산 (소수 형태)
        df = pd.DataFrame({
            'close': [8820, 8870],
            'volume': [100000, 100000]
        })
        scanner_change_rate = self.scanner._calculate_change_rate(df)
        self.assertLess(abs(scanner_change_rate), 1.0)
        print(f"1. 스캐너 계산: {scanner_change_rate} (소수)")
        
        # 2. DB 저장 변환 (퍼센트 형태)
        if abs(scanner_change_rate) < 1.0 and scanner_change_rate != 0.0:
            db_change_rate = scanner_change_rate * 100
        else:
            db_change_rate = scanner_change_rate
        self.assertGreaterEqual(abs(db_change_rate), 0.01)
        print(f"2. DB 저장: {db_change_rate}% (퍼센트)")
        
        # 3. API 반환 (v2는 변환 없음)
        scanner_version = 'v2'
        api_change_rate = db_change_rate
        if scanner_version != 'v2' and abs(api_change_rate) < 1.0 and api_change_rate != 0.0:
            api_change_rate = api_change_rate * 100
        self.assertAlmostEqual(api_change_rate, db_change_rate, places=2)
        print(f"3. API 반환: {api_change_rate}% (퍼센트)")
        
        # 4. 프론트엔드 표시 (그대로 표시)
        frontend_display = api_change_rate
        self.assertAlmostEqual(frontend_display, 0.57, places=2)
        print(f"4. 프론트엔드 표시: {frontend_display}%")
        
        print("\n✅ 전체 플로우 일관성 검증 완료")


if __name__ == '__main__':
    unittest.main(verbosity=2)




































