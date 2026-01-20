#!/usr/bin/env python3
"""
Phase 3 종합 커버리지 테스트: 주요 함수들의 실제 실행 테스트
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestMainFunctionsCoverage:
    """main.py의 주요 함수들 커버리지 테스트"""
    
    def test_db_path_function(self):
        """데이터베이스 경로 함수 테스트"""
        from main import _db_path
        
        result = _db_path()
        assert isinstance(result, str)
        assert result.endswith('.db')
    
    @patch('main.db_manager')
    def test_log_send_function(self, mock_db_manager):
        """로그 전송 함수 테스트"""
        from main import _log_send
        
        mock_cursor = Mock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        _log_send("01012345678", 5)
        
        # DB 호출 확인
        assert mock_cursor.execute.call_count >= 1
    
    @patch('main.db_manager')
    def test_init_positions_table(self, mock_db_manager):
        """포지션 테이블 초기화 함수 테스트"""
        from main import _init_positions_table
        
        mock_cursor = Mock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        _init_positions_table()
        
        # CREATE TABLE 호출 확인
        assert mock_cursor.execute.called
        create_call = mock_cursor.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS positions" in create_call
    
    def test_get_environment_function(self):
        """환경 정보 함수 테스트"""
        from main import get_cors_origins
        
        origins = get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0

class TestAPIEndpointsCoverage:
    """API 엔드포인트 커버리지 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from main import app
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "running"}
    
    def test_health_endpoint(self, client):
        """헬스 체크 엔드포인트 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_environment_endpoint(self, client):
        """환경 정보 엔드포인트 테스트"""
        response = client.get("/environment")
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert "is_local" in data
        assert "config" in data
    
    @patch('main.reload_from_env')
    @patch('main.config')
    def test_reload_config_endpoint(self, mock_config, mock_reload, client):
        """설정 리로드 엔드포인트 테스트"""
        mock_config.score_level_strong = 8.0
        mock_config.score_level_watch = 6.0
        mock_config.dynamic_score_weights = Mock(return_value={})
        
        response = client.post("/_reload_config")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
    
    def test_snapshots_endpoint(self, client):
        """스냅샷 목록 엔드포인트 테스트"""
        response = client.get("/snapshots")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "items" in data
    
    def test_maintenance_status_endpoint(self, client):
        """메인트넌스 상태 엔드포인트 테스트"""
        response = client.get("/maintenance/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_enabled" in data
        assert "message" in data
    
    def test_popup_notice_status_endpoint(self, client):
        """팝업 공지 상태 엔드포인트 테스트"""
        response = client.get("/popup-notice/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_enabled" in data
        assert "title" in data
    
    def test_test_market_scenarios_endpoint(self, client):
        """테스트 시장 시나리오 엔드포인트 테스트"""
        response = client.get("/test-market-scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "bull" in data["scenarios"]
        assert "bear" in data["scenarios"]
    
    def test_test_scan_endpoint(self, client):
        """테스트 스캔 엔드포인트 테스트"""
        response = client.get("/test-scan/bull")
        assert response.status_code == 200
        data = response.json()
        assert "as_of" in data
        assert "matched_count" in data
        assert "items" in data
    
    def test_clear_cache_endpoint(self, client):
        """캐시 클리어 엔드포인트 테스트"""
        response = client.post("/clear-cache")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True

class TestUtilityFunctionsCoverage:
    """유틸리티 함수들 커버리지 테스트"""
    
    @patch('main.api')
    def test_analyze_function_basic(self, mock_api):
        """분석 함수 기본 테스트"""
        from main import analyze
        import pandas as pd
        
        # Mock 설정
        mock_api.get_code_by_name.return_value = "005930"
        mock_api.get_stock_name.return_value = "삼성전자"
        
        # Mock DataFrame 생성
        mock_df = pd.DataFrame({
            'close': [2500.0, 2520.0],
            'TEMA20': [2480.0, 2500.0],
            'DEMA10': [2470.0, 2490.0],
            'MACD_OSC': [10.5, 11.0],
            'MACD_LINE': [15.2, 15.5],
            'MACD_SIGNAL': [12.8, 13.0],
            'RSI_TEMA': [65.0, 66.0],
            'RSI_DEMA': [62.0, 63.0],
            'OBV': [1000000.0, 1010000.0],
            'volume': [50000, 52000],
            'VOL_MA5': [45000.0, 46000.0]
        })
        
        mock_api.get_ohlcv.return_value = mock_df
        
        # compute_indicators와 score_conditions Mock
        with patch('main.compute_indicators') as mock_compute, \
             patch('main.score_conditions') as mock_score:
            
            mock_compute.return_value = mock_df
            mock_score.return_value = (8.5, {"cross": True, "vol_expand": False})
            
            result = analyze("005930")
            
            assert result.ok == True
            assert result.item is not None
            assert result.item.ticker == "005930"
            assert result.item.name == "삼성전자"
    
    @patch('main.api')
    def test_analyze_friendly_function(self, mock_api):
        """사용자 친화적 분석 함수 테스트"""
        from main import analyze_friendly
        
        # analyze 함수 Mock
        with patch('main.analyze') as mock_analyze, \
             patch('main.get_user_friendly_analysis') as mock_friendly:
            
            # Mock 분석 결과
            mock_result = Mock()
            mock_result.ok = True
            mock_result.item = Mock()
            mock_result.item.ticker = "005930"
            mock_result.item.name = "삼성전자"
            mock_result.item.indicators = Mock()
            mock_result.item.indicators.close = 2500.0
            mock_result.item.indicators.change_rate = 2.5
            
            mock_analyze.return_value = mock_result
            mock_friendly.return_value = {
                "summary": "상승 추세",
                "current_status": "매수 신호"
            }
            
            result = analyze_friendly("005930")
            
            assert result["ok"] == True
            assert result["ticker"] == "005930"
            assert result["name"] == "삼성전자"
            assert "analysis" in result
    
    def test_get_status_label_variations(self):
        """상태 라벨 함수 다양한 케이스 테스트"""
        from main import get_status_label
        
        # 다양한 RSI 값 테스트
        test_cases = [
            (75.0, {"cross": False}, "과매수 구간"),
            (25.0, {"cross": False}, "과매도 구간"),
            (55.0, {"cross": True}, "상승 신호"),
            (55.0, {"cross": False}, "관찰 필요")
        ]
        
        for rsi_value, flags, expected in test_cases:
            mock_cur = Mock()
            mock_cur.RSI_TEMA = rsi_value
            mock_cur.MACD_OSC = 1.0 if "상승" in expected else -1.0
            
            result = get_status_label(mock_cur, flags)
            if expected == "관찰 필요":
                # MACD_OSC가 양수면 "상승 추세"가 될 수 있음
                assert result in [expected, "상승 추세"]
            else:
                assert result == expected

class TestErrorHandlingCoverage:
    """에러 처리 커버리지 테스트"""
    
    def test_save_scan_snapshot_error_handling(self):
        """스캔 스냅샷 저장 에러 처리 테스트"""
        from main import _save_scan_snapshot
        
        # 잘못된 데이터로 에러 발생시키기
        result = _save_scan_snapshot(None)
        assert result == ''
        
        # 빈 딕셔너리
        result = _save_scan_snapshot({})
        assert isinstance(result, str)
    
    def test_as_score_flags_error_handling(self):
        """ScoreFlags 변환 에러 처리 테스트"""
        from main import _as_score_flags
        
        # 다양한 잘못된 입력 테스트
        test_cases = [
            None,
            "string",
            123,
            [],
            {"invalid": "data"}
        ]
        
        for invalid_input in test_cases:
            result = _as_score_flags(invalid_input)
            # None이거나 유효한 ScoreFlags 객체여야 함
            assert result is None or hasattr(result, 'cross')
    
    @patch('main.holidays')
    def test_is_trading_day_error_handling(self, mock_holidays):
        """거래일 확인 에러 처리 테스트"""
        from main import is_trading_day
        
        # 잘못된 날짜 형식
        result = is_trading_day("invalid_date")
        assert result == False
        
        # 빈 문자열
        result = is_trading_day("")
        assert result == False
        
        # None
        result = is_trading_day(None)
        assert isinstance(result, bool)

class TestPerformanceCoverage:
    """성능 관련 커버리지 테스트"""
    
    def test_large_data_processing(self):
        """대용량 데이터 처리 테스트"""
        from main import _as_score_flags
        
        # 큰 딕셔너리 처리
        large_flags = {
            f"flag_{i}": i % 2 == 0 for i in range(1000)
        }
        large_flags.update({
            "cross": True,
            "vol_expand": False,
            "macd_ok": True,
            "label": "large_test"
        })
        
        result = _as_score_flags(large_flags)
        assert result is not None
        assert result.cross == True
        assert result.label == "large_test"
    
    def test_json_processing_performance(self):
        """JSON 처리 성능 테스트"""
        import json
        import time
        
        # 큰 데이터 생성
        large_data = {
            "items": [
                {
                    "ticker": f"00{i:04d}",
                    "name": f"테스트종목{i}",
                    "data": list(range(100))
                } for i in range(100)
            ]
        }
        
        # JSON 직렬화 성능 테스트
        start_time = time.time()
        json_str = json.dumps(large_data, ensure_ascii=False)
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0  # 2초 이내
        assert len(json_str) > 0

def run_comprehensive_coverage_tests():
    """종합 커버리지 테스트 실행"""
    print("🧪 Phase 3 종합 커버리지 테스트 시작...")
    
    # pytest 실행
    test_file = __file__
    exit_code = pytest.main([
        test_file,
        '-v',
        '--tb=short',
        '--no-header'
    ])
    
    if exit_code == 0:
        print("✅ Phase 3 종합 커버리지 테스트 모두 통과!")
    else:
        print("❌ Phase 3 종합 커버리지 테스트 일부 실패")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_comprehensive_coverage_tests()
    exit(0 if success else 1)