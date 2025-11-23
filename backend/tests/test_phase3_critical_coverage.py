#!/usr/bin/env python3
"""
Phase 3 핵심 커버리지 테스트: 비즈니스 로직 중심 테스트
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestCriticalBusinessLogic:
    """핵심 비즈니스 로직 테스트"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    @patch('main.api')
    @patch('main.config')
    @patch('main.is_trading_day')
    @patch('main.execute_scan_with_fallback')
    def test_scan_endpoint_full_flow(self, mock_scan, mock_trading, mock_config, mock_api, client):
        """스캔 엔드포인트 전체 플로우 테스트"""
        # Mock 설정
        mock_trading.return_value = True
        mock_config.universe_kospi = 100
        mock_config.universe_kosdaq = 100
        mock_config.market_analysis_enable = False
        mock_api.get_top_codes.return_value = ['005930', '000660']
        
        # 스캔 결과 Mock
        mock_scan.return_value = (
            [{'ticker': '005930', 'name': '삼성전자', 'score': 8.5, 'match': True,
              'indicators': {'close': 70000, 'change_rate': 2.5, 'TEMA20': 69000, 'DEMA10': 68000,
                           'MACD_OSC': 100, 'MACD_LINE': 200, 'MACD_SIGNAL': 150,
                           'RSI_TEMA': 65, 'RSI_DEMA': 62, 'OBV': 1000000, 'VOL': 50000, 'VOL_MA5': 45000},
              'trend': {'TEMA20_SLOPE20': 1.5, 'OBV_SLOPE20': 0.8, 'ABOVE_CNT5': 4, 'DEMA10_SLOPE20': 1.2},
              'flags': {'cross': True, 'vol_expand': False}, 'score_label': '강세', 'strategy': '상승추세'}],
            'step1',
            'v1'
        )
        
        with patch('main.get_recurrence_data') as mock_recur, \
             patch('main.calculate_returns_batch') as mock_returns, \
             patch('main.get_market_guide') as mock_guide:
            
            mock_recur.return_value = {}
            mock_returns.return_value = {}
            mock_guide.return_value = "시장 상황이 양호합니다"
            
            response = client.get("/scan")
            assert response.status_code == 200
            data = response.json()
            assert "matched_count" in data
            assert "items" in data
    
    @patch('main.db_manager')
    def test_save_snapshot_db_with_market_condition(self, mock_db):
        """시장 상황과 함께 스냅샷 저장 테스트"""
        from main import _save_snapshot_db, ScanItem, IndicatorPayload, TrendPayload
        
        mock_cursor = Mock()
        mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock 시장 상황
        mock_market = Mock()
        mock_market.market_sentiment = "bullish"
        mock_market.sentiment_score = 0.8
        mock_market.kospi_return = 0.02
        mock_market.volatility = 0.15
        mock_market.rsi_threshold = 65.0
        mock_market.sector_rotation = "tech"
        mock_market.foreign_flow = "inflow"
        mock_market.volume_trend = "increasing"
        mock_market.min_signals = 3
        mock_market.macd_osc_min = -5.0
        mock_market.vol_ma5_mult = 1.5
        mock_market.gap_max = 0.05
        mock_market.ext_from_tema20_max = 0.03
        
        # Mock 스캔 아이템
        scan_item = ScanItem(
            ticker="005930", name="삼성전자", match=True, score=8.5,
            indicators=IndicatorPayload(
                TEMA20=70000, DEMA10=69000, MACD_OSC=100, MACD_LINE=200, MACD_SIGNAL=150,
                RSI_TEMA=65, RSI_DEMA=62, OBV=1000000, VOL=50000, VOL_MA5=45000,
                close=70000, change_rate=2.5
            ),
            trend=TrendPayload(TEMA20_SLOPE20=1.5, OBV_SLOPE20=0.8, ABOVE_CNT5=4, DEMA10_SLOPE20=1.2),
            flags=None, score_label="강세", strategy="상승추세"
        )
        
        _save_snapshot_db("20241129", [scan_item], mock_market, "v1")
        
        # 시장 상황 저장 확인
        assert mock_cursor.execute.call_count >= 2  # 시장상황 + 스캔결과
    
    @patch('main.api')
    def test_universe_endpoint_with_scan(self, mock_api, client):
        """유니버스 엔드포인트 스캔 적용 테스트"""
        mock_api.get_top_codes.side_effect = [['005930'], ['000660']]
        
        with patch('main.config') as mock_config, \
             patch('main.compute_indicators') as mock_compute, \
             patch('main.match_condition') as mock_match:
            
            mock_config.universe_kospi = 1
            mock_config.universe_kosdaq = 1
            mock_config.ohlcv_count = 100
            
            # DataFrame Mock
            import pandas as pd
            mock_df = pd.DataFrame({
                'open': [69000], 'high': [71000], 'low': [68000], 
                'close': [70000], 'volume': [50000]
            })
            mock_api.get_ohlcv.return_value = mock_df
            mock_api.get_stock_name.return_value = "삼성전자"
            mock_compute.return_value = mock_df
            mock_match.return_value = True
            
            response = client.get("/universe?apply_scan=true")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
    
    @patch('main.api')
    def test_analyze_endpoint_success(self, mock_api, client):
        """분석 엔드포인트 성공 케이스 테스트"""
        import pandas as pd
        
        mock_api.get_code_by_name.return_value = None  # 코드 그대로 사용
        mock_api.get_stock_name.return_value = "삼성전자"
        
        # 충분한 데이터가 있는 DataFrame
        mock_df = pd.DataFrame({
            'close': [70000] * 25,  # 25일 데이터
            'TEMA20': [69000] * 25,
            'DEMA10': [68000] * 25,
            'MACD_OSC': [100] * 25,
            'MACD_LINE': [200] * 25,
            'MACD_SIGNAL': [150] * 25,
            'RSI_TEMA': [65] * 25,
            'RSI_DEMA': [62] * 25,
            'OBV': [1000000] * 25,
            'volume': [50000] * 25,
            'VOL_MA5': [45000] * 25
        })
        
        mock_api.get_ohlcv.return_value = mock_df
        
        with patch('main.compute_indicators') as mock_compute, \
             patch('main.score_conditions') as mock_score:
            
            mock_compute.return_value = mock_df
            mock_score.return_value = (8.5, {'cross': True, 'vol_expand': False})
            
            response = client.get("/analyze?name_or_code=005930")
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True
            assert data["item"]["ticker"] == "005930"
    
    def test_delete_scan_result(self, client):
        """스캔 결과 삭제 테스트"""
        with patch('main.db_manager') as mock_db, \
             patch('main.os.path.exists') as mock_exists, \
             patch('main.os.remove') as mock_remove:
            
            mock_cursor = Mock()
            mock_cursor.rowcount = 5
            mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_exists.return_value = True
            
            response = client.delete("/scan/20241129")
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True
            assert data["deleted_records"] == 5
    
    @patch('main.db_manager')
    def test_backfill_snapshots(self, mock_db, client):
        """스냅샷 백필 테스트"""
        mock_cursor = Mock()
        mock_cursor.statusmessage = "INSERT 0 1"
        mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('main.os.listdir') as mock_listdir, \
             patch('main.open', create=True) as mock_open:
            
            mock_listdir.return_value = ['scan-20241129.json']
            mock_open.return_value.__enter__.return_value.read.return_value = '''
            {
                "as_of": "20241129",
                "rank": [
                    {"ticker": "005930", "name": "삼성전자", "score": 8.5, "score_label": "강세"}
                ]
            }
            '''
            
            response = client.post("/_backfill_snapshots")
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True

class TestDatabaseOperations:
    """데이터베이스 연산 테스트"""
    
    @patch('main.db_manager')
    def test_get_available_scan_dates(self, mock_db):
        """사용 가능한 스캔 날짜 조회 테스트"""
        from main import get_available_scan_dates
        import asyncio
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'date': '2024-11-29'},
            {'date': '2024-11-28'}
        ]
        mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = asyncio.run(get_available_scan_dates())
        assert result["ok"] == True
        assert len(result["dates"]) == 2
    
    @patch('main.db_manager')
    def test_get_scan_by_date(self, mock_db):
        """날짜별 스캔 결과 조회 테스트"""
        from main import get_scan_by_date
        import asyncio
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {
                'code': '005930', 'name': '삼성전자', 'score': 8.5,
                'score_label': '강세', 'close_price': 70000, 'volume': 50000,
                'change_rate': 2.5, 'market': 'KOSPI', 'strategy': '상승추세',
                'indicators': '{}', 'trend': '{}', 'flags': '{}',
                'details': '{}', 'returns': '{}', 'recurrence': '{}'
            }
        ]
        mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('main.calculate_returns') as mock_calc:
            mock_calc.return_value = {
                'current_return': 5.2, 'max_return': 8.1,
                'min_return': -2.3, 'days_elapsed': 5
            }
            
            result = asyncio.run(get_scan_by_date("20241129"))
            assert result["ok"] == True
            assert len(result["data"]["items"]) == 1

class TestReportingAndAnalytics:
    """보고서 및 분석 테스트"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    @patch('main.db_manager')
    def test_quarterly_analysis(self, mock_db, client):
        """분기별 분석 테스트"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {
                'date': '2024-11-29', 'code': '005930', 'name': '삼성전자',
                'current_price': 70000, 'volume': 50000, 'change_rate': 2.5,
                'market': 'KOSPI', 'strategy': '상승추세'
            }
        ]
        mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('main.calculate_returns') as mock_calc:
            mock_calc.return_value = {
                'current_return': 5.2, 'max_return': 8.1,
                'min_return': -2.3, 'days_elapsed': 5
            }
            
            response = client.get("/quarterly-analysis?year=2024&quarter=4")
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True
            assert "data" in data
    
    def test_recurring_stocks(self, client):
        """재등장 종목 분석 테스트"""
        with patch('main.db_manager') as mock_db:
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                {
                    'date': '2024-11-29', 'code': '005930', 'name': '삼성전자',
                    'current_price': 70000, 'change_rate': 2.5
                },
                {
                    'date': '2024-11-28', 'code': '005930', 'name': '삼성전자',
                    'current_price': 68000, 'change_rate': 1.8
                }
            ]
            mock_db.get_cursor.return_value.__enter__.return_value = mock_cursor
            
            response = client.get("/recurring-stocks?days=7&min_appearances=2")
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True
            assert "recurring_stocks" in data["data"]

def run_critical_coverage_tests():
    """핵심 커버리지 테스트 실행"""
    print("🧪 Phase 3 핵심 커버리지 테스트 시작...")
    
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--no-header'
    ])
    
    if exit_code == 0:
        print("✅ Phase 3 핵심 커버리지 테스트 모두 통과!")
    else:
        print("❌ Phase 3 핵심 커버리지 테스트 일부 실패")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_critical_coverage_tests()
    exit(0 if success else 1)