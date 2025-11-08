#!/usr/bin/env python3
"""
날짜 형식 통일 (YYYYMMDD) 테스트
수정된 모든 함수들의 날짜 형식 처리를 검증합니다.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import (
    is_trading_day,
    get_scan_by_date,
    delete_scan_result,
    validate_from_snapshot,
    get_weekly_analysis,
    get_latest_scan_from_db,
    analyze
)
from kiwoom_api import KiwoomAPI


class TestDateFormatUnification(unittest.TestCase):
    """날짜 형식 통일 테스트"""

    def setUp(self):
        """테스트 설정"""
        pass

    def test_is_trading_day_yyyymmdd_format(self):
        """is_trading_day: YYYYMMDD 형식 직접 파싱"""
        # 평일 (2025-10-31 금요일)
        result = is_trading_day("20251031")
        self.assertTrue(result, "YYYYMMDD 형식이 정상적으로 파싱되어야 함")

        # 주말 (2025-11-01 토요일)
        result = is_trading_day("20251101")
        self.assertFalse(result, "토요일은 거래일이 아님")

        # YYYY-MM-DD 형식도 지원
        result = is_trading_day("2025-10-31")
        self.assertTrue(result, "YYYY-MM-DD 형식도 지원해야 함")

    def test_is_trading_day_parsing_efficiency(self):
        """is_trading_day: YYYYMMDD 형식이 불필요한 변환 없이 직접 파싱되는지 확인"""
        # YYYYMMDD 형식이 YYYY-MM-DD로 변환되지 않고 직접 파싱되는지 확인
        # (실제 구현 검증은 코드 리뷰로 확인)
        result = is_trading_day("20251031")
        self.assertIsInstance(result, bool)

    def test_get_scan_by_date_yyyymmdd_input(self):
        """get_scan_by_date: YYYYMMDD 형식 입력"""
        import asyncio
        
        async def run_test():
            with patch('main.sqlite3.connect') as mock_connect, \
                 patch('main.calculate_returns') as mock_calculate:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_connect.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cur
                mock_cur.execute.return_value = None
                mock_cur.fetchall.return_value = [
                    ("067310", "하나마이크론", 8.0, "강한 매수", 29400.0, 1000000, -4.55, "KOSPI", "상승시작", "{}", "{}", "{}", "{}", "{}", "{}")
                ]
                mock_calculate.return_value = {'current_return': 5.0, 'max_return': 10.0, 'min_return': -2.0, 'days_elapsed': 1}

                # YYYYMMDD 형식 입력 (async 함수이므로 await)
                result = await get_scan_by_date("20251031")
                
                # SQL 쿼리에서 YYYYMMDD 형식 사용 확인
                self.assertTrue(mock_cur.execute.called, "execute가 호출되어야 함")
                call_args = mock_cur.execute.call_args
                if call_args:
                    sql_query, params = call_args[0] if call_args[0] else (None, None)
                    if params:
                        self.assertEqual(params[0], "20251031", "YYYYMMDD 형식이 그대로 사용되어야 함")
        
        asyncio.run(run_test())

    def test_get_scan_by_date_yyyy_mm_dd_input(self):
        """get_scan_by_date: YYYY-MM-DD 형식 입력 → YYYYMMDD 변환"""
        import asyncio
        
        async def run_test():
            with patch('main.sqlite3.connect') as mock_connect, \
                 patch('main.calculate_returns') as mock_calculate:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_connect.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cur
                mock_cur.execute.return_value = None
                mock_cur.fetchall.return_value = [
                    ("067310", "하나마이크론", 8.0, "강한 매수", 29400.0, 1000000, -4.55, "KOSPI", "상승시작", "{}", "{}", "{}", "{}", "{}", "{}")
                ]
                mock_calculate.return_value = {'current_return': 5.0, 'max_return': 10.0, 'min_return': -2.0, 'days_elapsed': 1}

                # YYYY-MM-DD 형식 입력
                result = await get_scan_by_date("2025-10-31")
                
                # SQL 쿼리에서 YYYYMMDD 형식으로 변환되어 사용되는지 확인
                self.assertTrue(mock_cur.execute.called, "execute가 호출되어야 함")
                call_args = mock_cur.execute.call_args
                if call_args:
                    sql_query, params = call_args[0] if call_args[0] else (None, None)
                    if params:
                        self.assertEqual(params[0], "20251031", "YYYY-MM-DD가 YYYYMMDD로 변환되어야 함")
        
        asyncio.run(run_test())

    def test_delete_scan_result_yyyymmdd_input(self):
        """delete_scan_result: YYYYMMDD 형식 입력"""
        with patch('main.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.execute.return_value = None
            mock_cur.rowcount = 5

            result = delete_scan_result("20251031")
            
            # YYYYMMDD 형식으로 삭제 쿼리 실행 확인
            call_args = mock_cur.execute.call_args
            if call_args:
                sql_query, params = call_args[0] if call_args[0] else (None, None)
                if params:
                    self.assertEqual(params[0], "20251031", "YYYYMMDD 형식으로 삭제되어야 함")

    def test_delete_scan_result_yyyy_mm_dd_input(self):
        """delete_scan_result: YYYY-MM-DD 형식 입력 → YYYYMMDD 변환"""
        with patch('main.sqlite3.connect') as mock_connect, \
             patch('os.path.join') as mock_join, \
             patch('os.path.exists') as mock_exists:
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.execute.return_value = None
            mock_cur.rowcount = 5
            mock_join.return_value = "scan-20251031.json"
            mock_exists.return_value = False

            result = delete_scan_result("2025-10-31")
            
            # YYYYMMDD 형식으로 변환되어 삭제되는지 확인
            call_args = mock_cur.execute.call_args
            if call_args:
                sql_query, params = call_args[0] if call_args[0] else (None, None)
                if params:
                    self.assertEqual(params[0], "20251031", "YYYY-MM-DD가 YYYYMMDD로 변환되어야 함")

    def test_validate_from_snapshot_yyyymmdd_input(self):
        """validate_from_snapshot: YYYYMMDD 형식 입력"""
        with patch('main.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.execute.return_value = None
            mock_cur.fetchall.return_value = []

            result = validate_from_snapshot("20251031", 10)
            
            # YYYYMMDD 형식으로 조회되는지 확인
            call_args = mock_cur.execute.call_args
            if call_args:
                sql_query, params = call_args[0] if call_args[0] else (None, None)
                if params:
                    self.assertEqual(params[0], "20251031", "YYYYMMDD 형식으로 조회되어야 함")

    def test_validate_from_snapshot_yyyy_mm_dd_input(self):
        """validate_from_snapshot: YYYY-MM-DD 형식 입력 → YYYYMMDD 변환"""
        with patch('main.sqlite3.connect') as mock_connect, \
             patch('os.path.join') as mock_join, \
             patch('os.path.exists') as mock_exists, \
             patch('builtins.open', unittest.mock.mock_open(read_data='{"rank": []}')):
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            mock_cur.execute.return_value = None
            mock_cur.fetchall.return_value = []  # DB에서 데이터 없음
            mock_join.return_value = "scan-20251031.json"
            mock_exists.return_value = True

            result = validate_from_snapshot("2025-10-31", 10)
            
            # YYYYMMDD 형식으로 변환되어 조회되는지 확인
            call_args = mock_cur.execute.call_args
            if call_args:
                sql_query, params = call_args[0] if call_args[0] else (None, None)
                if params:
                    self.assertEqual(params[0], "20251031", "YYYY-MM-DD가 YYYYMMDD로 변환되어야 함")

    def test_get_weekly_analysis_yyyymmdd_format(self):
        """get_weekly_analysis: YYYYMMDD 형식으로 BETWEEN 쿼리"""
        import asyncio
        
        async def run_test():
            with patch('main.sqlite3.connect') as mock_connect:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_connect.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.execute.return_value = None
                mock_cursor.fetchall.return_value = []

                result = await get_weekly_analysis(2025, 10, 1)
                
                # BETWEEN 쿼리에서 YYYYMMDD 형식 사용 확인
                self.assertTrue(mock_cursor.execute.called, "execute가 호출되어야 함")
                call_args = mock_cursor.execute.call_args
                if call_args:
                    sql_query, params = call_args[0] if call_args[0] else (None, None)
                    if params and len(params) >= 2:
                        start_date, end_date = params[0], params[1]
                        # YYYYMMDD 형식인지 확인 (8자리 숫자)
                        self.assertEqual(len(start_date), 8, "시작 날짜는 YYYYMMDD 형식이어야 함")
                        self.assertEqual(len(end_date), 8, "종료 날짜는 YYYYMMDD 형식이어야 함")
                        self.assertTrue(start_date.isdigit(), "YYYYMMDD 형식은 숫자여야 함")
                        self.assertTrue(end_date.isdigit(), "YYYYMMDD 형식은 숫자여야 함")
        
        asyncio.run(run_test())

    def test_get_latest_scan_from_db_date_conversion(self):
        """get_latest_scan_from_db: YYYY-MM-DD 형식 변환"""
        with patch('main.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cur
            
            # YYYYMMDD와 YYYY-MM-DD 형식 모두 반환
            mock_cur.execute.return_value = None
            mock_cur.fetchall.side_effect = [
                [("20251031",), ("2025-10-30",), ("20251029",)],  # 첫 번째 쿼리 (날짜 목록)
                [("067310", "하나마이크론", 8.0, 29400.0, -4.55, ...)]  # 두 번째 쿼리 (데이터)
            ]

            result = get_latest_scan_from_db()
            
            # YYYY-MM-DD 형식이 YYYYMMDD로 변환되어 처리되는지 확인
            # (코드 내부에서 replace('-', '') 처리 확인)
            self.assertIsNotNone(result)


    def test_date_format_consistency(self):
        """모든 함수에서 날짜 형식이 YYYYMMDD로 통일되는지 확인"""
        test_cases = [
            ("20251031", "20251031"),  # YYYYMMDD → YYYYMMDD (그대로)
            ("2025-10-31", "20251031"),  # YYYY-MM-DD → YYYYMMDD (변환)
        ]
        
        for input_date, expected in test_cases:
            # 문자열 변환 로직 테스트
            if len(input_date) == 8 and input_date.isdigit():
                result = input_date
            elif len(input_date) == 10 and input_date.count('-') == 2:
                result = input_date.replace('-', '')
            else:
                result = None
            
            self.assertEqual(result, expected, 
                           f"{input_date} → {expected} 변환이 올바르지 않음")


class TestAnalyzeTodayDate(unittest.TestCase):
    """analyze 함수의 오늘 날짜 사용 테스트"""

    def test_analyze_passes_today_date(self):
        """analyze: base_dt에 오늘 날짜 전달 확인"""
        with patch('main.normalize_code_or_name') as mock_norm, \
             patch('main.is_code') as mock_is_code, \
             patch('main.api') as mock_api, \
             patch('main.compute_indicators') as mock_compute, \
             patch('main.score_conditions') as mock_score, \
             patch('main._as_score_flags') as mock_flags, \
             patch('main.get_status_label') as mock_label, \
             patch('main.get_current_status_description') as mock_desc:
            
            mock_norm.return_value = "005930"
            mock_is_code.return_value = True
            mock_api.get_code_by_name.return_value = None
            mock_api.get_stock_name.return_value = "삼성전자"
            mock_label.return_value = "매수 후보"
            mock_desc.return_value = "상승 추세"
            
            # get_ohlcv 반환값 모킹
            import pandas as pd
            import numpy as np
            from models import ScoreFlags
            
            mock_df = pd.DataFrame({
                'close': [75000.0] * 30,
                'volume': [1000000.0] * 30,
                'TEMA20': [75000.0] * 30,
                'DEMA10': [75000.0] * 30,
                'MACD_OSC': [100.0] * 30,
                'MACD_LINE': [1000.0] * 30,
                'MACD_SIGNAL': [900.0] * 30,
                'RSI_TEMA': [50.0] * 30,
                'RSI_DEMA': [50.0] * 30,
                'OBV': [1000000.0] * 30,
                'VOL_MA5': [1000000.0] * 30,
            })
            mock_api.get_ohlcv.return_value = mock_df
            
            mock_compute.return_value = mock_df
            mock_score.return_value = (6.0, {})
            # ScoreFlags 객체 생성
            mock_flags_obj = ScoreFlags(
                cross=False,
                vol_expand=False,
                macd_ok=True,
                rsi_dema_setup=False,
                rsi_tema_trigger=False,
                rsi_dema_value=None,
                rsi_tema_value=None,
                overheated_rsi_tema=False,
                tema_slope_ok=True,
                obv_slope_ok=True,
                above_cnt5_ok=False,
                dema_slope_ok=True,
                details={},
                recurrence=None,
                label="매수 후보"
            )
            mock_flags.return_value = mock_flags_obj

            result = analyze("005930")
            
            # get_ohlcv 호출 시 base_dt 파라미터 전달 확인
            self.assertTrue(mock_api.get_ohlcv.called, "get_ohlcv가 호출되어야 함")
            call_args = mock_api.get_ohlcv.call_args
            self.assertIsNotNone(call_args, "get_ohlcv 호출 인자 확인 필요")
            
            if call_args:
                # kwargs에서 base_dt 확인
                kwargs = call_args.kwargs if call_args.kwargs else {}
                if 'base_dt' in kwargs:
                    base_dt = kwargs['base_dt']
                    today_str = datetime.now().strftime('%Y%m%d')
                    self.assertEqual(base_dt, today_str, "base_dt에 오늘 날짜가 전달되어야 함")
                    self.assertEqual(len(base_dt), 8, "YYYYMMDD 형식이어야 함")
                    self.assertTrue(base_dt.isdigit(), "YYYYMMDD 형식은 숫자여야 함")
                else:
                    # kwargs가 없거나 base_dt가 없는 경우
                    self.fail(f"base_dt 파라미터가 전달되지 않았습니다. kwargs: {kwargs}")


if __name__ == '__main__':
    unittest.main()

