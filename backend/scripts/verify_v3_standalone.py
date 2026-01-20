#!/usr/bin/env python3
"""
v3 추천 시스템 독립 검증 스크립트
DB 연결 없이 코드 레벨에서 모든 핵심 계약 검증
"""
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def verify_migration_file() -> Tuple[bool, List[str]]:
    """마이그레이션 파일 검증"""
    issues = []
    migration_file = Path("backend/migrations/20251215_create_recommendations_tables_v2.sql")
    
    if not migration_file.exists():
        return False, ["마이그레이션 파일이 존재하지 않습니다"]
    
    sql = migration_file.read_text()
    
    checks = {
        "pgcrypto 확장": (r'CREATE\s+EXTENSION.*pgcrypto', re.I),
        "uuid-ossp 확장": (r'CREATE\s+EXTENSION.*uuid-ossp', re.I),
        "scan_results 테이블": (r'CREATE\s+TABLE.*scan_results', re.I),
        "recommendations 테이블": (r'CREATE\s+TABLE.*recommendations', re.I),
        "recommendation_state_events 테이블": (r'CREATE\s+TABLE.*recommendation_state_events', re.I),
        "REPLACED 상태": (r"'REPLACED'", 0),
        "UUID 기본키": (r'UUID\s+PRIMARY\s+KEY', re.I),
    }
    
    for name, (pattern, flags) in checks.items():
        if not re.search(pattern, sql, flags):
            issues.append(f"{name} 누락")
    
    # Partial unique index 특별 검증
    if 'uniq_active_recommendation_per_ticker' not in sql:
        issues.append("partial unique index (uniq_active_recommendation_per_ticker) 누락")
    else:
        # WHERE 조건이 같은 라인 근처에 있는지 확인
        index_pattern = r'uniq_active_recommendation_per_ticker.*?WHERE\s+status'
        if not re.search(index_pattern, sql, re.I | re.DOTALL):
            issues.append("partial unique index에 WHERE status 조건 누락")
    
    # gen_random_uuid 사용 횟수 확인
    uuid_count = len(re.findall(r'gen_random_uuid\(\)', sql, re.I))
    if uuid_count < 3:
        issues.append(f"gen_random_uuid() 사용 횟수 부족: {uuid_count}회 (최소 3회 필요)")
    
    return len(issues) == 0, issues


def verify_service_code() -> Tuple[bool, List[str]]:
    """recommendation_service_v2.py 검증"""
    issues = []
    service_file = Path("backend/services/recommendation_service_v2.py")
    
    if not service_file.exists():
        return False, ["서비스 파일이 존재하지 않습니다"]
    
    code = service_file.read_text()
    
    checks = {
        "FOR UPDATE 사용 (2회 이상)": code.count('FOR UPDATE') >= 2,
        "create_recommendation_transaction 함수": 'def create_recommendation_transaction' in code,
        "transition_recommendation_status_transaction 함수": 'def transition_recommendation_status_transaction' in code,
        "REPLACED 전환 로직": 'REPLACED' in code and 'replaced_by_recommendation_id' in code,
        "BROKEN->ACTIVE 금지 로직": 'BROKEN' in code and 'ACTIVE' in code and 
                                   re.search(r'BROKEN.*ACTIVE.*false', code, re.I),
        "상태 이벤트 로그": 'recommendation_state_events' in code,
        "UUID 사용": 'uuid.uuid4()' in code or 'gen_random_uuid' in code,
    }
    
    for name, result in checks.items():
        if not result:
            issues.append(f"{name} 누락 또는 불완전")
    
    # 트랜잭션 안전성 검증
    if 'commit=True' not in code:
        issues.append("트랜잭션 커밋 설정 누락")
    
    return len(issues) == 0, issues


def verify_backfill_script() -> Tuple[bool, List[str]]:
    """backfill_recommendations.py 검증"""
    issues = []
    backfill_file = Path("backend/scripts/backfill_recommendations.py")
    
    if not backfill_file.exists():
        return False, ["Backfill 스크립트가 존재하지 않습니다"]
    
    code = backfill_file.read_text()
    
    checks = {
        "create_recommendation_transaction 사용": 'create_recommendation_transaction' in code,
        "recommendation_service_v2 import": 'from services.recommendation_service_v2 import' in code,
        "anchor_date 고정": 'anchor_date' in code,
        "anchor_close 고정": 'anchor_close' in code,
    }
    
    for name, result in checks.items():
        if not result:
            issues.append(f"{name} 누락")
    
    return len(issues) == 0, issues


def verify_sql_queries() -> Tuple[bool, List[str]]:
    """SQL 쿼리 문법 검증"""
    issues = []
    service_file = Path("backend/services/recommendation_service_v2.py")
    
    if not service_file.exists():
        return True, []  # 파일이 없으면 스킵
    
    code = service_file.read_text()
    
    # SQL 쿼리 추출 (triple-quoted strings)
    sql_blocks = re.findall(r'"""(.*?)"""', code, re.DOTALL)
    sql_blocks += re.findall(r"'''(.*?)'''", code, re.DOTALL)
    
    for i, sql in enumerate(sql_blocks):
        sql_upper = sql.upper().strip()
        
        # SELECT 문 검증
        if 'SELECT' in sql_upper and 'FROM' not in sql_upper:
            issues.append(f"SQL 블록 {i+1}: SELECT 문에 FROM 절 없음")
        
        # INSERT 문 검증
        if 'INSERT' in sql_upper:
            if 'VALUES' not in sql_upper and 'SELECT' not in sql_upper:
                issues.append(f"SQL 블록 {i+1}: INSERT 문에 VALUES/SELECT 없음")
        
        # UPDATE 문 검증 (WITH 절이 있는 경우는 제외)
        if 'UPDATE' in sql_upper and 'WITH' not in sql_upper:
            # UPDATE ... SET 패턴 확인
            update_pattern = r'UPDATE\s+\w+\s+SET'
            if not re.search(update_pattern, sql_upper):
                issues.append(f"SQL 블록 {i+1}: UPDATE 문에 SET 절 없음 (또는 WITH 절 포함)")
    
    return len(issues) == 0, issues


def verify_test_files() -> Tuple[bool, List[str]]:
    """테스트 파일 존재 확인"""
    issues = []
    
    test_files = {
        "verify_v3_implementation.py": Path("backend/scripts/verify_v3_implementation.py"),
        "test_v3_constraints.py": Path("backend/tests/test_v3_constraints.py"),
        "verify_v3_complete.sh": Path("backend/scripts/verify_v3_complete.sh"),
    }
    
    for name, path in test_files.items():
        if not path.exists():
            issues.append(f"{name} 파일 없음")
    
    return len(issues) == 0, issues


def main():
    """메인 검증 함수"""
    print("=" * 80)
    print("v3 추천 시스템 종합 검증 (코드 레벨)")
    print("=" * 80)
    
    results = {}
    
    # 1. 마이그레이션 파일 검증
    print("\n[1] 마이그레이션 파일 검증")
    passed, issues = verify_migration_file()
    results["마이그레이션 파일"] = (passed, issues)
    if passed:
        print("  ✅ 통과")
    else:
        print(f"  ❌ 실패 ({len(issues)}개 이슈)")
        for issue in issues:
            print(f"     - {issue}")
    
    # 2. 서비스 코드 검증
    print("\n[2] recommendation_service_v2.py 검증")
    passed, issues = verify_service_code()
    results["서비스 코드"] = (passed, issues)
    if passed:
        print("  ✅ 통과")
    else:
        print(f"  ❌ 실패 ({len(issues)}개 이슈)")
        for issue in issues:
            print(f"     - {issue}")
    
    # 3. Backfill 스크립트 검증
    print("\n[3] backfill_recommendations.py 검증")
    passed, issues = verify_backfill_script()
    results["Backfill 스크립트"] = (passed, issues)
    if passed:
        print("  ✅ 통과")
    else:
        print(f"  ❌ 실패 ({len(issues)}개 이슈)")
        for issue in issues:
            print(f"     - {issue}")
    
    # 4. SQL 쿼리 문법 검증
    print("\n[4] SQL 쿼리 문법 검증")
    passed, issues = verify_sql_queries()
    results["SQL 쿼리"] = (passed, issues)
    if passed:
        print("  ✅ 통과")
    else:
        print(f"  ⚠️  경고 ({len(issues)}개 이슈)")
        for issue in issues[:5]:  # 최대 5개만 표시
            print(f"     - {issue}")
    
    # 5. 테스트 파일 확인
    print("\n[5] 테스트 파일 존재 확인")
    passed, issues = verify_test_files()
    results["테스트 파일"] = (passed, issues)
    if passed:
        print("  ✅ 통과")
    else:
        print(f"  ❌ 실패 ({len(issues)}개 이슈)")
        for issue in issues:
            print(f"     - {issue}")
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("최종 결과")
    print("=" * 80)
    
    all_passed = all(passed for passed, _ in results.values())
    critical_passed = all(
        results[k][0] for k in ["마이그레이션 파일", "서비스 코드", "Backfill 스크립트"]
    )
    
    if all_passed:
        print("✅ 모든 검증 통과")
        return 0
    elif critical_passed:
        print("⚠️  핵심 검증 통과, 일부 경고 있음")
        return 0
    else:
        print("❌ 핵심 검증 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())

