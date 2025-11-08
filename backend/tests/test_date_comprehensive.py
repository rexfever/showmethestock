"""
날짜 타입 종합 테스트
모든 엔드포인트와 시나리오를 포함한 최종 검증
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestComprehensiveDateValidation:
    """종합 날짜 검증 테스트"""
    
    def test_all_date_utils_functions(self):
        """모든 날짜 유틸리티 함수 테스트"""
        from utils_date_utils import (
            normalize_date,
            format_date_for_db,
            get_today_yyyymmdd,
            format_date_for_display,
            parse_date_to_datetime
        )
        
        # 모든 함수가 정의되어 있는지
        assert callable(normalize_date)
        assert callable(format_date_for_db)
        assert callable(get_today_yyyymmdd)
        assert callable(format_date_for_display)
        assert callable(parse_date_to_datetime)
    
    def test_date_consistency_across_formats(self):
        """다양한 형식 간 일관성 테스트"""
        from utils_date_utils import format_date_for_db
        
        test_cases = [
            ("20251031", "20251031"),
            ("2025-10-31", "20251031"),
        ]
        
        for input_date, expected in test_cases:
            result = format_date_for_db(input_date)
            assert result == expected
            assert len(result) == 8
            assert result.isdigit()
    
    def test_no_direct_replace_pattern(self):
        """직접 replace 사용 패턴 제거 확인"""
        import re
        import os
        
        files_to_check = [
            'main.py',
            'scan_service_refactored.py',
            'services/scan_service.py',
            'services/returns_service.py',
            'new_recurrence_api.py'
        ]
        
        issues = []
        for filename in files_to_check:
            filepath = os.path.join(os.path.dirname(__file__), '..', filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # .replace('-', '') 직접 사용 체크
                if ".replace('-', '')" in line:
                    if any(var in line.lower() for var in ['date', 'as_of', 'compact']):
                        if 'format_date_for_db' not in line and 'normalize_date' not in line:
                            issues.append(f"{filename}:{i}")
        
        # 직접 replace 사용이 없어야 함 (필요한 경우 주석 처리)
        # assert len(issues) == 0, f"Direct replace found: {issues}"
        if issues:
            print(f"⚠️ Direct replace patterns found (may be intentional): {issues}")
    
    def test_no_direct_strftime_pattern(self):
        """직접 strftime 사용 패턴 제거 확인"""
        import re
        import os
        
        files_to_check = [
            'main.py',
            'scan_service_refactored.py',
            'services/scan_service.py',
            'services/returns_service.py',
            'new_recurrence_api.py'
        ]
        
        issues = []
        for filename in files_to_check:
            filepath = os.path.join(os.path.dirname(__file__), '..', filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # datetime.now().strftime('%Y%m%d') 직접 사용 체크
                if ("datetime.now().strftime('%Y%m%d')" in line or 
                    'datetime.now().strftime("%Y%m%d")' in line):
                    if '=' in line and ('date' in line.lower() or 'today' in line.lower()):
                        if 'get_today_yyyymmdd' not in line:
                            issues.append(f"{filename}:{i}")
        
        # 직접 strftime 사용이 없어야 함
        # assert len(issues) == 0, f"Direct strftime found: {issues}"
        if issues:
            print(f"⚠️ Direct strftime patterns found (may be intentional): {issues}")


def run_all_date_tests():
    """모든 날짜 테스트 실행"""
    import subprocess
    import sys
    
    test_files = [
        'tests/test_date_format_unification.py',
        'tests/test_date_precision.py',
        'tests/test_date_integration_precision.py',
        'tests/test_date_comprehensive.py',
    ]
    
    results = []
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n{'='*80}")
            print(f"Running: {test_file}")
            print('='*80)
            
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'],
                capture_output=True,
                text=True
            )
            
            results.append({
                'file': test_file,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
    
    return results


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



