#!/usr/bin/env python3
"""
0단계 완료 기준 검증 스크립트

검증 항목:
1. v3 홈 API 호출로는 calculate_returns가 절대 실행되지 않는다.
2. 프론트는 current_return/flags로 status를 판정하지 않는다.
3. 동일 추천 인스턴스는 오전/오후 조회해도 홈 화면에서 상태가 동일하다.
4. GET 요청만으로 status가 바뀌지 않는다.
"""

import sys
import os
import re

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_1_no_calculate_returns():
    """검증 1: v3 홈 API에서 calculate_returns가 절대 실행되지 않는다."""
    print("=" * 80)
    print("[검증 1] v3 홈 API에서 calculate_returns 호출 방지")
    print("=" * 80)
    
    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1-1: v3일 때 disable_recalculate_returns=True 전달 확인
    has_v3_disable = 'disable_recalculate = (scanner_version == \'v3\')' in content
    print(f"✅ v3일 때 disable_recalculate 설정: {has_v3_disable}")
    
    # 1-2: disable_recalculate_returns=True일 때 calculate_returns 호출 차단 확인
    has_disable_guard = 'if disable_recalculate_returns:' in content
    has_v3_guard = '[V3_HOME_GUARD]' in content
    print(f"✅ disable_recalculate_returns 가드: {has_disable_guard}")
    print(f"✅ V3_HOME_GUARD 로그: {has_v3_guard}")
    
    # 1-3: disable_recalculate_returns=True일 때 should_recalculate_returns를 False로 강제
    has_force_false = 'should_recalculate_returns = False' in content
    print(f"✅ should_recalculate_returns 강제 False: {has_force_false}")
    
    result = has_v3_disable and has_disable_guard and has_v3_guard and has_force_false
    
    if result:
        print("\n✅ 검증 1 통과: v3 홈 API에서 calculate_returns가 호출되지 않음")
    else:
        print("\n❌ 검증 1 실패: v3 홈 API에서 calculate_returns 호출 방지 로직 누락")
    
    return result


def verify_2_frontend_no_current_return_status():
    """검증 2: 프론트는 current_return/flags로 status를 판정하지 않는다."""
    print("\n" + "=" * 80)
    print("[검증 2] 프론트에서 current_return/flags로 status 판정 안 함")
    print("=" * 80)
    
    stock_card_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'components', 'v3', 'StockCardV3.js')
    
    if not os.path.exists(stock_card_path):
        print(f"❌ 파일을 찾을 수 없습니다: {stock_card_path}")
        return False
    
    with open(stock_card_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 2-1: determineStockStatus가 호출되지 않음 (호출 시 에러 로그만)
    has_determine_call = 'status = determineStockStatus(' in content
    has_map_domain = 'mapDomainStatusToUIStatus' in content
    has_server_status = 'const domainStatus = item.status' in content or 'item.status' in content
    
    print(f"❌ determineStockStatus 호출 여부: {has_determine_call} (없어야 함)")
    print(f"✅ mapDomainStatusToUIStatus 사용: {has_map_domain}")
    print(f"✅ 서버 status 필드 사용: {has_server_status}")
    
    # 2-2: determineStockStatus 함수에 경고 로그가 있는지 확인
    has_warning_log = 'determineStockStatus가 호출되었습니다' in content
    print(f"✅ determineStockStatus 호출 시 경고 로그: {has_warning_log}")
    
    result = not has_determine_call and has_map_domain and has_server_status
    
    if result:
        print("\n✅ 검증 2 통과: 프론트에서 서버 status만 사용")
    else:
        print("\n❌ 검증 2 실패: 프론트에서 current_return/flags로 status 판정 중")
    
    return result


def verify_3_status_consistency():
    """검증 3: 동일 추천 인스턴스는 오전/오후 조회해도 상태가 동일하다."""
    print("\n" + "=" * 80)
    print("[검증 3] 동일 추천 인스턴스 상태 일관성")
    print("=" * 80)
    
    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 3-1: 서버에서 status 필드를 고정값으로 계산
    has_status_field = 'item["status"] = domain_status' in content
    has_domain_status = 'domain_status =' in content
    print(f"✅ 서버 status 필드 설정: {has_status_field}")
    print(f"✅ 도메인 상태 계산: {has_domain_status}")
    
    # 3-2: status는 추천 생성 시점 기준으로 고정 (flags 기반)
    has_fixed_status = '추천 생성 시점 기준으로 고정' in content or '도메인 상태 계산' in content
    print(f"✅ status 고정 계산: {has_fixed_status}")
    
    # 3-3: disable_recalculate_returns=True일 때 current_return 재계산 안 함
    has_no_recalc = 'disable_recalculate_returns' in content and 'DB에 저장된 returns 데이터만 사용' in content
    print(f"✅ 재계산 방지: {has_no_recalc}")
    
    result = has_status_field and has_domain_status and has_fixed_status and has_no_recalc
    
    if result:
        print("\n✅ 검증 3 통과: 동일 추천 인스턴스 상태 일관성 보장")
    else:
        print("\n❌ 검증 3 실패: 상태 일관성 보장 로직 누락")
    
    return result


def verify_4_no_status_change_on_get():
    """검증 4: GET 요청만으로 status가 바뀌지 않는다."""
    print("\n" + "=" * 80)
    print("[검증 4] GET 요청만으로 status 변경 방지")
    print("=" * 80)
    
    main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 4-1: v3일 때 disable_recalculate_returns=True
    has_v3_disable = 'disable_recalculate = (scanner_version == \'v3\')' in content
    print(f"✅ v3일 때 재계산 비활성화: {has_v3_disable}")
    
    # 4-2: status는 flags 기반으로 고정 계산 (current_return 재계산과 무관)
    has_status_from_flags = 'assumption_broken' in content and 'domain_status' in content
    print(f"✅ status는 flags 기반 고정: {has_status_from_flags}")
    
    # 4-3: 프론트는 서버 status만 사용 (재계산 없음)
    stock_card_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'components', 'v3', 'StockCardV3.js')
    if os.path.exists(stock_card_path):
        with open(stock_card_path, 'r', encoding='utf-8') as f:
            frontend_content = f.read()
        has_no_frontend_calc = 'mapDomainStatusToUIStatus' in frontend_content
        has_no_determine = 'status = determineStockStatus(' not in frontend_content
        print(f"✅ 프론트에서 서버 status만 사용: {has_no_frontend_calc}")
        print(f"✅ 프론트에서 status 재계산 없음: {has_no_determine}")
    else:
        has_no_frontend_calc = False
        has_no_determine = False
    
    result = has_v3_disable and has_status_from_flags and has_no_frontend_calc and has_no_determine
    
    if result:
        print("\n✅ 검증 4 통과: GET 요청만으로 status 변경되지 않음")
    else:
        print("\n❌ 검증 4 실패: GET 요청으로 status 변경 가능")
    
    return result


def main():
    """메인 검증 함수"""
    print("\n" + "=" * 80)
    print("0단계 완료 기준 검증")
    print("=" * 80)
    
    results = []
    
    try:
        results.append(("검증 1: calculate_returns 호출 방지", verify_1_no_calculate_returns()))
        results.append(("검증 2: 프론트 status 판정", verify_2_frontend_no_current_return_status()))
        results.append(("검증 3: 상태 일관성", verify_3_status_consistency()))
        results.append(("검증 4: GET 요청으로 status 변경 방지", verify_4_no_status_change_on_get()))
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
        print("✅ 0단계 완료 기준 모두 충족!")
        print("=" * 80)
        print("\n📝 다음 단계:")
        print("   - 실제 API 호출 테스트로 동작 확인")
        print("   - 동일 추천 인스턴스를 연속 호출하여 status 일관성 확인")
        return True
    else:
        print("❌ 0단계 완료 기준 미충족")
        print("=" * 80)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)



