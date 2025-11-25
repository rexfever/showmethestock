#!/usr/bin/env python3
"""
Global Regime v3 DB 마이그레이션 실행 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

def run_migration():
    """market_regime_daily 테이블 생성 마이그레이션 실행"""
    try:
        from migrations.create_market_regime_daily import apply_migration
        print("🔄 Running Global Regime v3 migration...")
        apply_migration()
        print("✅ Migration completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    if not run_migration():
        sys.exit(1)