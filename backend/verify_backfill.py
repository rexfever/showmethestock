#!/usr/bin/env python3
"""
간단한 백필 검증 스크립트
"""
import os
import psycopg
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rexsmac@localhost/stockfinder")

def verify_backfill(start_date, end_date):
    """백필 검증"""
    logger.info(f"백필 검증 시작: {start_date} ~ {end_date}")
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 레짐 데이터 확인
                cur.execute("""
                    SELECT COUNT(*), 
                           COUNT(DISTINCT final_regime) as regime_count,
                           final_regime,
                           COUNT(*) as count
                    FROM market_regime_daily 
                    WHERE date BETWEEN %s AND %s
                    GROUP BY final_regime
                    ORDER BY count DESC
                """, (start_date, end_date))
                
                regime_results = cur.fetchall()
                
                # 스캔 데이터 확인
                cur.execute("""
                    SELECT horizon, COUNT(*) as count
                    FROM scan_daily 
                    WHERE date BETWEEN %s AND %s AND version = 'simple-v1'
                    GROUP BY horizon
                    ORDER BY count DESC
                """, (start_date, end_date))
                
                scan_results = cur.fetchall()
                
                # 날짜별 통계
                cur.execute("""
                    SELECT DATE(date) as date, final_regime, COUNT(sd.code) as candidates
                    FROM market_regime_daily mrd
                    LEFT JOIN scan_daily sd ON mrd.date = sd.date AND sd.version = 'simple-v1'
                    WHERE mrd.date BETWEEN %s AND %s
                    GROUP BY DATE(mrd.date), final_regime
                    ORDER BY date DESC
                    LIMIT 10
                """, (start_date, end_date))
                
                daily_results = cur.fetchall()
        
        # 결과 출력
        print("\n" + "="*60)
        print("📊 백필 검증 리포트")
        print("="*60)
        print(f"📅 검증 기간: {start_date} ~ {end_date}")
        
        print(f"\n📈 레짐 분포:")
        total_days = sum(result[3] for result in regime_results)
        for result in regime_results:
            regime = result[2]
            count = result[3]
            percentage = (count / total_days * 100) if total_days > 0 else 0
            print(f"  - {regime}: {count}일 ({percentage:.1f}%)")
        
        print(f"\n🎯 스캔 결과:")
        total_candidates = sum(result[1] for result in scan_results)
        for result in scan_results:
            horizon = result[0]
            count = result[1]
            print(f"  - {horizon}: {count}개 후보")
        print(f"  - 총 후보: {total_candidates}개")
        
        print(f"\n📋 최근 10일 상세:")
        for result in daily_results:
            date = result[0]
            regime = result[1]
            candidates = result[2] or 0
            print(f"  - {date}: {regime} ({candidates}개 후보)")
        
        print("\n" + "="*60)
        
        # 성공 기준
        if total_days > 0 and len(regime_results) >= 2:
            print("✅ 검증 상태: PASS")
            return True
        else:
            print("❌ 검증 상태: FAIL")
            return False
            
    except Exception as e:
        logger.error(f"검증 실패: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("사용법: python verify_backfill.py 2020-01-01 2025-11-22")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    success = verify_backfill(start_date, end_date)
    sys.exit(0 if success else 1)