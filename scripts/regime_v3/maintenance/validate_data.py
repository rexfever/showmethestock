#!/usr/bin/env python3
"""
Global Regime v3 데이터 검증 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def validate_regime_data():
    """market_regime_daily 테이블 데이터 검증"""
    try:
        from db_manager import db_manager
        
        print("🔍 Global Regime v3 데이터 검증 중...")
        
        with db_manager.get_cursor(commit=False) as cur:
            # 테이블 존재 확인
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'market_regime_daily'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                print("❌ market_regime_daily 테이블이 존재하지 않습니다")
                return False
            
            print("✅ market_regime_daily 테이블 존재 확인")
            
            # 데이터 개수 확인
            cur.execute("SELECT COUNT(*) FROM market_regime_daily WHERE version = 'regime_v3'")
            total_count = cur.fetchone()[0]
            print(f"📊 총 레코드 수: {total_count}개")
            
            # 레짐별 분포
            cur.execute("""
                SELECT final_regime, COUNT(*) 
                FROM market_regime_daily 
                WHERE version = 'regime_v3'
                GROUP BY final_regime
                ORDER BY COUNT(*) DESC
            """)
            regime_dist = cur.fetchall()
            
            print("📈 레짐별 분포:")
            for regime, count in regime_dist:
                pct = (count / total_count * 100) if total_count > 0 else 0
                print(f"  {regime}: {count}개 ({pct:.1f}%)")
            
            # 최근 데이터 확인
            cur.execute("""
                SELECT date, final_regime, final_score 
                FROM market_regime_daily 
                WHERE version = 'regime_v3'
                ORDER BY date DESC 
                LIMIT 5
            """)
            recent_data = cur.fetchall()
            
            print("\n📅 최근 5일 데이터:")
            for date, regime, score in recent_data:
                print(f"  {date}: {regime} (점수: {score:.2f})")
            
            # 데이터 무결성 검증
            cur.execute("""
                SELECT COUNT(*) FROM market_regime_daily 
                WHERE version = 'regime_v3' 
                AND (final_regime IS NULL OR final_regime = '')
            """)
            null_regimes = cur.fetchone()[0]
            
            if null_regimes > 0:
                print(f"⚠️ NULL 레짐 데이터: {null_regimes}개")
            else:
                print("✅ 레짐 데이터 무결성 확인")
            
            return True
            
    except Exception as e:
        print(f"❌ 데이터 검증 실패: {e}")
        return False

def validate_us_data_connectivity():
    """미국 데이터 연결성 테스트"""
    try:
        from services.us_market_data import get_us_prev_snapshot
        from datetime import datetime
        
        print("\n🌐 미국 데이터 연결성 테스트...")
        
        today = datetime.now().strftime('%Y%m%d')
        snapshot = get_us_prev_snapshot(today)
        
        if snapshot.get('valid', False):
            print("✅ 미국 데이터 연결 정상")
            print(f"  SPY r1: {snapshot['spy_r1']*100:.2f}%")
            print(f"  VIX: {snapshot['vix']:.1f}")
        else:
            print("⚠️ 미국 데이터 연결 실패")
            
        return snapshot.get('valid', False)
        
    except Exception as e:
        print(f"❌ 미국 데이터 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Global Regime v3 시스템 검증\n")
    
    db_ok = validate_regime_data()
    us_ok = validate_us_data_connectivity()
    
    if db_ok and us_ok:
        print("\n🎉 모든 검증 통과!")
    else:
        print("\n⚠️ 일부 검증 실패")
        sys.exit(1)