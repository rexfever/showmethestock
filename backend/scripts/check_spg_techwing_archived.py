"""
에스피지(SPG)와 테크윙(Techwing) ARCHIVED 데이터 검증 스크립트
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

def check_spg_techwing_archived():
    """에스피지(SPG)와 테크윙(Techwing) ARCHIVED 데이터 검증"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 에스피지(058610), 테크윙 관련 종목 찾기
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy, anchor_date, archived_at,
                    archive_reason, archive_return_pct, broken_at, broken_return_pct,
                    anchor_close, archive_price, replaced_by_recommendation_id, status
                FROM recommendations
                WHERE scanner_version = 'v3'
                AND (ticker = '058610' 
                     OR name LIKE '%에스피지%' OR name LIKE '%SPG%'
                     OR name LIKE '%테크윙%' OR name LIKE '%Techwing%')
                ORDER BY archived_at DESC NULLS LAST, created_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("에스피지/테크윙 관련 데이터가 없습니다.")
                return
            
            print(f"에스피지/테크윙 관련 데이터: {len(rows)}개\n")
            print("=" * 150)
            
            issues = []
            
            for row in rows:
                rec_id, ticker, name, strategy, anchor_date, archived_at, \
                archive_reason, archive_return_pct, broken_at, broken_return_pct, \
                anchor_close, archive_price, replaced_by, status = row
                
                print(f"\n[{ticker}] {name if name else 'N/A'} ({status})")
                print(f"  recommendation_id: {rec_id}")
                print(f"  전략: {strategy}")
                print(f"  archive_reason: {archive_reason}")
                print(f"  archive_return_pct: {archive_return_pct}%")
                print(f"  anchor_date: {anchor_date}")
                print(f"  archived_at: {archived_at}")
                print(f"  broken_at: {broken_at}")
                print(f"  broken_return_pct: {broken_return_pct}")
                print(f"  replaced_by: {replaced_by}")
                
                if status != 'ARCHIVED':
                    print(f"  ⚠️ ARCHIVED 상태가 아님 (건너뜀)")
                    continue
                
                if not anchor_date:
                    print(f"  ⚠️ anchor_date 없음 (건너뜀)")
                    continue
                
                # TTL 계산
                ttl_days = 25 if strategy == 'midterm' else (15 if strategy == 'v2_lite' else 20)
                anchor_date_obj = anchor_date if isinstance(anchor_date, datetime) else yyyymmdd_to_date(str(anchor_date).replace('-', '')[:8])
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                ttl_expiry = get_nth_trading_day_after(anchor_date_obj, ttl_days)
                archived_at_obj = archived_at.date() if isinstance(archived_at, datetime) else archived_at
                
                trading_days = get_trading_days_since(anchor_date_obj)
                
                print(f"  TTL: {ttl_days}거래일")
                print(f"  TTL 만료일: {ttl_expiry}")
                print(f"  실제 거래일 수: {trading_days}거래일")
                print(f"  TTL 초과 여부: {trading_days >= ttl_days}")
                
                # 문제 확인
                issue = None
                
                # 1. REPLACED인데 TTL을 초과한 경우
                if archive_reason == 'REPLACED' and trading_days >= ttl_days:
                    issue = {
                        'type': 'REPLACED_BUT_TTL_EXPIRED',
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'current_reason': archive_reason,
                        'should_be': 'TTL_EXPIRED',
                        'trading_days': trading_days,
                        'ttl_days': ttl_days,
                        'ttl_expiry': ttl_expiry
                    }
                    print(f"  ⚠️ 문제: REPLACED인데 TTL을 초과함 → TTL_EXPIRED로 변경 필요")
                    issues.append(issue)
                
                # 2. TTL_EXPIRED인데 TTL 만료 시점 수익률이 아닌 경우
                if archive_reason == 'TTL_EXPIRED':
                    # TTL 만료 시점의 가격 조회
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
                                    
                                    if archive_return_pct is None or abs(ttl_return_pct - float(archive_return_pct)) > 0.01:
                                        issue = {
                                            'type': 'TTL_EXPIRED_WRONG_RETURN',
                                            'rec_id': rec_id,
                                            'ticker': ticker,
                                            'current_return': archive_return_pct,
                                            'ttl_return': ttl_return_pct,
                                            'ttl_expiry': ttl_expiry
                                        }
                                        print(f"  ⚠️ 문제: TTL 만료 시점 수익률 불일치")
                                        print(f"    현재: {archive_return_pct}%")
                                        print(f"    TTL 시점: {ttl_return_pct}%")
                                        issues.append(issue)
                                    else:
                                        print(f"  ✅ TTL 시점 수익률 정확함: {ttl_return_pct}%")
                    except Exception as e:
                        print(f"  ⚠️ TTL 시점 가격 조회 실패: {e}")
            
            print("\n" + "=" * 150)
            print(f"\n[결과]")
            print(f"  전체 항목: {len(rows)}개")
            print(f"  문제 항목: {len(issues)}개")
            
            if issues:
                print(f"\n[문제 상세]")
                for i, issue in enumerate(issues, 1):
                    print(f"\n{i}. {issue['ticker']} ({issue['type']})")
                    if issue['type'] == 'REPLACED_BUT_TTL_EXPIRED':
                        print(f"   현재: {issue['current_reason']}")
                        print(f"   변경 필요: {issue['should_be']}")
                        print(f"   거래일 수: {issue['trading_days']}일 (TTL: {issue['ttl_days']}일)")
                    elif issue['type'] == 'TTL_EXPIRED_WRONG_RETURN':
                        print(f"   현재 수익률: {issue['current_return']}%")
                        print(f"   TTL 시점 수익률: {issue['ttl_return']}%")
            else:
                print("\n✅ 모든 데이터가 정책을 준수합니다.")
            
    except Exception as e:
        import traceback
        print(f"오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_spg_techwing_archived()

