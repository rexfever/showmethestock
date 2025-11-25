#!/usr/bin/env python3
"""
Global Regime v3 기본 사용법 예제
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def basic_regime_analysis():
    """기본적인 장세 분석 사용법"""
    print("📊 Global Regime v3 기본 사용법\n")
    
    try:
        from market_analyzer import market_analyzer
        from datetime import datetime
        
        # 1. 오늘 장세 분석
        today = datetime.now().strftime('%Y%m%d')
        print(f"1️⃣ 오늘({today}) 장세 분석:")
        
        condition = market_analyzer.analyze_market_condition_v3(today, mode="backtest")
        
        if condition.version == "regime_v3":
            print(f"   최종 레짐: {condition.final_regime}")
            print(f"   최종 점수: {condition.final_score:.2f}")
            print(f"   한국 점수: {condition.kr_score:.2f}")
            print(f"   미국 점수: {condition.us_prev_score:.2f}")
        else:
            print("   v3 분석 실패, v1 결과 사용됨")
        
        # 2. 특정 날짜 분석
        print(f"\n2️⃣ 특정 날짜(20241201) 장세 분석:")
        
        condition_past = market_analyzer.analyze_market_condition_v3("20241201", mode="backtest")
        
        if condition_past.version == "regime_v3":
            print(f"   최종 레짐: {condition_past.final_regime}")
            print(f"   최종 점수: {condition_past.final_score:.2f}")
        
        # 3. DB에서 저장된 데이터 로드
        print(f"\n3️⃣ DB에서 저장된 장세 데이터 로드:")
        
        from services.regime_storage import load_regime
        
        stored_data = load_regime("20241201")
        if stored_data:
            print(f"   저장된 레짐: {stored_data['final_regime']}")
            print(f"   한국 레짐: {stored_data['kr_regime']}")
            print(f"   미국 레짐: {stored_data['us_prev_regime']}")
        else:
            print("   저장된 데이터 없음")
        
        print("\n✅ 기본 사용법 완료!")
        
    except Exception as e:
        print(f"❌ 예제 실행 실패: {e}")

def scanner_integration_example():
    """스캐너 연동 예제"""
    print("\n🔍 스캐너 연동 예제\n")
    
    try:
        from services.scan_service import execute_scan_with_fallback
        from kiwoom_api import api
        import config
        
        # 유니버스 가져오기 (샘플)
        print("1️⃣ 유니버스 준비 중...")
        kospi_sample = api.get_top_codes('KOSPI', 50)
        print(f"   KOSPI 샘플: {len(kospi_sample)}개 종목")
        
        # v3 장세 기반 스캔 실행
        print("2️⃣ v3 장세 기반 스캔 실행...")
        items, step, version = execute_scan_with_fallback(kospi_sample[:20])  # 샘플 20개만
        
        print(f"   스캔 결과: {len(items)}개 종목")
        print(f"   Fallback Step: {step}")
        print(f"   스캐너 버전: {version}")
        
        if items:
            print("   상위 3개 종목:")
            for i, item in enumerate(items[:3]):
                print(f"     {i+1}. {item['name']} ({item['ticker']}) - {item['score']:.1f}점")
        
        print("\n✅ 스캐너 연동 예제 완료!")
        
    except Exception as e:
        print(f"❌ 스캐너 연동 예제 실패: {e}")

if __name__ == "__main__":
    basic_regime_analysis()
    scanner_integration_example()