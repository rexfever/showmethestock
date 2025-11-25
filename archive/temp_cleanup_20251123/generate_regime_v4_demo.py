#!/usr/bin/env python3
"""
Global Regime v4 데모 데이터 생성
"""
import sys
import os
from datetime import datetime, timedelta

# backend 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def generate_demo_regime_v4():
    """데모용 Regime v4 데이터 생성"""
    try:
        from services.regime_storage import upsert_regime
        
        print("📊 Global Regime v4 데모 데이터 생성")
        
        # 최근 5일 거래일 (가상)
        demo_dates = [
            "20241118", "20241119", "20241120", "20241121", "20241122"
        ]
        
        # 데모 시나리오: 점진적 상승 추세
        demo_scenarios = [
            {
                "date": "20241118",
                "kr_score": 1.0, "kr_regime": "neutral",
                "us_prev_score": 0.5, "us_prev_regime": "neutral", 
                "us_futures_score": 1.5, "us_futures_regime": "bull",
                "final_score": 1.1, "final_regime": "neutral"
            },
            {
                "date": "20241119", 
                "kr_score": 2.0, "kr_regime": "bull",
                "us_prev_score": 1.0, "us_prev_regime": "neutral",
                "us_futures_score": 2.0, "us_futures_regime": "bull", 
                "final_score": 1.6, "final_regime": "bull"
            },
            {
                "date": "20241120",
                "kr_score": 1.5, "kr_regime": "neutral", 
                "us_prev_score": 1.5, "us_prev_regime": "bull",
                "us_futures_score": 1.0, "us_futures_regime": "neutral",
                "final_score": 1.4, "final_regime": "bull"
            },
            {
                "date": "20241121",
                "kr_score": -1.0, "kr_regime": "bear",
                "us_prev_score": 0.0, "us_prev_regime": "neutral",
                "us_futures_score": -0.5, "us_futures_regime": "neutral", 
                "final_score": -0.7, "final_regime": "bear"
            },
            {
                "date": "20241122",
                "kr_score": 0.5, "kr_regime": "neutral",
                "us_prev_score": -0.5, "us_prev_regime": "neutral", 
                "us_futures_score": 1.0, "us_futures_regime": "neutral",
                "final_score": 0.4, "final_regime": "bull"
            }
        ]
        
        generated_count = 0
        
        for scenario in demo_scenarios:
            date_str = scenario["date"]
            print(f"🔄 {date_str} 데모 데이터 생성 중...")
            
            try:
                # v4 데이터 구성
                regime_data = {
                    'final_regime': scenario["final_regime"],
                    'kr_regime': scenario["kr_regime"], 
                    'us_prev_regime': scenario["us_prev_regime"],
                    'us_futures_score': scenario["us_futures_score"],
                    'us_futures_regime': scenario["us_futures_regime"],
                    'dxy': 105.5,  # 달러 인덱스 예시
                    'version': 'regime_v4'
                }
                
                upsert_regime(date_str, regime_data)
                
                print(f"✅ {date_str}: {scenario['final_regime']} (KR:{scenario['kr_score']:.1f}, US:{scenario['us_prev_score']:.1f}, FUT:{scenario['us_futures_score']:.1f})")
                generated_count += 1
                
            except Exception as e:
                print(f"❌ {date_str} 생성 실패: {e}")
        
        print(f"\n🎯 데모 데이터 생성 완료: {generated_count}개")
        
        # 생성된 데이터 확인
        print("\n📋 생성된 v4 레짐 데이터:")
        verify_v4_data()
        
    except Exception as e:
        print(f"❌ 데모 데이터 생성 실패: {e}")
        import traceback
        traceback.print_exc()

def verify_v4_data():
    """생성된 v4 데이터 검증"""
    try:
        from services.regime_storage import load_regime
        
        demo_dates = ["20241118", "20241119", "20241120", "20241121", "20241122"]
        
        for date_str in demo_dates:
            regime_data = load_regime(date_str)
            if regime_data:
                final_regime = regime_data.get('final_regime', 'N/A')
                kr_regime = regime_data.get('kr_regime', 'N/A')
                us_regime = regime_data.get('us_prev_regime', 'N/A')
                us_futures_regime = regime_data.get('us_futures_regime', 'N/A')
                
                print(f"  {date_str}: {final_regime} (KR:{kr_regime}, US:{us_regime}, FUT:{us_futures_regime})")
            else:
                print(f"  {date_str}: 데이터 없음")
        
    except Exception as e:
        print(f"❌ 데이터 검증 실패: {e}")

if __name__ == "__main__":
    generate_demo_regime_v4()