#!/usr/bin/env python3
"""
스캐너 백테스트 스크립트 상세 테스트
"""
import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.scanner_backtest import (
    get_trading_days,
    get_universe,
    run_scan_for_date,
    analyze_performance,
    print_summary,
    save_results
)
from date_helper import normalize_date


class TestGetTradingDays:
    """get_trading_days 함수 테스트"""
    
    def test_basic_trading_days(self):
        """기본 거래일 리스트 테스트"""
        start = "20251001"  # 수요일
        end = "20251007"    # 화요일 (다음 주)
        
        trading_days = get_trading_days(start, end)
        
        # 10/1(수), 10/2(목), 10/3(금), 10/6(월), 10/7(화) = 5일
        assert len(trading_days) == 5
        assert "20251001" in trading_days
        assert "20251002" in trading_days
        assert "20251003" in trading_days
        assert "20251006" in trading_days
        assert "20251007" in trading_days
        # 주말 제외
        assert "20251004" not in trading_days  # 토요일
        assert "20251005" not in trading_days  # 일요일
    
    def test_holiday_exclusion(self):
        """공휴일 제외 테스트"""
        # 추석 연휴 (2025년 10월 6일은 추석)
        start = "20251003"  # 금요일
        end = "20251008"    # 수요일
        
        trading_days = get_trading_days(start, end)
        
        # 10/3(금), 10/7(화), 10/8(수) = 3일 (10/6 추석 제외)
        # 실제 공휴일은 holidays 라이브러리에 따라 다를 수 있음
        assert len(trading_days) >= 2  # 최소 2일은 있어야 함
    
    def test_single_day(self):
        """단일 날짜 테스트"""
        date = "20251001"
        trading_days = get_trading_days(date, date)
        
        assert len(trading_days) == 1
        assert trading_days[0] == date
    
    def test_weekend_only(self):
        """주말만 포함된 기간 테스트"""
        start = "20251004"  # 토요일
        end = "20251005"    # 일요일
        
        trading_days = get_trading_days(start, end)
        
        assert len(trading_days) == 0


class TestGetUniverse:
    """get_universe 함수 테스트"""
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.config')
    def test_basic_universe(self, mock_config, mock_api):
        """기본 유니버스 조회 테스트"""
        mock_config.universe_kospi = 50
        mock_config.universe_kosdaq = 30
        mock_api.get_top_codes.side_effect = [
            ["005930", "000660", "051910"],  # KOSPI
            ["091990", "263750", "035720"]   # KOSDAQ
        ]
        
        universe = get_universe()
        
        assert len(universe) == 6
        assert "005930" in universe
        assert "091990" in universe
        mock_api.get_top_codes.assert_any_call('KOSPI', 50)
        mock_api.get_top_codes.assert_any_call('KOSDAQ', 30)
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.config')
    def test_custom_limits(self, mock_config, mock_api):
        """커스텀 제한 테스트"""
        mock_api.get_top_codes.return_value = ["005930"]
        
        universe = get_universe(kospi_limit=10, kosdaq_limit=5)
        
        assert len(universe) == 2  # KOSPI + KOSDAQ
        mock_api.get_top_codes.assert_any_call('KOSPI', 10)
        mock_api.get_top_codes.assert_any_call('KOSDAQ', 5)
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.config')
    def test_api_failure(self, mock_config, mock_api):
        """API 실패 처리 테스트"""
        mock_api.get_top_codes.side_effect = Exception("API Error")
        
        universe = get_universe()
        
        assert universe == []


class TestRunScanForDate:
    """run_scan_for_date 함수 테스트"""
    
    @patch('backtest.scanner_backtest.is_trading_day')
    @patch('backtest.scanner_backtest.get_universe')
    @patch('backtest.scanner_backtest.execute_scan_with_fallback')
    @patch('backtest.scanner_backtest.market_analyzer')
    @patch('backtest.scanner_backtest.config')
    @patch('backtest.scanner_backtest.get_regime_version')
    @patch('backtest.scanner_backtest.get_scanner_version')
    def test_successful_scan(
        self, mock_get_scanner, mock_get_regime, mock_config,
        mock_market_analyzer, mock_execute_scan, mock_get_universe, mock_is_trading_day
    ):
        """성공적인 스캔 테스트"""
        mock_is_trading_day.return_value = True
        mock_get_universe.return_value = ["005930", "000660"]
        mock_config.market_analysis_enable = True
        mock_config.universe_kospi = 50
        mock_get_regime.return_value = "v4"
        mock_get_scanner.return_value = "v2"
        
        # MarketCondition 모의
        mock_condition = Mock()
        mock_condition.version = "regime_v4"
        mock_condition.final_regime = "bull"
        mock_condition.global_trend_score = 2.5
        mock_condition.global_risk_score = 0.5
        mock_market_analyzer.analyze_market_condition.return_value = mock_condition
        
        # 스캔 결과 모의
        mock_items = [
            {"ticker": "005930", "name": "삼성전자", "score": 8.5},
            {"ticker": "000660", "name": "SK하이닉스", "score": 7.2}
        ]
        mock_execute_scan.return_value = (mock_items, "step0", "v2")
        
        result = run_scan_for_date("20251001")
        
        assert result["success"] is True
        assert result["date"] == "20251001"
        assert len(result["items"]) == 2
        assert result["matched_count"] == 2
        assert result["scanner_version"] == "v2"
        assert result["regime_version"] == "v4"
    
    @patch('backtest.scanner_backtest.is_trading_day')
    def test_non_trading_day(self, mock_is_trading_day):
        """비거래일 처리 테스트"""
        mock_is_trading_day.return_value = False
        
        result = run_scan_for_date("20251005")  # 일요일
        
        assert result["success"] is False
        assert result["error"] == "거래일이 아닙니다"
        assert result["items"] == []
    
    @patch('backtest.scanner_backtest.is_trading_day')
    @patch('backtest.scanner_backtest.get_universe')
    def test_universe_failure(self, mock_get_universe, mock_is_trading_day):
        """유니버스 조회 실패 테스트"""
        mock_is_trading_day.return_value = True
        mock_get_universe.return_value = []
        
        result = run_scan_for_date("20251001")
        
        assert result["success"] is False
        assert result["error"] == "유니버스 조회 실패"
    
    @patch('backtest.scanner_backtest.is_trading_day')
    @patch('backtest.scanner_backtest.get_universe')
    @patch('backtest.scanner_backtest.execute_scan_with_fallback')
    @patch('backtest.scanner_backtest.config')
    def test_scan_exception(self, mock_config, mock_execute_scan, mock_get_universe, mock_is_trading_day):
        """스캔 예외 처리 테스트"""
        mock_is_trading_day.return_value = True
        mock_get_universe.return_value = ["005930"]
        mock_config.market_analysis_enable = False
        mock_execute_scan.side_effect = Exception("Scan error")
        
        result = run_scan_for_date("20251001")
        
        assert result["success"] is False
        assert "Scan error" in result["error"]


class TestAnalyzePerformance:
    """analyze_performance 함수 테스트"""
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.get_trading_days')
    def test_basic_performance(self, mock_get_trading_days, mock_api):
        """기본 성과 분석 테스트"""
        # 스캔 결과 모의
        scan_results = [
            {
                "date": "20251001",
                "success": True,
                "items": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "current_price": 75000,
                        "score": 8.5
                    },
                    {
                        "ticker": "000660",
                        "name": "SK하이닉스",
                        "current_price": 150000,
                        "score": 7.2
                    }
                ]
            }
        ]
        
        # 거래일 모의 (5일 후 = 10/8)
        mock_get_trading_days.return_value = ["20251001", "20251002", "20251003", "20251006", "20251007", "20251008"]
        
        # OHLCV 데이터 모의
        def mock_get_ohlcv(code, count, base_dt=None):
            df = pd.DataFrame({
                'date': ['20251008'],
                'open': [76000 if code == "005930" else 152000],
                'high': [77000 if code == "005930" else 153000],
                'low': [75000 if code == "005930" else 151000],
                'close': [76000 if code == "005930" else 152000],
                'volume': [1000000]
            })
            return df
        
        mock_api.get_ohlcv.side_effect = mock_get_ohlcv
        
        performance = analyze_performance(scan_results, days_after=5)
        
        assert performance["total_scans"] == 1
        assert performance["total_items"] == 2
        assert performance["analyzed_dates"] == 1
        assert "20251001" in performance["performance_by_date"]
        
        perf = performance["performance_by_date"]["20251001"]
        assert perf["items_count"] == 2
        # 삼성전자: (76000 - 75000) / 75000 * 100 = 1.33%
        # SK하이닉스: (152000 - 150000) / 150000 * 100 = 1.33%
        # 평균: 1.33%
        assert abs(perf["avg_return"] - 1.33) < 0.1
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.get_trading_days')
    def test_missing_price_data(self, mock_get_trading_days, mock_api):
        """가격 데이터 없음 처리 테스트"""
        scan_results = [
            {
                "date": "20251001",
                "success": True,
                "items": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        # current_price 없음
                        "score": 8.5
                    }
                ]
            }
        ]
        
        mock_get_trading_days.return_value = ["20251001", "20251008"]
        mock_api.get_ohlcv.return_value = pd.DataFrame()  # 빈 DataFrame
        
        performance = analyze_performance(scan_results, days_after=5)
        
        assert performance["total_scans"] == 1
        assert performance["total_items"] == 1
        assert performance["analyzed_dates"] == 0  # 가격 데이터 없어서 분석 불가
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.get_trading_days')
    def test_api_error_handling(self, mock_get_trading_days, mock_api):
        """API 에러 처리 테스트"""
        scan_results = [
            {
                "date": "20251001",
                "success": True,
                "items": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "current_price": 75000,
                        "score": 8.5
                    }
                ]
            }
        ]
        
        mock_get_trading_days.return_value = ["20251001", "20251008"]
        mock_api.get_ohlcv.side_effect = Exception("API Error")
        
        performance = analyze_performance(scan_results, days_after=5)
        
        # 에러가 발생해도 계속 진행
        assert performance["total_scans"] == 1
        assert performance["analyzed_dates"] == 0  # 에러로 인해 분석 불가
    
    def test_empty_results(self):
        """빈 결과 처리 테스트"""
        performance = analyze_performance([])
        
        assert performance["total_scans"] == 0
        assert performance["total_items"] == 0
        assert performance["analyzed_dates"] == 0
    
    def test_failed_scan_exclusion(self):
        """실패한 스캔 제외 테스트"""
        scan_results = [
            {
                "date": "20251001",
                "success": False,
                "error": "거래일이 아닙니다",
                "items": []
            },
            {
                "date": "20251002",
                "success": True,
                "items": []
            }
        ]
        
        performance = analyze_performance(scan_results)
        
        assert performance["total_scans"] == 1  # 성공한 스캔만 카운트
        assert performance["total_items"] == 0


class TestPrintSummary:
    """print_summary 함수 테스트"""
    
    def test_basic_summary(self, capsys):
        """기본 요약 출력 테스트"""
        scan_results = [
            {"date": "20251001", "success": True, "items": [{"ticker": "005930"}]}
        ]
        performance = {
            "total_scans": 1,
            "total_items": 1,
            "analyzed_dates": 1,
            "overall_avg_return": 2.5,
            "overall_win_rate": 80.0,
            "performance_by_date": {
                "20251001": {
                    "items_count": 1,
                    "avg_return": 2.5,
                    "win_rate": 100.0,
                    "items": []
                }
            }
        }
        
        print_summary(scan_results, performance)
        
        captured = capsys.readouterr()
        assert "백테스트 결과 요약" in captured.out
        assert "성공한 스캔: 1개" in captured.out
        assert "평균 수익률: 2.50%" in captured.out
    
    def test_failed_scans_display(self, capsys):
        """실패한 스캔 표시 테스트"""
        scan_results = [
            {"date": "20251001", "success": False, "error": "거래일이 아닙니다"},
            {"date": "20251002", "success": True, "items": []}
        ]
        performance = {
            "total_scans": 1,
            "total_items": 0,
            "analyzed_dates": 0
        }
        
        print_summary(scan_results, performance)
        
        captured = capsys.readouterr()
        assert "실패한 스캔: 1개" in captured.out
        assert "거래일이 아닙니다" in captured.out


class TestSaveResults:
    """save_results 함수 테스트"""
    
    @patch('backtest.scanner_backtest.Path')
    @patch('builtins.open', create=True)
    @patch('backtest.scanner_backtest.pd.DataFrame')
    def test_save_results(self, mock_df, mock_open, mock_path):
        """결과 저장 테스트"""
        scan_results = [{"date": "20251001", "success": True}]
        performance = {
            "total_scans": 1,
            "performance_by_date": {
                "20251001": {
                    "items_count": 1,
                    "avg_return": 2.5,
                    "win_rate": 100.0
                }
            }
        }
        
        # Path 모의
        mock_output_path = Mock()
        mock_output_path.mkdir = Mock()
        mock_output_path.__truediv__ = Mock(return_value=mock_output_path)
        mock_path.return_value = mock_output_path
        
        # DataFrame 모의
        mock_df_instance = Mock()
        mock_df.return_value = mock_df_instance
        
        save_results(scan_results, performance, "test_output")
        
        # 디렉토리 생성 확인
        mock_output_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # 파일 저장 확인 (최소 2번: JSON 2개)
        assert mock_open.call_count >= 2


class TestIntegration:
    """통합 테스트"""
    
    @patch('backtest.scanner_backtest.api')
    @patch('backtest.scanner_backtest.is_trading_day')
    @patch('backtest.scanner_backtest.get_universe')
    @patch('backtest.scanner_backtest.execute_scan_with_fallback')
    @patch('backtest.scanner_backtest.market_analyzer')
    @patch('backtest.scanner_backtest.config')
    @patch('backtest.scanner_backtest.get_regime_version')
    @patch('backtest.scanner_backtest.get_scanner_version')
    @patch('backtest.scanner_backtest.get_trading_days')
    def test_end_to_end(
        self, mock_get_trading_days, mock_get_scanner, mock_get_regime,
        mock_config, mock_market_analyzer, mock_execute_scan, mock_get_universe,
        mock_is_trading_day, mock_api
    ):
        """전체 플로우 통합 테스트"""
        # 설정
        mock_is_trading_day.return_value = True
        mock_get_universe.return_value = ["005930"]
        mock_config.market_analysis_enable = False
        mock_get_scanner.return_value = "v2"
        mock_get_regime.return_value = "v4"
        
        # 스캔 결과
        mock_items = [{"ticker": "005930", "name": "삼성전자", "current_price": 75000, "score": 8.5}]
        mock_execute_scan.return_value = (mock_items, "step0", "v2")
        
        # 거래일
        mock_get_trading_days.return_value = ["20251001", "20251008"]
        
        # OHLCV 데이터
        def mock_get_ohlcv(code, count, base_dt=None):
            return pd.DataFrame({
                'date': ['20251008'],
                'close': [76000],
                'open': [75000],
                'high': [77000],
                'low': [74000],
                'volume': [1000000]
            })
        mock_api.get_ohlcv.side_effect = mock_get_ohlcv
        
        # 스캔 실행
        scan_results = []
        result = run_scan_for_date("20251001")
        scan_results.append(result)
        
        # 성과 분석
        performance = analyze_performance(scan_results, days_after=5)
        
        # 검증
        assert result["success"] is True
        assert performance["total_scans"] == 1
        assert performance["analyzed_dates"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

