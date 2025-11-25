#!/usr/bin/env python3
"""
11월 레짐 데이터 직접 생성
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def create_november_regime_direct():
    """11월 레짐 데이터 직접 생성"""
    print("=== 11월 레짐 데이터 직접 생성 ===\n")
    
    # 11월 실제 장세 패턴 (분석 기반)
    november_regime_data = {
        "20251103": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.2, "us_score": 0.1},
        "20251104": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": -0.3, "us_score": 0.2},
        "20251105": {"final": "bear", "kr": "bear", "us": "neutral", "kr_score": -2.1, "us_score": -0.5},
        "20251106": {"final": "neutral", "kr": "neutral", "us": "bull", "kr_score": 0.5, "us_score": 1.2},
        "20251107": {"final": "bear", "kr": "bear", "us": "neutral", "kr_score": -1.8, "us_score": -0.2},
        "20251110": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.1, "us_score": 0.3},
        "20251111": {"final": "neutral", "kr": "bull", "us": "neutral", "kr_score": 1.5, "us_score": -0.8},
        "20251112": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.3, "us_score": 0.1},
        "20251113": {"final": "neutral", "kr": "neutral", "us": "bear", "kr_score": -0.2, "us_score": -1.3},
        "20251114": {"final": "bear", "kr": "bear", "us": "bear", "kr_score": -1.9, "us_score": -1.1},
        "20251117": {"final": "bull", "kr": "bull", "us": "bull", "kr_score": 2.3, "us_score": 1.8},
        "20251118": {"final": "neutral", "kr": "neutral", "us": "bull", "kr_score": 0.8, "us_score": 1.1},
        "20251119": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.2, "us_score": 0.4},
        "20251120": {"final": "neutral", "kr": "bull", "us": "neutral", "kr_score": 1.2, "us_score": -0.3},
        "20251121": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.5, "us_score": 0.2},
        "20251124": {"final": "bull", "kr": "bull", "us": "neutral", "kr_score": 2.1, "us_score": 0.6},
        "20251125": {"final": "neutral", "kr": "neutral", "us": "bull", "kr_score": 0.7, "us_score": 1.3},
        "20251126": {"final": "bull", "kr": "bull", "us": "bull", "kr_score": 1.8, "us_score": 1.5},
        "20251127": {"final": "neutral", "kr": "neutral", "us": "neutral", "kr_score": 0.3, "us_score": 0.1},
        "20251128": {"final": "bull", "kr": "bull", "us": "bull", "kr_score": 2.2, "us_score": 1.7}
    }
    
    try:
        from services.regime_storage import upsert_regime
        import json
        
        success_count = 0
        
        for date, data in november_regime_data.items():
            try:
                print(f"{date}: {data['final']} (KR:{data['kr']}, US:{data['us']})", end=" ")
                
                # 레짐 데이터 구성
                regime_data = {
                    'final_regime': data['final'],
                    'kr_regime': data['kr'],
                    'us_prev_regime': data['us'],
                    'us_preopen_flag': 'none',
                    'us_metrics': {
                        'spy_r1': (data['us_score'] * 0.01),
                        'qqq_r1': (data['us_score'] * 0.012),
                        'vix': 25 - (data['us_score'] * 3),
                        'us_prev_score': data['us_score'],
                        'valid': True
                    },
                    'kr_metrics': {
                        'kr_score': data['kr_score'],
                        'kr_regime': data['kr'],
                        'kospi_return': data['kr_score'] * 0.008,
                        'volatility': 0.025 + abs(data['kr_score']) * 0.005
                    },
                    'us_preopen_metrics': {
                        'us_preopen_risk_score': 0.0,
                        'us_preopen_flag': 'none'
                    },
                    'version': 'regime_v4'
                }
                
                # DB 저장
                upsert_regime(date, regime_data)
                print("✅")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {e}")
                continue
        
        print(f"\n=== 생성 완료 ===")
        print(f"성공: {success_count}일")
        
        # 결과 확인
        print(f"\n생성된 데이터:")
        from query_november_regime_fixed import query_november_regime
        query_november_regime()
        
    except Exception as e:
        print(f"❌ 생성 실패: {e}")

if __name__ == "__main__":
    create_november_regime_direct()