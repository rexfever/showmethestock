"""
API 엔드포인트 통합 테스트
"""
import pytest
import httpx
from fastapi.testclient import TestClient
import tempfile
import os
from unittest.mock import Mock, patch

# 테스트 대상 모듈 import
import sys
sys.path.append(os.path.dirname(__file__))

from main import app


class TestAPIEndpoints:
    """API 엔드포인트 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """헬스 체크 엔드포인트 테스트"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_scan_endpoint_without_save(self):
        """스캔 API 테스트 (저장 없음)"""
        with patch('main.api') as mock_api:
            # Mock 데이터 설정
            mock_api.get_top_codes.return_value = ["005930", "000660"]
            mock_api.get_ohlcv.return_value = Mock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            mock_api.get_ohlcv.return_value.iloc = [Mock(), Mock()]
            mock_api.get_ohlcv.return_value.iloc[-1] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-1]["close"] = 50000.0
            mock_api.get_ohlcv.return_value.iloc[-1]["volume"] = 1000000
            mock_api.get_ohlcv.return_value.iloc[-2] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-2]["close"] = 49000.0
            
            # 스캔 실행 함수 모킹
            with patch('main.execute_scan_with_fallback') as mock_scan:
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
                
                response = self.client.get("/scan?save_snapshot=false")
                assert response.status_code == 200
                data = response.json()
                assert "as_of" in data
                assert "matched_count" in data
                assert "items" in data
    
    def test_scan_endpoint_with_save(self):
        """스캔 API 테스트 (저장 포함)"""
        with patch('main.api') as mock_api:
            # Mock 데이터 설정
            mock_api.get_top_codes.return_value = ["005930"]
            mock_api.get_ohlcv.return_value = Mock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            mock_api.get_ohlcv.return_value.iloc = [Mock(), Mock()]
            mock_api.get_ohlcv.return_value.iloc[-1] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-1]["close"] = 50000.0
            mock_api.get_ohlcv.return_value.iloc[-1]["volume"] = 1000000
            mock_api.get_ohlcv.return_value.iloc[-2] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-2]["close"] = 49000.0
            
            # 스캔 실행 함수 모킹
            with patch('main.execute_scan_with_fallback') as mock_scan:
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
                
                # DB 저장 함수 모킹
                with patch('main._save_snapshot_db') as mock_save:
                    response = self.client.get("/scan?save_snapshot=true")
                    assert response.status_code == 200
                    # DB 저장 함수가 호출되었는지 확인
                    mock_save.assert_called_once()
    
    def test_scan_historical_endpoint(self):
        """과거 스캔 API 테스트"""
        with patch('main.api') as mock_api:
            mock_api.get_ohlcv.return_value = Mock()
            mock_api.get_ohlcv.return_value.empty = False
            mock_api.get_ohlcv.return_value.__len__ = Mock(return_value=2)
            mock_api.get_ohlcv.return_value.iloc = [Mock(), Mock()]
            mock_api.get_ohlcv.return_value.iloc[-1] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-1]["close"] = 50000.0
            mock_api.get_ohlcv.return_value.iloc[-1]["volume"] = 1000000
            mock_api.get_ohlcv.return_value.iloc[-2] = Mock()
            mock_api.get_ohlcv.return_value.iloc[-2]["close"] = 49000.0
            
            with patch('main.execute_scan_with_fallback') as mock_scan:
                mock_scan.return_value = {
                    "items": [],
                    "chosen_step": 0
                }
                
                response = self.client.get("/scan/historical?date=2025-10-01")
                assert response.status_code == 200
                data = response.json()
                assert "as_of" in data
                assert data["as_of"] == "2025-10-01"
    
    def test_universe_endpoint(self):
        """유니버스 API 테스트"""
        with patch('main.api') as mock_api:
            mock_api.get_top_codes.return_value = ["005930", "000660"]
            
            response = self.client.get("/universe")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) > 0
    
    def test_latest_scan_endpoint(self):
        """최신 스캔 API 테스트"""
        with patch('main.sqlite3') as mock_sqlite3:
            # Mock DB 연결 설정
            mock_conn = Mock()
            mock_cur = Mock()
            mock_conn.cursor.return_value = mock_cur
            mock_sqlite3.connect.return_value = mock_conn
            
            # Mock DB 결과 설정
            mock_cur.fetchall.return_value = [
                ("2025-10-13", "005930", "삼성전자", 8.0, "강한 매수", 
                 50000.0, 1000000, 2.0, "KOSPI", "상승시작",
                 '{"TEMA": 50000.0}', '{"TEMA20_SLOPE20": 100.0}',
                 '{"cross": true}', '{"close": 50000.0}', 'null', 'null')
            ]
            
            response = self.client.get("/latest-scan")
            assert response.status_code == 200
            data = response.json()
            assert "as_of" in data
            assert "items" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])












