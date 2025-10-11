def _save_snapshot_db(as_of: str, items: List[ScanItem]):
    """스캔 결과를 DB에 저장 (모든 필드 포함)"""
    try:
        print(f"💾 데이터베이스 저장 시작: {as_of}, {len(items)}개 항목")
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 새로운 스키마로 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_rank(
                date TEXT, code TEXT, name TEXT, score REAL, score_label TEXT,
                close_price REAL, volume INTEGER, change_rate REAL, market TEXT,
                strategy TEXT, indicators TEXT, trend TEXT, flags TEXT,
                details TEXT, returns TEXT, recurrence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(date, code)
            )
        """)
        
        # 기존 데이터 삭제 (같은 날짜)
        cur.execute("DELETE FROM scan_rank WHERE date = ?", (as_of,))
        
        # 새로운 데이터 삽입
        for item in items:
            cur.execute("""
                INSERT INTO scan_rank (
                    date, code, name, score, score_label, close_price, volume,
                    change_rate, market, strategy, indicators, trend, flags,
                    details, returns, recurrence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                as_of,
                item.ticker,
                item.name,
                item.score,
                item.score_label,
                item.indicators.close if hasattr(item.indicators, "close") else 0,
                item.indicators.VOL if hasattr(item.indicators, "VOL") else 0,
                getattr(item, "change_rate", 0),
                getattr(item, "market", ""),
                item.strategy,
                json.dumps(item.indicators.__dict__ if hasattr(item.indicators, "__dict__") else {}, ensure_ascii=False),
                json.dumps(item.trend.__dict__ if hasattr(item.trend, "__dict__") else {}, ensure_ascii=False),
                json.dumps(item.flags.__dict__ if hasattr(item.flags, "__dict__") else {}, ensure_ascii=False),
                json.dumps(getattr(item, "details", {}), ensure_ascii=False),
                json.dumps(getattr(item, "returns", None), ensure_ascii=False),
                json.dumps(getattr(item, "recurrence", None), ensure_ascii=False)
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ 데이터베이스 저장 완료: {as_of}")
        
    except Exception as e:
        print(f"❌ 데이터베이스 저장 오류: {e}")
        if "conn" in locals():
            conn.close()
