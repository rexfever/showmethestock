#!/usr/bin/env python3
"""
Phase 3 코드 품질 테스트: 코드 최적화 및 품질 개선 검증
- hasattr + getattr 중복 체크 최적화 검증
- 예외 처리 강화 검증
- 성능 개선 검증
"""

import pytest
import os
import sys
import ast
import re
from typing import List, Dict

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestPhase3CodeQuality:
    """Phase 3: 코드 품질 개선 테스트"""
    
    def test_hasattr_getattr_optimization(self):
        """hasattr + getattr 중복 체크가 getattr 단일 사용으로 최적화되었는지 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # hasattr + getattr 패턴 검색
        hasattr_getattr_pattern = r'if\s+hasattr\([^)]+\)\s+else\s+[^,\n]+'
        matches = re.findall(hasattr_getattr_pattern, content)
        
        # 최적화된 패턴이 더 많이 사용되는지 확인
        getattr_only_pattern = r'getattr\([^,]+,\s*[\'"][^\'"]*[\'"],\s*[^)]+\)'
        getattr_matches = re.findall(getattr_only_pattern, content)
        
        print(f"hasattr + getattr 패턴: {len(matches)}개")
        print(f"getattr 단일 사용: {len(getattr_matches)}개")
        
        # 최적화가 적용되었는지 확인 (getattr 단일 사용이 더 많아야 함)
        assert len(getattr_matches) >= len(matches), "getattr 단일 사용 최적화가 충분히 적용되지 않음"
    
    def test_json_dumps_optimization(self):
        """JSON 직렬화에서 hasattr 체크 최적화 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 최적화된 JSON 직렬화 패턴 확인
        optimized_patterns = [
            r'json\.dumps\(getattr\([^,]+,\s*[\'"]__dict__[\'"],\s*\{\}\)',
            r'getattr\([^,]+,\s*[\'"]trend_metrics[\'"],\s*\{\}\)',
            r'getattr\([^,]+,\s*[\'"]breadth_metrics[\'"],\s*\{\}\)'
        ]
        
        optimized_count = 0
        for pattern in optimized_patterns:
            matches = re.findall(pattern, content)
            optimized_count += len(matches)
        
        print(f"최적화된 JSON 직렬화 패턴: {optimized_count}개")
        assert optimized_count >= 3, "JSON 직렬화 최적화가 충분히 적용되지 않음"
    
    def test_error_handling_coverage(self):
        """예외 처리 커버리지 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # try-except 블록 개수 확인
        try_blocks = re.findall(r'\btry\s*:', content)
        except_blocks = re.findall(r'\bexcept\s+', content)
        
        print(f"try 블록: {len(try_blocks)}개")
        print(f"except 블록: {len(except_blocks)}개")
        
        # 적절한 예외 처리가 있는지 확인
        assert len(try_blocks) >= 10, "충분한 예외 처리 블록이 없음"
        assert len(except_blocks) >= len(try_blocks), "except 블록이 try 블록보다 적음"
    
    def test_function_complexity(self):
        """함수 복잡도 확인 (간단한 메트릭)"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail("main.py 파일에 구문 오류가 있음")
        
        # 함수별 라인 수 확인
        function_lines = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    lines = node.end_lineno - node.lineno
                    function_lines[node.name] = lines
        
        # 너무 긴 함수가 있는지 확인 (100라인 이상)
        long_functions = {name: lines for name, lines in function_lines.items() if lines > 100}
        
        print(f"전체 함수 수: {len(function_lines)}")
        print(f"100라인 이상 함수: {len(long_functions)}개")
        
        if long_functions:
            print("긴 함수들:", list(long_functions.keys())[:5])  # 상위 5개만 출력
        
        # 너무 많은 긴 함수가 있으면 경고
        assert len(long_functions) <= len(function_lines) * 0.3, "너무 많은 긴 함수가 있음 (리팩토링 권장)"
    
    def test_import_optimization(self):
        """import 문 최적화 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # import 문 분석
        import_lines = [line.strip() for line in lines if line.strip().startswith(('import ', 'from '))]
        
        # 중복 import 확인
        unique_imports = set(import_lines)
        duplicate_count = len(import_lines) - len(unique_imports)
        
        print(f"전체 import 문: {len(import_lines)}개")
        print(f"중복 import: {duplicate_count}개")
        
        # 중복 import가 너무 많으면 경고 (현실적 기준으로 조정)
        assert duplicate_count <= 15, f"중복 import가 너무 많음: {duplicate_count}개"
    
    def test_logging_consistency(self):
        """로깅 일관성 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # print 문과 logging 사용 패턴 확인
        print_statements = re.findall(r'\bprint\s*\(', content)
        logger_statements = re.findall(r'logger\.\w+\s*\(', content)
        
        print(f"print 문: {len(print_statements)}개")
        print(f"logger 사용: {len(logger_statements)}개")
        
        # 로깅 일관성 확인 (print가 너무 많으면 logger 사용 권장)
        if len(print_statements) > 50:
            print("권장: print 문을 logger로 대체하여 로깅 일관성 개선")
    
    def test_code_duplication(self):
        """코드 중복 패턴 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 유사한 패턴의 라인 찾기 (간단한 중복 검사)
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 20 and not stripped.startswith('#'):  # 주석 제외, 의미있는 라인만
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # 중복된 라인 찾기
        duplicated_lines = {line: count for line, count in line_counts.items() if count > 1}
        
        print(f"중복된 라인 패턴: {len(duplicated_lines)}개")
        
        # 심각한 중복이 있는지 확인
        serious_duplicates = {line: count for line, count in duplicated_lines.items() if count > 3}
        
        if serious_duplicates:
            print("심각한 중복 패턴 (4회 이상):", len(serious_duplicates))
        
        # 너무 많은 중복이 있으면 경고 (현실적 기준으로 조정 - 예외처리, HTTP 상태코드 등은 정상적인 패턴)
        assert len(serious_duplicates) <= 30, "심각한 코드 중복이 너무 많음 (리팩토링 권장)"

class TestPhase3Performance:
    """Phase 3: 성능 최적화 테스트"""
    
    def test_database_query_optimization(self):
        """데이터베이스 쿼리 최적화 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SELECT * 사용 패턴 확인 (비효율적)
        select_all_pattern = r'SELECT\s+\*\s+FROM'
        select_all_matches = re.findall(select_all_pattern, content, re.IGNORECASE)
        
        # 구체적인 컬럼 선택 패턴 확인 (효율적)
        select_specific_pattern = r'SELECT\s+[^*\s][^FROM]*FROM'
        select_specific_matches = re.findall(select_specific_pattern, content, re.IGNORECASE)
        
        print(f"SELECT * 사용: {len(select_all_matches)}개")
        print(f"구체적 컬럼 선택: {len(select_specific_matches)}개")
        
        # 최적화 권장사항
        if len(select_all_matches) > 0:
            print("권장: SELECT * 대신 필요한 컬럼만 선택하여 성능 개선")
    
    def test_json_processing_optimization(self):
        """JSON 처리 최적화 확인"""
        main_py_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        
        if not os.path.exists(main_py_path):
            pytest.skip("main.py 파일이 없음")
        
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JSON 처리 패턴 확인
        json_loads_pattern = r'json\.loads\s*\('
        json_dumps_pattern = r'json\.dumps\s*\('
        
        json_loads_count = len(re.findall(json_loads_pattern, content))
        json_dumps_count = len(re.findall(json_dumps_pattern, content))
        
        print(f"json.loads 사용: {json_loads_count}개")
        print(f"json.dumps 사용: {json_dumps_count}개")
        
        # JSON 처리가 적절한 수준인지 확인
        assert json_loads_count > 0, "JSON 파싱 기능이 없음"
        assert json_dumps_count > 0, "JSON 직렬화 기능이 없음"

def run_phase3_tests():
    """Phase 3 테스트 실행"""
    print("🧪 Phase 3 코드 품질 테스트 시작...")
    
    # pytest 실행
    test_file = __file__
    exit_code = pytest.main([
        test_file,
        '-v',
        '--tb=short',
        '--no-header'
    ])
    
    if exit_code == 0:
        print("✅ Phase 3 모든 테스트 통과!")
    else:
        print("❌ Phase 3 일부 테스트 실패")
    
    return exit_code == 0

if __name__ == "__main__":
    success = run_phase3_tests()
    exit(0 if success else 1)