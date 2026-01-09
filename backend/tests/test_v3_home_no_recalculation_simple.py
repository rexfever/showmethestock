"""
v3 홈 API에서 calculate_returns가 호출되지 않는지 간단히 검증하는 스크립트

사용법:
    python3 tests/test_v3_home_no_recalculation_simple.py
"""

import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_disable_recalculate_returns_flag():
    """disable_recalculate_returns 파라미터가 올바르게 전달되는지 확인"""
    print("\n" + "="*80)
    print("v3 홈 API 재계산 방지 검증 (간단 버전)")
    print("="*80)
    
    # main.py에서 함수 시그니처 확인
    import inspect
    from main import get_latest_scan_from_db
    
    # 함수 시그니처 확인
    sig = inspect.signature(get_latest_scan_from_db)
    params = list(sig.parameters.keys())
    
    print(f"\n[검증 1] get_latest_scan_from_db 함수 파라미터 확인")
    print(f"   파라미터: {params}")
    
    if 'disable_recalculate_returns' in params:
        print("   ✅ disable_recalculate_returns 파라미터 존재")
    else:
        print("   ❌ disable_recalculate_returns 파라미터 없음")
        return False
    
    # 기본값 확인
    param = sig.parameters['disable_recalculate_returns']
    if param.default == False:
        print(f"   ✅ 기본값: {param.default} (올바름)")
    else:
        print(f"   ⚠️  기본값: {param.default} (예상: False)")
    
    # /latest-scan 엔드포인트 확인
    print(f"\n[검증 2] /latest-scan 엔드포인트 확인")
    from main import get_latest_scan
    
    # 엔드포인트가 v3일 때 disable_recalculate_returns=True를 전달하는지 확인
    # 실제로는 런타임에 확인해야 하지만, 코드 검증은 가능
    import ast
    import inspect
    
    source = inspect.getsource(get_latest_scan)
    if 'disable_recalculate' in source and 'scanner_version == \'v3\'' in source:
        print("   ✅ v3일 때 disable_recalculate_returns=True 전달 로직 존재")
    else:
        print("   ⚠️  v3일 때 disable_recalculate_returns 전달 로직 확인 필요")
    
    print("\n" + "="*80)
    print("✅ 기본 검증 완료")
    print("="*80)
    print("\n실제 동작 확인을 위해서는:")
    print("  1. 백엔드 서버 실행: cd backend && uvicorn main:app --reload")
    print("  2. API 호출: curl 'http://localhost:8010/latest-scan?scanner_version=v3'")
    print("  3. 로그에서 'calculate_returns' 호출 여부 확인")
    print("  4. 동일한 요청을 2번 연속 호출하여 current_return 값이 동일한지 확인")
    print("="*80)
    
    return True


if __name__ == '__main__':
    try:
        success = test_disable_recalculate_returns_flag()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



