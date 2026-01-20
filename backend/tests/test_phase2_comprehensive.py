#!/usr/bin/env python3
"""
Phase 2 종합 테스트: Market Conditions 테이블 확장 검증
- 테이블 스키마 검증
- 버전별 데이터 저장 테스트
- 복합 Primary Key 검증
- 마이그레이션 무결성 테스트
"""

import pytest
import sqlite3
import os
import sys
from datetime import datetime

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def get_test_db_path():
    """테스트용 데이터베이스 경로"""
    return os.path.join(os.path.dirname(__file__), '..', 'snapshots.db')

class TestPhase2MarketConditions:
    """Phase 2: Market Conditions 테이블 확장 테스트"""
    
    def test_market_conditions_table_exists(self):
        """market_conditions 테이블 존재 확인"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='market_conditions'
            """)
            result = cursor.fetchone()
            assert result is not None, "market_conditions 테이블이 존재하지 않음"
    
    def test_scanner_version_column_exists(self):
        """scanner_version 컬럼 존재 확인"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(market_conditions)")
            columns = [col[1] for col in cursor.fetchall()]
            assert 'scanner_version' in columns, "scanner_version 컬럼이 없음"
    
    def test_composite_primary_key(self):
        """복합 Primary Key (date, scanner_version) 확인"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='market_conditions'
            """)
            schema = cursor.fetchone()[0]
            assert 'PRIMARY KEY (date, scanner_version)' in schema, "복합 Primary Key가 설정되지 않음"
    
    def test_table_schema_completeness(self):
        """테이블 스키마 완전성 확인 (26개 컬럼)"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        expected_columns = [
            'date', 'market_sentiment', 'sentiment_score', 'kospi_return', 
            'volatility', 'rsi_threshold', 'sector_rotation', 'foreign_flow',
            'volume_trend', 'min_signals', 'macd_osc_min', 'vol_ma5_mult',
            'gap_max', 'ext_from_tema20_max', 'trend_metrics', 'breadth_metrics',
            'flow_metrics', 'sector_metrics', 'volatility_metrics', 
            'foreign_flow_label', 'volume_trend_label', 'adjusted_params',
            'analysis_notes', 'scanner_version', 'created_at', 'updated_at'
        ]
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(market_conditions)")
            actual_columns = [col[1] for col in cursor.fetchall()]
            
            for col in expected_columns:
                assert col in actual_columns, f"필수 컬럼 {col}이 없음"
            
            assert len(actual_columns) == 26, f"컬럼 수 불일치: 예상 26개, 실제 {len(actual_columns)}개"
    
    def test_version_specific_data_insertion(self):
        """버전별 데이터 삽입 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        test_date = datetime.now().strftime('%Y%m%d')
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # V1 데이터 삽입
            cursor.execute("""
                INSERT OR REPLACE INTO market_conditions 
                (date, market_sentiment, scanner_version)
                VALUES (?, 'bullish', 'v1')
            """, (test_date,))
            
            # V2 데이터 삽입
            cursor.execute("""
                INSERT OR REPLACE INTO market_conditions 
                (date, market_sentiment, scanner_version)
                VALUES (?, 'bearish', 'v2')
            """, (test_date,))
            
            # 데이터 확인
            cursor.execute("""
                SELECT market_sentiment, scanner_version 
                FROM market_conditions 
                WHERE date = ?
                ORDER BY scanner_version
            """, (test_date,))
            
            results = cursor.fetchall()
            assert len(results) == 2, "V1, V2 데이터가 모두 저장되지 않음"
            assert results[0] == ('bullish', 'v1'), "V1 데이터 불일치"
            assert results[1] == ('bearish', 'v2'), "V2 데이터 불일치"
            
            # 테스트 데이터 정리
            cursor.execute("DELETE FROM market_conditions WHERE date = ?", (test_date,))
    
    def test_default_scanner_version(self):
        """기본 scanner_version 값 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        test_date = datetime.now().strftime('%Y%m%d') + '_default'
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # scanner_version 없이 삽입
            cursor.execute("""
                INSERT INTO market_conditions (date, market_sentiment)
                VALUES (?, 'neutral')
            """, (test_date,))
            
            # 기본값 확인
            cursor.execute("""
                SELECT scanner_version FROM market_conditions WHERE date = ?
            """, (test_date,))
            
            result = cursor.fetchone()
            assert result[0] == 'v1', "기본 scanner_version이 'v1'이 아님"
            
            # 테스트 데이터 정리
            cursor.execute("DELETE FROM market_conditions WHERE date = ?", (test_date,))
    
    def test_json_fields_structure(self):
        """JSON 필드 구조 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        json_fields = [
            'trend_metrics', 'breadth_metrics', 'flow_metrics', 
            'sector_metrics', 'volatility_metrics', 'adjusted_params'
        ]
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(market_conditions)")
            columns = cursor.fetchall()
            
            for field in json_fields:
                field_info = next((col for col in columns if col[1] == field), None)
                assert field_info is not None, f"JSON 필드 {field}가 없음"
                # 기본값이 '{}' 또는 "'{}'"인지 확인
                default_value = str(field_info[4]) if field_info[4] else ''
                assert "'{}'" in default_value or '{}' in default_value, f"{field}의 기본값이 빈 JSON 객체가 아님: {default_value}"
    
    def test_timestamp_fields(self):
        """타임스탬프 필드 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(market_conditions)")
            columns = {col[1]: col for col in cursor.fetchall()}
            
            # created_at 필드 확인
            assert 'created_at' in columns, "created_at 컬럼이 없음"
            created_at_info = columns['created_at']
            assert 'CURRENT_TIMESTAMP' in str(created_at_info), "created_at 기본값이 CURRENT_TIMESTAMP가 아님"
            
            # updated_at 필드 확인
            assert 'updated_at' in columns, "updated_at 컬럼이 없음"
            updated_at_info = columns['updated_at']
            assert 'CURRENT_TIMESTAMP' in str(updated_at_info), "updated_at 기본값이 CURRENT_TIMESTAMP가 아님"

class TestPhase2Integration:
    """Phase 2 통합 테스트"""
    
    def test_phase1_and_phase2_compatibility(self):
        """Phase 1과 Phase 2 호환성 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # scan_rank 테이블 확인 (Phase 1)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='scan_rank'
            """)
            scan_rank_exists = cursor.fetchone() is not None
            
            # market_conditions 테이블 확인 (Phase 2)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='market_conditions'
            """)
            market_conditions_exists = cursor.fetchone() is not None
            
            if scan_rank_exists:
                # scan_rank에 scanner_version 컬럼 확인
                cursor.execute("PRAGMA table_info(scan_rank)")
                scan_rank_columns = [col[1] for col in cursor.fetchall()]
                assert 'scanner_version' in scan_rank_columns, "scan_rank에 scanner_version 컬럼이 없음"
            
            if market_conditions_exists:
                # market_conditions에 scanner_version 컬럼 확인
                cursor.execute("PRAGMA table_info(market_conditions)")
                market_conditions_columns = [col[1] for col in cursor.fetchall()]
                assert 'scanner_version' in market_conditions_columns, "market_conditions에 scanner_version 컬럼이 없음"
    
    def test_migration_integrity(self):
        """마이그레이션 무결성 테스트"""
        db_path = get_test_db_path()
        if not os.path.exists(db_path):
            pytest.skip("데이터베이스 파일이 없음")
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 백업 테이블 존재 확인 (있다면)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'market_conditions_backup_%'
            """)
            backup_tables = cursor.fetchall()
            
            # 메인 테이블 무결성 확인
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            assert integrity_result == 'ok', f"데이터베이스 무결성 검사 실패: {integrity_result}"

def run_phase2_tests():
    """Phase 2 테스트 실행"""
    print("🧪 Phase 2 종합 테스트 시작...")
    
    # pytest 실행
    test_file = __file__
    exit_code = pytest.main([
        test_file,
        '-v',
        '--tb=short',
        '--no-header'
    ])
    
    if exit_code == 0:
        print("✅ Phase 2 모든 테스트 통과!")
    else:
        print("❌ Phase 2 일부 테스트 실패")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_phase2_tests()
    exit(0 if success else 1)