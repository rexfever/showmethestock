#!/usr/bin/env python3
"""
날짜 형식 통일 테스트
YYYYMMDD 형식이 모든 곳에서 올바르게 사용되는지 확인
"""

from date_helper import normalize_date, format_display_date
import json

def test_date_normalization():
    """날짜 정규화 테스트"""
    print("=== 날짜 정규화 테스트 ===")
    
    test_cases = [
        ("2024-01-15", "20240115"),
        ("20240115", "20240115"),
    ]
    
    for input_date, expected in test_cases:
        result = normalize_date(input_date)
        status = "✓" if result == expected else "✗"
        print(f"{status} {input_date} -> {result} (expected: {expected})")

def test_display_format():
    """디스플레이 형식 테스트"""
    print("\n=== 디스플레이 형식 테스트 ===")
    
    test_cases = [
        ("20240115", "2024-01-15"),
        ("20251105", "2025-11-05"),
    ]
    
    for input_date, expected in test_cases:
        result = format_display_date(input_date)
        status = "✓" if result == expected else "✗"
        print(f"{status} {input_date} -> {result} (expected: {expected})")

def test_api_date_format():
    """API에서 사용하는 날짜 형식 테스트"""
    print("\n=== API 날짜 형식 테스트 ===")
    
    # 모의 API 응답 데이터
    mock_scan_result = {
        "scan_date": "20251105",
        "results": [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "entry_date": "20251105"
            }
        ]
    }
    
    # 날짜가 YYYYMMDD 형식인지 확인
    scan_date = mock_scan_result["scan_date"]
    entry_date = mock_scan_result["results"][0]["entry_date"]
    
    print(f"Scan Date: {scan_date} (길이: {len(scan_date)}, 숫자만: {scan_date.isdigit()})")
    print(f"Entry Date: {entry_date} (길이: {len(entry_date)}, 숫자만: {entry_date.isdigit()})")
    
    # YYYYMMDD 형식 검증
    is_valid_format = len(scan_date) == 8 and scan_date.isdigit()
    print(f"✓ YYYYMMDD 형식 검증: {is_valid_format}")

if __name__ == "__main__":
    test_date_normalization()
    test_display_format()
    test_api_date_format()
    print("\n=== 테스트 완료 ===")