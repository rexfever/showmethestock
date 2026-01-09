"""
TTL_EXPIRED 케이스의 archive_return_pct를 TTL 만료 시점의 수익률로 수정
- 정책: TTL_EXPIRED인 경우 TTL 만료 시점의 수익률을 archive_return_pct로 사용해야 함
- 현재 문제: 현재 시점(archived_at)의 수익률이 저장되어 있음
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

def fix_archived_ttl_expired_return(dry_run=True):
    """TTL_EXPIRED 케이스의 archive_return_pct를 TTL 만료 시점의 수익률로 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # TTL_EXPIRED 케이스 조회 (REPLACED 상태도 포함 - archive_reason이 TTL_EXPIRED인 경우)
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
                    r.archived_at,
                    r.status
                FROM recommendations r
                WHERE r.scanner_version = 'v3'
                AND r.archive_reason = 'TTL_EXPIRED'
                ORDER BY r.archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("TTL_EXPIRED 케이스가 없습니다.")
                return
            
            print(f"TTL_EXPIRED 케이스: {len(rows)}개")
            if dry_run:
                print("⚠️ DRY RUN 모드: 실제 업데이트는 수행하지 않습니다.\n")
            else:
                print("✅ 실제 업데이트를 수행합니다.\n")
            print("=" * 150)
            
            update_count = 0
            skip_count = 0
            error_count = 0
            
            for row in rows:
                rec_id, ticker, name, anchor_date, anchor_close, strategy, \
                archive_return_pct, archive_price, archived_at, status = row
                
                archive_return_pct_float = float(archive_return_pct) if archive_return_pct is not None else None
                anchor_close_float = float(anchor_close) if anchor_close is not None else None
                
                print(f"\n[{update_count + skip_count + error_count + 1}/{len(rows)}] {ticker} ({name if name else 'N/A'})")
                print(f"  상태: {status}")
                print(f"  전략: {strategy}")
                print(f"  현재 archive_return_pct: {archive_return_pct_float:.2f}%" if archive_return_pct_float is not None else "  현재 archive_return_pct: None")
                print(f"  anchor_date: {anchor_date}")
                print(f"  archived_at: {archived_at}")
                
                if not anchor_close_float:
                    print("  ⚠️ anchor_close가 없어 건너뜀")
                    skip_count += 1
                    continue
                
                # anchor_date 파싱
                if isinstance(anchor_date, str):
                    anchor_date_obj = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                else:
                    anchor_date_obj = anchor_date
                
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                # TTL 만료일 계산
                ttl_expiry_date, ttl_days = get_ttl_expiry_date(anchor_date_obj, strategy)
                print(f"  TTL 만료일: {ttl_expiry_date} (TTL: {ttl_days}거래일)")
                
                # TTL 시점의 가격 조회
                try:
                    days_diff = (ttl_expiry_date - anchor_date_obj).days
                    df = api.get_ohlcv(ticker, days_diff + 30, ttl_expiry_date.strftime('%Y%m%d'))
                    
                    if df.empty:
                        print("  ⚠️ 가격 데이터 없음 (건너뜀)")
                        skip_count += 1
                        continue
                    
                    # 날짜 컬럼 정리
                    if 'date' in df.columns:
                        df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                        df = df.sort_values('date_str')
                    else:
                        print("  ⚠️ 날짜 컬럼 없음 (건너뜀)")
                        skip_count += 1
                        continue
                    
                    # TTL 만료일 이하의 가장 가까운 거래일 데이터 찾기
                    ttl_date_str = ttl_expiry_date.strftime('%Y%m%d')
                    df_filtered = df[df['date_str'] <= ttl_date_str].sort_values('date_str')
                    
                    if df_filtered.empty:
                        print("  ⚠️ TTL 시점 데이터 없음 (건너뜀)")
                        skip_count += 1
                        continue
                    
                    # TTL 시점의 가격
                    last_row = df_filtered.iloc[-1]
                    ttl_close = float(last_row['close']) if 'close' in last_row else None
                    ttl_date_actual = str(last_row['date_str']) if 'date_str' in last_row else ttl_date_str
                    
                    if not ttl_close:
                        print("  ⚠️ TTL 시점 가격 없음 (건너뜀)")
                        skip_count += 1
                        continue
                    
                    # TTL 시점의 수익률 계산
                    ttl_return_pct = round(((ttl_close - anchor_close_float) / anchor_close_float) * 100, 2)
                    print(f"  TTL 시점 수익률: {ttl_return_pct:.2f}% (날짜: {ttl_date_actual})")
                    
                    # 현재 archive_return_pct와 비교
                    if archive_return_pct_float is None or abs(ttl_return_pct - archive_return_pct_float) > 0.01:
                        print(f"  ⚠️ 수정 필요: 현재({archive_return_pct_float:.2f}%) → TTL 시점({ttl_return_pct:.2f}%)")
                        
                        # 업데이트할 값 계산
                        new_archive_return_pct = ttl_return_pct
                        new_archive_price = round(anchor_close_float * (1 + new_archive_return_pct / 100), 0)
                        
                        print(f"  업데이트 내용:")
                        print(f"    archive_return_pct: {archive_return_pct_float:.2f}% → {new_archive_return_pct:.2f}%")
                        print(f"    archive_price: {archive_price if archive_price else 'None'} → {new_archive_price}")
                        
                        if not dry_run:
                            # 실제 업데이트
                            try:
                                with db_manager.get_cursor(commit=True) as update_cur:
                                    update_cur.execute("""
                                        UPDATE recommendations
                                        SET archive_return_pct = %s,
                                            archive_price = %s,
                                            updated_at = NOW()
                                        WHERE recommendation_id = %s
                                    """, (
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
                        print(f"  ✅ 이미 정확함 (차이: {abs(ttl_return_pct - archive_return_pct_float):.2f}%)")
                        skip_count += 1
                    
                except Exception as e:
                    print(f"  ❌ 오류: {e}")
                    import traceback
                    traceback.print_exc()
                    error_count += 1
                
                print("-" * 150)
            
            # 결과 출력
            print(f"\n\n[결과]")
            print(f"  전체 항목: {len(rows)}개")
            print(f"  업데이트: {update_count}개")
            print(f"  건너뜀: {skip_count}개")
            print(f"  오류: {error_count}개")
            
            if dry_run:
                print(f"\n⚠️ DRY RUN 모드였습니다. 실제 업데이트를 수행하려면 --execute 옵션을 사용하세요.")
            
            return {
                'total': len(rows),
                'updated': update_count,
                'skipped': skip_count,
                'errors': error_count
            }
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    import sys
    
    # 명령줄 인자로 dry_run 모드 제어
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False
        print("⚠️ 실제 업데이트를 수행합니다!\n")
    else:
        print("⚠️ DRY RUN 모드입니다. 실제 업데이트를 수행하려면 --execute 옵션을 사용하세요.\n")
    
    fix_archived_ttl_expired_return(dry_run=dry_run)

