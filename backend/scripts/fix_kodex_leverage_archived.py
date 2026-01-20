"""
KODEX 레버리지 관련 ARCHIVED 데이터 수정 스크립트
- REPLACED인데 TTL을 초과한 경우 TTL_EXPIRED로 변경
- TTL_EXPIRED인 경우 TTL 만료 시점의 수익률로 수정
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from services.state_transition_service import get_trading_days_since
from services.recommendation_service import get_nth_trading_day_after
from date_helper import yyyymmdd_to_date
from datetime import datetime
import holidays
from datetime import timedelta
from kiwoom_api import api

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

def fix_kodex_leverage_archived(dry_run=True):
    """KODEX 레버리지 관련 ARCHIVED 데이터 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # KODEX 레버리지 관련 종목 찾기
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy, anchor_date, archived_at,
                    archive_reason, archive_return_pct, broken_at, broken_return_pct,
                    anchor_close, archive_price, replaced_by_recommendation_id
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND (ticker LIKE '122630%' OR ticker LIKE '233740%' OR ticker LIKE '252670%'
                     OR ticker LIKE '114800%' OR ticker LIKE '251340%' OR ticker LIKE '229200%'
                     OR name LIKE '%레버리지%' OR name LIKE '%KODEX%')
                ORDER BY archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("KODEX 레버리지 관련 ARCHIVED 데이터가 없습니다.")
                return
            
            print(f"KODEX 레버리지 관련 ARCHIVED 데이터: {len(rows)}개")
            if dry_run:
                print("⚠️ DRY RUN 모드: 실제 업데이트는 수행하지 않습니다.\n")
            else:
                print("✅ 실제 업데이트를 수행합니다.\n")
            print("=" * 150)
            
            update_count = 0
            skip_count = 0
            error_count = 0
            
            for row in rows:
                rec_id, ticker, name, strategy, anchor_date, archived_at, \
                archive_reason, archive_return_pct, broken_at, broken_return_pct, \
                anchor_close, archive_price, replaced_by = row
                
                print(f"\n[{update_count + skip_count + error_count + 1}/{len(rows)}] {ticker} ({name if name else 'N/A'})")
                print(f"  recommendation_id: {rec_id}")
                print(f"  전략: {strategy}")
                print(f"  현재 archive_reason: {archive_reason}")
                print(f"  현재 archive_return_pct: {archive_return_pct}%")
                
                # TTL 계산
                ttl_days = 25 if strategy == 'midterm' else 15
                anchor_date_obj = anchor_date if isinstance(anchor_date, datetime) else yyyymmdd_to_date(str(anchor_date).replace('-', '')[:8])
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                ttl_expiry = get_nth_trading_day_after(anchor_date_obj, ttl_days)
                trading_days = get_trading_days_since(anchor_date_obj)
                
                print(f"  TTL: {ttl_days}거래일")
                print(f"  TTL 만료일: {ttl_expiry}")
                print(f"  실제 거래일 수: {trading_days}거래일")
                
                needs_update = False
                new_archive_reason = archive_reason
                new_archive_return_pct = archive_return_pct
                new_archive_price = archive_price
                
                # 1. REPLACED인데 TTL을 초과한 경우 → TTL_EXPIRED로 변경
                if archive_reason == 'REPLACED' and trading_days >= ttl_days:
                    print(f"  ⚠️ REPLACED인데 TTL 초과 → TTL_EXPIRED로 변경 필요")
                    new_archive_reason = 'TTL_EXPIRED'
                    needs_update = True
                
                # 2. TTL_EXPIRED인 경우 TTL 만료 시점의 수익률 조회
                if new_archive_reason == 'TTL_EXPIRED':
                    try:
                        ttl_expiry_str = ttl_expiry.strftime('%Y%m%d')
                        df_ttl = api.get_ohlcv(ticker, 30, ttl_expiry_str)
                        
                        if not df_ttl.empty and 'date' in df_ttl.columns:
                            df_ttl['date_str'] = df_ttl['date'].astype(str).str.replace('-', '').str[:8]
                            df_filtered = df_ttl[df_ttl['date_str'] <= ttl_expiry_str].sort_values('date_str')
                            
                            if not df_filtered.empty:
                                ttl_row = df_filtered.iloc[-1]
                                ttl_close = float(ttl_row['close']) if 'close' in ttl_row else None
                                
                                if ttl_close and anchor_close and anchor_close > 0:
                                    ttl_return_pct = round(((ttl_close - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                    
                                    if abs(ttl_return_pct - float(archive_return_pct)) > 0.01:
                                        print(f"  ⚠️ TTL 만료 시점 수익률 불일치")
                                        print(f"    현재: {archive_return_pct}%")
                                        print(f"    TTL 시점: {ttl_return_pct}%")
                                        new_archive_return_pct = ttl_return_pct
                                        new_archive_price = round(float(anchor_close) * (1 + ttl_return_pct / 100), 0)
                                        needs_update = True
                    except Exception as e:
                        print(f"  ⚠️ TTL 시점 가격 조회 실패: {e}")
                        skip_count += 1
                        continue
                
                if needs_update:
                    print(f"  업데이트 내용:")
                    if new_archive_reason != archive_reason:
                        print(f"    archive_reason: {archive_reason} → {new_archive_reason}")
                    if new_archive_return_pct != archive_return_pct:
                        print(f"    archive_return_pct: {archive_return_pct}% → {new_archive_return_pct}%")
                    if new_archive_price != archive_price:
                        print(f"    archive_price: {archive_price} → {new_archive_price}")
                    
                    if not dry_run:
                        try:
                            with db_manager.get_cursor(commit=True) as update_cur:
                                update_cur.execute("""
                                    UPDATE recommendations
                                    SET archive_reason = %s,
                                        archive_return_pct = %s,
                                        archive_price = %s,
                                        updated_at = NOW()
                                    WHERE recommendation_id = %s
                                """, (
                                    new_archive_reason,
                                    new_archive_return_pct,
                                    new_archive_price,
                                    rec_id
                                ))
                            print(f"  ✅ 업데이트 완료")
                            update_count += 1
                        except Exception as e:
                            print(f"  ❌ 업데이트 실패: {e}")
                            error_count += 1
                    else:
                        print(f"  [DRY RUN] 업데이트 예정")
                        update_count += 1
                else:
                    print(f"  ✅ 정책 준수 (수정 불필요)")
                    skip_count += 1
            
            print("\n" + "=" * 150)
            print(f"\n[결과]")
            print(f"  전체 항목: {len(rows)}개")
            print(f"  업데이트: {update_count}개")
            print(f"  건너뜀: {skip_count}개")
            print(f"  오류: {error_count}개")
            
            if dry_run:
                print("\n⚠️ DRY RUN 모드였습니다. 실제 업데이트를 수행하려면 --execute 옵션을 사용하세요.")
            
    except Exception as e:
        import traceback
        print(f"오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    dry_run = '--execute' not in sys.argv
    fix_kodex_leverage_archived(dry_run=dry_run)

