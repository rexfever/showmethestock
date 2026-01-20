"""
ARCHIVED 데이터 중 비정상적인 수익률 확인
- archive_return_pct가 비정상적으로 높거나 낮은 경우
- broken_return_pct와 archive_return_pct의 차이가 큰 경우
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json

def check_abnormal_archived():
    """비정상적인 ARCHIVED 데이터 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 비정상적인 케이스 조회
            # 1. archive_return_pct가 50% 이상 또는 -50% 이하
            # 2. broken_return_pct와 archive_return_pct의 차이가 20%p 이상
            cur.execute("""
                SELECT 
                    recommendation_id,
                    ticker,
                    name,
                    anchor_date,
                    anchor_close,
                    broken_at,
                    broken_return_pct,
                    archived_at,
                    archive_return_pct,
                    archive_price,
                    archive_phase,
                    archive_reason,
                    flags
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND archive_return_pct IS NOT NULL
                AND (
                    archive_return_pct >= 50.0
                    OR archive_return_pct <= -50.0
                    OR (broken_return_pct IS NOT NULL AND ABS(archive_return_pct - broken_return_pct) >= 20.0)
                )
                ORDER BY ABS(archive_return_pct) DESC
                LIMIT 20
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("비정상적인 ARCHIVED 데이터가 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 비정상적인 ARCHIVED 데이터 발견\n")
            print("=" * 120)
            
            for idx, row in enumerate(rows, 1):
                print(f"\n[{idx}] 추천 ID: {row[0]}")
                print(f"    종목: {row[1]} ({row[2]})")
                print(f"    추천일: {row[3]}")
                print(f"    추천 시점 가격: {row[4]:,.0f}원" if row[4] else "    추천 시점 가격: None")
                print(f"    BROKEN 시점: {row[5]}")
                print(f"    BROKEN 시점 수익률: {row[6]}%" if row[6] is not None else "    BROKEN 시점 수익률: None")
                print(f"    ARCHIVED 시점: {row[7]}")
                print(f"    ARCHIVED 시점 수익률: {row[8]:,.2f}%")
                print(f"    ARCHIVED 시점 가격: {row[9]:,.0f}원" if row[9] else "    ARCHIVED 시점 가격: None")
                print(f"    ARCHIVED 단계: {row[10]}")
                print(f"    ARCHIVED 사유: {row[11]}")
                
                # 비정상성 분석
                issues = []
                if row[8] >= 50.0:
                    issues.append(f"수익률이 비정상적으로 높음 ({row[8]:,.2f}%)")
                if row[8] <= -50.0:
                    issues.append(f"수익률이 비정상적으로 낮음 ({row[8]:,.2f}%)")
                if row[6] is not None and abs(row[8] - row[6]) >= 20.0:
                    issues.append(f"BROKEN과 ARCHIVED 수익률 차이가 큼 ({row[6]}% → {row[8]:,.2f}%, 차이: {abs(row[8] - row[6]):,.2f}%p)")
                
                if issues:
                    print(f"\n    ⚠️  문제:")
                    for issue in issues:
                        print(f"      - {issue}")
                
                # 검증: 계산된 수익률과 저장된 수익률 비교
                if row[4] and row[9]:
                    calculated_return = ((row[9] - row[4]) / row[4]) * 100
                    if abs(calculated_return - row[8]) > 0.01:
                        print(f"\n    ⚠️  계산 불일치:")
                        print(f"      계산된 수익률: {calculated_return:.2f}%")
                        print(f"      저장된 수익률: {row[8]:,.2f}%")
                        print(f"      차이: {abs(calculated_return - row[8]):.2f}%p")
                
                print("-" * 120)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_abnormal_archived()


