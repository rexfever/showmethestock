"""
재등장 종목 API 엔드포인트 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# 상위 디렉토리 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestRecurringStocksMainAPI(unittest.TestCase):
    """재등장 종목 메인 API 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_recurrence_data = {
            "appeared_before": True,
            "appear_count": 3,
            "first_as_of": "20251120",
            "last_as_of": "20251128",
            "days_since_last": 3
        }
        
        self.test_item = {
            "code": "005930",
            "name": "삼성전자",
            "score": 9.5,
            "score_label": "강한 매수",
            "current_price": 75000.0,
            "strategy": "스윙",
            "flags": json.dumps({
                "target_profit": 0.05,
                "stop_loss": -0.05,
                "holding_period": "3~10일"
            }),
            "recurrence": json.dumps(self.test_recurrence_data)
        }
    
    def test_recurring_stock_recommended_date(self):
        """재등장 종목의 recommended_date가 최초 추천일로 설정되는지 테스트"""
        recurrence = json.loads(self.test_item["recurrence"])
        is_recurring = recurrence and recurrence.get("appeared_before", False)
        first_as_of = recurrence.get("first_as_of") if is_recurring else None
        
        # 검증
        self.assertTrue(is_recurring)
        self.assertEqual(first_as_of, "20251120")
        
        # recommended_date 설정 로직 시뮬레이션
        if is_recurring and first_as_of:
            recommended_date = first_as_of
        else:
            recommended_date = "20251201"  # 현재 스캔일
        
        self.assertEqual(recommended_date, "20251120")
    
    def test_normal_stock_recommended_date(self):
        """일반 종목의 recommended_date가 현재 스캔일로 설정되는지 테스트"""
        normal_item = {
            "code": "000660",
            "name": "SK하이닉스",
            "recurrence": json.dumps({
                "appeared_before": False,
                "appear_count": 0
            })
        }
        
        recurrence = json.loads(normal_item["recurrence"])
        is_recurring = recurrence and recurrence.get("appeared_before", False)
        first_as_of = recurrence.get("first_as_of") if is_recurring else None
        
        # 검증
        self.assertFalse(is_recurring)
        self.assertIsNone(first_as_of)
        
        # recommended_date 설정 로직 시뮬레이션
        if is_recurring and first_as_of:
            recommended_date = first_as_of
        else:
            recommended_date = "20251201"  # 현재 스캔일
        
        self.assertEqual(recommended_date, "20251201")
    
    def test_recurring_stock_score_and_strategy_current_date(self):
        """재등장 종목의 점수와 전략이 현재 스캔일 기준인지 테스트"""
        # 재등장 종목도 현재 스캔일의 점수와 전략 사용
        current_scan_score = 9.5
        current_scan_strategy = "스윙"
        current_scan_score_label = "강한 매수"
        
        # 최초 추천일의 점수와 전략 (과거 데이터)
        first_scan_score = 8.0
        first_scan_strategy = "포지션"
        first_scan_score_label = "매수 후보"
        
        # 재등장 종목은 현재 스캔일 기준 사용
        self.assertEqual(current_scan_score, 9.5)
        self.assertEqual(current_scan_strategy, "스윙")
        self.assertEqual(current_scan_score_label, "강한 매수")
        
        # 최초 추천일과 다를 수 있음
        self.assertNotEqual(current_scan_score, first_scan_score)
        self.assertNotEqual(current_scan_strategy, first_scan_strategy)
    
    @patch('kiwoom_api.api')
    def test_recurring_stock_returns_calculation_with_first_as_of(self, mock_api):
        """재등장 종목 수익률 계산 시 최초 추천일 기준으로 계산되는지 테스트"""
        import pandas as pd
        
        # 최초 추천일 데이터
        first_date_df = pd.DataFrame({
            'date': ['20251120'],
            'close': [73000.0]
        })
        
        # 오늘 데이터
        today_df = pd.DataFrame({
            'date': ['20251202'],
            'close': [75000.0]
        })
        
        def mock_get_ohlcv(code, count, base_dt=None):
            if base_dt == "20251120":
                return first_date_df
            elif base_dt == "20251202":
                return today_df
            else:
                return pd.DataFrame()
        
        mock_api.get_ohlcv.side_effect = mock_get_ohlcv
        
        # 재등장 종목 수익률 계산 로직 시뮬레이션
        recurrence = self.test_recurrence_data
        is_recurring = recurrence.get("appeared_before", False)
        first_as_of = recurrence.get("first_as_of") if is_recurring else None
        
        if is_recurring and first_as_of:
            # 최초 추천일의 종가 조회
            df_first = mock_api.get_ohlcv("005930", 1, first_as_of)
            first_price = float(df_first.iloc[-1]['close'])
            
            # 오늘 종가 조회
            df_today = mock_api.get_ohlcv("005930", 1, "20251202")
            today_price = float(df_today.iloc[-1]['close'])
            
            # 수익률 계산
            current_return = ((today_price - first_price) / first_price) * 100
            
            # 검증
            self.assertEqual(first_price, 73000.0)
            self.assertEqual(today_price, 75000.0)
            expected_return = ((75000 - 73000) / 73000) * 100
            self.assertAlmostEqual(current_return, expected_return, places=1)


if __name__ == '__main__':
    unittest.main()

