"""
거래일 검증 테스트
"""
import unittest
from unittest.mock import patch, Mock
from datetime import datetime, date
import pytz
import holidays

# main.py에서 is_trading_day 함수 import
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import is_trading_day


class TestTradingDayValidation(unittest.TestCase):
    """거래일 검증 테스트"""
    
    def test_is_trading_day_weekday(self):
        """평일 거래일 테스트"""
        # 월요일 테스트
        result = is_trading_day("2025-10-27")  # 월요일
        self.assertTrue(result)
        
        # 금요일 테스트
        result = is_trading_day("2025-10-24")  # 금요일
        self.assertTrue(result)
    
    def test_is_trading_day_weekend(self):
        """주말 비거래일 테스트"""
        # 토요일 테스트
        result = is_trading_day("2025-10-25")  # 토요일
        self.assertFalse(result)
        
        # 일요일 테스트
        result = is_trading_day("2025-10-26")  # 일요일
        self.assertFalse(result)
    
    def test_is_trading_day_holiday(self):
        """공휴일 비거래일 테스트"""
        # 신정 테스트
        result = is_trading_day("2025-01-01")  # 신정
        self.assertFalse(result)
        
        # 추석 연휴 테스트 (2025년 추석은 10월 6일)
        result = is_trading_day("2025-10-06")  # 추석
        self.assertFalse(result)
    
    def test_is_trading_day_date_formats(self):
        """다양한 날짜 형식 테스트"""
        # YYYY-MM-DD 형식
        result1 = is_trading_day("2025-10-27")
        self.assertTrue(result1)
        
        # YYYYMMDD 형식
        result2 = is_trading_day("20251027")
        self.assertTrue(result2)
        
        # 두 결과가 같아야 함
        self.assertEqual(result1, result2)
    
    def test_is_trading_day_invalid_format(self):
        """잘못된 날짜 형식 테스트"""
        # 잘못된 형식
        result = is_trading_day("2025/10/27")
        self.assertFalse(result)
        
        # 빈 문자열
        result = is_trading_day("")
        self.assertFalse(result)
        
        # None
        result = is_trading_day(None)
        self.assertFalse(result)
    
    def test_is_trading_day_today(self):
        """오늘 날짜 테스트 (매개변수 없이 호출)"""
        with patch('main.datetime') as mock_datetime:
            # 월요일로 설정
            mock_now = Mock()
            mock_now.strftime.return_value = "2025-10-27"
            mock_datetime.now.return_value = mock_now
            
            result = is_trading_day()
            self.assertTrue(result)
    
    def test_is_trading_day_today_weekend(self):
        """오늘 날짜가 주말인 경우 테스트"""
        with patch('main.datetime') as mock_datetime:
            # 토요일로 설정
            mock_now = Mock()
            mock_now.strftime.return_value = "2025-10-25"
            mock_datetime.now.return_value = mock_now
            
            result = is_trading_day()
            self.assertFalse(result)


class TestScanEndpointTradingDayValidation(unittest.TestCase):
    """스캔 엔드포인트 거래일 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)
    
    def test_scan_endpoint_weekend_rejection(self):
        """주말에 스캔 요청 시 거부 테스트"""
        # 토요일 스캔 요청
        response = self.client.get("/scan?date=2025-10-25")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("거래일이 아닙니다", response.json()["detail"])
        self.assertIn("주말", response.json()["detail"])
    
    def test_scan_endpoint_holiday_rejection(self):
        """공휴일에 스캔 요청 시 거부 테스트"""
        # 신정 스캔 요청
        response = self.client.get("/scan?date=2025-01-01")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("거래일이 아닙니다", response.json()["detail"])
        self.assertIn("공휴일", response.json()["detail"])
    
    def test_scan_endpoint_weekday_acceptance(self):
        """평일에 스캔 요청 시 허용 테스트"""
        # 금요일 스캔 요청 (모킹 필요)
        with patch('main.api') as mock_api, \
             patch('main.execute_scan_with_fallback') as mock_execute, \
             patch('main._save_snapshot_db') as mock_save:
            
            # Mock 설정
            mock_api.get_top_codes.return_value = ["005930", "000660"]
            mock_execute.return_value = ([], "step1")
            
            response = self.client.get("/scan?date=2025-10-24")
            
            # 거래일이므로 400 에러가 아니어야 함
            self.assertNotEqual(response.status_code, 400)
    
    def test_scan_endpoint_invalid_date_format(self):
        """잘못된 날짜 형식 테스트"""
        response = self.client.get("/scan?date=2025/10/25")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("날짜 형식이 올바르지 않습니다", response.json()["detail"])


if __name__ == '__main__':
    unittest.main()



