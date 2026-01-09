"""
REPLACED로 ARCHIVED된 데이터 수정
status_changed_at 시점의 OHLCV 데이터를 조회하여 수정
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import get_trading_date, yyyymmdd_to_date
from kiwoom_api import api
import json
from datetime import datetime

def fix_replaced_archived_with_ohlcv():
    """REPLACED로 ARCHIVED된 데이터 수정 (OHLCV 조회)"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # REPLACED로 ARCHIVED된 항목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.status_changed_at,
                    r.archived_at,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_phase,
                    r.archive_reason
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_reason = 'REPLACED'
                AND r.archive_return_pct IS NOT NULL
                AND r.status_changed_at IS NOT NULL
                ORDER BY r.archive_return_pct DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 REPLACED ARCHIVED 데이터가 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 REPLACED ARCHIVED 데이터 발견\n")
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
                status_changed_at = row[5]
                archived_at = row[6]
                archive_return_pct = row[7]
                archive_price = row[8]
                archive_phase = row[9]
                archive_reason = row[10]
                
                print(f"\n[{idx}] 추천 ID: {rec_id}")
                print(f"    종목: {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    상태 변경 시점: {status_changed_at}")
                print(f"    ARCHIVED 시점: {archived_at}")
                print(f"    현재 archive_return_pct: {archive_return_pct:,.2f}%")
                print(f"    현재 archive_price: {archive_price:,.0f}원")
                
                # status_changed_at 시점의 날짜 추출
                if isinstance(status_changed_at, str):
                    changed_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                elif isinstance(status_changed_at, datetime):
                    changed_date = status_changed_at.date()
                else:
                    changed_date = status_changed_at
                
                changed_date_str = changed_date.strftime('%Y%m%d')
                
                print(f"    REPLACED 전환일: {changed_date_str}")
                
                try:
                    # REPLACED 전환일의 OHLCV 조회
                    df = api.get_ohlcv(ticker, 10, changed_date_str)
                    
                    if df.empty:
                        print(f"    ⚠️  OHLCV 데이터 없음")
                        error_count += 1
                        continue
                    
                    # changed_date_str에 해당하는 날짜의 종가 조회
                    if 'date' in df.columns:
                        df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                        df_filtered = df[df['date_str'] == changed_date_str]
                        if not df_filtered.empty:
                            replaced_price = float(df_filtered.iloc[-1]['close'])
                        else:
                            # 정확한 날짜가 없으면 그 이전 날짜 사용
                            df_sorted = df.sort_values('date_str')
                            df_before = df_sorted[df_sorted['date_str'] <= changed_date_str]
                            if not df_before.empty:
                                replaced_price = float(df_before.iloc[-1]['close'])
                            else:
                                replaced_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    else:
                        replaced_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                    
                    print(f"    REPLACED 시점 가격 (OHLCV): {replaced_price:,.0f}원")
                    
                    # REPLACED 시점 수익률 계산
                    anchor_close_float = float(anchor_close) if anchor_close else None
                    if anchor_close_float and anchor_close_float > 0:
                        replaced_return_pct = round(((replaced_price - anchor_close_float) / anchor_close_float) * 100, 2)
                        
                        print(f"    REPLACED 시점 수익률: {replaced_return_pct:,.2f}%")
                        
                        # 현재 archive_return_pct와 비교
                        archive_return_pct_float = float(archive_return_pct) if archive_return_pct is not None else None
                        diff = abs(replaced_return_pct - archive_return_pct_float) if archive_return_pct_float is not None else replaced_return_pct
                        if diff > 0.01:
                            print(f"    → 차이: {diff:,.2f}%p (수정 필요)")
                            
                            # archive_phase 재계산
                            if replaced_return_pct > 2:
                                new_archive_phase = 'PROFIT'
                            elif replaced_return_pct < -2:
                                new_archive_phase = 'LOSS'
                            else:
                                new_archive_phase = 'FLAT'
                            
                            print(f"    ✅ 업데이트: archive_return_pct={replaced_return_pct:,.2f}%, archive_price={replaced_price:,.0f}원, archive_phase={new_archive_phase}")
                            
                            # DB 업데이트
                            with db_manager.get_cursor(commit=True) as update_cur:
                                update_cur.execute("""
                                    UPDATE recommendations
                                    SET archive_return_pct = %s,
                                        archive_price = %s,
                                        archive_phase = %s,
                                        updated_at = NOW()
                                    WHERE recommendation_id = %s
                                """, (replaced_return_pct, replaced_price, new_archive_phase, rec_id))
                            
                            update_count += 1
                        else:
                            print(f"    ⏭️  스킵: REPLACED 시점 수익률과 동일 (차이: {diff:.2f}%p)")
                            skip_count += 1
                    else:
                        print(f"    ⚠️  anchor_close가 없어서 계산 불가")
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
    print("REPLACED ARCHIVED 데이터 수정 시작 (OHLCV 조회)...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_replaced_archived_with_ohlcv()
    print("\n완료!")

