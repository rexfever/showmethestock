#!/usr/bin/env python3
"""
Phase 1 Critical Issues 해결 검증 테스트

1. DB 스키마 통일 검증
2. 반환값 통일 검증
3. 스캐너 버전별 구분 저장 검증
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'backend'))

from db_manager import db_manager
from services.scan_service import execute_scan_with_fallback, save_scan_snapshot


class TestPhase1Fixes(unittest.TestCase):
    """Phase 1 수정사항 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_date = "20251122"
        self.test_universe = ["005930", "000660"]  # 삼성전자, SK하이닉스
    
    def test_db_schema_consistency(self):
        """DB 스키마 통일 검증"""
        print("🔍 DB 스키마 통일 검증...")
        
        with db_manager.get_cursor(commit=False) as cur:
            # scan_rank 테이블 스키마 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'scan_rank' 
                ORDER BY ordinal_position
            """)
            scan_rank_columns = cur.fetchall()
            
            # market_conditions 테이블 스키마 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'market_conditions' 
                ORDER BY ordinal_position
            """)
            market_conditions_columns = cur.fetchall()
            
            # scanner_version 컬럼 존재 확인
            scan_rank_has_version = any(col[0] == 'scanner_version' for col in scan_rank_columns)
            market_conditions_has_version = any(col[0] == 'scanner_version' for col in market_conditions_columns)
            
            self.assertTrue(scan_rank_has_version, "scan_rank 테이블에 scanner_version 컬럼이 없습니다")
            self.assertTrue(market_conditions_has_version, "market_conditions 테이블에 scanner_version 컬럼이 없습니다")
            
            # 복합 기본키 확인
            cur.execute("""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'scan_rank' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            scan_rank_pkey = [row[0] for row in cur.fetchall()]
            
            cur.execute("""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'market_conditions' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            market_conditions_pkey = [row[0] for row in cur.fetchall()]
            
            expected_scan_rank_pkey = ['date', 'code', 'scanner_version']
            expected_market_conditions_pkey = ['date', 'scanner_version']
            
            self.assertEqual(scan_rank_pkey, expected_scan_rank_pkey, 
                           f"scan_rank 기본키가 예상과 다릅니다. 예상: {expected_scan_rank_pkey}, 실제: {scan_rank_pkey}")
            self.assertEqual(market_conditions_pkey, expected_market_conditions_pkey,
                           f"market_conditions 기본키가 예상과 다릅니다. 예상: {expected_market_conditions_pkey}, 실제: {market_conditions_pkey}")
            
            print("✅ DB 스키마 통일 검증 완료")
    
    @patch('services.scan_service.scan_with_scanner')
    def test_execute_scan_with_fallback_return_values(self, mock_scan):
        """execute_scan_with_fallback 반환값 통일 검증"""
        print("🔍 반환값 통일 검증...")
        
        # Mock 스캔 결과 설정
        mock_scan.return_value = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "match": True,
                "score": 8.5,
                "indicators": {"close": 70000, "change_rate": 1.5},
                "trend": {"TEMA20_SLOPE20": 0.1},
                "strategy": "상승 추세",
                "flags": {"cross": True},
                "score_label": "강세"
            }
        ]
        
        # Mock 시장 상황
        mock_market_condition = MagicMock()
        mock_market_condition.market_sentiment = "bull"
        mock_market_condition.rsi_threshold = 60
        mock_market_condition.kospi_return = 0.025  # format string 오류 방지
        
        # execute_scan_with_fallback 호출
        result = execute_scan_with_fallback(
            universe=self.test_universe,
            date=self.test_date,
            market_condition=mock_market_condition
        )
        
        # 반환값이 항상 3개인지 확인
        self.assertIsInstance(result, tuple, "반환값이 tuple이 아닙니다")
        self.assertEqual(len(result), 3, f"반환값이 3개가 아닙니다. 실제: {len(result)}개")
        
        items, chosen_step, scanner_version = result
        
        # 각 반환값 타입 검증
        self.assertIsInstance(items, list, "items가 list가 아닙니다")
        self.assertIsInstance(chosen_step, (int, type(None)), "chosen_step이 int 또는 None이 아닙니다")
        self.assertIsInstance(scanner_version, str, "scanner_version이 str이 아닙니다")
        self.assertIn(scanner_version, ['v1', 'v2'], f"scanner_version이 유효하지 않습니다: {scanner_version}")
        
        print(f"✅ 반환값 통일 검증 완료: items={len(items)}개, step={chosen_step}, version={scanner_version}")
    
    def test_save_scan_snapshot_with_version(self):
        """스캐너 버전별 구분 저장 검증"""
        print("🔍 스캐너 버전별 구분 저장 검증...")
        
        # 테스트 데이터
        test_scan_items = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "score": 8.5,
                "score_label": "강세",
                "flags": {"cross": True}
            }
        ]
        
        test_date = "20251122"
        
        # v1 버전으로 저장
        save_scan_snapshot(test_scan_items, test_date, "v1")
        
        # v2 버전으로 저장 (다른 점수)
        test_scan_items_v2 = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "score": 9.2,  # 다른 점수
                "score_label": "매우 강세",
                "flags": {"cross": True}
            }
        ]
        save_scan_snapshot(test_scan_items_v2, test_date, "v2")
        
        # DB에서 버전별로 구분 저장되었는지 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT scanner_version, score, score_label
                FROM scan_rank 
                WHERE date = %s AND code = '005930'
                ORDER BY scanner_version
            """, (test_date,))
            
            results = cur.fetchall()
            
            self.assertEqual(len(results), 2, f"버전별 저장이 안되었습니다. 결과: {len(results)}개")
            
            # v1 버전 확인
            v1_result = next((r for r in results if r[0] == 'v1'), None)
            self.assertIsNotNone(v1_result, "v1 버전 데이터가 없습니다")
            self.assertEqual(v1_result[1], 8.5, f"v1 점수가 다릅니다: {v1_result[1]}")
            
            # v2 버전 확인
            v2_result = next((r for r in results if r[0] == 'v2'), None)
            self.assertIsNotNone(v2_result, "v2 버전 데이터가 없습니다")
            self.assertEqual(v2_result[1], 9.2, f"v2 점수가 다릅니다: {v2_result[1]}")
            
            print(f"✅ 버전별 구분 저장 검증 완료: v1={v1_result[1]}, v2={v2_result[1]}")
    
    def test_market_conditions_version_support(self):
        """market_conditions 테이블 버전별 저장 검증"""
        print("🔍 market_conditions 버전별 저장 검증...")
        
        test_date = "20251122"
        
        # 테스트 데이터 삽입
        with db_manager.get_cursor(commit=True) as cur:
            # v1 버전 시장 상황
            cur.execute("""
                INSERT INTO market_conditions (
                    date, market_sentiment, kospi_return, rsi_threshold, scanner_version
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, scanner_version) DO UPDATE SET
                    market_sentiment = EXCLUDED.market_sentiment,
                    kospi_return = EXCLUDED.kospi_return,
                    rsi_threshold = EXCLUDED.rsi_threshold
            """, (test_date, "bull", 0.025, 60, "v1"))
            
            # v2 버전 시장 상황 (다른 임계값)
            cur.execute("""
                INSERT INTO market_conditions (
                    date, market_sentiment, kospi_return, rsi_threshold, scanner_version
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, scanner_version) DO UPDATE SET
                    market_sentiment = EXCLUDED.market_sentiment,
                    kospi_return = EXCLUDED.kospi_return,
                    rsi_threshold = EXCLUDED.rsi_threshold
            """, (test_date, "bull", 0.025, 65, "v2"))
            
            # 저장된 데이터 확인
            cur.execute("""
                SELECT scanner_version, rsi_threshold
                FROM market_conditions 
                WHERE date = %s
                ORDER BY scanner_version
            """, (test_date,))
            
            results = cur.fetchall()
            
            self.assertEqual(len(results), 2, f"market_conditions 버전별 저장이 안되었습니다. 결과: {len(results)}개")
            
            # v1, v2 버전 확인
            versions = {r[0]: r[1] for r in results}
            self.assertIn('v1', versions, "v1 버전 market_conditions가 없습니다")
            self.assertIn('v2', versions, "v2 버전 market_conditions가 없습니다")
            self.assertEqual(versions['v1'], 60, f"v1 RSI 임계값이 다릅니다: {versions['v1']}")
            self.assertEqual(versions['v2'], 65, f"v2 RSI 임계값이 다릅니다: {versions['v2']}")
            
            print(f"✅ market_conditions 버전별 저장 검증 완료: v1={versions['v1']}, v2={versions['v2']}")
    
    def tearDown(self):
        """테스트 정리"""
        # 테스트 데이터 정리
        try:
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("DELETE FROM scan_rank WHERE date = %s", (self.test_date,))
                cur.execute("DELETE FROM market_conditions WHERE date = %s", (self.test_date,))
        except Exception as e:
            print(f"⚠️ 테스트 데이터 정리 실패: {e}")


def run_tests():
    """테스트 실행"""
    print("🚀 Phase 1 Critical Issues 해결 검증 테스트 시작")
    print("=" * 60)
    
    # 테스트 스위트 생성
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase1Fixes)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ 모든 테스트 통과! Phase 1 Critical Issues 해결 완료")
        return True
    else:
        print(f"❌ 테스트 실패: {len(result.failures)}개 실패, {len(result.errors)}개 오류")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)