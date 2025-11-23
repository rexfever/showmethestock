#!/usr/bin/env python3
"""
일일 장세 분석 및 확인 스크립트 (캐시 기반)
"""
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def check_daily_regime(date=None):
    """오늘 또는 지정된 날짜의 장세 분석 (캐시 기반)"""
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        
        print(f"📊 {date} 장세 분석 중... (캐시 기반)")
        
        # 캐시 기반 v4 분석 실행
        result = regime_analyzer_cached.analyze_regime_v4_cached(date)
        
        print(f"\n🎯 Global Regime v4 결과 (캐시):")
        print(f"  최종 레짐: {result['final_regime']}")
        print(f"  최종 점수: {result['final_score']:.2f}")
        print(f"  한국 레짐: {result['kr_regime']} (점수: {result['kr_score']:.2f})")
        print(f"  미국 레짐: {result['us_prev_regime']} (점수: {result['us_prev_score']:.2f})")
        print(f"  미국 선물: {result['us_futures_regime']} (점수: {result['us_futures_score']:.2f})")
        
        # 캐시 통계 출력
        cache_stats = regime_analyzer_cached.get_cache_stats()
        print(f"\n📊 캐시 통계: {cache_stats.get('total_files', 0)}개 파일")
        
        return result
        
    except Exception as e:
        print(f"❌ 장세 분석 실패: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='일일 장세 분석')
    parser.add_argument('--date', help='분석할 날짜 (YYYYMMDD)', default=None)
    args = parser.parse_args()
    
    check_daily_regime(args.date)