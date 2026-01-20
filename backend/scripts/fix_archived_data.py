"""
ARCHIVED 데이터 이상 케이스 확인 및 수정
1. archive_return_pct가 10% 이상인데 archive_reason이 'NO_MOMENTUM'인 경우
2. BROKEN을 거쳐서 ARCHIVED로 전환된 경우, broken_return_pct를 archive_return_pct로 사용
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json

def fix_archived_data():
    """ARCHIVED 데이터 이상 케이스 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 이상 케이스 조회
            # 1. archive_return_pct >= 10%인데 archive_reason이 'NO_MOMENTUM'인 경우
            # 2. BROKEN을 거쳐서 ARCHIVED로 전환된 경우 (broken_at이 있거나 broken_return_pct가 있는 경우)
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
                    reason,
                    archive_reason,
                    status_changed_at,
                    flags
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND (
                    (archive_return_pct >= 10.0 AND archive_reason = 'NO_MOMENTUM')
                    OR (broken_at IS NOT NULL AND broken_return_pct IS NOT NULL)
                    OR (broken_return_pct IS NOT NULL AND archive_return_pct IS NULL)
                )
                ORDER BY archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 이상 데이터가 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 이상 데이터 발견\n")
            print("=" * 120)
            
            update_count = 0
            skip_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                broken_at = row[5]
                broken_return_pct = row[6]
                archive_return_pct = row[8]
                archive_price = row[9]
                archive_phase = row[10]
                archive_reason = row[12]
                
                print(f"\n[{idx}] 추천 ID: {rec_id}")
                print(f"    종목: {ticker} ({name})")
                print(f"    현재 archive_return_pct: {archive_return_pct}")
                print(f"    현재 archive_reason: {archive_reason}")
                print(f"    broken_at: {broken_at}")
                print(f"    broken_return_pct: {broken_return_pct}")
                
                # 수정 로직
                new_archive_return_pct = archive_return_pct
                new_archive_price = archive_price
                new_archive_phase = archive_phase
                new_archive_reason = archive_reason
                needs_update = False
                
                # 1. BROKEN을 거쳐서 ARCHIVED로 전환된 경우: broken_return_pct 사용
                if broken_return_pct is not None:
                    if archive_return_pct != broken_return_pct:
                        print(f"    → BROKEN 시점 스냅샷 사용: {broken_return_pct}%")
                        new_archive_return_pct = round(float(broken_return_pct), 2)
                        needs_update = True
                        
                        # BROKEN 시점의 가격 계산
                        anchor_close = row[4]
                        if anchor_close and anchor_close > 0:
                            new_archive_price = round(float(anchor_close) * (1 + new_archive_return_pct / 100), 0)
                        
                        # archive_phase 재계산
                        if new_archive_return_pct > 2:
                            new_archive_phase = 'PROFIT'
                        elif new_archive_return_pct < -2:
                            new_archive_phase = 'LOSS'
                        else:
                            new_archive_phase = 'FLAT'
                
                # 2. archive_return_pct >= 10%인데 archive_reason이 'NO_MOMENTUM'인 경우
                if new_archive_return_pct is not None and new_archive_return_pct >= 10.0:
                    if new_archive_reason == 'NO_MOMENTUM':
                        # 수익률이 10% 이상이면 'NO_MOMENTUM'이 아닌 'TTL_EXPIRED'로 변경
                        print(f"    → 수익률 {new_archive_return_pct}%인데 'NO_MOMENTUM' → 'TTL_EXPIRED'로 변경")
                        new_archive_reason = 'TTL_EXPIRED'
                        needs_update = True
                
                if needs_update:
                    print(f"    ✅ 업데이트: archive_return_pct={new_archive_return_pct}, archive_price={new_archive_price}, archive_phase={new_archive_phase}, archive_reason={new_archive_reason}")
                    
                    # DB 업데이트
                    with db_manager.get_cursor(commit=True) as update_cur:
                        update_cur.execute("""
                            UPDATE recommendations
                            SET archive_return_pct = %s,
                                archive_price = %s,
                                archive_phase = %s,
                                archive_reason = %s,
                                updated_at = NOW()
                            WHERE recommendation_id = %s
                        """, (new_archive_return_pct, new_archive_price, new_archive_phase, new_archive_reason, rec_id))
                    
                    update_count += 1
                else:
                    print(f"    ⏭️  스킵: 수정 불필요")
                    skip_count += 1
                
                print("-" * 120)
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  스킵: {skip_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ARCHIVED 데이터 이상 케이스 수정 시작...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_archived_data()
    print("\n완료!")


