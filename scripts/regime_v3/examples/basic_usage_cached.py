#!/usr/bin/env python3
"""
캐시 기반 레짐 분석 기본 사용법
"""
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def basic_regime_analysis():
    """기본 캐시 기반 레짐 분석"""
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        
        # 오늘 날짜
        today = datetime.now().strftime('%Y%m%d')
        print(f"📊 {today} 캐시 기반 레짐 분석")
        
        # v4 분석 실행
        result = regime_analyzer_cached.analyze_regime_v4_cached(today)
        
        print(f"\n🎯 분석 결과:")
        print(f"  최종 레짐: {result['final_regime']}")
        print(f"  최종 점수: {result['final_score']:.2f}")
        print(f"  한국: {result['kr_regime']} ({result['kr_score']:.2f})")
        print(f"  미국: {result['us_prev_regime']} ({result['us_prev_score']:.2f})")
        
        return result
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return None

def analyze_recent_days(days=5):
    """최근 며칠간 캐시 기반 분석"""
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        from datetime import datetime, timedelta
        
        print(f"📊 최근 {days}일 캐시 기반 레짐 분석")
        
        results = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            try:
                result = regime_analyzer_cached.analyze_regime_v4_cached(date)
                results.append({
                    'date': date,
                    'regime': result['final_regime'],
                    'score': result['final_score']
                })
                print(f"  {date}: {result['final_regime']} ({result['final_score']:.2f})")
            except Exception as e:
                print(f"  {date}: 오류 - {e}")
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return []

if __name__ == "__main__":
    print("🚀 캐시 기반 레짐 분석 기본 사용법\n")
    
    # 기본 분석
    basic_regime_analysis()
    
    print("\n" + "="*50 + "\n")
    
    # 최근 5일 분석
    analyze_recent_days(5)
    
    print("\n🎯 완료!")