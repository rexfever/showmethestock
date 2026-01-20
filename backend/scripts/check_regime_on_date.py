"""
특정 날짜의 레짐 정보 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
import json

def check_regime_on_date(date_str):
    """특정 날짜의 레짐 정보 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # market_conditions 테이블에서 해당 날짜의 레짐 정보 조회
            cur.execute("""
                SELECT 
                    date,
                    final_regime,
                    midterm_regime,
                    longterm_regime,
                    market_sentiment,
                    short_term_risk_score,
                    created_at
                FROM market_conditions
                WHERE date = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (date_str,))
            
            row = cur.fetchone()
            
            if not row:
                print(f"{date_str} 날짜의 레짐 정보가 없습니다.")
                return
            
            print(f"[{date_str} 날짜의 레짐 정보 (v3)]")
            print("=" * 80)
            print(f"날짜: {row[0]}")
            print(f"최종 레짐 (final_regime): {row[1]}")
            print(f"중기 레짐 (midterm_regime): {row[2]}")
            print(f"장기 레짐 (longterm_regime): {row[3]}")
            print(f"시장 심리 (market_sentiment): {row[4]}")
            print(f"단기 리스크 점수: {row[5]}")
            print(f"생성일: {row[6]}")
            
            # 레짐 분석
            print("\n[레짐 분석]")
            if row[1] == 'crash':
                print("⚠️  최종 레짐이 'crash'입니다!")
            elif row[1] == 'bear':
                print("⚠️  최종 레짐이 'bear'입니다!")
            elif row[1] == 'bull':
                print("✅ 최종 레짐이 'bull'입니다!")
            elif row[1] == 'neutral':
                print("➖ 최종 레짐이 'neutral'입니다!")
            
            if row[2]:
                print(f"중기 레짐: {row[2]}")
            if row[3]:
                print(f"장기 레짐: {row[3]}")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 2025-12-31 날짜 확인
    check_regime_on_date("20251231")

