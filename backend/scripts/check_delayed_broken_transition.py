"""
-10% 이상 손실이었는데도 BROKEN 전환이 늦었던 케이스 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from datetime import datetime

def check_delayed_broken_transition():
    """-10% 이상 손실이었는데도 BROKEN 전환이 늦었던 케이스 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # BROKEN 또는 ARCHIVED된 종목 중 -10% 이상 손실인 케이스 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.status,
                    r.broken_at,
                    r.broken_return_pct,
                    r.reason,
                    r.archive_return_pct,
                    r.archive_reason,
                    r.archived_at
                FROM recommendations r
                WHERE r.status IN ('BROKEN', 'ARCHIVED')
                AND r.scanner_version = 'v3'
                AND (
                    (r.broken_return_pct IS NOT NULL AND r.broken_return_pct < -10.0)
                    OR (r.archive_return_pct IS NOT NULL AND r.archive_return_pct < -10.0)
                )
                ORDER BY 
                    COALESCE(r.broken_return_pct, r.archive_return_pct) ASC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("-10% 이상 손실인 BROKEN/ARCHIVED 종목이 없습니다.")
                return
            
            print(f"-10% 이상 손실인 BROKEN/ARCHIVED 종목: {len(rows)}개\n")
            print("=" * 150)
            
            delayed_cases = []
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                strategy = row[5]
                status = row[6]
                broken_at = row[7]
                broken_return_pct = row[8]
                reason = row[9]
                archive_return_pct = row[10]
                archive_reason = row[11]
                archived_at = row[12]
                
                # 전략별 손절 조건 확인
                stop_loss_pct = -2.0  # 기본값
                if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                    stop_loss_pct = -2.0
                elif strategy == "midterm" or strategy == "MIDTERM":
                    stop_loss_pct = -7.0
                
                # 실제 손실 확인
                actual_loss = float(broken_return_pct) if broken_return_pct is not None else (float(archive_return_pct) if archive_return_pct is not None else None)
                
                if actual_loss and actual_loss < -10.0:
                    print(f"\n[{idx}] {ticker} ({name})")
                    print(f"    상태: {status}")
                    print(f"    전략: {strategy} (손절 조건: {stop_loss_pct}%)")
                    print(f"    추천일: {anchor_date}")
                    print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                    print(f"    BROKEN 시점: {broken_at}")
                    print(f"    BROKEN 수익률: {broken_return_pct}%")
                    print(f"    BROKEN 사유: {reason}")
                    print(f"    ARCHIVED 수익률: {archive_return_pct}%")
                    print(f"    ARCHIVED 사유: {archive_reason}")
                    
                    # 문제 분석
                    issues = []
                    
                    if actual_loss < stop_loss_pct:
                        # 손절 조건보다 더 많이 떨어졌음
                        excess_loss = abs(actual_loss) - abs(stop_loss_pct)
                        issues.append(f"손절 조건({stop_loss_pct}%)보다 {excess_loss:.2f}%p 더 떨어졌습니다. ({actual_loss:.2f}%)")
                        delayed_cases.append({
                            'ticker': ticker,
                            'name': name,
                            'strategy': strategy,
                            'stop_loss': stop_loss_pct,
                            'actual_loss': actual_loss,
                            'excess_loss': excess_loss,
                            'broken_at': broken_at,
                            'reason': reason
                        })
                    
                    if broken_at and broken_return_pct:
                        if broken_return_pct < -10.0:
                            issues.append(f"BROKEN 시점에 손실이 -10% 이상({broken_return_pct}%)이었습니다.")
                    
                    if issues:
                        print(f"\n    ⚠️  문제:")
                        for issue in issues:
                            print(f"      - {issue}")
                    else:
                        print(f"\n    ✅ 정상: 손절 조건에 따라 적절히 전환되었습니다.")
                    
                    print("-" * 150)
            
            if delayed_cases:
                print(f"\n[요약]")
                print(f"  손절 조건보다 더 많이 떨어진 케이스: {len(delayed_cases)}개")
                print(f"  평균 초과 손실: {sum(x['excess_loss'] for x in delayed_cases) / len(delayed_cases):.2f}%p")
                print(f"  최대 초과 손실: {max(x['excess_loss'] for x in delayed_cases):.2f}%p")
                
                print(f"\n  상세:")
                for item in sorted(delayed_cases, key=lambda x: x['excess_loss'], reverse=True):
                    print(f"    {item['ticker']} ({item['name']}): 손절 {item['stop_loss']}% → 실제 {item['actual_loss']:.2f}% (초과 {item['excess_loss']:.2f}%p)")
            else:
                print(f"\n[요약]")
                print(f"  손절 조건보다 더 많이 떨어진 케이스가 없습니다.")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("-10% 이상 손실인데도 BROKEN 전환이 늦었던 케이스 확인...")
    print("=" * 150)
    check_delayed_broken_transition()
    print("\n완료!")

