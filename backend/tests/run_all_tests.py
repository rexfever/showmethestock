"""
모든 테스트 실행 스크립트
"""
import unittest
import sys
import os
import time
from io import StringIO

# 테스트 모듈들 import
from test_scanner_core import TestScannerCore
from test_market_analyzer import TestMarketAnalyzer
from test_user_friendly_analysis import TestUserFriendlyAnalysis
from test_new_recurrence_logic import TestNewRecurrenceLogic
from test_api_endpoints import TestAPIEndpoints
from test_integration import TestIntegration

def run_tests():
    """모든 테스트 실행"""
    print("🧪 **테스트 실행 시작**")
    print("=" * 50)
    
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 단위 테스트 추가
    print("📋 **단위 테스트 추가**")
    test_suite.addTest(unittest.makeSuite(TestScannerCore))
    test_suite.addTest(unittest.makeSuite(TestMarketAnalyzer))
    test_suite.addTest(unittest.makeSuite(TestUserFriendlyAnalysis))
    test_suite.addTest(unittest.makeSuite(TestNewRecurrenceLogic))
    
    # API 테스트 추가
    print("🌐 **API 테스트 추가**")
    test_suite.addTest(unittest.makeSuite(TestAPIEndpoints))
    
    # 통합 테스트 추가
    print("🔗 **통합 테스트 추가**")
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    
    # 테스트 실행
    print("\n🚀 **테스트 실행 중...**")
    print("=" * 50)
    
    # 결과를 캡처하기 위한 StringIO 사용
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    
    start_time = time.time()
    result = runner.run(test_suite)
    end_time = time.time()
    
    # 결과 출력
    print(stream.getvalue())
    
    # 요약 출력
    print("\n📊 **테스트 결과 요약**")
    print("=" * 50)
    print(f"⏱️  실행 시간: {end_time - start_time:.2f}초")
    print(f"✅ 성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 실패: {len(result.failures)}")
    print(f"💥 오류: {len(result.errors)}")
    print(f"📈 총 테스트: {result.testsRun}")
    
    if result.failures:
        print("\n❌ **실패한 테스트:**")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 **오류가 발생한 테스트:**")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    # 성공률 계산
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n🎯 **성공률: {success_rate:.1f}%**")
    
    if success_rate >= 90:
        print("🎉 **테스트 결과: 우수!**")
    elif success_rate >= 80:
        print("👍 **테스트 결과: 양호**")
    elif success_rate >= 70:
        print("⚠️ **테스트 결과: 보통**")
    else:
        print("🚨 **테스트 결과: 개선 필요**")
    
    return result.wasSuccessful()

def run_specific_test(test_class):
    """특정 테스트 클래스만 실행"""
    print(f"🧪 **{test_class.__name__} 테스트 실행**")
    print("=" * 50)
    
    test_suite = unittest.makeSuite(test_class)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name == "scanner":
            success = run_specific_test(TestScannerCore)
        elif test_name == "market":
            success = run_specific_test(TestMarketAnalyzer)
        elif test_name == "analysis":
            success = run_specific_test(TestUserFriendlyAnalysis)
        elif test_name == "recurrence":
            success = run_specific_test(TestNewRecurrenceLogic)
        elif test_name == "api":
            success = run_specific_test(TestAPIEndpoints)
        elif test_name == "integration":
            success = run_specific_test(TestIntegration)
        else:
            print(f"❌ 알 수 없는 테스트: {test_name}")
            print("사용 가능한 테스트: scanner, market, analysis, recurrence, api, integration")
            return False
    else:
        success = run_tests()
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
