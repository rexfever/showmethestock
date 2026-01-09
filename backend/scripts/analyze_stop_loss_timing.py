"""
손절 정책 위반 항목의 손절 조건 만족 시점 분석
- 각 종목이 언제 손절 조건을 만족했는지 확인
- 왜 그 시점에 BROKEN으로 전이되지 않았는지 분석
"""
import sys
import os
from pathlib import Path
from decimal import Decimal

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_kst_now
from kiwoom_api import api
from datetime import datetime, timedelta
import holidays

def get_stop_loss_pct(strategy):
    """전략별 손절 기준 반환"""
    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
        return -2.0
    elif strategy == "midterm" or strategy == "MIDTERM":
        return -7.0
    else:
        return -2.0  # 기본값

def is_trading_day(date_str):
    """거래일 여부 확인"""
    if isinstance(date_str, str):
        date_obj = yyyymmdd_to_date(date_str.replace('-', '')[:8])
    else:
        date_obj = date_str
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    kr_holidays = holidays.SouthKorea(years=date_obj.year)
    return date_obj.weekday() < 5 and date_obj not in kr_holidays

def analyze_stop_loss_timing():
    """손절 정책 위반 항목의 손절 조건 만족 시점 분석"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 손실이 -7%를 넘는 ARCHIVED 항목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.broken_at,
                    r.broken_return_pct,
                    r.archive_return_pct,
                    r.archive_reason
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct IS NOT NULL
                AND r.archive_return_pct < -7.0
                ORDER BY r.archive_return_pct ASC
                LIMIT 5
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("분석할 항목이 없습니다.")
                return
            
            print(f"분석 대상: {len(rows)}개\n")
            print("=" * 150)
            
            for row in rows:
                rec_id, ticker, name, anchor_date, anchor_close, strategy, broken_at, \
                broken_return_pct, archive_return_pct, archive_reason = row
                
                stop_loss_pct = get_stop_loss_pct(strategy)
                archive_return_pct_float = float(archive_return_pct) if archive_return_pct else None
                anchor_close_float = float(anchor_close) if anchor_close else None
                
                print(f"\n[분석] {ticker} ({name if name else 'N/A'})")
                print(f"  전략: {strategy} (손절 기준: {stop_loss_pct}%)")
                print(f"  anchor_date: {anchor_date}")
                print(f"  anchor_close: {anchor_close_float:,.0f}" if anchor_close_float else "  anchor_close: None")
                print(f"  broken_at: {broken_at}")
                print(f"  broken_return_pct: {broken_return_pct:.2f}%" if broken_return_pct else "  broken_return_pct: None")
                print(f"  archive_return_pct: {archive_return_pct_float:.2f}%")
                
                if not anchor_close_float:
                    print("  ⚠️ anchor_close가 없어 분석 불가")
                    continue
                
                # anchor_date부터 broken_at까지의 일별 가격 조회
                if isinstance(anchor_date, str):
                    start_date = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                else:
                    start_date = anchor_date
                
                if isinstance(broken_at, str):
                    end_date = yyyymmdd_to_date(broken_at.replace('-', '')[:8])
                elif broken_at:
                    end_date = broken_at.date() if isinstance(broken_at, datetime) else broken_at
                else:
                    end_date = get_kst_now().date()
                
                print(f"\n  손절 조건 만족 시점 추적:")
                print(f"    기간: {start_date} ~ {end_date}")
                
                # 일별 OHLCV 데이터 조회
                try:
                    days_diff = (end_date - start_date).days
                    df = api.get_ohlcv(ticker, days_diff + 30, end_date.strftime('%Y%m%d'))
                    
                    if df.empty:
                        print("    ⚠️ 가격 데이터 없음")
                        continue
                    
                    # 날짜 컬럼 정리
                    if 'date' in df.columns:
                        df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                        df = df.sort_values('date_str')
                    else:
                        print("    ⚠️ 날짜 컬럼 없음")
                        continue
                    
                    # anchor_date 이후 데이터만 필터링
                    anchor_date_str = start_date.strftime('%Y%m%d')
                    df_filtered = df[df['date_str'] >= anchor_date_str].copy()
                    
                    if df_filtered.empty:
                        print("    ⚠️ anchor_date 이후 데이터 없음")
                        continue
                    
                    # 각 날짜별 손익률 계산
                    first_breach_date = None
                    breach_count = 0
                    
                    for idx, row_data in df_filtered.iterrows():
                        date_str = row_data['date_str']
                        close = float(row_data['close']) if 'close' in row_data else None
                        
                        if not close:
                            continue
                        
                        # 손익률 계산
                        return_pct = ((close - anchor_close_float) / anchor_close_float) * 100
                        
                        # 손절 조건 만족 확인
                        if return_pct <= stop_loss_pct:
                            breach_count += 1
                            if first_breach_date is None:
                                first_breach_date = date_str
                                print(f"    ✅ 첫 손절 조건 만족: {date_str} (손익률: {return_pct:.2f}%)")
                    
                    if first_breach_date:
                        # 첫 손절 조건 만족일부터 broken_at까지의 기간 계산
                        first_breach_date_obj = yyyymmdd_to_date(first_breach_date)
                        if isinstance(broken_at, str):
                            broken_at_obj = yyyymmdd_to_date(broken_at.replace('-', '')[:8])
                        elif broken_at:
                            broken_at_obj = broken_at.date() if isinstance(broken_at, datetime) else broken_at
                        else:
                            broken_at_obj = end_date
                        
                        delay_days = (broken_at_obj - first_breach_date_obj).days
                        print(f"    ⚠️ 손절 조건 만족 후 BROKEN 전이까지 지연: {delay_days}일")
                        print(f"    ⚠️ 손절 조건 만족 횟수: {breach_count}일")
                    else:
                        print(f"    ⚠️ 손절 조건 만족 시점을 찾을 수 없음 (데이터 부족 가능)")
                    
                except Exception as e:
                    print(f"    ❌ 오류: {e}")
                    import traceback
                    traceback.print_exc()
                
                print("-" * 150)
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    analyze_stop_loss_timing()

