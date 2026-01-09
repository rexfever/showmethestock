"""
수익률이 극단적으로 높은 종목들의 실제 가격 변동 확인
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
from datetime import datetime, timedelta

def check_extreme_returns():
    """수익률 100% 이상인 종목들의 실제 가격 변동 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 수익률 100% 이상인 ARCHIVED 종목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_reason,
                    r.status_changed_at,
                    r.archived_at
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct >= 100.0
                ORDER BY r.archive_return_pct DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수익률 100% 이상인 ARCHIVED 종목이 없습니다.")
                return
            
            print(f"수익률 100% 이상인 ARCHIVED 종목: {len(rows)}개\n")
            print("=" * 150)
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                archive_return_pct = row[5]
                archive_price = row[6]
                archive_reason = row[7]
                status_changed_at = row[8]
                archived_at = row[9]
                
                print(f"\n[{idx}] {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    ARCHIVED 수익률: {archive_return_pct:,.2f}%")
                print(f"    ARCHIVED 가격: {archive_price:,.0f}원")
                print(f"    ARCHIVED 사유: {archive_reason}")
                
                # 실제 가격 변동 확인
                try:
                    # REPLACED 시점 또는 ARCHIVED 시점의 날짜 사용
                    if archive_reason == 'REPLACED' and status_changed_at:
                        if isinstance(status_changed_at, str):
                            check_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                        elif isinstance(status_changed_at, datetime):
                            check_date = status_changed_at.date()
                        else:
                            check_date = status_changed_at
                    elif archived_at:
                        if isinstance(archived_at, str):
                            check_date = yyyymmdd_to_date(archived_at.replace('-', '')[:8])
                        elif isinstance(archived_at, datetime):
                            check_date = archived_at.date()
                        else:
                            check_date = archived_at
                    else:
                        check_date = anchor_date
                    
                    check_date_str = check_date.strftime('%Y%m%d') if hasattr(check_date, 'strftime') else str(check_date).replace('-', '')[:8]
                    anchor_date_str = anchor_date.strftime('%Y%m%d') if isinstance(anchor_date, datetime) else str(anchor_date).replace('-', '')[:8]
                    
                    # 최근 200일 데이터 조회 (check_date 기준)
                    df = api.get_ohlcv(ticker, 200, check_date_str)
                    
                    if not df.empty:
                        # 추천일 가격
                        if 'date' in df.columns:
                            df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                            anchor_row = df[df['date_str'] == anchor_date_str]
                            if anchor_row.empty:
                                df_sorted = df.sort_values('date_str')
                                anchor_row = df_sorted[df_sorted['date_str'] >= anchor_date_str]
                                if not anchor_row.empty:
                                    anchor_price_actual = float(anchor_row.iloc[0]['close'])
                                else:
                                    anchor_price_actual = float(df.iloc[0]['close']) if 'close' in df.columns else None
                            else:
                                anchor_price_actual = float(anchor_row.iloc[0]['close'])
                        else:
                            anchor_price_actual = float(df.iloc[0]['close']) if 'close' in df.columns else None
                        
                        # REPLACED/ARCHIVED 시점 가격
                        if 'date' in df.columns:
                            df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                            check_row = df[df['date_str'] == check_date_str]
                            if check_row.empty:
                                df_sorted = df.sort_values('date_str')
                                check_row = df_sorted[df_sorted['date_str'] <= check_date_str]
                                if not check_row.empty:
                                    check_price = float(check_row.iloc[-1]['close'])
                                    check_date_actual = check_row.iloc[-1]['date']
                                else:
                                    check_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                                    check_date_actual = df.iloc[-1]['date'] if 'date' in df.columns else None
                            else:
                                check_price = float(check_row.iloc[0]['close'])
                                check_date_actual = check_row.iloc[0]['date']
                        else:
                            check_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                            check_date_actual = None
                        
                        print(f"\n    실제 가격 변동:")
                        if anchor_price_actual:
                            print(f"      추천일 실제 가격: {anchor_price_actual:,.0f}원")
                            if check_price:
                                actual_return = ((check_price - anchor_price_actual) / anchor_price_actual) * 100
                                print(f"      {archive_reason} 시점 가격 ({check_date_actual}): {check_price:,.0f}원")
                                print(f"      실제 수익률: {actual_return:,.2f}%")
                                
                                # 저장된 수익률과 비교
                                if archive_reason == 'REPLACED' and status_changed_at:
                                    # REPLACED 시점 확인
                                    if isinstance(status_changed_at, str):
                                        replaced_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                                    elif isinstance(status_changed_at, datetime):
                                        replaced_date = status_changed_at.date()
                                    else:
                                        replaced_date = status_changed_at
                                    
                                    replaced_date_str = replaced_date.strftime('%Y%m%d')
                                    replaced_row = df[df['date_str'] == replaced_date_str] if 'date_str' in df.columns else None
                                    if replaced_row is not None and not replaced_row.empty:
                                        replaced_price_actual = float(replaced_row.iloc[0]['close'])
                                        replaced_return_actual = ((replaced_price_actual - anchor_price_actual) / anchor_price_actual) * 100
                                        print(f"      REPLACED 시점 가격 ({replaced_date_str}): {replaced_price_actual:,.0f}원")
                                        print(f"      REPLACED 시점 실제 수익률: {replaced_return_actual:,.2f}%")
                                        
                                        if abs(replaced_return_actual - float(archive_return_pct)) > 1.0:
                                            print(f"      ⚠️  저장된 수익률과 실제 수익률 차이: {abs(replaced_return_actual - float(archive_return_pct)):,.2f}%p")
                                
                                # 가격 배수 확인
                                price_multiplier = check_price / anchor_price_actual
                                print(f"      가격 배수: {price_multiplier:.2f}배")
                                
                                # 저장된 수익률과 비교
                                if abs(actual_return - float(archive_return_pct)) > 1.0:
                                    print(f"      ⚠️  저장된 수익률({archive_return_pct:,.2f}%)과 실제 수익률({actual_return:,.2f}%) 차이: {abs(actual_return - float(archive_return_pct)):,.2f}%p")
                                
                                if price_multiplier > 3.0:
                                    print(f"      ⚠️  가격이 3배 이상 상승했습니다. 실제 주가 변동 확인 필요")
                except Exception as e:
                    print(f"    ⚠️  가격 조회 실패: {e}")
                
                print("-" * 150)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("수익률 100% 이상 종목 실제 가격 변동 확인...")
    print("=" * 150)
    check_extreme_returns()
    print("\n완료!")

