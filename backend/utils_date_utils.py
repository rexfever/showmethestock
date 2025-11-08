"""
날짜 형식 통일 유틸리티
모든 날짜 처리를 이 모듈을 통해 수행하여 일관성 유지
"""
from datetime import datetime
from typing import Optional


def normalize_date(date_str: Optional[str]) -> str:
    """
    날짜 문자열을 YYYYMMDD 형식으로 정규화
    
    Args:
        date_str: YYYYMMDD 또는 YYYY-MM-DD 형식의 날짜 문자열, 또는 None
        
    Returns:
        YYYYMMDD 형식의 날짜 문자열 (오늘 날짜가 None인 경우)
    """
    if not date_str:
        return datetime.now().strftime('%Y%m%d')
    
    if isinstance(date_str, int):
        date_str = str(date_str)
    
    # 이미 YYYYMMDD 형식인 경우
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    
    # YYYY-MM-DD 형식인 경우
    if len(date_str) == 10 and date_str.count('-') == 2:
        return date_str.replace('-', '')
    
    # 기타 형식 시도
    try:
        # datetime으로 파싱 후 YYYYMMDD로 변환
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        elif '-' in date_str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        elif len(date_str) == 8:
            dt = datetime.strptime(date_str, '%Y%m%d')
        else:
            raise ValueError(f"Unsupported date format: {date_str}")
        return dt.strftime('%Y%m%d')
    except Exception:
        # 파싱 실패 시 오늘 날짜 반환
        return datetime.now().strftime('%Y%m%d')


def format_date_for_db(date_str: Optional[str]) -> str:
    """
    DB 저장용 날짜 형식 변환 (YYYYMMDD)
    normalize_date의 별칭
    """
    return normalize_date(date_str)


def format_date_for_display(date_str: Optional[str]) -> str:
    """
    사용자 표시용 날짜 형식 변환 (YYYY-MM-DD)
    
    Args:
        date_str: YYYYMMDD 또는 YYYY-MM-DD 형식
        
    Returns:
        YYYY-MM-DD 형식의 날짜 문자열
    """
    normalized = normalize_date(date_str)
    if len(normalized) == 8 and normalized.isdigit():
        return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"
    return normalized


def parse_date_to_datetime(date_str: Optional[str]) -> datetime:
    """
    날짜 문자열을 datetime 객체로 변환
    
    Args:
        date_str: YYYYMMDD 또는 YYYY-MM-DD 형식
        
    Returns:
        datetime 객체
    """
    normalized = normalize_date(date_str)
    return datetime.strptime(normalized, '%Y%m%d')


def get_today_yyyymmdd() -> str:
    """오늘 날짜를 YYYYMMDD 형식으로 반환"""
    return datetime.now().strftime('%Y%m%d')

