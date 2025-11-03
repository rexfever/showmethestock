from datetime import datetime
import pytz

def get_kst_now():
    """KST 기준 현재 시간 반환"""
    return datetime.now(pytz.timezone('Asia/Seoul'))

def normalize_date(date_str):
    """날짜를 YYYYMMDD 형식으로 통일"""
    if not date_str:
        return get_kst_now().strftime('%Y%m%d')
    
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    elif len(date_str) == 10 and date_str.count('-') == 2:
        return date_str.replace('-', '')
    else:
        raise ValueError(f"잘못된 날짜 형식: {date_str}")

def format_display_date(date_str):
    """YYYYMMDD를 YYYY-MM-DD로 변환 (표시용)"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str