"""
v3 홈 API에서 calculate_returns가 호출되지 않는지 검증하는 테스트

목적:
- v3 홈 API (/latest-scan?scanner_version=v3) 호출 시
- calculate_returns가 절대 호출되지 않는지 확인
- 동일한 추천 인스턴스를 연속으로 호출했을 때 current_return이 동일한지 확인
"""

import sys
import os
import time
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import get_latest_scan_from_db


def test_v3_home_no_recalculation():
    """v3 홈에서 calculate_returns가 호출되지 않는지 테스트"""
    print("\n" + "="*80)
    print("v3 홈 API 재계산 방지 검증 테스트")
    print("="*80)
    
    # calculate_returns 호출 여부를 추적
    calculate_returns_called = []
    
    def mock_calculate_returns(*args, **kwargs):
        """calculate_returns 호출을 가로채서 기록"""
        calculate_returns_called.append({
            'args': args,
            'kwargs': kwargs,
            'timestamp': time.time()
        })
        # 실제 함수는 호출하지 않음 (테스트 목적)
        return {
            'current_return': 5.5,
            'current_price': 10000,
            'max_return': 10.0,
            'min_return': -2.0,
            'days_elapsed': 3,
            'scan_price': 9500
        }
    
    # calculate_returns를 모킹
    with patch('main.calculate_returns', side_effect=mock_calculate_returns):
        print("\n[테스트 1] v3 홈 API 호출 (disable_recalculate_returns=True)")
        print("-" * 80)
        
        # 첫 번째 호출
        result1 = get_latest_scan_from_db(scanner_version='v3', disable_recalculate_returns=True)
        
        if not result1.get('ok'):
            print(f"❌ 첫 번째 호출 실패: {result1.get('error')}")
            return False
        
        items1 = result1.get('data', {}).get('items', [])
        print(f"✅ 첫 번째 호출 성공: {len(items1)}개 항목")
        
        # calculate_returns 호출 여부 확인
        if calculate_returns_called:
            print(f"❌ 실패: calculate_returns가 {len(calculate_returns_called)}번 호출됨!")
            for call in calculate_returns_called:
                print(f"   - 호출: {call}")
            return False
        else:
            print("✅ 성공: calculate_returns가 호출되지 않음")
        
        # current_return 값 추출 (첫 번째 호출)
        current_returns_1 = {}
        for item in items1:
            if item.get('ticker') and item.get('ticker') != 'NORESULT':
                ticker = item.get('ticker')
                current_return = item.get('current_return')
                current_returns_1[ticker] = current_return
                print(f"   - {ticker}: current_return={current_return}")
        
        # 잠시 대기 (시간 차이를 두기 위해)
        time.sleep(1)
        
        print("\n[테스트 2] 동일한 v3 홈 API 재호출 (1초 후)")
        print("-" * 80)
        
        # 두 번째 호출 (동일한 조건)
        result2 = get_latest_scan_from_db(scanner_version='v3', disable_recalculate_returns=True)
        
        if not result2.get('ok'):
            print(f"❌ 두 번째 호출 실패: {result2.get('error')}")
            return False
        
        items2 = result2.get('data', {}).get('items', [])
        print(f"✅ 두 번째 호출 성공: {len(items2)}개 항목")
        
        # calculate_returns 호출 여부 확인 (여전히 호출되지 않아야 함)
        if len(calculate_returns_called) > 0:
            print(f"❌ 실패: 두 번째 호출에서 calculate_returns가 추가로 {len(calculate_returns_called)}번 호출됨!")
            return False
        else:
            print("✅ 성공: 두 번째 호출에서도 calculate_returns가 호출되지 않음")
        
        # current_return 값 비교 (두 번째 호출)
        current_returns_2 = {}
        for item in items2:
            if item.get('ticker') and item.get('ticker') != 'NORESULT':
                ticker = item.get('ticker')
                current_return = item.get('current_return')
                current_returns_2[ticker] = current_return
                print(f"   - {ticker}: current_return={current_return}")
        
        # current_return 값이 동일한지 확인
        print("\n[테스트 3] current_return 값 일관성 확인")
        print("-" * 80)
        
        all_match = True
        for ticker in current_returns_1.keys():
            if ticker in current_returns_2:
                val1 = current_returns_1[ticker]
                val2 = current_returns_2[ticker]
                if val1 == val2:
                    print(f"✅ {ticker}: {val1} == {val2} (일치)")
                else:
                    print(f"❌ {ticker}: {val1} != {val2} (불일치!)")
                    all_match = False
        
        if all_match:
            print("\n✅ 모든 테스트 통과!")
            print("   - calculate_returns가 호출되지 않음")
            print("   - current_return 값이 일관성 있게 유지됨")
            return True
        else:
            print("\n❌ 테스트 실패: current_return 값이 일관되지 않음")
            return False


def test_v3_home_vs_other_versions():
    """v3 홈과 다른 버전의 동작 차이 확인"""
    print("\n" + "="*80)
    print("v3 홈 vs 다른 버전 비교 테스트")
    print("="*80)
    
    # v3 홈 (재계산 비활성화)
    print("\n[테스트 A] v3 홈 (disable_recalculate_returns=True)")
    result_v3_home = get_latest_scan_from_db(scanner_version='v3', disable_recalculate_returns=True)
    print(f"   결과: ok={result_v3_home.get('ok')}, items={len(result_v3_home.get('data', {}).get('items', []))}")
    
    # v3 일반 (재계산 활성화 - 다른 용도)
    print("\n[테스트 B] v3 일반 (disable_recalculate_returns=False)")
    result_v3_normal = get_latest_scan_from_db(scanner_version='v3', disable_recalculate_returns=False)
    print(f"   결과: ok={result_v3_normal.get('ok')}, items={len(result_v3_normal.get('data', {}).get('items', []))}")
    
    print("\n✅ 비교 테스트 완료")


if __name__ == '__main__':
    try:
        # 메인 테스트 실행
        success = test_v3_home_no_recalculation()
        
        # 비교 테스트 실행
        test_v3_home_vs_other_versions()
        
        if success:
            print("\n" + "="*80)
            print("✅ 모든 검증 테스트 통과!")
            print("="*80)
            sys.exit(0)
        else:
            print("\n" + "="*80)
            print("❌ 검증 테스트 실패")
            print("="*80)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



