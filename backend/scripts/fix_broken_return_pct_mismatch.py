"""
broken_at이 None인데 broken_return_pct가 있는 경우 수정
이 경우 archive_return_pct를 broken_return_pct로 업데이트
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager

def fix_broken_return_pct_mismatch():
    """broken_at이 None인데 broken_return_pct가 있는 경우 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # broken_at이 None인데 broken_return_pct가 있고, archive_return_pct와 다른 케이스 찾기
            cur.execute("""
                SELECT 
                    recommendation_id,
                    ticker,
                    name,
                    strategy,
                    anchor_close,
                    broken_at,
                    broken_return_pct,
                    archive_return_pct,
                    archive_price,
                    archive_phase,
                    archive_reason
                FROM recommendations
                WHERE status = 'ARCHIVED'
                AND scanner_version = 'v3'
                AND broken_at IS NULL
                AND broken_return_pct IS NOT NULL
                AND archive_return_pct IS NOT NULL
                AND ABS(archive_return_pct - broken_return_pct) > 0.01
                ORDER BY ABS(archive_return_pct - broken_return_pct) DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 케이스가 없습니다.")
                return
            
            print(f"수정 대상: {len(rows)}개\n")
            print("=" * 100)
            
            update_count = 0
            
            for row in rows:
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                strategy = row[3]
                anchor_close = row[4]
                broken_at = row[5]
                broken_return_pct = row[6]
                archive_return_pct = row[7]
                archive_price = row[8]
                archive_phase = row[9]
                archive_reason = row[10]
                
                print(f"\n[{update_count + 1}] {ticker} ({name})")
                print(f"    추천 ID: {rec_id}")
                print(f"    전략: {strategy}")
                print(f"    현재: archive_return_pct={archive_return_pct}%, broken_return_pct={broken_return_pct}%")
                print(f"    차이: {abs(float(archive_return_pct) - float(broken_return_pct)):.2f}%")
                
                # broken_return_pct를 archive_return_pct로 사용
                new_archive_return_pct = round(float(broken_return_pct), 2)
                
                # archive_price 재계산
                new_archive_price = None
                if anchor_close:
                    anchor_close_float = float(anchor_close)
                    new_archive_price = round(anchor_close_float * (1 + new_archive_return_pct / 100), 0)
                
                # archive_phase 재계산
                if new_archive_return_pct > 2:
                    new_archive_phase = 'PROFIT'
                elif new_archive_return_pct < -2:
                    new_archive_phase = 'LOSS'
                else:
                    new_archive_phase = 'FLAT'
                
                # 손절 조건 체크
                stop_loss = 0.02  # 기본값
                if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                    stop_loss = 0.02
                elif strategy == "midterm" or strategy == "MIDTERM":
                    stop_loss = 0.07
                
                stop_loss_pct = -abs(float(stop_loss) * 100)
                new_archive_reason = archive_reason
                
                # 손절 조건 만족 시 NO_MOMENTUM으로 변경
                if new_archive_return_pct <= stop_loss_pct:
                    if new_archive_reason != 'NO_MOMENTUM':
                        new_archive_reason = 'NO_MOMENTUM'
                        print(f"    ⚠️  손절 조건 만족: {new_archive_return_pct:.2f}% <= {stop_loss_pct:.2f}%, reason 변경: {archive_reason} → NO_MOMENTUM")
                
                print(f"    수정: archive_return_pct={new_archive_return_pct}%, archive_price={new_archive_price}, archive_phase={new_archive_phase}, archive_reason={new_archive_reason}")
                
                # 업데이트 실행
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("""
                        UPDATE recommendations
                        SET archive_return_pct = %s,
                            archive_price = %s,
                            archive_phase = %s,
                            archive_reason = %s,
                            updated_at = NOW()
                        WHERE recommendation_id = %s
                    """, (
                        new_archive_return_pct,
                        new_archive_price,
                        new_archive_phase,
                        new_archive_reason,
                        rec_id
                    ))
                
                update_count += 1
                print(f"    ✅ 업데이트 완료")
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("broken_return_pct 불일치 수정 시작...")
    print("=" * 100)
    fix_broken_return_pct_mismatch()
    print("\n완료!")


