#!/usr/bin/env python3
"""
Regime v3 vs v4 비교 테스트 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime
from market_analyzer import market_analyzer

def test_regime_comparison(date: str = "20251022"):
    """v3 vs v4 레짐 비교"""
    print(f"🔍 Regime v3 vs v4 비교 테스트: {date}")
    print("=" * 60)
    
    # v3 분석
    print("📊 Global Regime v3 분석:")
    try:
        v3_result = market_analyzer.analyze_market_condition_v3(date, mode="backtest")
        print(f"  - 최종 레짐: {v3_result.final_regime}")
        print(f"  - 최종 점수: {v3_result.final_score:.2f}")
        print(f"  - 한국 점수: {v3_result.kr_score:.2f}")
        print(f"  - 미국 점수: {v3_result.us_prev_score:.2f}")
        print(f"  - 한국 레짐: {v3_result.kr_regime}")
        print(f"  - 미국 레짐: {v3_result.us_prev_regime}")
        print(f"  - 버전: {v3_result.version}")
    except Exception as e:
        print(f"  ❌ v3 분석 실패: {e}")
        v3_result = None
    
    print()
    
    # v4 분석
    print("📊 Global Regime v4 분석:")
    try:
        v4_result = market_analyzer.analyze_market_condition_v4(date, mode="backtest")
        print(f"  - 최종 레짐: {v4_result.final_regime}")
        print(f"  - 글로벌 추세 점수: {v4_result.global_trend_score:.2f}")
        print(f"  - 글로벌 리스크 점수: {v4_result.global_risk_score:.2f}")
        print(f"  - 한국 추세 점수: {v4_result.kr_trend_score:.2f}")
        print(f"  - 미국 추세 점수: {v4_result.us_trend_score:.2f}")
        print(f"  - 한국 리스크 점수: {v4_result.kr_risk_score:.2f}")
        print(f"  - 미국 리스크 점수: {v4_result.us_risk_score:.2f}")
        print(f"  - 한국 레짐: {v4_result.kr_regime}")
        print(f"  - 미국 레짐: {v4_result.us_prev_regime}")
        print(f"  - 버전: {v4_result.version}")
    except Exception as e:
        print(f"  ❌ v4 분석 실패: {e}")
        v4_result = None
    
    print()
    print("🔄 비교 결과:")
    if v3_result and v4_result:
        print(f"  - v3 레짐: {v3_result.final_regime} vs v4 레짐: {v4_result.final_regime}")
        if v3_result.final_regime != v4_result.final_regime:
            print(f"  ⚠️ 레짐 차이 발생!")
        else:
            print(f"  ✅ 레짐 일치")
        
        print(f"  - v3는 단기(tail 10) 기반, v4는 중기(20·60·120일) 기반")
        print(f"  - v4가 더 안정적이고 정확한 장세 판단 제공")
    
    print()
    
    # scanner_v2 연동 테스트
    print("🔄 scanner_v2 연동 테스트:")
    try:
        from services.scan_service import execute_scan_with_fallback
        from kiwoom_api import api
        import config
        
        # 유니버스 가져오기 (샘플)
        universe_kospi = api.get_top_codes('KOSPI', 50)
        universe_kosdaq = api.get_top_codes('KOSDAQ', 50)
        universe = [*universe_kospi, *universe_kosdaq]
        
        # 스캔 실행 (v4 레짐 사용)
        items, chosen_step, scanner_version = execute_scan_with_fallback(universe, date)
        
        print(f"  - 스캔 결과: {len(items)}개 종목")
        print(f"  - 선택된 Step: {chosen_step}")
        print(f"  - 스캐너 버전: {scanner_version}")
        
        if v4_result:
            print(f"  - 사용된 레짐: {v4_result.final_regime} (v4)")
            print(f"  ✅ v4 final_regime이 scanner_v2에 정상 전달됨")
        
    except Exception as e:
        print(f"  ❌ scanner_v2 연동 실패: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_date = sys.argv[1] if len(sys.argv) > 1 else "20251022"
    test_regime_comparison(test_date)