"""
TTL_EXPIRED로 ARCHIVED된 종목들의 TTL 만료 시점 스냅샷으로 수정
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date
from kiwoom_api import api
import holidays
from datetime import datetime, timedelta

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

def fix_ttl_expired_snapshot():
    """TTL_EXPIRED로 ARCHIVED된 종목들의 TTL 만료 시점 스냅샷으로 수정"""
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
                    r.archive_phase
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_reason = 'TTL_EXPIRED'
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("TTL_EXPIRED로 ARCHIVED된 종목이 없습니다.")
                return
            
            print(f"TTL_EXPIRED로 ARCHIVED된 종목: {len(rows)}개\n")
            print("=" * 150)
            
            update_count = 0
            skip_count = 0
            error_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                strategy = row[5]
                archive_return_pct = row[6]
                archive_price = row[7]
                archive_phase = row[8]
                
                print(f"\n[{idx}] {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    전략: {strategy}")
                print(f"    현재 archive_return_pct: {archive_return_pct:,.2f}%")
                print(f"    현재 archive_price: {archive_price:,.0f}원")
                
                # TTL 만료일 계산
                ttl_expiry_date, ttl_days = get_ttl_expiry_date(anchor_date, strategy)
                print(f"    TTL 만료일: {ttl_expiry_date} ({ttl_days}거래일)")
                
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
                                else:
                                    ttl_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                            else:
                                ttl_price = float(ttl_row.iloc[0]['close'])
                        else:
                            ttl_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                        
                        if ttl_price and anchor_close:
                            anchor_close_float = float(anchor_close)
                            ttl_return_pct = round(((ttl_price - anchor_close_float) / anchor_close_float) * 100, 2)
                            
                            print(f"    TTL 만료일 가격: {ttl_price:,.0f}원")
                            print(f"    TTL 만료 시점 수익률: {ttl_return_pct:,.2f}%")
                            
                            # 저장된 수익률과 비교
                            archive_return_pct_float = float(archive_return_pct)
                            diff = abs(ttl_return_pct - archive_return_pct_float)
                            
                            if diff > 0.01:
                                print(f"    → 차이: {diff:,.2f}%p (수정 필요)")
                                
                                # archive_phase 재계산
                                if ttl_return_pct > 2:
                                    new_archive_phase = 'PROFIT'
                                elif ttl_return_pct < -2:
                                    new_archive_phase = 'LOSS'
                                else:
                                    new_archive_phase = 'FLAT'
                                
                                print(f"    ✅ 업데이트: archive_return_pct={ttl_return_pct:,.2f}%, archive_price={ttl_price:,.0f}원, archive_phase={new_archive_phase}")
                                
                                # DB 업데이트
                                with db_manager.get_cursor(commit=True) as update_cur:
                                    update_cur.execute("""
                                        UPDATE recommendations
                                        SET archive_return_pct = %s,
                                            archive_price = %s,
                                            archive_phase = %s,
                                            updated_at = NOW()
                                        WHERE recommendation_id = %s
                                    """, (ttl_return_pct, ttl_price, new_archive_phase, rec_id))
                                
                                update_count += 1
                            else:
                                print(f"    ⏭️  스킵: TTL 만료 시점 수익률과 동일 (차이: {diff:.2f}%p)")
                                skip_count += 1
                        else:
                            print(f"    ⚠️  가격 정보 없음")
                            error_count += 1
                    else:
                        print(f"    ⚠️  OHLCV 데이터 없음")
                        error_count += 1
                except Exception as e:
                    print(f"    ⚠️  오류: {e}")
                    error_count += 1
                
                print("-" * 150)
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  스킵: {skip_count}개")
            print(f"  오류: {error_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("TTL_EXPIRED ARCHIVED 종목 TTL 만료 시점 스냅샷으로 수정...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_ttl_expired_snapshot()
    print("\n완료!")


