#!/usr/bin/env python3
"""
Global Regime v3 오래된 데이터 정리 스크립트
"""
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def cleanup_old_regime_data(days_to_keep=90):
    """지정된 일수보다 오래된 레짐 데이터 삭제"""
    try:
        from db_manager import db_manager
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        print(f"🧹 {cutoff_str} 이전 레짐 데이터 정리 중...")
        
        with db_manager.get_cursor(commit=True) as cur:
            # 삭제 전 개수 확인
            cur.execute("""
                SELECT COUNT(*) FROM market_regime_daily 
                WHERE version = 'regime_v3' AND date < %s
            """, (cutoff_str,))
            old_count = cur.fetchone()[0]
            
            if old_count == 0:
                print("✅ 정리할 오래된 데이터가 없습니다")
                return True
            
            print(f"📊 정리 대상: {old_count}개 레코드")
            
            # 사용자 확인
            response = input(f"정말로 {old_count}개 레코드를 삭제하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("❌ 정리 작업이 취소되었습니다")
                return False
            
            # 삭제 실행
            cur.execute("""
                DELETE FROM market_regime_daily 
                WHERE version = 'regime_v3' AND date < %s
            """, (cutoff_str,))
            
            deleted_count = cur.rowcount
            print(f"✅ {deleted_count}개 레코드 삭제 완료")
            
            return True
            
    except Exception as e:
        print(f"❌ 데이터 정리 실패: {e}")
        return False

def vacuum_database():
    """데이터베이스 VACUUM 실행"""
    try:
        from db_manager import db_manager
        
        print("🔧 데이터베이스 최적화 중...")
        
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("VACUUM ANALYZE market_regime_daily")
            print("✅ 데이터베이스 최적화 완료")
            
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 최적화 실패: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Global Regime v3 데이터 정리')
    parser.add_argument('--days', type=int, default=90, help='보관할 일수 (기본: 90일)')
    parser.add_argument('--vacuum', action='store_true', help='VACUUM 실행')
    args = parser.parse_args()
    
    success = cleanup_old_regime_data(args.days)
    
    if success and args.vacuum:
        vacuum_database()
    
    if not success:
        sys.exit(1)