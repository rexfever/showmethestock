"""
손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 ARCHIVED 종목 수정
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from datetime import datetime

def fix_missed_stop_loss_archived():
    """손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 ARCHIVED 종목 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ARCHIVED된 종목 중 손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 케이스 조회
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
                    r.archive_phase
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct IS NOT NULL
                AND r.archive_reason != 'NO_MOMENTUM'
                ORDER BY r.archive_return_pct ASC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 데이터가 없습니다.")
                return
            
            print(f"ARCHIVED된 종목 중 NO_MOMENTUM이 아닌 케이스: {len(rows)}개\n")
            print("=" * 150)
            
            needs_fix = []
            
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
                
                # 전략별 손절 조건 확인
                stop_loss = 0.02  # 기본값
                if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                    stop_loss = 0.02
                elif strategy == "midterm" or strategy == "MIDTERM":
                    stop_loss = 0.07
                
                stop_loss_pct = -abs(float(stop_loss) * 100)
                archive_return_pct_float = float(archive_return_pct)
                
                # 손절 조건 체크
                if archive_return_pct_float <= stop_loss_pct:
                    needs_fix.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'stop_loss': stop_loss_pct,
                        'archive_return_pct': archive_return_pct_float,
                        'archive_reason': archive_reason,
                        'archive_phase': archive_phase
                    })
            
            if not needs_fix:
                print("손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 케이스가 없습니다.")
                return
            
            print(f"손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 케이스: {len(needs_fix)}개\n")
            print("=" * 150)
            
            update_count = 0
            
            for idx, item in enumerate(sorted(needs_fix, key=lambda x: x['archive_return_pct']), 1):
                print(f"\n[{idx}] {item['ticker']} ({item['name']})")
                print(f"    전략: {item['strategy']} (손절 조건: {item['stop_loss']}%)")
                print(f"    현재 archive_return_pct: {item['archive_return_pct']:,.2f}%")
                print(f"    현재 archive_reason: {item['archive_reason']}")
                print(f"    현재 archive_phase: {item['archive_phase']}")
                
                # NO_MOMENTUM으로 변경
                print(f"    → archive_reason을 'NO_MOMENTUM'으로 변경")
                
                # DB 업데이트
                with db_manager.get_cursor(commit=True) as update_cur:
                    update_cur.execute("""
                        UPDATE recommendations
                        SET archive_reason = 'NO_MOMENTUM',
                            updated_at = NOW()
                        WHERE recommendation_id = %s
                    """, (item['rec_id'],))
                
                update_count += 1
                print("-" * 150)
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  총: {len(needs_fix)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("손절 조건을 만족했는데도 NO_MOMENTUM이 아닌 ARCHIVED 종목 수정...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_missed_stop_loss_archived()
    print("\n완료!")


