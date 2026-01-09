"""
특정 종목들의 ARCHIVED 데이터를 정책에 맞게 수정
107640 (한중엔시에스), 078600 (대주전자재료)
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
from datetime import datetime

def fix_specific_stocks_archived():
    """특정 종목들의 ARCHIVED 데이터 수정"""
    tickers = ['107640', '078600']  # 한중엔시에스, 대주전자재료
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            for ticker in tickers:
                print(f"\n[{ticker}] 처리 시작...")
                print("=" * 100)
                
                # 해당 종목의 ARCHIVED 추천 조회
                cur.execute("""
                    SELECT 
                        recommendation_id,
                        ticker,
                        name,
                        anchor_date,
                        anchor_close,
                        strategy,
                        broken_at,
                        broken_return_pct,
                        status_changed_at,
                        archived_at,
                        archive_return_pct,
                        archive_price,
                        archive_phase,
                        archive_reason
                    FROM recommendations
                    WHERE ticker = %s
                    AND status = 'ARCHIVED'
                    AND scanner_version = 'v3'
                    ORDER BY archived_at DESC
                """, (ticker,))
                
                rows = cur.fetchall()
                
                if not rows:
                    print(f"  ARCHIVED 데이터 없음")
                    continue
                
                for row in rows:
                    rec_id = row[0]
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
                    
                    print(f"\n  추천 ID: {rec_id}")
                    print(f"  종목명: {name}")
                    print(f"  현재 상태:")
                    print(f"    archive_return_pct: {archive_return_pct}")
                    print(f"    archive_reason: {archive_reason}")
                    print(f"    broken_at: {broken_at}")
                    print(f"    broken_return_pct: {broken_return_pct}")
                    
                    new_archive_return_pct = None
                    new_archive_price = None
                    new_archive_phase = None
                    new_archive_reason = archive_reason
                    needs_update = False
                    update_reasons = []
                    
                    # 1. BROKEN을 거친 경우: BROKEN 시점 스냅샷 사용
                    if broken_at and broken_return_pct is not None:
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
                        
                        if archive_return_pct is None or abs(float(archive_return_pct) - new_archive_return_pct) > 0.01:
                            needs_update = True
                            update_reasons.append(f"BROKEN 스냅샷 적용: {archive_return_pct} → {new_archive_return_pct}")
                    
                    # 2. REPLACED 케이스: REPLACED 전환 시점 스냅샷 사용
                    elif archive_reason == 'REPLACED' and status_changed_at:
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
                                    
                                    if archive_return_pct is None or abs(float(archive_return_pct) - new_archive_return_pct) > 0.01:
                                        needs_update = True
                                        update_reasons.append(f"REPLACED 스냅샷 적용: {archive_return_pct} → {new_archive_return_pct}")
                        except Exception as e:
                            print(f"    ⚠️  OHLCV 조회 실패: {e}")
                            continue
                    
                    # 3. 손절 조건 체크
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
                                update_reasons.append(f"손절 조건 만족: {new_archive_return_pct:.2f}% <= {stop_loss_pct:.2f}%")
                    
                    # 업데이트 실행
                    if needs_update:
                        print(f"  수정 사항:")
                        print(f"    return_pct: {archive_return_pct} → {new_archive_return_pct}")
                        print(f"    price: {archive_price} → {new_archive_price}")
                        print(f"    phase: {archive_phase} → {new_archive_phase}")
                        print(f"    reason: {archive_reason} → {new_archive_reason}")
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
                        print(f"  ✅ 업데이트 완료")
                    else:
                        print(f"  ✅ 수정 불필요 (정책 준수)")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("특정 종목 ARCHIVED 데이터 수정 시작...")
    print("=" * 100)
    fix_specific_stocks_archived()
    print("\n완료!")


