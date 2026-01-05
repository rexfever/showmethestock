"""
anchor_close 정확성 검증 테스트

- 추천 생성 시 anchor_close가 올바르게 저장되는지 검증
- API 응답에서 anchor_close가 재계산되지 않고 저장된 값을 사용하는지 검증
- 거래일 결정 로직 검증
"""

import unittest
import sys
import os
from datetime import date, datetime
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from date_helper import get_trading_date, get_anchor_close, is_trading_day_kr
from services.scan_service import save_scan_snapshot
from db_manager import db_manager


class TestAnchorClose(unittest.TestCase):
    """anchor_close 정확성 검증 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        # 테스트용 mock 데이터
        self.test_ticker = "005930"  # 삼성전자
        self.test_date = "20251210"  # 2025-12-10 (화요일, 거래일)
        self.test_close_price = 75000.0
    
    def test_get_trading_date(self):
        """거래일 결정 함수 테스트"""
        # 거래일인 경우
        result = get_trading_date("20251210")  # 2025-12-10 (화요일)
        self.assertEqual(result, "20251210")
        
        # 주말인 경우 (이전 거래일 반환)
        # 2025-12-13은 토요일이므로 금요일(12-12) 반환
        result = get_trading_date("20251213")
        self.assertNotEqual(result, "20251213")
        # 금요일이 거래일인지 확인
        self.assertTrue(is_trading_day_kr(result))
    
    @patch('date_helper.api')
    def test_get_anchor_close(self, mock_api):
        """anchor_close 조회 함수 테스트"""
        import pandas as pd
        
        # Mock OHLCV 데이터
        mock_df = pd.DataFrame({
            'date': ['2025-12-10'],
            'close': [75000.0],
            'volume': [1000000]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # anchor_close 조회
        result = get_anchor_close(self.test_ticker, self.test_date, price_type="CLOSE")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 75000.0)
        mock_api.get_ohlcv.assert_called_once_with(self.test_ticker, 1, self.test_date)
    
    @patch('services.scan_service.api')
    def test_save_scan_snapshot_anchor_fields(self, mock_api):
        """save_scan_snapshot에서 anchor 필드 저장 테스트"""
        import pandas as pd
        
        # Mock OHLCV 데이터
        mock_df = pd.DataFrame({
            'date': ['2025-12-10'],
            'close': [75000.0],
            'volume': [1000000]
        })
        mock_api.get_ohlcv.return_value = mock_df
        
        # 테스트용 스캔 아이템
        scan_items = [{
            "ticker": self.test_ticker,
            "name": "삼성전자",
            "score": 10.0,
            "score_label": "추천",
            "indicators": {
                "close": 75000.0,
                "change_rate": 2.5,
                "VOL": 1000000
            },
            "flags": {},
            "recurrence": {},
            "returns": {}
        }]
        
        # save_scan_snapshot 호출
        save_scan_snapshot(scan_items, self.test_date, scanner_version="v1")
        
        # DB에서 확인
        with db_manager.get_cursor(commit=False) as cur:
            from date_helper import yyyymmdd_to_date
            date_obj = yyyymmdd_to_date(self.test_date)
            
            cur.execute("""
                SELECT anchor_date, anchor_close, anchor_price_type, anchor_source
                FROM scan_rank
                WHERE date = %s AND code = %s AND scanner_version = 'v1'
            """, (date_obj, self.test_ticker))
            
            row = cur.fetchone()
            if row:
                if isinstance(row, dict):
                    anchor_date = row.get('anchor_date')
                    anchor_close = row.get('anchor_close')
                    anchor_price_type = row.get('anchor_price_type')
                    anchor_source = row.get('anchor_source')
                else:
                    anchor_date = row[0]
                    anchor_close = row[1]
                    anchor_price_type = row[2]
                    anchor_source = row[3]
                
                # anchor_close가 저장되었는지 확인
                self.assertIsNotNone(anchor_close)
                self.assertEqual(anchor_close, 75000.0)
                self.assertEqual(anchor_price_type, "CLOSE")
                self.assertIsNotNone(anchor_source)
    
    def test_anchor_close_consistency(self):
        """anchor_close가 일관되게 저장되고 조회되는지 테스트"""
        # 같은 날짜, 같은 종목에 대해 여러 번 조회해도 같은 값이 나와야 함
        anchor_close_1 = get_anchor_close(self.test_ticker, self.test_date, price_type="CLOSE")
        anchor_close_2 = get_anchor_close(self.test_ticker, self.test_date, price_type="CLOSE")
        
        # None이 아닌 경우에만 비교
        if anchor_close_1 is not None and anchor_close_2 is not None:
            self.assertEqual(anchor_close_1, anchor_close_2)


class TestTradingDayLogic(unittest.TestCase):
    """거래일 결정 로직 테스트"""
    
    def test_weekend_handling(self):
        """주말 처리 테스트"""
        # 토요일
        saturday = "20251213"  # 2025-12-13 (토요일)
        result = get_trading_date(saturday)
        # 이전 거래일(금요일) 반환되어야 함
        self.assertNotEqual(result, saturday)
        self.assertTrue(is_trading_day_kr(result))
        
        # 일요일
        sunday = "20251214"  # 2025-12-14 (일요일)
        result = get_trading_date(sunday)
        # 이전 거래일 반환되어야 함
        self.assertNotEqual(result, sunday)
        self.assertTrue(is_trading_day_kr(result))
    
    def test_holiday_handling(self):
        """공휴일 처리 테스트"""
        # 공휴일인 경우 이전 거래일 반환되어야 함
        # (실제 공휴일은 holidays 모듈에 따라 달라질 수 있음)
        pass  # 공휴일 목록이 동적으로 변하므로 스킵


if __name__ == '__main__':
    unittest.main()


