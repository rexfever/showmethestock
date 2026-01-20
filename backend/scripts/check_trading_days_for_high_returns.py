"""
수익률 100% 이상 종목들의 추천일부터 REPLACED/ARCHIVED 시점까지의 거래일 수 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date
import holidays
from datetime import datetime, timedelta

def get_trading_days_between_dates(start_date, end_date):
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

def check_trading_days_for_high_returns():
    """수익률 100% 이상 종목들의 거래일 수 확인"""
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
                
                # 거래일 수 계산
                if archive_reason == 'REPLACED' and status_changed_at:
                    end_date = status_changed_at
                    end_date_label = "REPLACED 시점"
                elif archived_at:
                    end_date = archived_at
                    end_date_label = "ARCHIVED 시점"
                else:
                    end_date = None
                    end_date_label = "알 수 없음"
                
                if end_date:
                    if isinstance(end_date, str):
                        end_date_obj = yyyymmdd_to_date(end_date.replace('-', '')[:8])
                    elif isinstance(end_date, datetime):
                        end_date_obj = end_date.date()
                    else:
                        end_date_obj = end_date
                    
                    trading_days = get_trading_days_between_dates(anchor_date, end_date_obj)
                    
                    # 실제 일수 계산
                    if isinstance(anchor_date, datetime):
                        anchor_date_obj = anchor_date.date()
                    else:
                        anchor_date_obj = anchor_date
                    
                    actual_days = (end_date_obj - anchor_date_obj).days
                    
                    print(f"\n    기간 분석:")
                    print(f"      {end_date_label}: {end_date_obj}")
                    print(f"      실제 일수: {actual_days}일")
                    print(f"      거래일 수: {trading_days}일")
                    print(f"      주말/공휴일 제외: {actual_days - trading_days}일")
                    
                    # 일평균 수익률 계산
                    if trading_days > 0:
                        archive_return_pct_float = float(archive_return_pct)
                        daily_return = (archive_return_pct_float / trading_days)
                        print(f"      일평균 수익률: {daily_return:.2f}%")
                        
                        # 복리 수익률 계산 (일평균 수익률로 복리 적용 시)
                        compound_return = ((1 + archive_return_pct_float / 100) ** (1 / trading_days) - 1) * 100
                        print(f"      복리 일평균 수익률: {compound_return:.2f}%")
                        
                        # 경고: 비정상적으로 높은 일평균 수익률
                        if daily_return > 5.0:
                            print(f"      ⚠️  일평균 수익률이 5%를 초과합니다. 비정상적으로 높은 수익률입니다.")
                        if compound_return > 3.0:
                            print(f"      ⚠️  복리 일평균 수익률이 3%를 초과합니다. 매우 비정상적입니다.")
                    
                    # 가격 변동 분석
                    if anchor_close and archive_price:
                        price_multiplier = float(archive_price) / float(anchor_close)
                        print(f"\n    가격 변동:")
                        print(f"      가격 배수: {price_multiplier:.2f}배")
                        print(f"      가격 상승: {float(archive_price) - float(anchor_close):,.0f}원")
                        
                        if trading_days > 0:
                            daily_price_increase = (float(archive_price) - float(anchor_close)) / trading_days
                            print(f"      일평균 가격 상승: {daily_price_increase:,.0f}원")
                
                print("-" * 150)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("수익률 100% 이상 종목 거래일 수 확인...")
    print("=" * 150)
    check_trading_days_for_high_returns()
    print("\n완료!")

