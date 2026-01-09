"""
모든 ARCHIVED 데이터를 정책에 맞게 재계산하여 업데이트
정책:
1. BROKEN을 거친 경우: broken_return_pct를 archive_return_pct로 사용
2. broken_at이 None인데 broken_return_pct가 있는 경우: broken_return_pct를 archive_return_pct로 사용
3. REPLACED 케이스: REPLACED 전환 시점 스냅샷 사용
4. TTL_EXPIRED 케이스: TTL 만료 시점 스냅샷 사용
5. 손절 조건 만족 시: archive_reason을 NO_MOMENTUM으로 변경
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date
from services.state_transition_service import get_trading_days_since
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

def fix_all_archived_with_policy():
    """모든 ARCHIVED 데이터를 정책에 맞게 재계산하여 업데이트"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 모든 ARCHIVED 종목 조회
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
                    r.status_changed_at,
                    r.archived_at,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_phase,
                    r.archive_reason
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                ORDER BY r.archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("ARCHIVED된 종목이 없습니다.")
                return
            
            print(f"ARCHIVED된 종목: {len(rows)}개\n")
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
                broken_at = row[6]
                broken_return_pct = row[7]
                status_changed_at = row[8]
                archived_at = row[9]
                archive_return_pct = row[10]
                archive_price = row[11]
                archive_phase = row[12]
                archive_reason = row[13]
                
                if idx % 20 == 0:
                    print(f"[진행 중] {idx}/{len(rows)} 처리 중...")
                
                new_archive_return_pct = None
                new_archive_price = None
                new_archive_phase = None
                new_archive_reason = archive_reason
                needs_update = False
                update_reasons = []
                
                # 정책 1: BROKEN을 거친 경우 또는 broken_at이 None인데 broken_return_pct가 있는 경우
                # broken_return_pct를 archive_return_pct로 사용 (최우선)
                if broken_return_pct is not None:
                    new_archive_return_pct = round(float(broken_return_pct), 2)
                    if anchor_close:
                        anchor_close_float = float(anchor_close)
                        new_archive_price = round(anchor_close_float * (1 + new_archive_return_pct / 100), 0)
                    
                    if new_archive_return_pct > 2:
                        new_archive_phase = 'PROFIT'
                    elif new_archive_return_pct < -2:
                        new_archive_phase = 'LOSS'
                    else:
                        new_archive_phase = 'FLAT'
                    
                    # 기존 값과 비교
                    if archive_return_pct is None:
                        needs_update = True
                        update_reasons.append("archive_return_pct가 None")
                    elif abs(float(archive_return_pct) - new_archive_return_pct) > 0.01:
                        needs_update = True
                        update_reasons.append(f"broken_return_pct 사용: {archive_return_pct} → {new_archive_return_pct}")
                    
                    if archive_price is None or (new_archive_price and abs(float(archive_price) - new_archive_price) > 1):
                        needs_update = True
                        if "가격" not in " ".join(update_reasons):
                            update_reasons.append("archive_price 불일치")
                    
                    if archive_phase != new_archive_phase:
                        needs_update = True
                        if "phase" not in " ".join(update_reasons):
                            update_reasons.append(f"archive_phase: {archive_phase} → {new_archive_phase}")
                
                # 정책 2: REPLACED 케이스 (broken_return_pct가 없는 경우만)
                elif archive_reason == 'REPLACED' and status_changed_at and broken_return_pct is None:
                    try:
                        if isinstance(status_changed_at, str):
                            changed_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                        elif isinstance(status_changed_at, datetime):
                            changed_date = status_changed_at.date()
                        else:
                            changed_date = status_changed_at
                        
                        changed_date_str = changed_date.strftime('%Y%m%d')
                        df = api.get_ohlcv(ticker, 10, changed_date_str)
                        
                        if not df.empty:
                            if 'date' in df.columns:
                                df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                                df_filtered = df[df['date_str'] == changed_date_str]
                                if not df_filtered.empty:
                                    replaced_price = float(df_filtered.iloc[-1]['close'])
                                else:
                                    df_sorted = df.sort_values('date_str')
                                    df_before = df_sorted[df_sorted['date_str'] <= changed_date_str]
                                    if not df_before.empty:
                                        replaced_price = float(df_before.iloc[-1]['close'])
                                    else:
                                        replaced_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                            else:
                                replaced_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                            
                            if replaced_price and anchor_close:
                                anchor_close_float = float(anchor_close)
                                new_archive_return_pct = round(((replaced_price - anchor_close_float) / anchor_close_float) * 100, 2)
                                new_archive_price = replaced_price
                                
                                if new_archive_return_pct > 2:
                                    new_archive_phase = 'PROFIT'
                                elif new_archive_return_pct < -2:
                                    new_archive_phase = 'LOSS'
                                else:
                                    new_archive_phase = 'FLAT'
                                
                                # 기존 값과 비교
                                if archive_return_pct is None:
                                    needs_update = True
                                    update_reasons.append("archive_return_pct가 None")
                                elif abs(float(archive_return_pct) - new_archive_return_pct) > 0.01:
                                    needs_update = True
                                    update_reasons.append(f"REPLACED 스냅샷: {archive_return_pct} → {new_archive_return_pct}")
                                
                                if archive_price is None or (new_archive_price and abs(float(archive_price) - new_archive_price) > 1):
                                    needs_update = True
                                    if "가격" not in " ".join(update_reasons):
                                        update_reasons.append("archive_price 불일치")
                                
                                if archive_phase != new_archive_phase:
                                    needs_update = True
                                    if "phase" not in " ".join(update_reasons):
                                        update_reasons.append(f"archive_phase: {archive_phase} → {new_archive_phase}")
                    except Exception as e:
                        error_count += 1
                        continue
                
                # 정책 3: TTL_EXPIRED 케이스 (broken_return_pct가 없는 경우만)
                elif archive_reason == 'TTL_EXPIRED' and broken_return_pct is None:
                    try:
                        ttl_expiry_date, ttl_days = get_ttl_expiry_date(anchor_date, strategy)
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
                                new_archive_return_pct = round(((ttl_price - anchor_close_float) / anchor_close_float) * 100, 2)
                                new_archive_price = ttl_price
                                
                                if new_archive_return_pct > 2:
                                    new_archive_phase = 'PROFIT'
                                elif new_archive_return_pct < -2:
                                    new_archive_phase = 'LOSS'
                                else:
                                    new_archive_phase = 'FLAT'
                                
                                # 기존 값과 비교
                                if archive_return_pct is None:
                                    needs_update = True
                                    update_reasons.append("archive_return_pct가 None")
                                elif abs(float(archive_return_pct) - new_archive_return_pct) > 0.01:
                                    needs_update = True
                                    update_reasons.append(f"TTL 만료 시점 스냅샷: {archive_return_pct} → {new_archive_return_pct}")
                                
                                if archive_price is None or (new_archive_price and abs(float(archive_price) - new_archive_price) > 1):
                                    needs_update = True
                                    if "가격" not in " ".join(update_reasons):
                                        update_reasons.append("archive_price 불일치")
                                
                                if archive_phase != new_archive_phase:
                                    needs_update = True
                                    if "phase" not in " ".join(update_reasons):
                                        update_reasons.append(f"archive_phase: {archive_phase} → {new_archive_phase}")
                    except Exception as e:
                        error_count += 1
                        continue
                
                # 정책 4: 손절 조건 체크
                if new_archive_return_pct is None and archive_return_pct is not None:
                    new_archive_return_pct = float(archive_return_pct)
                
                if new_archive_return_pct is not None:
                    # 전략별 손절 조건 확인
                    stop_loss = 0.02  # 기본값
                    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                        stop_loss = 0.02
                    elif strategy == "midterm" or strategy == "MIDTERM":
                        stop_loss = 0.07
                    
                    stop_loss_pct = -abs(float(stop_loss) * 100)
                    
                    # 손절 조건 만족 시 NO_MOMENTUM으로 변경
                    if new_archive_return_pct <= stop_loss_pct:
                        if new_archive_reason != 'NO_MOMENTUM':
                            new_archive_reason = 'NO_MOMENTUM'
                            needs_update = True
                            update_reasons.append(f"손절 조건: {new_archive_return_pct:.2f}% <= {stop_loss_pct:.2f}%")
                
                # 업데이트 실행
                if needs_update:
                    if update_count < 10:  # 처음 10개만 상세 로그
                        print(f"\n[{update_count + 1}] {ticker} ({name})")
                        print(f"    전략: {strategy}")
                        print(f"    현재: return_pct={archive_return_pct}, price={archive_price}, phase={archive_phase}, reason={archive_reason}")
                        print(f"    수정: return_pct={new_archive_return_pct}, price={new_archive_price}, phase={new_archive_phase}, reason={new_archive_reason}")
                        print(f"    이유: {', '.join(update_reasons)}")
                    
                    with db_manager.get_cursor(commit=True) as update_cur:
                        update_cur.execute("""
                            UPDATE recommendations
                            SET archive_return_pct = %s,
                                archive_price = %s,
                                archive_phase = %s,
                                archive_reason = %s,
                                updated_at = NOW()
                            WHERE recommendation_id = %s
                        """, (
                            new_archive_return_pct,
                            new_archive_price,
                            new_archive_phase,
                            new_archive_reason,
                            rec_id
                        ))
                    update_count += 1
                else:
                    skip_count += 1
            
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
    print("ARCHIVED 데이터 정책에 맞게 재계산 시작...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_all_archived_with_policy()
    print("\n완료!")


