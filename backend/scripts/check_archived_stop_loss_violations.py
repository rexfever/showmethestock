"""
ARCHIVED 데이터 중 손절 정책 위반 케이스 조회 및 분석
- v2_lite: stop_loss = -2.0% → archive_return_pct가 -2%보다 낮으면 위반
- midterm: stop_loss = -7.0% → archive_return_pct가 -7%보다 낮으면 위반
"""
import sys
import os
from pathlib import Path
from decimal import Decimal

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date
from datetime import datetime

def get_stop_loss_pct(strategy):
    """전략별 손절 기준 반환"""
    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
        return -2.0
    elif strategy == "midterm" or strategy == "MIDTERM":
        return -7.0
    else:
        return -2.0  # 기본값

def check_archived_stop_loss_violations():
    """ARCHIVED 데이터 중 손절 정책 위반 케이스 조회"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 모든 ARCHIVED 종목 조회 (archive_return_pct가 -7% 이하인 것들)
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
                    r.archive_reason,
                    r.reason
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct IS NOT NULL
                AND r.archive_return_pct < -7.0
                ORDER BY r.archive_return_pct ASC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("손실이 -7%를 넘는 ARCHIVED 항목이 없습니다.")
                return
            
            print(f"손실이 -7%를 넘는 ARCHIVED 항목: {len(rows)}개\n")
            print("=" * 150)
            
            violations = []
            potential_issues = []
            
            for row in rows:
                rec_id, ticker, name, anchor_date, anchor_close, strategy, broken_at, broken_return_pct, \
                status_changed_at, archived_at, archive_return_pct, archive_price, archive_phase, \
                archive_reason, reason = row
                
                stop_loss_pct = get_stop_loss_pct(strategy)
                archive_return_pct_float = float(archive_return_pct) if archive_return_pct else None
                
                # 정책 위반 여부 확인
                is_violation = False
                violation_reason = []
                
                # 1. 전략별 손절 기준 확인
                if archive_return_pct_float and archive_return_pct_float < stop_loss_pct:
                    is_violation = True
                    violation_reason.append(f"전략({strategy}) 손절 기준({stop_loss_pct}%)보다 낮음: {archive_return_pct_float:.2f}%")
                
                # 2. broken_return_pct와 archive_return_pct 일치 여부 확인
                if broken_return_pct is not None:
                    broken_return_pct_float = float(broken_return_pct)
                    if archive_return_pct_float is not None:
                        if abs(broken_return_pct_float - archive_return_pct_float) > 0.01:  # 0.01% 이상 차이
                            is_violation = True
                            violation_reason.append(f"broken_return_pct({broken_return_pct_float:.2f}%)와 archive_return_pct({archive_return_pct_float:.2f}%) 불일치")
                
                # 3. broken_at이 없는데 broken_return_pct가 있는 경우
                if broken_at is None and broken_return_pct is not None:
                    is_violation = True
                    violation_reason.append("broken_at이 None인데 broken_return_pct가 있음")
                
                # 4. 손절 조건 만족했는데 archive_reason이 NO_MOMENTUM이 아닌 경우
                if archive_return_pct_float and archive_return_pct_float <= stop_loss_pct:
                    if archive_reason != 'NO_MOMENTUM':
                        is_violation = True
                        violation_reason.append(f"손절 조건 만족했는데 archive_reason이 '{archive_reason}'임 (NO_MOMENTUM이어야 함)")
                
                # 5. broken_at이 있는데 broken_return_pct가 없는 경우
                if broken_at is not None and broken_return_pct is None:
                    potential_issues.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'issue': "broken_at이 있는데 broken_return_pct가 None"
                    })
                
                if is_violation:
                    violations.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'stop_loss_pct': stop_loss_pct,
                        'archive_return_pct': archive_return_pct_float,
                        'broken_return_pct': float(broken_return_pct) if broken_return_pct else None,
                        'broken_at': broken_at,
                        'archive_reason': archive_reason,
                        'violation_reasons': violation_reason,
                        'anchor_date': anchor_date,
                        'archived_at': archived_at
                    })
            
            # 결과 출력
            print(f"\n정책 위반 항목: {len(violations)}개\n")
            print("=" * 150)
            
            for v in violations:
                print(f"\n[위반 항목]")
                print(f"  티커: {v['ticker']} ({v['name']})")
                print(f"  전략: {v['strategy']} (손절 기준: {v['stop_loss_pct']}%)")
                print(f"  archive_return_pct: {v['archive_return_pct']:.2f}%")
                print(f"  broken_return_pct: {v['broken_return_pct']:.2f}%" if v['broken_return_pct'] else "  broken_return_pct: None")
                print(f"  broken_at: {v['broken_at']}")
                print(f"  archive_reason: {v['archive_reason']}")
                print(f"  anchor_date: {v['anchor_date']}")
                print(f"  archived_at: {v['archived_at']}")
                print(f"  위반 사유:")
                for reason in v['violation_reasons']:
                    print(f"    - {reason}")
                print(f"  recommendation_id: {v['rec_id']}")
                print("-" * 150)
            
            if potential_issues:
                print(f"\n잠재적 문제 항목: {len(potential_issues)}개\n")
                for issue in potential_issues:
                    print(f"  - {issue['ticker']} ({issue['name']}): {issue['issue']}")
            
            # 통계 출력
            print(f"\n\n[통계]")
            print(f"  전체 조회 항목: {len(rows)}개")
            print(f"  정책 위반 항목: {len(violations)}개")
            print(f"  잠재적 문제 항목: {len(potential_issues)}개")
            
            # 전략별 통계
            strategy_stats = {}
            for v in violations:
                strategy = v['strategy']
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {'count': 0, 'avg_loss': 0, 'min_loss': 0, 'max_loss': 0}
                strategy_stats[strategy]['count'] += 1
                loss = v['archive_return_pct']
                strategy_stats[strategy]['avg_loss'] += loss
                if strategy_stats[strategy]['min_loss'] == 0 or loss < strategy_stats[strategy]['min_loss']:
                    strategy_stats[strategy]['min_loss'] = loss
                if loss > strategy_stats[strategy]['max_loss']:
                    strategy_stats[strategy]['max_loss'] = loss
            
            for strategy, stats in strategy_stats.items():
                stats['avg_loss'] = stats['avg_loss'] / stats['count']
                print(f"\n  [{strategy}]")
                print(f"    위반 건수: {stats['count']}개")
                print(f"    평균 손실: {stats['avg_loss']:.2f}%")
                print(f"    최소 손실: {stats['min_loss']:.2f}%")
                print(f"    최대 손실: {stats['max_loss']:.2f}%")
            
            return violations, potential_issues
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == '__main__':
    check_archived_stop_loss_violations()

