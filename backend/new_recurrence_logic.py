import sqlite3
import json
from collections import defaultdict
from typing import List, Dict, Any

def get_recurring_stocks(days: int = 7, min_appearances: int = 2) -> Dict[str, Any]:
    """
    최근 N일간 스캔된 종목 중 재등장한 종목들을 찾는 함수
    
    Args:
        days: 최근 몇 일간의 데이터를 확인할지
        min_appearances: 최소 등장 횟수 (기본값: 2)
    
    Returns:
        재등장 종목 정보
    """
    conn = sqlite3.connect('snapshots.db')
    cur = conn.cursor()
    
    # 최근 N일간의 스캔 결과 조회 (파라미터화된 쿼리)
    query = """
    SELECT code, name, date, score, score_label, close_price
    FROM scan_rank 
    WHERE date >= date('now', '-' || ? || ' days')
    ORDER BY date DESC, score DESC
    """
    
    cur.execute(query, (days,))
    results = cur.fetchall()
    conn.close()
    
    # 종목별 등장 횟수 계산
    stock_appearances = defaultdict(list)
    for row in results:
        code, name, date, score, score_label, close_price = row
        stock_appearances[code].append({
            'name': name,
            'date': date,
            'score': score,
            'score_label': score_label,
            'close_price': close_price
        })
    
    # 재등장 종목 필터링
    recurring_stocks = {}
    for code, appearances in stock_appearances.items():
        if len(appearances) >= min_appearances:
            recurring_stocks[code] = {
                'name': appearances[0]['name'],
                'appear_count': len(appearances),
                'appearances': appearances,
                'latest_score': appearances[0]['score'],
                'latest_date': appearances[0]['date']
            }
    
    return recurring_stocks

# 테스트 실행
if __name__ == "__main__":
    print("📊 **새로운 재등장 로직 테스트**")
    print("=============================")
    
    recurring = get_recurring_stocks(days=30, min_appearances=2)
    
    print(f"📊 **재등장 종목 수**: {len(recurring)}개")
    print("=============================")
    
    for code, data in recurring.items():
        print(f"• {code} ({data['name']}): {data['appear_count']}회 등장")
        print(f"  - 최신 점수: {data['latest_score']}")
        print(f"  - 최신 날짜: {data['latest_date']}")
        print()
