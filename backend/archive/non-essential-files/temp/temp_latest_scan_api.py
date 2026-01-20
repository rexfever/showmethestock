@app.get("/latest-scan")
async def get_latest_scan():
    """최신 스캔 결과를 DB에서 가져옵니다."""
    try:
        import sqlite3
        import json
        
        conn = sqlite3.connect("snapshots.db")
        cur = conn.cursor()
        
        # 가장 최신 날짜의 스캔 결과 조회
        cur.execute("""
            SELECT date, COUNT(*) as count 
            FROM scan_rank 
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 1
        """)
        
        latest_date_result = cur.fetchone()
        if not latest_date_result:
            return {"ok": False, "error": "스캔 결과가 없습니다."}
        
        latest_date = latest_date_result[0]
        
        # 해당 날짜의 모든 스캔 결과 조회
        cur.execute("""
            SELECT date, code, name, score, score_label, close_price, volume,
                   change_rate, market, strategy, indicators, trend, flags,
                   details, returns, recurrence
            FROM scan_rank 
            WHERE date = ? 
            ORDER BY score DESC
        """, (latest_date,))
        
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return {"ok": False, "error": "해당 날짜의 스캔 결과가 없습니다."}
        
        # 데이터 변환
        items = []
        for row in rows:
            item = {
                "ticker": row[1],
                "name": row[2],
                "score": row[3],
                "score_label": row[4],
                "match": True,
                "market": row[8],
                "strategy": row[9],
                "evaluation": {"total_score": row[3]},
                "current_price": row[5],
                "change_rate": row[7],
                "volume": row[6],
                "market_interest": "높음"  # 기본값
            }
            
            # JSON 필드들 파싱
            if row[10]:  # indicators
                item["indicators"] = json.loads(row[10])
            if row[11]:  # trend
                item["trend"] = json.loads(row[11])
            if row[12]:  # flags
                item["flags"] = json.loads(row[12])
            if row[13]:  # details
                item["details"] = json.loads(row[13])
            if row[14]:  # returns
                item["returns"] = json.loads(row[14])
            if row[15]:  # recurrence
                item["recurrence"] = json.loads(row[15])
            
            items.append(item)
        
        # 응답 구성
        response_data = {
            "as_of": latest_date,
            "created_at": latest_date + "T00:00:00",
            "universe_count": 100,  # 기본값
            "matched_count": len(items),
            "rsi_mode": "tema_dema",
            "rsi_period": 14,
            "rsi_threshold": 57.0,
            "scan_date": latest_date.replace("-", ""),
            "is_latest": True,
            "items": items
        }
        
        return {"ok": True, "data": response_data}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
