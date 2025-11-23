#!/usr/bin/env python3
"""
11월 v4 레짐 분석 테스트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime, timedelta
from market_analyzer import market_analyzer

def test_november_regime_v4():
    """11월 전체 v4 레짐 분석"""
    print("📊 11월 Global Regime v4 분석")
    print("=" * 50)
    
    # 11월 거래일 (주말 제외)
    november_dates = [
        "20251101", "20251104", "20251105", "20251106", "20251107",
        "20251108", "20251111", "20251112", "20251113", "20251114",
        "20251115", "20251118", "20251119", "20251120", "20251121",
        "20251122", "20251125", "20251126", "20251127", "20251128"
    ]
    
    results = []
    
    for date in november_dates:
        try:
            condition = market_analyzer.analyze_market_condition_v4(date, mode="backtest")
            
            result = {
                "date": date,
                "final_regime": condition.final_regime,
                "global_trend_score": condition.global_trend_score,
                "global_risk_score": condition.global_risk_score,
                "kr_trend_score": condition.kr_trend_score,
                "us_trend_score": condition.us_trend_score,
                "kr_risk_score": condition.kr_risk_score,
                "us_risk_score": condition.us_risk_score,
                "kr_regime": condition.kr_regime,
                "us_regime": condition.us_prev_regime
            }
            results.append(result)
            
            print(f"{date}: {condition.final_regime:>7} (trend:{condition.global_trend_score:+5.1f}, risk:{condition.global_risk_score:+5.1f}) KR:{condition.kr_regime:>7} US:{condition.us_prev_regime:>7}")
            
        except Exception as e:
            print(f"{date}: ERROR - {e}")
    
    print("\n📈 11월 레짐 통계:")
    regime_counts = {}
    for r in results:
        regime = r["final_regime"]
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
    
    total = len(results)
    for regime, count in sorted(regime_counts.items()):
        pct = count / total * 100
        print(f"  {regime:>7}: {count:2d}일 ({pct:4.1f}%)")
    
    print(f"\n총 분석일: {total}일")
    
    # 추세별 평균 점수
    trend_scores = [r["global_trend_score"] for r in results]
    risk_scores = [r["global_risk_score"] for r in results]
    
    print(f"평균 추세 점수: {sum(trend_scores)/len(trend_scores):+5.2f}")
    print(f"평균 리스크 점수: {sum(risk_scores)/len(risk_scores):+5.2f}")

if __name__ == "__main__":
    test_november_regime_v4()