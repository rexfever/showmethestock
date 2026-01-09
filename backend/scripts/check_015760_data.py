"""
두산에너빌리티(015760)의 실제 데이터 확인
- BROKEN 시점의 broken_return_pct
- ARCHIVED 전환 시점의 archive_return_pct
- anchor_close, 각 시점의 가격
- reason, archive_reason
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json

def check_015760_data():
    """두산에너빌리티의 추천 데이터 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ARCHIVED 상태인 두산에너빌리티 추천 조회
            cur.execute("""
                SELECT 
                    recommendation_id,
                    ticker,
                    name,
                    status,
                    anchor_date,
                    anchor_close,
                    broken_at,
                    broken_return_pct,
                    archived_at,
                    archive_return_pct,
                    archive_price,
                    archive_phase,
                    reason,
                    archive_reason,
                    status_changed_at,
                    created_at,
                    flags
                FROM recommendations
                WHERE ticker = '015760'
                AND status = 'ARCHIVED'
                AND scanner_version = 'v3'
                ORDER BY archived_at DESC
                LIMIT 5
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("ARCHIVED 상태인 두산에너빌리티 추천이 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 ARCHIVED 추천 발견\n")
            print("=" * 100)
            
            for idx, row in enumerate(rows, 1):
                print(f"\n[{idx}] 추천 ID: {row[0]}")
                print(f"    종목: {row[1]} ({row[2]})")
                print(f"    상태: {row[3]}")
                print(f"    추천일 (anchor_date): {row[4]}")
                print(f"    추천 시점 가격 (anchor_close): {row[5]:,.0f}원" if row[5] else "    추천 시점 가격: None")
                print(f"    BROKEN 시점 (broken_at): {row[6]}")
                print(f"    BROKEN 시점 수익률 (broken_return_pct): {row[7]}%" if row[7] is not None else "    BROKEN 시점 수익률: None")
                print(f"    ARCHIVED 시점 (archived_at): {row[8]}")
                print(f"    ARCHIVED 시점 수익률 (archive_return_pct): {row[9]}%" if row[9] is not None else "    ARCHIVED 시점 수익률: None")
                print(f"    ARCHIVED 시점 가격 (archive_price): {row[10]:,.0f}원" if row[10] else "    ARCHIVED 시점 가격: None")
                print(f"    ARCHIVED 단계 (archive_phase): {row[11]}")
                print(f"    BROKEN 사유 (reason): {row[12]}")
                print(f"    ARCHIVED 사유 (archive_reason): {row[13]}")
                print(f"    상태 변경일 (status_changed_at): {row[14]}")
                print(f"    생성일 (created_at): {row[15]}")
                
                # flags 파싱
                if row[16]:
                    try:
                        flags = json.loads(row[16]) if isinstance(row[16], str) else row[16]
                        if isinstance(flags, dict):
                            print(f"    flags.broken_anchor_return: {flags.get('broken_anchor_return')}")
                            print(f"    flags.stop_loss: {flags.get('stop_loss')}")
                    except:
                        pass
                
                # 수익률 계산 검증
                if row[5] and row[10]:  # anchor_close와 archive_price가 모두 있으면
                    calculated_return = ((row[10] - row[5]) / row[5]) * 100
                    print(f"\n    [검증] 계산된 수익률: ({row[10]:,.0f} - {row[5]:,.0f}) / {row[5]:,.0f} * 100 = {calculated_return:.2f}%")
                    if row[9] is not None:
                        print(f"    [검증] 저장된 archive_return_pct: {row[9]}%")
                        diff = abs(calculated_return - row[9])
                        if diff > 0.01:
                            print(f"    ⚠️  차이 발생: {diff:.2f}%")
                        else:
                            print(f"    ✅ 일치")
                
                print("-" * 100)
            
            # BROKEN 상태인 항목도 확인
            print("\n\n[BROKEN 상태인 두산에너빌리티 추천]")
            cur.execute("""
                SELECT 
                    recommendation_id,
                    ticker,
                    name,
                    status,
                    anchor_date,
                    anchor_close,
                    broken_at,
                    broken_return_pct,
                    reason,
                    status_changed_at,
                    flags
                FROM recommendations
                WHERE ticker = '015760'
                AND status = 'BROKEN'
                AND scanner_version = 'v3'
                ORDER BY broken_at DESC
                LIMIT 3
            """)
            
            broken_rows = cur.fetchall()
            if broken_rows:
                print(f"총 {len(broken_rows)}개의 BROKEN 추천 발견\n")
                for idx, row in enumerate(broken_rows, 1):
                    print(f"[{idx}] 추천 ID: {row[0]}")
                    print(f"    종목: {row[1]} ({row[2]})")
                    print(f"    상태: {row[3]}")
                    print(f"    추천일: {row[4]}")
                    print(f"    추천 시점 가격: {row[5]:,.0f}원" if row[5] else "    추천 시점 가격: None")
                    print(f"    BROKEN 시점: {row[6]}")
                    print(f"    BROKEN 시점 수익률: {row[7]}%" if row[7] is not None else "    BROKEN 시점 수익률: None")
                    print(f"    사유: {row[8]}")
                    print(f"    상태 변경일: {row[9]}")
                    print("-" * 100)
            else:
                print("BROKEN 상태인 추천이 없습니다.")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_015760_data()


