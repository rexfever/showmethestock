"""
오름태라퓨틱(475830) 상세 데이터 확인
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

def check_475830_detail():
    """오름태라퓨틱 상세 데이터 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 오름태라퓨틱의 모든 추천 이력 조회
            cur.execute("""
                SELECT 
                    recommendation_id,
                    ticker,
                    name,
                    anchor_date,
                    anchor_close,
                    status,
                    broken_at,
                    broken_return_pct,
                    archived_at,
                    archive_return_pct,
                    archive_price,
                    archive_phase,
                    archive_reason,
                    replaced_by_recommendation_id,
                    status_changed_at,
                    flags,
                    created_at,
                    updated_at
                FROM recommendations
                WHERE ticker = '475830'
                ORDER BY anchor_date DESC, created_at DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("오름태라퓨틱 데이터를 찾을 수 없습니다.")
                return
            
            print(f"오름태라퓨틱(475830) 추천 이력: {len(rows)}개\n")
            print("=" * 150)
            
            for idx, row in enumerate(rows, 1):
                print(f"\n[{idx}] 추천 ID: {row[0]}")
                print(f"    종목명: {row[2]}")
                print(f"    추천일: {row[3]}")
                print(f"    추천 시점 가격: {row[4]:,.0f}원" if row[4] else "    추천 시점 가격: None")
                print(f"    현재 상태: {row[5]}")
                print(f"    BROKEN 시점: {row[6]}")
                print(f"    BROKEN 시점 수익률: {row[7]}%" if row[7] is not None else "    BROKEN 시점 수익률: None")
                print(f"    ARCHIVED 시점: {row[8]}")
                print(f"    ARCHIVED 시점 수익률: {row[9]:,.2f}%" if row[9] is not None else "    ARCHIVED 시점 수익률: None")
                print(f"    ARCHIVED 시점 가격: {row[10]:,.0f}원" if row[10] else "    ARCHIVED 시점 가격: None")
                print(f"    ARCHIVED 단계: {row[11]}")
                print(f"    ARCHIVED 사유: {row[12]}")
                print(f"    대체 추천 ID: {row[13]}")
                print(f"    상태 변경 시점: {row[14]}")
                print(f"    생성 시점: {row[15]}")
                print(f"    업데이트 시점: {row[16]}")
                
                # flags 파싱
                if row[15]:
                    try:
                        flags = json.loads(row[15]) if isinstance(row[15], str) else row[15]
                        print(f"\n    Flags:")
                        if flags:
                            for key, value in flags.items():
                                print(f"      {key}: {value}")
                    except:
                        pass
                
                # 검증: 계산된 수익률과 저장된 수익률 비교
                if row[4] and row[10]:
                    calculated_return = ((row[10] - row[4]) / row[4]) * 100
                    print(f"\n    검증:")
                    print(f"      계산된 수익률: {calculated_return:.2f}%")
                    print(f"      저장된 수익률: {row[9]:,.2f}%" if row[9] is not None else "      저장된 수익률: None")
                    if row[9] is not None:
                        diff = abs(calculated_return - row[9])
                        if diff > 0.01:
                            print(f"      ⚠️  차이: {diff:.2f}%p")
                        else:
                            print(f"      ✅ 일치")
                
                # REPLACED 케이스 분석
                if row[12] == 'REPLACED' and row[13]:
                    print(f"\n    REPLACED 분석:")
                    # 대체 추천 정보 조회
                    cur.execute("""
                        SELECT anchor_date, anchor_close, status
                        FROM recommendations
                        WHERE recommendation_id = %s
                    """, (row[13],))
                    replaced_by_row = cur.fetchone()
                    if replaced_by_row:
                        print(f"      대체 추천일: {replaced_by_row[0]}")
                        print(f"      대체 추천 시점 가격: {replaced_by_row[1]:,.0f}원" if replaced_by_row[1] else "      대체 추천 시점 가격: None")
                        print(f"      대체 추천 상태: {replaced_by_row[2]}")
                
                print("-" * 150)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_475830_detail()

