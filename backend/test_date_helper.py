#!/usr/bin/env python3
"""날짜 헬퍼 함수 동작 테스트"""

from date_helper import normalize_date, get_kst_now, format_display_date

def test_date_helper():
    print("=== 날짜 헬퍼 함수 테스트 ===")
    
    # normalize_date 테스트
    print("\n--- normalize_date 테스트 ---")
    test_cases = [
        None,              # 현재 날짜
        "20251103",        # YYYYMMDD
        "2025-11-03",      # YYYY-MM-DD
        "2025/11/03",      # 잘못된 형식
        "invalid",         # 완전히 잘못된 형식
    ]
    
    for case in test_cases:
        try:
            result = normalize_date(case)
            print(f"입력: {case} → 출력: {result}")
        except Exception as e:
            print(f"입력: {case} → 오류: {e}")
    
    # get_kst_now 테스트
    print(f"\n--- KST 현재 시간 ---")
    kst_now = get_kst_now()
    print(f"KST 현재 시간: {kst_now}")
    print(f"YYYYMMDD 형식: {kst_now.strftime('%Y%m%d')}")
    
    # format_display_date 테스트
    print(f"\n--- 표시용 날짜 변환 ---")
    display_cases = ["20251103", "2025-11-03", "invalid"]
    for case in display_cases:
        result = format_display_date(case)
        print(f"{case} → {result}")

if __name__ == "__main__":
    test_date_helper()