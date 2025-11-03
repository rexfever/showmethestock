"""보안 유틸리티 함수들"""
import os
import re
from pathlib import Path
from typing import Optional

def sanitize_file_path(file_path: str, base_dir: str) -> Optional[str]:
    """파일 경로를 안전하게 검증하고 정규화"""
    try:
        # 빈 문자열 검사
        if not file_path or not file_path.strip():
            return None
            
        # 위험한 패턴 사전 검사
        dangerous_patterns = ['..', '~', '$', '|', ';', '&']
        if any(pattern in file_path for pattern in dangerous_patterns):
            return None
        
        # Windows/Unix 경로 구분자 통일
        normalized_path = file_path.replace('\\', '/').replace('\\', '/')
        
        # 상대 경로를 절대 경로로 변환
        base_path = Path(base_dir).resolve()
        target_path = (base_path / normalized_path).resolve()
        
        # base_dir 밖으로 나가는지 확인
        if not str(target_path).startswith(str(base_path)):
            return None
            
        return str(target_path)
    except Exception:
        return None

def sanitize_sql_input(input_str: str) -> str:
    """SQL 입력값 기본 검증"""
    if not isinstance(input_str, str):
        return ""
    
    # 기본적인 SQL 인젝션 패턴 제거
    dangerous_patterns = [
        r"[';\"\\]",  # 따옴표, 백슬래시
        r"--",        # SQL 주석
        r"/\*.*?\*/", # 블록 주석
        r"\b(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|ALTER|CREATE)\b",  # SQL 키워드
    ]
    
    result = input_str
    for pattern in dangerous_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    
    return result.strip()

def escape_html(text: str) -> str:
    """HTML 특수문자 이스케이프"""
    if not isinstance(text, str):
        return ""
    
    html_escape_table = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    
    return "".join(html_escape_table.get(c, c) for c in text)