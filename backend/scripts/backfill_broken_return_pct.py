#!/usr/bin/env python3
"""
BROKEN 상태 추천의 broken_return_pct 백필 스크립트
"""
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import db_manager
from date_helper import get_kst_now
from kiwoom_api import api

def get_price_at_date(ticker: str, date_str: str) -> float:
    """특정 날짜의 종가 조회"""
    try:
        df = api.get_ohlcv(ticker, 5, date_str)
        if df.empty:
            return None
        
        # 날짜 필터링
        date_dt = datetime.strptime(date_str, '%Y%m%d').date()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df_filtered = df[df['date'] == date_dt]
            if not df_filtered.empty:
                return float(df_filtered.iloc[-1]['close'])
            else:
                # 가장 가까운 이전 거래일 데이터 사용
                df_sorted = df.sort_values('date')
                df_before = df_sorted[df_sorted['date'] <= date_dt]
                if not df_before.empty:
                    return float(df_before.iloc[-1]['close'])
        
        # date 컬럼이 없으면 마지막 행 사용
        return float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
    except Exception as e:
        print(f"  ⚠️ 가격 조회 실패 ({ticker}, {date_str}): {e}")
        return None

def main():
    """broken_return_pct 백필"""
    print("=" * 60)
    print("🚀 BROKEN 상태 추천의 broken_return_pct 백필 시작")
    print("=" * 60)
    
    today_str = get_kst_now().strftime('%Y%m%d')
    
    # broken_return_pct가 NULL인 BROKEN 추천 조회
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT recommendation_id, ticker, name, anchor_date, anchor_close, 
                   status_changed_at, broken_at, reason
            FROM recommendations
            WHERE status = 'BROKEN'
            AND scanner_version = 'v3'
            AND broken_return_pct IS NULL
            ORDER BY status_changed_at ASC NULLS FIRST, broken_at ASC NULLS FIRST
        """)
        
        rows = cur.fetchall()
        total_count = len(rows)
        print(f"\n📊 broken_return_pct가 NULL인 BROKEN 추천: {total_count}개\n")
        
        if total_count == 0:
            print("✅ 백필할 데이터가 없습니다.")
            return
        
        updated_count = 0
        failed_count = 0
        
        for idx, row in enumerate(rows, 1):
            if isinstance(row, dict):
                rec_id = row.get('recommendation_id')
                ticker = row.get('ticker')
                name = row.get('name')
                anchor_date = row.get('anchor_date')
                anchor_close = row.get('anchor_close')
                status_changed_at = row.get('status_changed_at')
                broken_at = row.get('broken_at')
                reason = row.get('reason')
            else:
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                status_changed_at = row[5]
                broken_at = row[6]
                reason = row[7] if len(row) > 7 else None
            
            if not ticker or ticker == 'NORESULT':
                continue
            
            if not anchor_close or anchor_close <= 0:
                print(f"[{idx}/{total_count}] {ticker}: anchor_close 없음, 건너뜀")
                failed_count += 1
                continue
            
            # BROKEN 전환 시점 결정 (broken_at > status_changed_at > anchor_date)
            target_date_str = None
            if broken_at:
                try:
                    if isinstance(broken_at, str):
                        target_date_str = broken_at.replace('-', '')[:8]
                    else:
                        target_date_str = broken_at.strftime('%Y%m%d')
                except:
                    pass
            
            if not target_date_str and status_changed_at:
                try:
                    if isinstance(status_changed_at, str):
                        target_date_str = status_changed_at.replace('-', '')[:8]
                    else:
                        target_date_str = status_changed_at.strftime('%Y%m%d')
                except:
                    pass
            
            if not target_date_str and anchor_date:
                try:
                    if isinstance(anchor_date, str):
                        target_date_str = anchor_date.replace('-', '')[:8]
                    else:
                        target_date_str = anchor_date.strftime('%Y%m%d')
                except:
                    pass
            
            if not target_date_str:
                print(f"[{idx}/{total_count}] {ticker}: 날짜 정보 없음, 건너뜀")
                failed_count += 1
                continue
            
            # 전환 시점의 가격 조회
            print(f"[{idx}/{total_count}] {ticker} ({name or 'N/A'}): {target_date_str} 시점 가격 조회 중...")
            broken_price = get_price_at_date(ticker, target_date_str)
            
            if not broken_price or broken_price <= 0:
                print(f"  ❌ 가격 조회 실패")
                failed_count += 1
                continue
            
            # broken_return_pct 계산
            broken_return_pct = round(((broken_price - float(anchor_close)) / float(anchor_close)) * 100, 2)
            
            # DB 업데이트
            try:
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("""
                        UPDATE recommendations
                        SET broken_return_pct = %s
                        WHERE recommendation_id = %s
                    """, (broken_return_pct, rec_id))
                
                print(f"  ✅ broken_return_pct 업데이트: {broken_return_pct}% (가격: {broken_price}, 기준가: {anchor_close})")
                updated_count += 1
            except Exception as e:
                print(f"  ❌ DB 업데이트 실패: {e}")
                failed_count += 1
        
        print("\n" + "=" * 60)
        print("📊 백필 결과")
        print("=" * 60)
        print(f"✅ 성공: {updated_count}개")
        print(f"❌ 실패: {failed_count}개")
        print(f"📅 총: {total_count}개")
        print("=" * 60)

if __name__ == "__main__":
    import pandas as pd
    main()


