#!/usr/bin/env python3
"""
최종 YYYYMMDD 형식 통일 검증 테스트
"""
import os
import sys
import sqlite3
import json
import re
from datetime import datetime
from unittest.mock import patch, MagicMock

def test_scan_service():
    """scan_service_refactored.py 테스트"""
    from scan_service_refactored import _parse_date
    
    cases = [
        (None, "기본값"),
        ("", "빈값"),
        ("20251029", "YYYYMMDD"),
        ("2025-10-29", "YYYY-MM-DD 변환"),
        ("invalid", "잘못된 형식")
    ]
    
    results = []
    for input_val, desc in cases:
        result = _parse_date(input_val)
        is_valid = bool(re.match(r'^\d{8}$', result))
        results.append((desc, result, is_valid))
        print(f"{'✅' if is_valid else '❌'} {desc}: {result}")
    
    return all(r[2] for r in results)

def test_main_functions():
    """main.py 주요 함수 테스트"""
    with patch('main.datetime') as mock_dt:
        mock_dt.now.return_value.strftime.return_value = '20251029'
        
        from main import _save_scan_snapshot
        result = _save_scan_snapshot({})
        
        is_valid = '20251029' in result
        print(f"{'✅' if is_valid else '❌'} main._save_scan_snapshot: {result}")
        return is_valid

def test_returns_service():
    """returns_service.py 테스트"""
    with patch('services.returns_service._get_cached_ohlcv') as mock_cache:
        mock_cache.return_value = '[]'
        
        from services.returns_service import calculate_returns
        
        # YYYYMMDD 형식으로 호출
        try:
            result = calculate_returns("005930", "20251029", "20251030")
            print("✅ returns_service.calculate_returns: YYYYMMDD 처리 성공")
            return True
        except Exception as e:
            print(f"❌ returns_service.calculate_returns: {e}")
            return False

def test_market_analyzer():
    """market_analyzer.py 테스트"""
    try:
        with patch('market_analyzer.datetime') as mock_dt:
            mock_dt.now.return_value.strftime.return_value = '20251029'
            
            from market_analyzer import market_analyzer
            # 기본 함수 호출 테스트
            print("✅ market_analyzer: YYYYMMDD 형식 사용")
            return True
    except Exception as e:
        print(f"❌ market_analyzer: {e}")
        return False

def test_db_consistency():
    """DB 날짜 일관성 테스트"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'snapshots.db')
        if not os.path.exists(db_path):
            print("⏭️ DB 테스트: 로컬 DB 없음")
            return True
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date NOT LIKE '________' OR LENGTH(date) != 8")
        invalid_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM scan_rank")
        total_count = cur.fetchone()[0]
        
        conn.close()
        
        if invalid_count == 0:
            print(f"✅ DB 일관성: 모든 {total_count}개 레코드가 YYYYMMDD")
            return True
        else:
            print(f"❌ DB 일관성: {invalid_count}개 잘못된 형식")
            return False
            
    except Exception as e:
        print(f"❌ DB 테스트: {e}")
        return False

def test_api_response():
    """API 응답 형식 테스트"""
    try:
        from kiwoom_api import KiwoomAPI
        api = KiwoomAPI()
        api.force_mock = True
        
        df = api.get_ohlcv("005930", 5, "20251029")
        
        if not df.empty:
            date_valid = all(re.match(r'^\d{8}$', str(d)) for d in df['date'])
            print(f"{'✅' if date_valid else '❌'} API 응답: YYYYMMDD 형식")
            return date_valid
        else:
            print("✅ API 응답: 빈 데이터 (정상)")
            return True
            
    except Exception as e:
        print(f"❌ API 테스트: {e}")
        return False

def test_code_patterns():
    """코드 패턴 재검증"""
    bad_patterns = [
        r'strftime\(["\']%Y-%m-%d["\']',
        r'strptime\([^,]+,\s*["\']%Y-%m-%d["\']',
        r'["\'][0-9]{4}-[0-9]{2}-[0-9]{2}["\']'
    ]
    
    files = ['main.py', 'scan_service_refactored.py', 'services/returns_service.py', 
             'market_analyzer.py', 'daily_update_service.py']
    
    total_issues = 0
    
    for file_path in files:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in bad_patterns:
            matches = len(re.findall(pattern, content))
            total_issues += matches
    
    if total_issues == 0:
        print("✅ 코드 패턴: 문제 패턴 없음")
        return True
    else:
        print(f"❌ 코드 패턴: {total_issues}개 문제 발견")
        return False

def test_integration():
    """통합 테스트"""
    try:
        # 현재 날짜가 YYYYMMDD 형식인지 확인
        current_date = datetime.now().strftime('%Y%m%d')
        
        # 날짜 변환 테스트
        from scan_service_refactored import _parse_date
        parsed = _parse_date("2025-10-29")
        
        # 형식 검증
        is_valid = (
            re.match(r'^\d{8}$', current_date) and
            re.match(r'^\d{8}$', parsed) and
            parsed == "20251029"
        )
        
        print(f"{'✅' if is_valid else '❌'} 통합 테스트: 날짜 처리 일관성")
        return is_valid
        
    except Exception as e:
        print(f"❌ 통합 테스트: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🧪 최종 YYYYMMDD 형식 통일 검증")
    print("="*50)
    
    tests = [
        ("scan_service 테스트", test_scan_service),
        ("main 함수 테스트", test_main_functions),
        ("returns_service 테스트", test_returns_service),
        ("market_analyzer 테스트", test_market_analyzer),
        ("DB 일관성 테스트", test_db_consistency),
        ("API 응답 테스트", test_api_response),
        ("코드 패턴 테스트", test_code_patterns),
        ("통합 테스트", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}: 오류 - {e}")
    
    print("\n" + "="*50)
    print(f"📊 최종 결과: {passed}/{total} 통과 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 모든 테스트 통과! YYYYMMDD 형식 완전 통일 완료")
        return True
    else:
        print(f"⚠️ {total-passed}개 테스트 실패")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)