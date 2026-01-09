"""
전체 ARCHIVED 데이터 정책 준수 검증 스크립트
- REPLACED인데 TTL을 초과한 경우 확인
- TTL_EXPIRED인 경우 TTL 만료 시점의 수익률 확인
- NO_MOMENTUM인 경우 broken_return_pct 사용 확인
- 기타 정책 준수 사항 확인
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

def verify_all_archived_policy_compliance():
    """전체 ARCHIVED 데이터 정책 준수 검증"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 모든 ARCHIVED 데이터 조회
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy, anchor_date, archived_at,
                    archive_reason, archive_return_pct, broken_at, broken_return_pct,
                    anchor_close, archive_price, replaced_by_recommendation_id
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                ORDER BY archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("ARCHIVED 데이터가 없습니다.")
                return
            
            print(f"전체 ARCHIVED 데이터: {len(rows)}개\n")
            print("=" * 150)
            
            issues = []
            stats = {
                'total': len(rows),
                'replaced_ttl_violations': 0,
                'ttl_expired_wrong_return': 0,
                'no_momentum_wrong_return': 0,
                'missing_data': 0,
                'compliant': 0
            }
            
            for idx, row in enumerate(rows, 1):
                if idx % 50 == 0:
                    print(f"진행 상황: {idx}/{len(rows)} ({idx*100//len(rows)}%)")
                
                rec_id, ticker, name, strategy, anchor_date, archived_at, \
                archive_reason, archive_return_pct, broken_at, broken_return_pct, \
                anchor_close, archive_price, replaced_by = row
                
                # 필수 데이터 확인
                if not anchor_date or not anchor_close:
                    stats['missing_data'] += 1
                    continue
                
                # TTL 계산
                ttl_days = 25 if strategy == 'midterm' else (15 if strategy == 'v2_lite' else 20)
                anchor_date_obj = anchor_date if isinstance(anchor_date, datetime) else yyyymmdd_to_date(str(anchor_date).replace('-', '')[:8])
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                if not anchor_date_obj:
                    stats['missing_data'] += 1
                    continue
                
                ttl_expiry = get_nth_trading_day_after(anchor_date_obj, ttl_days)
                trading_days = get_trading_days_since(anchor_date_obj)
                
                issue = None
                is_compliant = True
                
                # 1. REPLACED인데 TTL을 초과한 경우
                if archive_reason == 'REPLACED' and trading_days >= ttl_days:
                    issue = {
                        'type': 'REPLACED_BUT_TTL_EXPIRED',
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'current_reason': archive_reason,
                        'should_be': 'TTL_EXPIRED',
                        'trading_days': trading_days,
                        'ttl_days': ttl_days,
                        'ttl_expiry': ttl_expiry,
                        'anchor_date': anchor_date,
                        'archived_at': archived_at
                    }
                    issues.append(issue)
                    stats['replaced_ttl_violations'] += 1
                    is_compliant = False
                
                # 2. TTL_EXPIRED인 경우 TTL 만료 시점의 수익률 확인
                if archive_reason == 'TTL_EXPIRED':
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
                                            'name': name,
                                            'strategy': strategy,
                                            'current_return': archive_return_pct,
                                            'ttl_return': ttl_return_pct,
                                            'ttl_expiry': ttl_expiry,
                                            'anchor_date': anchor_date,
                                            'archived_at': archived_at
                                        }
                                        issues.append(issue)
                                        stats['ttl_expired_wrong_return'] += 1
                                        is_compliant = False
                    except Exception as e:
                        # 가격 조회 실패는 건너뜀 (네트워크 오류 등)
                        pass
                
                # 3. NO_MOMENTUM인 경우 broken_return_pct 사용 확인
                if archive_reason == 'NO_MOMENTUM' and broken_return_pct is not None:
                    if archive_return_pct is None or abs(float(broken_return_pct) - float(archive_return_pct)) > 0.01:
                        issue = {
                            'type': 'NO_MOMENTUM_WRONG_RETURN',
                            'rec_id': rec_id,
                            'ticker': ticker,
                            'name': name,
                            'strategy': strategy,
                            'current_return': archive_return_pct,
                            'broken_return': broken_return_pct,
                            'anchor_date': anchor_date,
                            'archived_at': archived_at
                        }
                        issues.append(issue)
                        stats['no_momentum_wrong_return'] += 1
                        is_compliant = False
                
                if is_compliant:
                    stats['compliant'] += 1
            
            print("\n" + "=" * 150)
            print(f"\n[검증 결과]")
            print(f"  전체 항목: {stats['total']}개")
            print(f"  정책 준수: {stats['compliant']}개")
            print(f"  문제 항목: {len(issues)}개")
            print(f"    - REPLACED인데 TTL 초과: {stats['replaced_ttl_violations']}개")
            print(f"    - TTL_EXPIRED 수익률 불일치: {stats['ttl_expired_wrong_return']}개")
            print(f"    - NO_MOMENTUM 수익률 불일치: {stats['no_momentum_wrong_return']}개")
            print(f"    - 필수 데이터 없음: {stats['missing_data']}개")
            
            if issues:
                print(f"\n[문제 상세]")
                for i, issue in enumerate(issues[:20], 1):  # 최대 20개만 표시
                    print(f"\n{i}. {issue['ticker']} ({issue.get('name', 'N/A')}) - {issue['type']}")
                    if issue['type'] == 'REPLACED_BUT_TTL_EXPIRED':
                        print(f"   현재: {issue['current_reason']} → 변경 필요: {issue['should_be']}")
                        print(f"   거래일 수: {issue['trading_days']}일 (TTL: {issue['ttl_days']}일)")
                        print(f"   anchor_date: {issue['anchor_date']}, archived_at: {issue['archived_at']}")
                    elif issue['type'] == 'TTL_EXPIRED_WRONG_RETURN':
                        print(f"   현재 수익률: {issue['current_return']}%")
                        print(f"   TTL 시점 수익률: {issue['ttl_return']}%")
                        print(f"   TTL 만료일: {issue['ttl_expiry']}")
                    elif issue['type'] == 'NO_MOMENTUM_WRONG_RETURN':
                        print(f"   현재 수익률: {issue['current_return']}%")
                        print(f"   broken_return_pct: {issue['broken_return']}%")
                
                if len(issues) > 20:
                    print(f"\n... 외 {len(issues) - 20}개 항목 생략")
            else:
                print("\n✅ 모든 데이터가 정책을 준수합니다.")
            
            # 통계 요약
            print(f"\n[통계 요약]")
            print(f"  정책 준수율: {stats['compliant']*100/stats['total']:.2f}%")
            print(f"  문제율: {len(issues)*100/stats['total']:.2f}%")
            
            return {
                'total': stats['total'],
                'compliant': stats['compliant'],
                'issues': len(issues),
                'issue_details': issues
            }
            
    except Exception as e:
        import traceback
        print(f"오류 발생: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    verify_all_archived_policy_compliance()

