"""
TTL_EXPIRED로 ARCHIVED된 종목들의 TTL 만료 시점 스냅샷 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date

def get_nth_trading_day_after(start_date, n):
    """시작일로부터 n번째 거래일 계산"""
    if isinstance(start_date, str):
        start_date = yyyymmdd_to_date(start_date.replace('-', '')[:8])
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    
    kr_holidays = holidays.SouthKorea(years=range(start_date.year, start_date.year + 2))
    
    current = start_date
    trading_days_count = 0
    
    while trading_days_count < n:
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days_count += 1
        if trading_days_count < n:
            current += timedelta(days=1)
    
    return current
from kiwoom_api import api
import holidays
from datetime import datetime, timedelta

def get_trading_days_between(start_date, end_date):
    """두 날짜 사이의 거래일 수 계산"""
    if isinstance(start_date, str):
        start_date = yyyymmdd_to_date(start_date.replace('-', '')[:8])
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = yyyymmdd_to_date(end_date.replace('-', '')[:8])
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    if start_date > end_date:
        return 0
    
    kr_holidays = holidays.SouthKorea(years=range(start_date.year, end_date.year + 2))
    
    trading_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days += 1
        current += timedelta(days=1)
    
    return trading_days

def get_ttl_expiry_date(anchor_date, strategy):
    """TTL 만료일 계산"""
    if isinstance(anchor_date, str):
        anchor_date = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
    if isinstance(anchor_date, datetime):
        anchor_date = anchor_date.date()
    
    # 전략별 TTL 설정
    ttl_days = 20  # 기본값
    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
        ttl_days = 15
    elif strategy == "midterm" or strategy == "MIDTERM":
        ttl_days = 25
    
    # TTL 만료일 계산 (anchor_date + ttl_days 거래일)
    ttl_expiry_date = get_nth_trading_day_after(anchor_date, ttl_days)
    
    return ttl_expiry_date, ttl_days

def check_ttl_expired_snapshot():
    """TTL_EXPIRED로 ARCHIVED된 종목들의 TTL 만료 시점 스냅샷 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # TTL_EXPIRED로 ARCHIVED된 종목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_reason,
                    r.archived_at,
                    r.broken_at,
                    r.broken_return_pct,
                    r.flags
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_reason = 'TTL_EXPIRED'
                ORDER BY r.archive_return_pct DESC
                LIMIT 20
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("TTL_EXPIRED로 ARCHIVED된 종목이 없습니다.")
                return
            
            print(f"TTL_EXPIRED로 ARCHIVED된 종목: {len(rows)}개\n")
            print("=" * 150)
            
            needs_fix_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                strategy = row[5]
                archive_return_pct = row[6]
                archive_price = row[7]
                archive_reason = row[8]
                archived_at = row[9]
                broken_at = row[10]
                broken_return_pct = row[11]
                flags = row[12]
                
                print(f"\n[{idx}] {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    전략: {strategy}")
                print(f"    ARCHIVED 수익률: {archive_return_pct:,.2f}%")
                print(f"    ARCHIVED 가격: {archive_price:,.0f}원")
                print(f"    ARCHIVED 시점: {archived_at}")
                print(f"    BROKEN 시점: {broken_at}")
                print(f"    BROKEN 수익률: {broken_return_pct}%")
                
                # TTL 만료일 계산
                ttl_expiry_date, ttl_days = get_ttl_expiry_date(anchor_date, strategy)
                print(f"\n    TTL 정보:")
                print(f"      TTL 거래일: {ttl_days}일")
                print(f"      TTL 만료일: {ttl_expiry_date}")
                
                # TTL 만료일부터 ARCHIVED 시점까지의 거래일 수
                if archived_at:
                    if isinstance(archived_at, str):
                        archived_date = yyyymmdd_to_date(archived_at.replace('-', '')[:8])
                    elif isinstance(archived_at, datetime):
                        archived_date = archived_at.date()
                    else:
                        archived_date = archived_at
                    
                    days_after_ttl = get_trading_days_between(ttl_expiry_date, archived_date)
                    print(f"      TTL 만료 후 ARCHIVED까지: {days_after_ttl}거래일")
                    
                    if days_after_ttl > 0:
                        print(f"      ⚠️  TTL 만료 후 {days_after_ttl}거래일 후에 ARCHIVED되었습니다.")
                
                # TTL 만료 시점의 가격 조회
                try:
                    ttl_expiry_date_str = ttl_expiry_date.strftime('%Y%m%d')
                    df = api.get_ohlcv(ticker, 10, ttl_expiry_date_str)
                    
                    if not df.empty:
                        if 'date' in df.columns:
                            df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                            ttl_row = df[df['date_str'] == ttl_expiry_date_str]
                            if ttl_row.empty:
                                df_sorted = df.sort_values('date_str')
                                ttl_row = df_sorted[df_sorted['date_str'] <= ttl_expiry_date_str]
                                if not ttl_row.empty:
                                    ttl_price = float(ttl_row.iloc[-1]['close'])
                                    ttl_date_actual = ttl_row.iloc[-1]['date']
                                else:
                                    ttl_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                                    ttl_date_actual = df.iloc[-1]['date'] if 'date' in df.columns else None
                            else:
                                ttl_price = float(ttl_row.iloc[0]['close'])
                                ttl_date_actual = ttl_row.iloc[0]['date']
                        else:
                            ttl_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                            ttl_date_actual = None
                        
                        if ttl_price and anchor_close:
                            anchor_close_float = float(anchor_close)
                            ttl_return_pct = round(((ttl_price - anchor_close_float) / anchor_close_float) * 100, 2)
                            
                            print(f"\n    TTL 만료 시점 스냅샷:")
                            print(f"      TTL 만료일 가격 ({ttl_date_actual}): {ttl_price:,.0f}원")
                            print(f"      TTL 만료 시점 수익률: {ttl_return_pct:,.2f}%")
                            
                            # 저장된 수익률과 비교
                            archive_return_pct_float = float(archive_return_pct)
                            diff = abs(ttl_return_pct - archive_return_pct_float)
                            
                            if diff > 0.01:
                                print(f"      ❌ 불일치: 저장된 수익률({archive_return_pct:,.2f}%)과 TTL 만료 시점 수익률({ttl_return_pct:,.2f}%) 차이: {diff:,.2f}%p")
                                needs_fix_count += 1
                            else:
                                print(f"      ✅ 일치: 저장된 수익률과 TTL 만료 시점 수익률이 일치합니다.")
                    else:
                        print(f"    ⚠️  OHLCV 데이터 없음")
                except Exception as e:
                    print(f"    ⚠️  TTL 만료 시점 가격 조회 실패: {e}")
                
                print("-" * 150)
            
            print(f"\n[결과]")
            print(f"  수정 필요: {needs_fix_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("TTL_EXPIRED ARCHIVED 종목 TTL 만료 시점 스냅샷 확인...")
    print("=" * 150)
    check_ttl_expired_snapshot()
    print("\n완료!")

