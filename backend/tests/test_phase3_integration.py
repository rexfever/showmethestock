#!/usr/bin/env python3
"""
Phase 3 통합 테스트: 실제 코드 실행 커버리지 확보
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestPhase3Integration:
    """Phase 3: 실제 코드 실행 통합 테스트"""
    
    def test_create_scan_rank_table(self):
        """scan_rank 테이블 생성 함수 테스트"""
        from main import create_scan_rank_table
        
        # Mock cursor 생성
        mock_cursor = Mock()
        
        # 함수 실행
        create_scan_rank_table(mock_cursor)
        
        # execute가 호출되었는지 확인
        assert mock_cursor.execute.call_count >= 1
        
        # 첫 번째 호출에서 CREATE TABLE 문이 포함되었는지 확인
        first_call = mock_cursor.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS scan_rank" in first_call
        assert "scanner_version" in first_call
    
    def test_create_market_conditions_table(self):
        """market_conditions 테이블 생성 함수 테스트"""
        from main import create_market_conditions_table
        
        # Mock cursor 생성
        mock_cursor = Mock()
        
        # 함수 실행
        create_market_conditions_table(mock_cursor)
        
        # execute가 호출되었는지 확인
        assert mock_cursor.execute.call_count >= 1
        
        # CREATE TABLE 문이 포함되었는지 확인
        first_call = mock_cursor.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS market_conditions" in first_call
        assert "scanner_version" in first_call
    
    def test_is_trading_day_function(self):
        """거래일 확인 함수 테스트"""
        from main import is_trading_day
        
        # 평일 테스트 (2024-11-29는 금요일)
        result = is_trading_day("20241129")
        assert isinstance(result, bool)
        
        # 주말 테스트 (2024-11-30은 토요일)
        result = is_trading_day("20241130")
        assert result == False
        
        # 일요일 테스트 (2024-12-01은 일요일)
        result = is_trading_day("20241201")
        assert result == False
    
    def test_save_scan_snapshot_function(self):
        """스캔 스냅샷 저장 함수 테스트"""
        from main import _save_scan_snapshot
        
        # 테스트 데이터
        test_payload = {
            "as_of": "20241129",
            "matched_count": 5,
            "items": [
                {"ticker": "005930", "name": "삼성전자", "score": 8.5}
            ]
        }
        
        # 함수 실행
        result = _save_scan_snapshot(test_payload)
        
        # 결과 확인 (파일 경로가 반환되거나 빈 문자열)
        assert isinstance(result, str)
        
        # 파일이 생성되었다면 정리
        if result and os.path.exists(result):
            os.remove(result)
    
    def test_as_score_flags_function(self):
        """ScoreFlags 변환 함수 테스트"""
        from main import _as_score_flags
        
        # 정상적인 딕셔너리 테스트
        test_flags = {
            "cross": True,
            "vol_expand": False,
            "macd_ok": True,
            "rsi_dema_setup": False,
            "rsi_tema_trigger": True,
            "label": "test_label"
        }
        
        result = _as_score_flags(test_flags)
        
        # 결과 확인
        assert result is not None
        assert result.cross == True
        assert result.vol_expand == False
        assert result.macd_ok == True
        assert result.label == "test_label"
        
        # 잘못된 입력 테스트
        result = _as_score_flags("invalid")
        assert result is None
        
        result = _as_score_flags(None)
        assert result is None
    
    @patch('main.db_manager')
    def test_save_snapshot_db_function(self, mock_db_manager):
        """데이터베이스 스냅샷 저장 함수 테스트"""
        from main import _save_snapshot_db, ScanItem, IndicatorPayload, TrendPayload
        
        # Mock 설정
        mock_cursor = Mock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        # 테스트 데이터
        test_items = [
            ScanItem(
                ticker="005930",
                name="삼성전자",
                match=True,
                score=8.5,
                indicators=IndicatorPayload(
                    TEMA20=2500.0,
                    DEMA10=2480.0,
                    MACD_OSC=10.5,
                    MACD_LINE=15.2,
                    MACD_SIGNAL=12.8,
                    RSI_TEMA=65.0,
                    RSI_DEMA=62.0,
                    OBV=1000000.0,
                    VOL=50000,
                    VOL_MA5=45000.0,
                    close=2500.0,
                    change_rate=2.5
                ),
                trend=TrendPayload(
                    TEMA20_SLOPE20=1.5,
                    OBV_SLOPE20=0.8,
                    ABOVE_CNT5=4,
                    DEMA10_SLOPE20=1.2
                ),
                flags=None,
                score_label="강세",
                strategy="상승 추세"
            )
        ]
        
        # 함수 실행
        _save_snapshot_db("20241129", test_items, scanner_version="v1")
        
        # DB 호출 확인
        assert mock_cursor.execute.called
        assert mock_cursor.executemany.called
    
    @patch('main.api')
    def test_get_cors_origins_function(self, mock_api):
        """CORS origins 설정 함수 테스트"""
        from main import get_cors_origins
        
        # 함수 실행
        origins = get_cors_origins()
        
        # 결과 확인
        assert isinstance(origins, list)
        assert len(origins) > 0
        
        # 로컬 또는 서버 URL이 포함되어 있는지 확인
        has_local = any("localhost" in origin for origin in origins)
        has_server = any("sohntech.ai.kr" in origin for origin in origins)
        assert has_local or has_server
    
    def test_get_status_label_function(self):
        """상태 라벨 생성 함수 테스트"""
        from main import get_status_label
        
        # Mock 데이터
        mock_cur = Mock()
        mock_cur.RSI_TEMA = 75.0  # 과매수
        mock_flags = {"cross": False}
        
        result = get_status_label(mock_cur, mock_flags)
        assert result == "과매수 구간"
        
        # 과매도 테스트
        mock_cur.RSI_TEMA = 25.0
        result = get_status_label(mock_cur, mock_flags)
        assert result == "과매도 구간"
        
        # 상승 신호 테스트
        mock_cur.RSI_TEMA = 55.0
        mock_flags = {"cross": True}
        result = get_status_label(mock_cur, mock_flags)
        assert result == "상승 신호"
    
    def test_get_current_status_description_function(self):
        """현재 상태 설명 생성 함수 테스트"""
        from main import get_current_status_description
        import pandas as pd
        
        # Mock 데이터프레임
        mock_df = pd.DataFrame({
            'RSI_TEMA': [75.0],
            'MACD_OSC': [5.0],
            'volume': [100000],
            'VOL_MA5': [50000]
        })
        
        mock_flags = {}
        
        result = get_current_status_description(mock_df, mock_flags)
        
        # 결과 확인
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('main.httpx.AsyncClient')
    async def test_kakao_callback_error_handling(self, mock_client):
        """카카오 콜백 에러 처리 테스트"""
        from main import kakao_callback
        from fastapi import HTTPException
        
        # 잘못된 요청 테스트
        with pytest.raises(HTTPException) as exc_info:
            await kakao_callback({"invalid": "request"})
        
        assert exc_info.value.status_code == 400
        assert "인증 코드가 없습니다" in str(exc_info.value.detail)

class TestPhase3PerformanceIntegration:
    """Phase 3: 성능 관련 통합 테스트"""
    
    def test_json_serialization_performance(self):
        """JSON 직렬화 성능 테스트"""
        import time
        
        # 큰 데이터 생성
        large_data = {
            f"key_{i}": {
                "nested_data": list(range(100)),
                "string_data": "test" * 50
            } for i in range(100)
        }
        
        # 직렬화 시간 측정
        start_time = time.time()
        json_str = json.dumps(large_data)
        end_time = time.time()
        
        serialization_time = end_time - start_time
        
        # 성능 확인 (1초 이내)
        assert serialization_time < 1.0
        assert len(json_str) > 0
        
        # 역직렬화 테스트
        start_time = time.time()
        parsed_data = json.loads(json_str)
        end_time = time.time()
        
        deserialization_time = end_time - start_time
        assert deserialization_time < 1.0
        assert len(parsed_data) == 100
    
    def test_getattr_optimization_performance(self):
        """getattr 최적화 성능 테스트"""
        import time
        
        class TestObject:
            def __init__(self):
                self.existing_attr = "value"
        
        test_obj = TestObject()
        iterations = 10000
        
        # 최적화된 방식 (getattr with default)
        start_time = time.time()
        for _ in range(iterations):
            value = getattr(test_obj, 'existing_attr', 'default')
            value = getattr(test_obj, 'non_existing_attr', 'default')
        end_time = time.time()
        
        optimized_time = end_time - start_time
        
        # 비최적화 방식 (hasattr + getattr)
        start_time = time.time()
        for _ in range(iterations):
            if hasattr(test_obj, 'existing_attr'):
                value = getattr(test_obj, 'existing_attr')
            else:
                value = 'default'
            
            if hasattr(test_obj, 'non_existing_attr'):
                value = getattr(test_obj, 'non_existing_attr')
            else:
                value = 'default'
        end_time = time.time()
        
        unoptimized_time = end_time - start_time
        
        # 최적화된 방식이 더 빠르거나 비슷해야 함
        assert optimized_time <= unoptimized_time * 1.2  # 20% 여유

def run_phase3_integration_tests():
    """Phase 3 통합 테스트 실행"""
    print("🧪 Phase 3 통합 테스트 시작...")
    
    # pytest 실행
    test_file = __file__
    exit_code = pytest.main([
        test_file,
        '-v',
        '--tb=short',
        '--no-header'
    ])
    
    if exit_code == 0:
        print("✅ Phase 3 통합 테스트 모두 통과!")
    else:
        print("❌ Phase 3 통합 테스트 일부 실패")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_phase3_integration_tests()
    exit(0 if success else 1)