from datetime import datetime, date
import pytz

# KST timezone 상수
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """KST 기준 현재 시간 반환"""
    return datetime.now(KST)

def normalize_date(date_str):
    """날짜를 YYYYMMDD 형식으로 통일"""
    if not date_str:
        return get_kst_now().strftime('%Y%m%d')
    
    # 문자열이 아닌 경우 (datetime 객체 등)
    if not isinstance(date_str, str):
        if hasattr(date_str, 'strftime'):
            return date_str.strftime('%Y%m%d')
        else:
            date_str = str(date_str)
    
    # 이미 YYYYMMDD 형식
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    # YYYY-MM-DD 형식
    elif len(date_str) >= 10 and date_str.count('-') >= 2:
        # TIMESTAMP 형식 (2025-11-24 00:00:00+09) 또는 DATE 형식 (2025-11-24)
        date_part = date_str.split()[0] if ' ' in date_str else date_str
        return date_part.replace('-', '')
    else:
        raise ValueError(f"잘못된 날짜 형식: {date_str}")

def format_display_date(date_str):
    """YYYYMMDD를 YYYY-MM-DD로 변환 (표시용)"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str

def yyyymmdd_to_date(yyyymmdd: str) -> date:
    """YYYYMMDD 문자열을 date 객체로 변환
    
    Args:
        yyyymmdd: YYYYMMDD 형식의 날짜 문자열 (예: "20251124")
    
    Returns:
        date 객체
    
    Raises:
        ValueError: 날짜 형식이 올바르지 않은 경우
    """
    if not yyyymmdd or len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        raise ValueError(f"잘못된 날짜 형식: {yyyymmdd} (YYYYMMDD 형식이어야 함)")
    return datetime.strptime(yyyymmdd, "%Y%m%d").date()

def yyyymmdd_to_timestamp(yyyymmdd: str, hour: int = 0, minute: int = 0, second: int = 0, tz=KST) -> datetime:
    """YYYYMMDD 문자열을 timezone-aware datetime 객체로 변환
    
    Args:
        yyyymmdd: YYYYMMDD 형식의 날짜 문자열 (예: "20251124")
        hour: 시간 (기본값: 0)
        minute: 분 (기본값: 0)
        second: 초 (기본값: 0)
        tz: timezone (기본값: KST)
    
    Returns:
        timezone-aware datetime 객체
    
    Raises:
        ValueError: 날짜 형식이 올바르지 않은 경우
    """
    if not yyyymmdd or len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        raise ValueError(f"잘못된 날짜 형식: {yyyymmdd} (YYYYMMDD 형식이어야 함)")
    dt = datetime.strptime(yyyymmdd, "%Y%m%d").replace(hour=hour, minute=minute, second=second)
    return tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)

def timestamp_to_yyyymmdd(dt: datetime, tz=KST) -> str:
    """timezone-aware datetime 객체를 YYYYMMDD 문자열로 변환
    
    Args:
        dt: datetime 객체 (timezone-aware 또는 naive)
        tz: 변환할 timezone (기본값: KST)
    
    Returns:
        YYYYMMDD 형식의 문자열
    """
    if dt.tzinfo is None:
        # timezone-naive인 경우 지정된 timezone으로 간주
        dt = tz.localize(dt)
    else:
        # timezone-aware인 경우 지정된 timezone으로 변환
        dt = dt.astimezone(tz)
    return dt.strftime('%Y%m%d')