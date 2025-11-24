from datetime import datetime
import pytz

def get_kst_now():
    """KST 기준 현재 시간 반환"""
    return datetime.now(pytz.timezone('Asia/Seoul'))

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