def save_scan_snapshot(scan_items: List[Dict], today_as_of: str) -> None:
    """스캔 스냅샷을 DB에 저장 (JSON 파일 제거)"""
    import json
    import sqlite3
    
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 기존 데이터 삭제 (같은 날짜)
        cur.execute("DELETE FROM scan_rank WHERE date = ?", (today_as_of,))
        
        # 새로운 데이터 삽입
        for item in scan_items:
            cur.execute("""
                INSERT INTO scan_rank (
                    date, code, name, score, score_label, close_price, volume,
                    change_rate, market, strategy, indicators, trend, flags,
                    details, returns, recurrence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                today_as_of,
                item.get("ticker"),
                item.get("name"),
                item.get("score"),
                item.get("score_label"),
                item.get("indicators", {}).get("close"),
                item.get("indicators", {}).get("VOL"),
                item.get("change_rate"),
                item.get("market"),
                item.get("strategy"),
                json.dumps(item.get("indicators", {}), ensure_ascii=False),
                json.dumps(item.get("trend", {}), ensure_ascii=False),
                json.dumps(item.get("flags", {}), ensure_ascii=False),
                json.dumps(item.get("details", {}), ensure_ascii=False),
                json.dumps(item.get("returns"), ensure_ascii=False),
                json.dumps(item.get("recurrence"), ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ DB에 {len(scan_items)}개 스캔 결과 저장 완료")
        
    except Exception as e:
        print(f"❌ DB 저장 오류: {e}")
        if "conn" in locals():
            conn.close()
        
        # JSON 파일 저장 로직 제거
        pass
