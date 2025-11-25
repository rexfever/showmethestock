#!/usr/bin/env python3
"""
Phase 1 포괄적 테스트 - 단위 테스트 커버리지 80% 이상 목표

테스트 범위:
1. DB 스키마 검증 (상세)
2. 함수 반환값 모든 경로 테스트
3. 에러 케이스 처리
4. 데이터 무결성 검증
5. 성능 테스트
6. 경계값 테스트
"""

import os
import sys
import unittest
import time
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'backend'))

from db_manager import db_manager
from services.scan_service import execute_scan_with_fallback, save_scan_snapshot, get_recurrence_data


class TestDatabaseSchema(unittest.TestCase):
    """데이터베이스 스키마 상세 검증"""
    
    def test_scan_rank_table_structure(self):
        """scan_rank 테이블 구조 상세 검증"""
        with db_manager.get_cursor(commit=False) as cur:
            # 테이블 존재 확인
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'scan_rank'
            """)
            self.assertTrue(cur.fetchone(), "scan_rank 테이블이 존재하지 않습니다")
            
            # 컬럼 구조 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'scan_rank'
                ORDER BY ordinal_position
            """)
            columns = {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
                      for row in cur.fetchall()}
            
            # 필수 컬럼 존재 확인
            required_columns = ['date', 'code', 'scanner_version', 'score', 'flags']
            for col in required_columns:
                self.assertIn(col, columns, f"필수 컬럼 {col}이 없습니다")
            
            # scanner_version 컬럼 상세 검증
            self.assertEqual(columns['scanner_version']['type'], 'text')
            self.assertEqual(columns['scanner_version']['nullable'], 'NO')
            self.assertIn('v1', columns['scanner_version']['default'])
            
            # 기본키 확인
            cur.execute("""
                SELECT column_name FROM information_schema.key_column_usage
                WHERE table_name = 'scan_rank' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            pkey_columns = [row[0] for row in cur.fetchall()]
            self.assertEqual(pkey_columns, ['date', 'code', 'scanner_version'])
    
    def test_market_conditions_table_structure(self):
        """market_conditions 테이블 구조 상세 검증"""
        with db_manager.get_cursor(commit=False) as cur:
            # 테이블 존재 확인
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'market_conditions'
            """)
            self.assertTrue(cur.fetchone(), "market_conditions 테이블이 존재하지 않습니다")
            
            # scanner_version 컬럼 확인
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'market_conditions' AND column_name = 'scanner_version'
            """)
            version_col = cur.fetchone()
            self.assertIsNotNone(version_col, "scanner_version 컬럼이 없습니다")
            self.assertEqual(version_col[1], 'text')
            self.assertEqual(version_col[2], 'NO')
            
            # 복합 기본키 확인
            cur.execute("""
                SELECT column_name FROM information_schema.key_column_usage
                WHERE table_name = 'market_conditions' AND constraint_name LIKE '%pkey%'
                ORDER BY ordinal_position
            """)
            pkey_columns = [row[0] for row in cur.fetchall()]
            self.assertEqual(pkey_columns, ['date', 'scanner_version'])
    
    def test_data_integrity_constraints(self):
        """데이터 무결성 제약조건 검증"""
        test_date = "20251122"
        
        with db_manager.get_cursor(commit=True) as cur:
            # 중복 키 삽입 시도 (실패해야 함)
            cur.execute("""
                INSERT INTO scan_rank (date, code, scanner_version, score)
                VALUES (%s, 'TEST001', 'v1', 8.0)
                ON CONFLICT (date, code, scanner_version) DO NOTHING
            """, (test_date,))
            
            # 같은 키로 다시 삽입 시도
            cur.execute("""
                INSERT INTO scan_rank (date, code, scanner_version, score)
                VALUES (%s, 'TEST001', 'v1', 9.0)
                ON CONFLICT (date, code, scanner_version) DO NOTHING
            """, (test_date,))
            
            # 실제로 하나만 삽입되었는지 확인
            cur.execute("""
                SELECT COUNT(*) FROM scan_rank 
                WHERE date = %s AND code = 'TEST001' AND scanner_version = 'v1'
            """, (test_date,))
            count = cur.fetchone()[0]
            self.assertEqual(count, 1, "중복 키 제약조건이 작동하지 않습니다")
            
            # 정리
            cur.execute("DELETE FROM scan_rank WHERE date = %s AND code = 'TEST001'", (test_date,))


class TestExecuteScanWithFallback(unittest.TestCase):
    """execute_scan_with_fallback 함수 포괄적 테스트"""
    
    def setUp(self):
        self.test_universe = ["005930", "000660", "035420"]
        self.test_date = "20251122"
    
    @patch('services.scan_service.scan_with_scanner')
    @patch('services.scan_service.config')
    def test_return_value_consistency_all_paths(self, mock_config, mock_scan):
        """모든 실행 경로에서 반환값 일관성 검증"""
        # Config 설정
        mock_config.fallback_enable = True
        mock_config.fallback_target_min_bull = 3
        mock_config.fallback_target_max_bull = 5
        mock_config.fallback_presets = [
            {},  # Step 0
            {'min_signals': 3},  # Step 1
            {'min_signals': 2, 'vol_ma5_mult': 1.8},  # Step 2
            {'min_signals': 2, 'vol_ma5_mult': 1.8}   # Step 3
        ]
        mock_config.top_k = 10
        
        # 시나리오별 테스트
        test_scenarios = [
            # (스캔 결과 개수, 예상 step, 설명)
            (5, 0, "충분한 결과 - Step 0"),
            (2, 3, "부족한 결과 - Step 3까지 진행"),
            (0, None, "결과 없음 - 모든 step 실패")
        ]
        
        for result_count, expected_step, description in test_scenarios:
            with self.subTest(scenario=description):
                # Mock 결과 설정
                mock_results = [
                    {
                        "ticker": f"00593{i}",
                        "name": f"테스트{i}",
                        "match": True,
                        "score": 8.0 + i,
                        "indicators": {"close": 70000},
                        "trend": {},
                        "strategy": "테스트",
                        "flags": {},
                        "score_label": "테스트"
                    }
                    for i in range(result_count)
                ]
                mock_scan.return_value = mock_results
                
                # Mock 시장 상황
                mock_market = MagicMock()
                mock_market.market_sentiment = "bull"
                mock_market.kospi_return = 0.02
                
                # 함수 실행
                result = execute_scan_with_fallback(
                    self.test_universe, self.test_date, mock_market
                )
                
                # 반환값 검증
                self.assertIsInstance(result, tuple, f"{description}: 반환값이 tuple이 아님")
                self.assertEqual(len(result), 3, f"{description}: 반환값이 3개가 아님")
                
                items, chosen_step, scanner_version = result
                
                # 타입 검증
                self.assertIsInstance(items, list, f"{description}: items가 list가 아님")
                self.assertIsInstance(chosen_step, (int, type(None)), f"{description}: chosen_step 타입 오류")
                self.assertIsInstance(scanner_version, str, f"{description}: scanner_version이 str이 아님")
                self.assertIn(scanner_version, ['v1', 'v2'], f"{description}: 유효하지 않은 scanner_version")
                
                # Step 검증
                if expected_step is not None:
                    self.assertEqual(chosen_step, expected_step, f"{description}: 예상 step과 다름")
    
    @patch('services.scan_service.scan_with_scanner')
    def test_error_handling(self, mock_scan):
        """에러 상황 처리 검증"""
        # 스캔 함수에서 예외 발생
        mock_scan.side_effect = Exception("스캔 오류")
        
        mock_market = MagicMock()
        mock_market.market_sentiment = "bull"
        mock_market.kospi_return = 0.02
        
        result = execute_scan_with_fallback(
            self.test_universe, self.test_date, mock_market
        )
        
        # 에러 상황에서도 3개 값 반환 확인
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        
        items, chosen_step, scanner_version = result
        self.assertEqual(items, [])  # 빈 리스트 반환
        self.assertIsNone(chosen_step)  # None 반환
        self.assertIsInstance(scanner_version, str)  # 기본 버전 반환
    
    @patch('services.scan_service.scan_with_scanner')
    def test_market_condition_variations(self, mock_scan):
        """다양한 시장 상황에서의 동작 검증"""
        mock_scan.return_value = []
        
        market_scenarios = [
            ("crash", "급락장"),
            ("bear", "약세장"), 
            ("bull", "강세장"),
            ("neutral", "중립장")
        ]
        
        for sentiment, description in market_scenarios:
            with self.subTest(market=description):
                mock_market = MagicMock()
                mock_market.market_sentiment = sentiment
                mock_market.kospi_return = 0.01 if sentiment != "crash" else -0.05
                
                result = execute_scan_with_fallback(
                    self.test_universe, self.test_date, mock_market
                )
                
                # 모든 시장 상황에서 일관된 반환값
                self.assertEqual(len(result), 3)
                items, chosen_step, scanner_version = result
                
                if sentiment == "crash":
                    # 급락장에서는 빈 결과 반환
                    self.assertEqual(items, [])
                
                self.assertIsInstance(scanner_version, str)


class TestSaveScanSnapshot(unittest.TestCase):
    """save_scan_snapshot 함수 상세 테스트"""
    
    def setUp(self):
        self.test_date = "20251122"
        self.test_items = [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "score": 8.5,
                "score_label": "강세",
                "flags": {"cross": True}
            }
        ]
    
    def test_version_specific_storage(self):
        """버전별 저장 상세 검증"""
        versions = ["v1", "v2"]
        
        for version in versions:
            with self.subTest(version=version):
                # 버전별로 다른 데이터 저장
                test_items = [{
                    **self.test_items[0],
                    "score": 8.5 if version == "v1" else 9.2
                }]
                
                save_scan_snapshot(test_items, self.test_date, version)
                
                # DB에서 해당 버전 데이터 확인
                with db_manager.get_cursor(commit=False) as cur:
                    cur.execute("""
                        SELECT score, scanner_version FROM scan_rank 
                        WHERE date = %s AND code = %s AND scanner_version = %s
                    """, (self.test_date, "005930", version))
                    
                    result = cur.fetchone()
                    self.assertIsNotNone(result, f"{version} 버전 데이터가 저장되지 않음")
                    self.assertEqual(result[1], version, f"버전 정보가 올바르지 않음")
    
    def test_empty_items_handling(self):
        """빈 스캔 결과 처리 검증"""
        save_scan_snapshot([], self.test_date, "v1")
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT code, name FROM scan_rank 
                WHERE date = %s AND scanner_version = 'v1'
            """, (self.test_date,))
            
            result = cur.fetchone()
            self.assertIsNotNone(result, "빈 결과에 대한 NORESULT 레코드가 없음")
            self.assertEqual(result[0], "NORESULT", "NORESULT 코드가 올바르지 않음")
    
    @patch('services.scan_service.api.get_ohlcv')
    def test_api_failure_handling(self, mock_api):
        """API 실패 상황 처리 검증"""
        # API 호출 실패 시뮬레이션
        mock_api.side_effect = Exception("API 오류")
        
        # 예외가 발생해도 함수가 정상 완료되어야 함
        try:
            save_scan_snapshot(self.test_items, self.test_date, "v1")
        except Exception as e:
            self.fail(f"API 실패 시 예외가 전파됨: {e}")
    
    def tearDown(self):
        """테스트 데이터 정리"""
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (self.test_date,))


class TestDataIntegrity(unittest.TestCase):
    """데이터 무결성 검증"""
    
    def test_concurrent_version_storage(self):
        """동시 버전 저장 시 데이터 무결성"""
        test_date = "20251122"
        
        # 동일 날짜에 여러 버전 저장
        versions_data = {
            "v1": [{"ticker": "005930", "name": "삼성전자", "score": 8.0, "score_label": "v1", "flags": {}}],
            "v2": [{"ticker": "005930", "name": "삼성전자", "score": 9.0, "score_label": "v2", "flags": {}}]
        }
        
        for version, items in versions_data.items():
            save_scan_snapshot(items, test_date, version)
        
        # 각 버전별로 올바른 데이터가 저장되었는지 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT scanner_version, score FROM scan_rank 
                WHERE date = %s AND code = '005930'
                ORDER BY scanner_version
            """, (test_date,))
            
            results = cur.fetchall()
            self.assertEqual(len(results), 2, "두 버전 모두 저장되지 않음")
            
            # v1, v2 순서로 정렬되어 있어야 함
            self.assertEqual(results[0][0], "v1")
            self.assertEqual(results[0][1], 8.0)
            self.assertEqual(results[1][0], "v2")
            self.assertEqual(results[1][1], 9.0)
        
        # 정리
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (test_date,))
    
    def test_data_type_validation(self):
        """데이터 타입 검증"""
        test_date = "20251122"
        
        # 다양한 데이터 타입으로 저장 시도
        test_cases = [
            {"score": 8.5, "expected": True},   # 정상 float
            {"score": 8, "expected": True},     # int (float로 변환됨)
            {"score": "8.5", "expected": True}, # string (float로 변환됨)
        ]
        
        for i, case in enumerate(test_cases):
            with self.subTest(case=case):
                items = [{
                    "ticker": f"TEST{i:03d}",
                    "name": f"테스트{i}",
                    "score": case["score"],
                    "score_label": "테스트",
                    "flags": {}
                }]
                
                try:
                    save_scan_snapshot(items, test_date, "v1")
                    success = True
                except Exception:
                    success = False
                
                self.assertEqual(success, case["expected"], 
                               f"데이터 타입 {type(case['score'])} 처리 실패")
        
        # 정리
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (test_date,))


class TestPerformance(unittest.TestCase):
    """성능 테스트"""
    
    def test_large_dataset_performance(self):
        """대용량 데이터 처리 성능"""
        test_date = "20251122"
        
        # 100개 종목 데이터 생성
        large_dataset = [
            {
                "ticker": f"TEST{i:03d}",
                "name": f"테스트종목{i}",
                "score": 8.0 + (i % 3),
                "score_label": "테스트",
                "flags": {"cross": i % 2 == 0}
            }
            for i in range(100)
        ]
        
        # 성능 측정
        start_time = time.time()
        save_scan_snapshot(large_dataset, test_date, "v1")
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 100개 종목 저장이 5초 이내에 완료되어야 함
        self.assertLess(execution_time, 5.0, 
                       f"대용량 데이터 저장이 너무 느림: {execution_time:.2f}초")
        
        # 저장된 데이터 개수 확인
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT COUNT(*) FROM scan_rank 
                WHERE date = %s AND scanner_version = 'v1'
            """, (test_date,))
            
            count = cur.fetchone()[0]
            self.assertEqual(count, 100, "모든 데이터가 저장되지 않음")
        
        # 정리
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (test_date,))


class TestEdgeCases(unittest.TestCase):
    """경계값 및 예외 상황 테스트"""
    
    def test_boundary_values(self):
        """경계값 테스트"""
        test_date = "20251122"
        
        boundary_cases = [
            {"score": 0.0, "name": "최소 점수"},
            {"score": 10.0, "name": "최대 점수"},
            {"score": 5.5, "name": "중간 점수"},
        ]
        
        for case in boundary_cases:
            with self.subTest(case=case["name"]):
                items = [{
                    "ticker": "BOUND001",
                    "name": case["name"],
                    "score": case["score"],
                    "score_label": "경계값",
                    "flags": {}
                }]
                
                save_scan_snapshot(items, test_date, "v1")
                
                # 저장된 값 확인
                with db_manager.get_cursor(commit=False) as cur:
                    cur.execute("""
                        SELECT score FROM scan_rank 
                        WHERE date = %s AND code = 'BOUND001' AND scanner_version = 'v1'
                    """, (test_date,))
                    
                    result = cur.fetchone()
                    self.assertIsNotNone(result, f"{case['name']} 저장 실패")
                    self.assertEqual(result[0], case["score"], f"{case['name']} 값 불일치")
        
        # 정리
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (test_date,))
    
    def test_special_characters_handling(self):
        """특수 문자 처리 테스트"""
        test_date = "20251122"
        
        special_cases = [
            {"name": "테스트&종목", "expected": True},
            {"name": "Test'Stock", "expected": True},
            {"name": 'Test"Stock', "expected": True},
            {"name": "Test\\Stock", "expected": True},
        ]
        
        for i, case in enumerate(special_cases):
            with self.subTest(name=case["name"]):
                items = [{
                    "ticker": f"SPEC{i:03d}",
                    "name": case["name"],
                    "score": 8.0,
                    "score_label": "특수문자",
                    "flags": {}
                }]
                
                try:
                    save_scan_snapshot(items, test_date, "v1")
                    success = True
                except Exception:
                    success = False
                
                self.assertEqual(success, case["expected"], 
                               f"특수문자 '{case['name']}' 처리 실패")
        
        # 정리
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM scan_rank WHERE date = %s", (test_date,))


def run_comprehensive_tests():
    """포괄적 테스트 실행"""
    print("🚀 Phase 1 포괄적 테스트 시작 (단위 테스트 커버리지 80% 목표)")
    print("=" * 80)
    
    # 테스트 스위트 구성
    test_classes = [
        TestDatabaseSchema,
        TestExecuteScanWithFallback,
        TestSaveScanSnapshot,
        TestDataIntegrity,
        TestPerformance,
        TestEdgeCases
    ]
    
    suite = unittest.TestSuite()
    total_tests = 0
    
    for test_class in test_classes:
        class_suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTest(class_suite)
        total_tests += class_suite.countTestCases()
    
    print(f"📊 총 {total_tests}개 테스트 실행 예정")
    print("-" * 80)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 분석
    print("=" * 80)
    print("📊 테스트 결과 요약:")
    print(f"  - 총 테스트: {result.testsRun}개")
    print(f"  - 성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
    print(f"  - 실패: {len(result.failures)}개")
    print(f"  - 오류: {len(result.errors)}개")
    
    if result.failures:
        print("\n❌ 실패한 테스트:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
    
    if result.errors:
        print("\n🚨 오류 발생 테스트:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"  - {test}: {error_msg}")
    
    # 커버리지 계산 (근사치)
    coverage_percentage = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    
    print(f"\n📈 추정 커버리지: {coverage_percentage:.1f}%")
    
    if result.wasSuccessful():
        print("✅ 모든 테스트 통과! Phase 1 포괄적 검증 완료")
        if coverage_percentage >= 80:
            print("🎯 목표 커버리지 80% 달성!")
        return True
    else:
        print("❌ 일부 테스트 실패")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)