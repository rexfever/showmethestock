"""
REPLACED로 ARCHIVED된 데이터 수정
REPLACED 전환 시점의 스냅샷을 사용해야 함
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json
from datetime import datetime

def fix_replaced_archived_data():
    """REPLACED로 ARCHIVED된 데이터 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # REPLACED로 ARCHIVED된 항목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.archived_at,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_phase,
                    r.archive_reason,
                    r.status_changed_at,
                    r.replaced_by_recommendation_id
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_reason = 'REPLACED'
                AND r.archive_return_pct IS NOT NULL
                ORDER BY r.archived_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 REPLACED ARCHIVED 데이터가 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 REPLACED ARCHIVED 데이터 발견\n")
            print("=" * 150)
            
            update_count = 0
            skip_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                archived_at = row[5]
                archive_return_pct = row[6]
                archive_price = row[7]
                archive_phase = row[8]
                archive_reason = row[9]
                status_changed_at = row[10]
                replaced_by_id = row[11]
                
                print(f"\n[{idx}] 추천 ID: {rec_id}")
                print(f"    종목: {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    상태 변경 시점: {status_changed_at}")
                print(f"    ARCHIVED 시점: {archived_at}")
                print(f"    현재 archive_return_pct: {archive_return_pct:,.2f}%")
                print(f"    현재 archive_price: {archive_price:,.0f}원")
                
                # REPLACED 전환 시점 확인 (status_changed_at 또는 state_events)
                # state_events에서 REPLACED 전환 시점 조회
                cur.execute("""
                    SELECT occurred_at, metadata
                    FROM recommendation_state_events
                    WHERE recommendation_id = %s
                    AND to_status = 'REPLACED'
                    ORDER BY occurred_at DESC
                    LIMIT 1
                """, (rec_id,))
                
                replaced_event = cur.fetchone()
                
                if replaced_event:
                    replaced_at = replaced_event[0]
                    replaced_metadata = replaced_event[1]
                    
                    print(f"    REPLACED 전환 시점: {replaced_at}")
                    
                    # REPLACED 전환 시점의 가격 조회 (metadata 또는 OHLCV)
                    if replaced_metadata and isinstance(replaced_metadata, dict):
                        replaced_price = replaced_metadata.get('close') or replaced_metadata.get('price')
                        if replaced_price:
                            print(f"    REPLACED 시점 가격 (metadata): {replaced_price:,.0f}원")
                            
                            # REPLACED 시점 수익률 계산
                            if anchor_close and anchor_close > 0:
                                replaced_return_pct = round(((replaced_price - anchor_close) / anchor_close) * 100, 2)
                                
                                # 현재 archive_return_pct와 비교
                                if abs(replaced_return_pct - archive_return_pct) > 0.01:
                                    print(f"    → REPLACED 시점 스냅샷 사용: {replaced_return_pct}%")
                                    
                                    # archive_phase 재계산
                                    if replaced_return_pct > 2:
                                        new_archive_phase = 'PROFIT'
                                    elif replaced_return_pct < -2:
                                        new_archive_phase = 'LOSS'
                                    else:
                                        new_archive_phase = 'FLAT'
                                    
                                    print(f"    ✅ 업데이트: archive_return_pct={replaced_return_pct}%, archive_price={replaced_price:,.0f}원, archive_phase={new_archive_phase}")
                                    
                                    # DB 업데이트
                                    with db_manager.get_cursor(commit=True) as update_cur:
                                        update_cur.execute("""
                                            UPDATE recommendations
                                            SET archive_return_pct = %s,
                                                archive_price = %s,
                                                archive_phase = %s,
                                                updated_at = NOW()
                                            WHERE recommendation_id = %s
                                        """, (replaced_return_pct, replaced_price, new_archive_phase, rec_id))
                                    
                                    update_count += 1
                                else:
                                    print(f"    ⏭️  스킵: REPLACED 시점 수익률과 동일")
                                    skip_count += 1
                            else:
                                print(f"    ⚠️  anchor_close가 없어서 계산 불가")
                                skip_count += 1
                        else:
                            print(f"    ⚠️  REPLACED 시점 가격 정보 없음 (metadata 확인 필요)")
                            skip_count += 1
                    else:
                        print(f"    ⚠️  REPLACED 시점 metadata 없음")
                        skip_count += 1
                else:
                    print(f"    ⚠️  REPLACED 전환 이벤트 없음")
                    skip_count += 1
                
                print("-" * 150)
            
            print(f"\n[결과]")
            print(f"  업데이트: {update_count}개")
            print(f"  스킵: {skip_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("REPLACED ARCHIVED 데이터 수정 시작...")
    print("주의: 이 스크립트는 데이터베이스를 수정합니다.\n")
    fix_replaced_archived_data()
    print("\n완료!")


