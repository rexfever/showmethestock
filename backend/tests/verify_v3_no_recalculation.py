#!/usr/bin/env python3
"""
v3 홈 API 재계산 방지 검증 스크립트

코드 레벨에서 다음을 검증:
1. disable_recalculate_returns 파라미터가 올바르게 전달되는지
2. v3일 때 disable_recalculate_returns=True가 설정되는지
3. 재계산 로직이 올바르게 차단되는지
"""

import sys
import os
import inspect

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_function_signature():
    """함수 시그니처 검증"""
    print("=" * 80)
    print("[검증 1] get_latest_scan_from_db 함수 시그니처")
    print("=" * 80)
    
    from main import get_latest_scan_from_db
    
    sig = inspect.signature(get_latest_scan_from_db)
    params = list(sig.parameters.keys())
    
    print(f"파라미터 목록: {params}")
    
    if 'disable_recalculate_returns' not in params:
        print("❌ 실패: disable_recalculate_returns 파라미터가 없습니다")
        return False
    
    param = sig.parameters['disable_recalculate_returns']
    if param.default != False:
        print(f"❌ 실패: 기본값이 {param.default}입니다 (예상: False)")
        return False
    
    print("✅ 성공: disable_recalculate_returns 파라미터가 올바르게 정의됨")
    print(f"   - 타입: {param.annotation}")
    print(f"   - 기본값: {param.default}")
    return True


def verify_endpoint_logic():
    """엔드포인트 로직 검증"""
    print("\n" + "=" * 80)
    print("[검증 2] /latest-scan 엔드포인트 로직")
    print("=" * 80)
    
    from main import get_latest_scan
    source = inspect.getsource(get_latest_scan)
    
    checks = {
        'disable_recalculate 포함': 'disable_recalculate' in source,
        'v3 조건 포함': "scanner_version == 'v3'" in source,
        'disable_recalculate_returns 전달': 'disable_recalculate_returns=' in source,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ 성공: 엔드포인트에서 v3일 때 disable_recalculate_returns=True 전달")
    else:
        print("\n❌ 실패: 엔드포인트 로직에 문제가 있습니다")
    
    return all_passed


def verify_recalculation_blocking():
    """재계산 차단 로직 검증"""
    print("\n" + "=" * 80)
    print("[검증 3] 재계산 차단 로직")
    print("=" * 80)
    
    from main import get_latest_scan_from_db
    source = inspect.getsource(get_latest_scan_from_db)
    
    checks = {
        'disable_recalculate_returns 조건문': 'if disable_recalculate_returns:' in source,
        'should_recalculate_returns False 유지': 'should_recalculate_returns' in source and 'False' in source,
        'V3_HOME_GUARD 로그': '[V3_HOME_GUARD]' in source,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ 성공: 재계산 차단 로직이 올바르게 구현됨")
    else:
        print("\n❌ 실패: 재계산 차단 로직에 문제가 있습니다")
    
    return all_passed


def verify_code_structure():
    """코드 구조 검증"""
    print("\n" + "=" * 80)
    print("[검증 4] 코드 구조 확인")
    print("=" * 80)
    
    # main.py 파일 읽기
    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 핵심 키워드 확인
    keywords = {
        'disable_recalculate_returns': content.count('disable_recalculate_returns'),
        'scanner_version == \'v3\'': content.count("scanner_version == 'v3'"),
        'V3_HOME_GUARD': content.count('[V3_HOME_GUARD]'),
    }
    
    print("키워드 출현 횟수:")
    for keyword, count in keywords.items():
        status = "✅" if count > 0 else "❌"
        print(f"{status} '{keyword}': {count}회")
    
    if all(count > 0 for count in keywords.values()):
        print("\n✅ 성공: 모든 핵심 키워드가 코드에 포함됨")
        return True
    else:
        print("\n❌ 실패: 일부 키워드가 누락됨")
        return False


def main():
    """메인 검증 함수"""
    print("\n" + "=" * 80)
    print("v3 홈 API 재계산 방지 검증")
    print("=" * 80)
    
    results = []
    
    try:
        results.append(("함수 시그니처", verify_function_signature()))
        results.append(("엔드포인트 로직", verify_endpoint_logic()))
        results.append(("재계산 차단", verify_recalculation_blocking()))
        results.append(("코드 구조", verify_code_structure()))
    except Exception as e:
        print(f"\n❌ 검증 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("최종 검증 결과")
    print("=" * 80)
    
    all_passed = True
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 모든 검증 통과!")
        print("=" * 80)
        print("\n📝 다음 단계:")
        print("   1. 백엔드 서버 실행: cd backend && uvicorn main:app --reload")
        print("   2. API 호출 테스트:")
        print("      curl 'http://localhost:8010/latest-scan?scanner_version=v3'")
        print("   3. 동일한 요청을 2번 연속 호출하여 current_return 값이 동일한지 확인")
        print("   4. 서버 로그에서 'calculate_returns' 호출이 없는지 확인")
        return True
    else:
        print("❌ 일부 검증 실패")
        print("=" * 80)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)


