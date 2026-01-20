"""
리팩토링된 스캔 서비스 테스트
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

# 테스트 대상 모듈 import
import sys
sys.path.append(os.path.dirname(__file__))

from scan_service_refactored import (
    _parse_date, _get_universe, _create_scan_items, 
    _as_score_flags, _create_scan_response, execute_scan
)
from models import ScanItem, IndicatorPayload, TrendPayload, ScoreFlags


class TestRefactoredScanService:
    """리팩토링된 스캔 서비스 테스트"""
    
    def test_parse_date_valid_formats(self):
        """날짜 파싱 함수 테스트 - 유효한 형식들"""
        # YYYYMMDD 형식
        assert _parse_date("20251013") == "2025-10-13"
        
        # YYYY-MM-DD 형식
        assert _parse_date("2025-10-13") == "2025-10-13"
        
        # None 또는 빈 문자열
        result = _parse_date(None)
        assert len(result) == 10  # YYYY-MM-DD 형식
        assert result.count('-') == 2
    
    def test_parse_date_invalid_formats(self):
        """날짜 파싱 함수 테스트 - 잘못된 형식들"""
        # 잘못된 형식은 현재 날짜 반환
        result = _parse_date("invalid")
        assert len(result) == 10
        assert result.count('-') == 2
    
    def test_get_universe(self):
        """유니버스 가져오기 함수 테스트"""
        mock_api = Mock()
        mock_api.get_top_codes.side_effect = [
            ["005930", "000660"],  # KOSPI
            ["035420", "207940"]   # KOSDAQ
        ]
        
        with patch('scan_service_refactored.config') as mock_config:
            mock_config.universe_kospi = 2
            mock_config.universe_kosdaq = 2
            
            universe = _get_universe(mock_api, None, None)
            
            assert len(universe) == 4
            assert "005930" in universe
            assert "035420" in universe
            mock_api.get_top_codes.assert_any_call('KOSPI', 2)
            mock_api.get_top_codes.assert_any_call('KOSDAQ', 2)
    
    def test_as_score_flags(self):
        """ScoreFlags 변환 함수 테스트"""
        flags_dict = {
            "cross": True,
            "vol_expand": False,
            "macd_ok": True,
            "rsi_dema_setup": True,
            "rsi_tema_trigger": False,
            "rsi_dema_value": 65.0,
            "rsi_tema_value": 60.0,
            "overheated_rsi_tema": False,
            "tema_slope_ok": True,
            "obv_slope_ok": True,
            "above_cnt5_ok": False,
            "dema_slope_ok": True,
            "details": {"test": "value"}
        }
        
        flags = _as_score_flags(flags_dict)
        
        assert isinstance(flags, ScoreFlags)
        assert flags.cross is True
        assert flags.vol_expand is False
        assert flags.macd_ok is True
        assert flags.rsi_dema_value == 65.0
        assert flags.details == {"test": "value"}
    
    def test_create_scan_items(self):
        """ScanItem 생성 함수 테스트"""
        items = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "match": True,
                "score": 8.0,
                "indicators": {
                    "TEMA": 50000.0, "DEMA": 51000.0, "MACD_OSC": 100.0,
                    "MACD_LINE": 200.0, "MACD_SIGNAL": 100.0, "RSI_TEMA": 60.0,
                    "RSI_DEMA": 65.0, "OBV": 1000000.0, "VOL": 1000000,
                    "VOL_MA5": 900000.0, "close": 52000.0
                },
                "trend": {
                    "TEMA20_SLOPE20": 100.0, "OBV_SLOPE20": 50000.0,
                    "ABOVE_CNT5": 3, "DEMA10_SLOPE20": 150.0
                },
                "flags": {
                    "cross": True, "vol_expand": True, "macd_ok": True,
                    "rsi_dema_setup": True, "rsi_tema_trigger": True,
                    "rsi_dema_value": 65.0, "rsi_tema_value": 60.0,
                    "overheated_rsi_tema": False, "tema_slope_ok": True,
                    "obv_slope_ok": True, "above_cnt5_ok": True,
                    "dema_slope_ok": True, "details": {}
                },
                "strategy": "상승시작",
                "score_label": "강한 매수"
            }
        ]
        
        scan_items = _create_scan_items(items, None, None)
        
        assert len(scan_items) == 1
        assert isinstance(scan_items[0], ScanItem)
        assert scan_items[0].ticker == "005930"
        assert scan_items[0].name == "삼성전자"
        assert scan_items[0].score == 8.0
        assert scan_items[0].indicators.TEMA20 == 50000.0
    
    def test_create_scan_response(self):
        """ScanResponse 생성 함수 테스트"""
        indicators = IndicatorPayload(
            TEMA20=50000.0, DEMA10=51000.0, MACD_OSC=100.0,
            MACD_LINE=200.0, MACD_SIGNAL=100.0, RSI_TEMA=60.0,
            RSI_DEMA=65.0, OBV=1000000.0, VOL=1000000,
            VOL_MA5=900000.0, close=52000.0
        )
        
        trend = TrendPayload(
            TEMA20_SLOPE20=100.0, OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3, DEMA10_SLOPE20=150.0
        )
        
        flags = ScoreFlags(
            cross=True, vol_expand=True, macd_ok=True,
            rsi_dema_setup=True, rsi_tema_trigger=True,
            rsi_dema_value=65.0, rsi_tema_value=60.0,
            overheated_rsi_tema=False, tema_slope_ok=True,
            obv_slope_ok=True, above_cnt5_ok=True,
            dema_slope_ok=True, details={}
        )
        
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=8.0,
            indicators=indicators,
            trend=trend,
            flags=flags,
            strategy="상승시작",
            score_label="강한 매수"
        )
        
        with patch('scan_service_refactored.config') as mock_config:
            mock_config.rsi_setup_min = 57.0
            mock_config.fallback_enable = True
            mock_config.score_level_strong = 8
            mock_config.score_level_watch = 5
            mock_config.dynamic_score_weights = Mock(return_value={})
            mock_config.require_dema_slope = "required"
            
            response = _create_scan_response(
                [scan_item], ["005930", "000660"], "2025-10-13", 0, None
            )
            
            assert response.as_of == "2025-10-13"
            assert response.universe_count == 2
            assert response.matched_count == 1
            assert len(response.items) == 1
            assert response.items[0].ticker == "005930"
    
    def test_execute_scan_without_save(self):
        """스캔 실행 테스트 (저장 없음)"""
        mock_api = Mock()
        mock_api.get_top_codes.return_value = ["005930"]
        
        with patch('scan_service_refactored.execute_scan_with_fallback') as mock_scan:
            mock_scan.return_value = {
                "items": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "match": True,
                        "score": 8.0,
                        "indicators": {
                            "TEMA": 50000.0, "DEMA": 51000.0, "MACD_OSC": 100.0,
                            "MACD_LINE": 200.0, "MACD_SIGNAL": 100.0, "RSI_TEMA": 60.0,
                            "RSI_DEMA": 65.0, "OBV": 1000000.0, "VOL": 1000000,
                            "VOL_MA5": 900000.0, "close": 52000.0
                        },
                        "trend": {
                            "TEMA20_SLOPE20": 100.0, "OBV_SLOPE20": 50000.0,
                            "ABOVE_CNT5": 3, "DEMA10_SLOPE20": 150.0
                        },
                        "flags": {
                            "cross": True, "vol_expand": True, "macd_ok": True,
                            "rsi_dema_setup": True, "rsi_tema_trigger": True,
                            "rsi_dema_value": 65.0, "rsi_tema_value": 60.0,
                            "overheated_rsi_tema": False, "tema_slope_ok": True,
                            "obv_slope_ok": True, "above_cnt5_ok": True,
                            "dema_slope_ok": True, "details": {}
                        },
                        "strategy": "상승시작",
                        "score_label": "강한 매수"
                    }
                ],
                "chosen_step": 0
            }
            
            with patch('scan_service_refactored.config') as mock_config:
                mock_config.universe_kospi = 1
                mock_config.universe_kosdaq = 0
                mock_config.rsi_setup_min = 57.0
                mock_config.fallback_enable = True
                mock_config.score_level_strong = 8
                mock_config.score_level_watch = 5
                mock_config.dynamic_score_weights = Mock(return_value={})
                mock_config.require_dema_slope = "required"
                mock_config.market_analysis_enabled = False
                
                response = execute_scan(
                    kospi_limit=1, 
                    save_snapshot=False, 
                    api=mock_api
                )
                
                assert response.as_of is not None
                assert response.matched_count == 1
                assert len(response.items) == 1
                assert response.items[0].ticker == "005930"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
