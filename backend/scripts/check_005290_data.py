"""
동진쎄미캠(005290)의 실제 데이터 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json

def check_005290_data():
    """동진쎄미캠의 ARCHIVED 추천 데이터 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ARCHIVED 상태인 동진쎄미캠 추천 조회
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
                    flags
                FROM recommendations
                WHERE ticker = '005290'
                AND status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND archive_reason = 'NO_MOMENTUM'
                ORDER BY archived_at DESC
                LIMIT 5
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("NO_MOMENTUM 사유인 ARCHIVED 상태인 동진쎄미캠 추천이 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 NO_MOMENTUM ARCHIVED 추천 발견\n")
            print("=" * 120)
            
            for idx, row in enumerate(rows, 1):
                print(f"\n[{idx}] 추천 ID: {row[0]}")
                print(f"    종목: {row[1]} ({row[2]})")
                print(f"    상태: {row[3]}")
                print(f"    추천일 (anchor_date): {row[4]}")
                print(f"    추천 시점 가격 (anchor_close): {row[5]:,.0f}원" if row[5] else "    추천 시점 가격: None")
                print(f"    BROKEN 시점 (broken_at): {row[6]}")
                print(f"    BROKEN 시점 수익률 (broken_return_pct): {row[7]}%" if row[7] is not None else "    BROKEN 시점 수익률: None")
                print(f"    ARCHIVED 시점 (archived_at): {row[8]}")
                print(f"    ARCHIVED 시점 수익률 (archive_return_pct): {row[9]:,.2f}%" if row[9] is not None else "    ARCHIVED 시점 수익률: None")
                print(f"    ARCHIVED 시점 가격 (archive_price): {row[10]:,.0f}원" if row[10] else "    ARCHIVED 시점 가격: None")
                print(f"    ARCHIVED 단계 (archive_phase): {row[11]}")
                print(f"    BROKEN 사유 (reason): {row[12]}")
                print(f"    ARCHIVED 사유 (archive_reason): {row[13]}")
                print(f"    상태 변경일 (status_changed_at): {row[14]}")
                
                # flags 파싱
                if row[15]:
                    try:
                        flags = json.loads(row[15]) if isinstance(row[15], str) else row[15]
                        if isinstance(flags, dict):
                            print(f"    flags.broken_anchor_return: {flags.get('broken_anchor_return')}")
                            print(f"    flags.stop_loss: {flags.get('stop_loss')}")
                            print(f"    flags.broken_at: {flags.get('broken_at')}")
                    except:
                        pass
                
                # 분석
                if row[9] is not None and row[9] >= 7.0:
                    print(f"\n    ⚠️  문제 발견: archive_return_pct가 {row[9]:,.2f}%인데 archive_reason이 'NO_MOMENTUM' (이전 흐름 유지 실패)입니다!")
                    if row[6]:  # broken_at이 있으면
                        print(f"    → BROKEN을 거쳐서 ARCHIVED로 전환됨")
                        if row[7] is not None:
                            print(f"    → BROKEN 시점 수익률: {row[7]}%")
                            print(f"    → ARCHIVED 시점 수익률: {row[9]:,.2f}%")
                            print(f"    → 수익률 변화: {row[9] - row[7]:,.2f}%p")
                    else:
                        print(f"    → ACTIVE에서 직접 ARCHIVED로 전환됨")
                
                print("-" * 120)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_005290_data()


