"""
ARCHIVED된 종목 중 -10% 이상 손실이었는데도 NO_MOMENTUM이 아닌 다른 사유로 종료된 케이스 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from datetime import datetime

def check_archived_loss_over_10pct():
    """ARCHIVED된 종목 중 -10% 이상 손실이었는데도 NO_MOMENTUM이 아닌 케이스 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ARCHIVED된 종목 중 -10% 이상 손실인데 NO_MOMENTUM이 아닌 케이스 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_reason,
                    r.archive_phase,
                    r.broken_at,
                    r.broken_return_pct,
                    r.reason,
                    r.archived_at
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct < -10.0
                AND r.archive_reason != 'NO_MOMENTUM'
                ORDER BY r.archive_return_pct ASC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("ARCHIVED된 종목 중 -10% 이상 손실인데 NO_MOMENTUM이 아닌 케이스가 없습니다.")
                return
            
            print(f"ARCHIVED된 종목 중 -10% 이상 손실인데 NO_MOMENTUM이 아닌 케이스: {len(rows)}개\n")
            print("=" * 150)
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                strategy = row[5]
                archive_return_pct = row[6]
                archive_price = row[7]
                archive_reason = row[8]
                archive_phase = row[9]
                broken_at = row[10]
                broken_return_pct = row[11]
                reason = row[12]
                archived_at = row[13]
                
                print(f"\n[{idx}] {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    전략: {strategy}")
                print(f"    ARCHIVED 수익률: {archive_return_pct:,.2f}%")
                print(f"    ARCHIVED 가격: {archive_price:,.0f}원")
                print(f"    ARCHIVED 사유: {archive_reason}")
                print(f"    ARCHIVED 단계: {archive_phase}")
                print(f"    BROKEN 시점: {broken_at}")
                print(f"    BROKEN 수익률: {broken_return_pct}%")
                print(f"    BROKEN 사유 (reason): {reason}")
                print(f"    ARCHIVED 시점: {archived_at}")
                
                # 문제 분석
                issues = []
                
                if archive_reason == 'TTL_EXPIRED':
                    if archive_return_pct < -10.0:
                        issues.append(f"TTL_EXPIRED로 종료되었지만 손실이 -10% 이상({archive_return_pct:,.2f}%)입니다. NO_MOMENTUM으로 종료되어야 했을 수 있습니다.")
                
                elif archive_reason == 'REPLACED':
                    if archive_return_pct < -10.0:
                        issues.append(f"REPLACED로 종료되었지만 손실이 -10% 이상({archive_return_pct:,.2f}%)입니다. NO_MOMENTUM으로 종료되어야 했을 수 있습니다.")
                
                # BROKEN을 거쳤는지 확인
                if broken_at:
                    if broken_return_pct and broken_return_pct < -10.0:
                        if reason != 'NO_MOMENTUM':
                            issues.append(f"BROKEN 시점에 손실이 -10% 이상({broken_return_pct}%)이었는데 reason이 '{reason}'입니다. NO_MOMENTUM이어야 합니다.")
                    elif broken_return_pct and broken_return_pct >= -10.0:
                        issues.append(f"BROKEN 시점 수익률({broken_return_pct}%)은 -10% 미만이었지만, ARCHIVED 시점 수익률({archive_return_pct:,.2f}%)은 -10% 미만입니다.")
                else:
                    if archive_return_pct < -10.0:
                        issues.append(f"BROKEN을 거치지 않고 바로 ARCHIVED되었는데 손실이 -10% 이상입니다. BROKEN으로 전환되어야 했습니다.")
                
                if issues:
                    print(f"\n    ⚠️  문제:")
                    for issue in issues:
                        print(f"      - {issue}")
                else:
                    print(f"\n    ✅ 정상: {archive_reason}로 종료된 것이 적절합니다.")
                
                print("-" * 150)
            
            print(f"\n[요약]")
            print(f"  총 {len(rows)}개의 종목이 -10% 이상 손실인데 NO_MOMENTUM이 아님")
            print(f"  평균 손실: {sum(float(row[6]) for row in rows) / len(rows):.2f}%")
            print(f"  최대 손실: {min(float(row[6]) for row in rows):.2f}%")
            
            # 사유별 통계
            reason_stats = {}
            for row in rows:
                reason = row[8]  # archive_reason
                reason_stats[reason] = reason_stats.get(reason, 0) + 1
            
            print(f"\n  사유별 통계:")
            for reason, count in sorted(reason_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"    {reason}: {count}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ARCHIVED된 종목 중 -10% 이상 손실인데 NO_MOMENTUM이 아닌 케이스 확인...")
    print("=" * 150)
    check_archived_loss_over_10pct()
    print("\n완료!")


