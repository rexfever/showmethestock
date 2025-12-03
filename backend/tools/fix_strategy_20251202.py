"""
12월 2일 스캔 데이터의 strategy 필드 업데이트 스크립트
flags.trading_strategy를 strategy 컬럼에 복사
"""
import json
from db_manager import db_manager

def fix_strategy_for_date(date_str: str):
    """특정 날짜의 strategy 필드를 flags.trading_strategy에서 복사"""
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 해당 날짜의 모든 레코드 조회
            cur.execute("""
                SELECT code, flags, strategy
                FROM scan_rank
                WHERE date = %s AND code != 'NORESULT'
            """, (date_str,))
            rows = cur.fetchall()
            
            updated_count = 0
            for row in rows:
                code = row["code"]
                flags_raw = row["flags"]
                current_strategy = row["strategy"]
                
                # strategy가 이미 있으면 스킵
                if current_strategy and current_strategy.strip():
                    continue
                
                # flags 파싱
                flags_dict = {}
                if flags_raw:
                    if isinstance(flags_raw, str):
                        try:
                            flags_dict = json.loads(flags_raw)
                        except:
                            continue
                    elif isinstance(flags_raw, dict):
                        flags_dict = flags_raw
                
                # trading_strategy 추출
                trading_strategy = flags_dict.get("trading_strategy")
                if trading_strategy:
                    # strategy 컬럼 업데이트
                    cur.execute("""
                        UPDATE scan_rank
                        SET strategy = %s
                        WHERE date = %s AND code = %s
                    """, (trading_strategy, date_str, code))
                    updated_count += 1
                    print(f"✅ {code}: strategy 업데이트 '{trading_strategy}'")
                else:
                    print(f"⚠️ {code}: flags에 trading_strategy 없음")
            
            print(f"\n✅ 총 {updated_count}개 종목의 strategy 업데이트 완료")
            return updated_count
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # 12월 2일 데이터 수정
    date_str = "2025-12-02"
    print(f"🔧 {date_str} 데이터의 strategy 필드 업데이트 시작...")
    fix_strategy_for_date(date_str)

