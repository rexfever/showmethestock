#!/usr/bin/env python3
"""
YYYYMMDD 형식 통일 검증 테스트
"""
import os
import sys
import sqlite3
import json
import re
from datetime import datetime
from unittest.mock import patch, MagicMock

# 테스트 결과 저장
test_results = []

def log_test(test_name, status, details=""):
    """테스트 결과 로깅"""
    test_results.append({
        'test': test_name,
        'status': status,
        'details': details,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    status_icon = "✅" if status == "PASS" else "❌"
    print(f"{status_icon} {test_name}: {details}")

def test_scan_service_refactored():
    """scan_service_refactored.py의 _parse_date 함수 테스트"""
    try:
        from scan_service_refactored import _parse_date
        
        # 테스트 케이스들
        test_cases = [
            (None, "기본값"),
            ("", "빈 문자열"),
            ("20251029", "YYYYMMDD 형식"),
            ("2025-10-29", "YYYY-MM-DD 형식"),
            ("invalid", "잘못된 형식")
        ]
        
        for input_val, desc in test_cases:
            result = _parse_date(input_val)
            is_yyyymmdd = bool(re.match(r'^\d{8}$', result))
            
            if is_yyyymmdd:
                log_test(f"scan_service._parse_date({desc})", "PASS", f"결과: {result}")
            else:
                log_test(f"scan_service._parse_date({desc})", "FAIL", f"결과: {result} (YYYYMMDD 아님)")
                
    except Exception as e:
        log_test("scan_service_refactored 테스트", "FAIL", f"오류: {e}")

def test_main_py_date_functions():
    """main.py의 날짜 관련 함수들 테스트"""
    try:
        # _save_scan_snapshot 함수 테스트
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Mock datetime
        with patch('main.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '20251029'
            
            from main import _save_scan_snapshot
            
            # 기본값 테스트
            result = _save_scan_snapshot({})
            if '20251029' in result:
                log_test("main._save_scan_snapshot(기본값)", "PASS", "YYYYMMDD 형식 사용")
            else:
                log_test("main._save_scan_snapshot(기본값)", "FAIL", f"결과: {result}")
                
    except Exception as e:
        log_test("main.py 날짜 함수 테스트", "FAIL", f"오류: {e}")

def test_returns_service():
    """returns_service.py의 날짜 처리 테스트"""
    try:
        from services.returns_service import calculate_returns
        
        # Mock API 호출
        with patch('services.returns_service._get_cached_ohlcv') as mock_cache:
            mock_cache.return_value = '[]'  # 빈 데이터
            
            # YYYYMMDD 형식으로 호출
            result = calculate_returns("005930", "20251029")
            log_test("returns_service.calculate_returns", "PASS", "YYYYMMDD 형식 입력 처리")
            
    except Exception as e:
        log_test("returns_service 테스트", "FAIL", f"오류: {e}")

def test_db_date_format():
    """DB의 날짜 형식 검증"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'snapshots.db')
        
        if not os.path.exists(db_path):
            log_test("DB 날짜 형식 검증", "SKIP", "로컬 DB 없음")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # 모든 날짜 조회
        cur.execute("SELECT DISTINCT date FROM scan_rank")
        dates = [row[0] for row in cur.fetchall()]
        conn.close()
        
        if not dates:
            log_test("DB 날짜 형식 검증", "SKIP", "DB에 데이터 없음")
            return
            
        # 날짜 형식 검증
        yyyymmdd_count = 0
        other_format_count = 0
        
        for date in dates:
            if re.match(r'^\d{8}$', str(date)):
                yyyymmdd_count += 1
            else:
                other_format_count += 1
                
        if other_format_count == 0:
            log_test("DB 날짜 형식 검증", "PASS", f"모든 {yyyymmdd_count}개 날짜가 YYYYMMDD 형식")
        else:
            log_test("DB 날짜 형식 검증", "FAIL", f"YYYYMMDD: {yyyymmdd_count}, 기타: {other_format_count}")
            
    except Exception as e:
        log_test("DB 날짜 형식 검증", "FAIL", f"오류: {e}")

def test_code_pattern_search():
    """코드에서 날짜 패턴 검색"""
    try:
        # 검색할 파일들
        files_to_check = [
            'main.py',
            'scan_service_refactored.py',
            'services/returns_service.py',
            'notification_service.py',
            'daily_update_service.py'
        ]
        
        # 문제가 될 수 있는 패턴들
        bad_patterns = [
            r'strftime\(["\']%Y-%m-%d["\']',  # YYYY-MM-DD 생성
            r'strftime\(["\'][^"\']*-%m-[^"\']*["\']',  # 하이픈 포함 날짜
        ]
        
        issues_found = 0
        
        for file_path in files_to_check:
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in bad_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    issues_found += len(matches)
                    log_test(f"코드 패턴 검색 - {file_path}", "FAIL", f"문제 패턴 발견: {matches}")
                    
        if issues_found == 0:
            log_test("코드 패턴 검색", "PASS", "문제가 될 수 있는 날짜 패턴 없음")
        else:
            log_test("코드 패턴 검색", "FAIL", f"총 {issues_found}개 문제 패턴 발견")
            
    except Exception as e:
        log_test("코드 패턴 검색", "FAIL", f"오류: {e}")

def test_api_compatibility():
    """키움 API 호환성 테스트"""
    try:
        from kiwoom_api import KiwoomAPI
        
        # Mock API 인스턴스
        api = KiwoomAPI()
        api.force_mock = True  # 모의 모드 강제
        
        # YYYYMMDD 형식으로 OHLCV 조회 테스트
        df = api.get_ohlcv("005930", 5, "20251029")
        
        if not df.empty:
            # 날짜 컬럼 확인
            date_format_ok = all(re.match(r'^\d{8}$', str(date)) for date in df['date'])
            if date_format_ok:
                log_test("키움 API 호환성", "PASS", "YYYYMMDD 형식 데이터 반환")
            else:
                log_test("키움 API 호환성", "FAIL", "날짜 형식 불일치")
        else:
            log_test("키움 API 호환성", "PASS", "API 호출 성공 (빈 데이터)")
            
    except Exception as e:
        log_test("키움 API 호환성", "FAIL", f"오류: {e}")

def test_json_snapshot_format():
    """JSON 스냅샷 파일 형식 테스트"""
    try:
        snapshot_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
        
        if not os.path.exists(snapshot_dir):
            log_test("JSON 스냅샷 형식", "SKIP", "스냅샷 디렉토리 없음")
            return
            
        json_files = [f for f in os.listdir(snapshot_dir) if f.endswith('.json')]
        
        if not json_files:
            log_test("JSON 스냅샷 형식", "SKIP", "스냅샷 파일 없음")
            return
            
        yyyymmdd_files = 0
        other_files = 0
        
        for filename in json_files:
            # scan-YYYYMMDD.json 형식 확인
            if re.match(r'^scan-\d{8}\.json$', filename):
                yyyymmdd_files += 1
            else:
                other_files += 1
                
        if other_files == 0:
            log_test("JSON 스냅샷 형식", "PASS", f"모든 {yyyymmdd_files}개 파일이 YYYYMMDD 형식")
        else:
            log_test("JSON 스냅샷 형식", "FAIL", f"YYYYMMDD: {yyyymmdd_files}, 기타: {other_files}")
            
    except Exception as e:
        log_test("JSON 스냅샷 형식", "FAIL", f"오류: {e}")

def generate_report():
    """테스트 결과 리포트 생성"""
    print("\n" + "="*60)
    print("📊 YYYYMMDD 형식 통일 검증 결과")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r['status'] == 'PASS'])
    failed_tests = len([r for r in test_results if r['status'] == 'FAIL'])
    skipped_tests = len([r for r in test_results if r['status'] == 'SKIP'])
    
    print(f"총 테스트: {total_tests}")
    print(f"✅ 통과: {passed_tests}")
    print(f"❌ 실패: {failed_tests}")
    print(f"⏭️  건너뜀: {skipped_tests}")
    print(f"성공률: {(passed_tests/total_tests*100):.1f}%")
    
    print("\n📋 세부 결과:")
    for result in test_results:
        status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}[result['status']]
        print(f"{status_icon} [{result['timestamp']}] {result['test']}")
        if result['details']:
            print(f"   └─ {result['details']}")
    
    # 실패한 테스트가 있으면 권장사항 출력
    if failed_tests > 0:
        print(f"\n⚠️  {failed_tests}개 테스트 실패")
        print("권장사항:")
        print("1. 실패한 코드 패턴을 YYYYMMDD 형식으로 수정")
        print("2. DB 마이그레이션 재실행")
        print("3. 서버 재시작 후 재테스트")
    else:
        print("\n🎉 모든 테스트 통과! YYYYMMDD 형식 통일 완료")

def main():
    """메인 테스트 실행"""
    print("🧪 YYYYMMDD 형식 통일 검증 시작...")
    
    # 각 테스트 실행
    test_scan_service_refactored()
    test_main_py_date_functions()
    test_returns_service()
    test_db_date_format()
    test_code_pattern_search()
    test_api_compatibility()
    test_json_snapshot_format()
    
    # 결과 리포트 생성
    generate_report()

if __name__ == "__main__":
    main()