"""
main.py의 핵심 기능들에 대한 단위 테스트
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 테스트 대상 모듈 import
import sys
sys.path.append(os.path.dirname(__file__))

from main import _save_snapshot_db, _db_path
from models import ScanItem, IndicatorPayload, TrendPayload, ScoreFlags


class TestMainFunctions:
    """main.py의 핵심 함수들 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        # 임시 DB 파일 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
    
    def teardown_method(self):
        """각 테스트 후에 실행"""
        # 임시 파일 정리
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_save_snapshot_db_success(self):
        """_save_snapshot_db 함수 정상 동작 테스트"""
        # 테스트 데이터 준비
        test_items = [
            ScanItem(
                ticker="005930",
                name="삼성전자",
                match=True,
                score=8.0,
                indicators=IndicatorPayload(
                    TEMA=50000.0,
                    DEMA=51000.0,
                    MACD_OSC=100.0,
                    MACD_LINE=200.0,
                    MACD_SIGNAL=100.0,
                    RSI_TEMA=60.0,
                    RSI_DEMA=65.0,
                    OBV=1000000.0,
                    VOL=1000000,
                    VOL_MA5=900000.0,
                    close=52000.0
                ),
                trend=TrendPayload(
                    TEMA20_SLOPE20=100.0,
                    OBV_SLOPE20=50000.0,
                    ABOVE_CNT5=3,
                    DEMA10_SLOPE20=150.0
                ),
                flags=ScoreFlags(
                    cross=True,
                    vol_expand=True,
                    macd_ok=True,
                    rsi_dema_setup=True,
                    rsi_tema_trigger=True,
                    rsi_dema_value=65.0,
                    rsi_tema_value=60.0,
                    overheated_rsi_tema=False,
                    tema_slope_ok=True,
                    obv_slope_ok=True,
                    above_cnt5_ok=True,
                    dema_slope_ok=True,
                    details={}
                ),
                strategy="상승시작",
                score_label="강한 매수"
            )
        ]
        
        # KiwoomAPI 모킹
        with patch('main.api') as mock_api, patch('main._db_path') as mock_db_path:
            mock_db_path.return_value = self.temp_db.name
            
            # Mock DataFrame 생성
            mock_df = Mock()
            mock_df.empty = False
            mock_df.__len__ = Mock(return_value=2)
            
            # iloc[-1] Mock 설정
            mock_latest = Mock()
            mock_latest.__getitem__ = Mock(side_effect=lambda key: {
                "close": 52000.0,
                "volume": 1000000
            }[key])
            
            # iloc[-2] Mock 설정  
            mock_prev = Mock()
            mock_prev.__getitem__ = Mock(side_effect=lambda key: {
                "close": 51000.0
            }[key])
            
            mock_df.iloc = [mock_prev, mock_latest]
            
            mock_api.get_ohlcv.return_value = mock_df
            
            # 함수 실행
            _save_snapshot_db("2025-10-13", test_items)
            
            # DB에 데이터가 저장되었는지 확인
            conn = sqlite3.connect(self.temp_db.name)
            cur = conn.cursor()
            cur.execute("SELECT * FROM scan_rank WHERE date = '2025-10-13'")
            rows = cur.fetchall()
            conn.close()
            
            assert len(rows) == 1
            assert rows[0][1] == "005930"  # code
            assert rows[0][2] == "삼성전자"  # name
            assert rows[0][3] == 8.0  # score
    
    def test_save_snapshot_db_with_api_error(self):
        """API 오류 시 _save_snapshot_db 함수 동작 테스트"""
        test_items = [
            ScanItem(
                ticker="005930",
                name="삼성전자",
                match=True,
                score=8.0,
                indicators=IndicatorPayload(
                    TEMA=50000.0, DEMA=51000.0, MACD_OSC=100.0,
                    MACD_LINE=200.0, MACD_SIGNAL=100.0, RSI_TEMA=60.0,
                    RSI_DEMA=65.0, OBV=1000000.0, VOL=1000000,
                    VOL_MA5=900000.0, close=52000.0
                ),
                trend=TrendPayload(
                    TEMA20_SLOPE20=100.0, OBV_SLOPE20=50000.0,
                    ABOVE_CNT5=3, DEMA10_SLOPE20=150.0
                ),
                flags=ScoreFlags(
                    cross=True, vol_expand=True, macd_ok=True,
                    rsi_dema_setup=True, rsi_tema_trigger=True,
                    rsi_dema_value=65.0, rsi_tema_value=60.0,
                    overheated_rsi_tema=False, tema_slope_ok=True,
                    obv_slope_ok=True, above_cnt5_ok=True,
                    dema_slope_ok=True, details={}
                ),
                strategy="상승시작",
                score_label="강한 매수"
            )
        ]
        
        # API 오류 시뮬레이션
        with patch('main.api') as mock_api, patch('main._db_path') as mock_db_path:
            mock_db_path.return_value = self.temp_db.name
            mock_api.get_ohlcv.side_effect = Exception("API 오류")
            
            # 함수 실행 (오류가 발생하지 않아야 함)
            _save_snapshot_db("2025-10-13", test_items)
            
            # DB에 기본값으로 저장되었는지 확인
            conn = sqlite3.connect(self.temp_db.name)
            cur = conn.cursor()
            cur.execute("SELECT * FROM scan_rank WHERE date = '2025-10-13'")
            rows = cur.fetchall()
            conn.close()
            
            assert len(rows) == 1
            assert rows[0][6] == 1000000.0  # volume (indicators에서 가져온 값)
            assert rows[0][7] == 0.0  # change_rate (기본값)
    
    def test_save_snapshot_db_empty_items(self):
        """빈 items 리스트로 _save_snapshot_db 함수 테스트"""
        with patch('main._db_path') as mock_db_path:
            mock_db_path.return_value = self.temp_db.name
            # 빈 리스트로 함수 실행
            _save_snapshot_db("2025-10-13", [])
        
        # DB에 데이터가 없어야 함
        conn = sqlite3.connect(self.temp_db.name)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = '2025-10-13'")
        count = cur.fetchone()[0]
        conn.close()
        
        assert count == 0
    
    def test_db_path_function(self):
        """_db_path 함수 테스트"""
        db_path = _db_path()
        assert db_path.endswith('snapshots.db')
        assert os.path.dirname(db_path) == os.path.dirname(__file__)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
