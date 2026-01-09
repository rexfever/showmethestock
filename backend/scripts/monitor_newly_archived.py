"""
최근 ARCHIVED된 항목 모니터링 스크립트
- 최근 N일 동안 ARCHIVED된 항목의 정책 준수 확인
- broken_at이 None인 항목 감지
- 정책 위반 항목 리포트
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from services.state_transition_service import get_trading_days_since
from services.recommendation_service import get_nth_trading_day_after
from date_helper import yyyymmdd_to_date, get_kst_now
from kiwoom_api import api


def check_policy_compliance(rec_id, ticker, name, strategy, anchor_date, archived_at,
                           archive_reason, archive_return_pct, broken_at, broken_return_pct,
                           anchor_close, archive_price):
    """개별 항목의 정책 준수 여부 확인"""
    issues = []
    
    # 1. broken_return_pct가 있으면 broken_at도 있어야 함
    if broken_return_pct is not None and broken_at is None:
        issues.append({
            'type': 'MISSING_BROKEN_AT',
            'message': f'broken_return_pct({broken_return_pct}%)가 있는데 broken_at이 None입니다.'
        })
    
    # 2. broken_return_pct가 있으면 archive_return_pct는 broken_return_pct와 일치해야 함
    if broken_return_pct is not None and archive_return_pct is not None:
        if abs(float(broken_return_pct) - float(archive_return_pct)) > 0.01:
            issues.append({
                'type': 'BROKEN_ARCHIVE_RETURN_MISMATCH',
                'message': f'broken_return_pct({broken_return_pct}%)와 archive_return_pct({archive_return_pct}%)가 일치하지 않습니다.'
            })
    
    # 3. 손절 조건 만족 시 archive_reason은 NO_MOMENTUM이어야 함
    if archive_return_pct is not None:
        stop_loss_pct = -7.0 if strategy == 'midterm' else -2.0
        if float(archive_return_pct) <= stop_loss_pct:
            if archive_reason != 'NO_MOMENTUM':
                issues.append({
                    'type': 'STOP_LOSS_WRONG_REASON',
                    'message': f'손절 조건 만족({archive_return_pct}% <= {stop_loss_pct}%)인데 archive_reason이 "{archive_reason}"입니다. NO_MOMENTUM이어야 합니다.'
                })
    
    # 4. TTL_EXPIRED인 경우 TTL 만료 시점의 수익률 확인
    if archive_reason == 'TTL_EXPIRED':
        ttl_days = 25 if strategy == 'midterm' else 15
        anchor_date_obj = anchor_date if isinstance(anchor_date, datetime) else yyyymmdd_to_date(str(anchor_date).replace('-', '')[:8])
        if isinstance(anchor_date_obj, datetime):
            anchor_date_obj = anchor_date_obj.date()
        
        if anchor_date_obj:
            ttl_expiry = get_nth_trading_day_after(anchor_date_obj, ttl_days)
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
                                issues.append({
                                    'type': 'TTL_EXPIRED_WRONG_RETURN',
                                    'message': f'TTL 만료 시점 수익률({ttl_return_pct}%)과 archive_return_pct({archive_return_pct}%)가 일치하지 않습니다.'
                                })
            except Exception as e:
                issues.append({
                    'type': 'TTL_EXPIRED_CHECK_ERROR',
                    'message': f'TTL 만료 시점 수익률 확인 중 오류: {str(e)}'
                })
    
    return issues


def monitor_newly_archived(days=7):
    """최근 N일 동안 ARCHIVED된 항목 모니터링"""
    try:
        cutoff_date = get_kst_now() - timedelta(days=days)
        
        with db_manager.get_cursor(commit=False) as cur:
            # 최근 N일 동안 ARCHIVED된 항목 조회
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, strategy, anchor_date, archived_at,
                    archive_reason, archive_return_pct, broken_at, broken_return_pct,
                    anchor_close, archive_price
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND archived_at >= %s
                ORDER BY archived_at DESC
            """, (cutoff_date,))
            
            rows = cur.fetchall()
            
            if not rows:
                print(f"최근 {days}일 동안 ARCHIVED된 항목이 없습니다.")
                return
            
            print(f"최근 {days}일 동안 ARCHIVED된 항목: {len(rows)}개\n")
            print("=" * 150)
            
            issues_found = []
            broken_at_missing = []
            stats = {
                'total': len(rows),
                'compliant': 0,
                'with_issues': 0,
                'broken_at_missing': 0
            }
            
            for idx, row in enumerate(rows, 1):
                rec_id, ticker, name, strategy, anchor_date, archived_at, \
                archive_reason, archive_return_pct, broken_at, broken_return_pct, \
                anchor_close, archive_price = row
                
                # broken_at이 None인 항목 확인
                if broken_return_pct is not None and broken_at is None:
                    broken_at_missing.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'broken_return_pct': broken_return_pct,
                        'archived_at': archived_at
                    })
                    stats['broken_at_missing'] += 1
                
                # 정책 준수 확인
                issues = check_policy_compliance(
                    rec_id, ticker, name, strategy, anchor_date, archived_at,
                    archive_reason, archive_return_pct, broken_at, broken_return_pct,
                    anchor_close, archive_price
                )
                
                if issues:
                    issues_found.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'archive_reason': archive_reason,
                        'archived_at': archived_at,
                        'issues': issues
                    })
                    stats['with_issues'] += 1
                else:
                    stats['compliant'] += 1
            
            # 결과 출력
            print(f"\n📊 모니터링 결과 요약")
            print("=" * 150)
            print(f"전체 항목: {stats['total']}개")
            print(f"정책 준수: {stats['compliant']}개")
            print(f"문제 항목: {stats['with_issues']}개")
            print(f"broken_at 누락: {stats['broken_at_missing']}개")
            
            # broken_at 누락 항목 출력
            if broken_at_missing:
                print(f"\n⚠️ broken_at이 None인 항목 ({len(broken_at_missing)}개)")
                print("=" * 150)
                for item in broken_at_missing:
                    print(f"  - {item['ticker']} ({item['name']}): broken_return_pct={item['broken_return_pct']}%, archived_at={item['archived_at']}")
            
            # 정책 위반 항목 출력
            if issues_found:
                print(f"\n❌ 정책 위반 항목 ({len(issues_found)}개)")
                print("=" * 150)
                for item in issues_found:
                    print(f"\n  [{item['ticker']}] {item['name']} (전략: {item['strategy']})")
                    print(f"    - ARCHIVED 일시: {item['archived_at']}")
                    print(f"    - archive_reason: {item['archive_reason']}")
                    for issue in item['issues']:
                        print(f"    - [{issue['type']}] {issue['message']}")
            else:
                print(f"\n✅ 모든 항목이 정책을 준수합니다!")
            
            return {
                'stats': stats,
                'broken_at_missing': broken_at_missing,
                'issues_found': issues_found
            }
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='최근 ARCHIVED된 항목 모니터링')
    parser.add_argument('--days', type=int, default=7, help='모니터링 기간 (일, 기본값: 7)')
    
    args = parser.parse_args()
    
    print(f"최근 {args.days}일 동안 ARCHIVED된 항목 모니터링 시작...")
    print("=" * 150)
    monitor_newly_archived(days=args.days)
    print("\n완료!")

