"""
코드 리뷰 수정 사항 테스트 실행 스크립트
"""
import unittest
import sys
import os

# 테스트 모듈 import
from test_code_review_fixes import (
    TestArraySafety,
    TestDataChangesSafety,
    TestReverseMappingSafety,
    TestTypeSafety,
    TestErrorHandling
)
from test_trend_apply_api import (
    TestTrendApplyAPI,
    TestEnvFileEdgeCases
)
from test_trend_adaptive_scanner import (
    TestTrendAdaptiveScanner,
    TestPerformanceMetrics
)


def run_code_review_tests():
    """코드 리뷰 수정 사항 테스트 실행"""
    print("=" * 80)
    print("🧪 코드 리뷰 수정 사항 테스트 실행")
    print("=" * 80)
    
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    print("\n📋 테스트 클래스 추가 중...")
    
    # 코드 리뷰 수정 사항 테스트
    print("  - TestArraySafety: 배열 안전성 테스트")
    test_suite.addTest(unittest.makeSuite(TestArraySafety))
    
    print("  - TestDataChangesSafety: data.changes 안전성 테스트")
    test_suite.addTest(unittest.makeSuite(TestDataChangesSafety))
    
    print("  - TestReverseMappingSafety: 역매핑 안전성 테스트")
    test_suite.addTest(unittest.makeSuite(TestReverseMappingSafety))
    
    print("  - TestTypeSafety: 타입 안전성 테스트")
    test_suite.addTest(unittest.makeSuite(TestTypeSafety))
    
    print("  - TestErrorHandling: 에러 처리 테스트")
    test_suite.addTest(unittest.makeSuite(TestErrorHandling))
    
    # .env 파일 파싱 테스트
    print("  - TestTrendApplyAPI: .env 파일 파싱 및 업데이트 테스트")
    test_suite.addTest(unittest.makeSuite(TestTrendApplyAPI))
    
    print("  - TestEnvFileEdgeCases: .env 파일 엣지 케이스 테스트")
    test_suite.addTest(unittest.makeSuite(TestEnvFileEdgeCases))
    
    # 추세 적응 스캐너 테스트
    print("  - TestPerformanceMetrics: PerformanceMetrics 데이터클래스 테스트")
    test_suite.addTest(unittest.makeSuite(TestPerformanceMetrics))
    
    print("  - TestTrendAdaptiveScanner: 추세 적응 스캐너 테스트")
    test_suite.addTest(unittest.makeSuite(TestTrendAdaptiveScanner))
    
    # 테스트 실행
    print("\n🚀 테스트 실행 중...")
    print("=" * 80)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    print(f"✅ 성공: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    print(f"❌ 실패: {len(result.failures)}")
    print(f"💥 오류: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n💥 오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_code_review_tests()
    sys.exit(0 if success else 1)


