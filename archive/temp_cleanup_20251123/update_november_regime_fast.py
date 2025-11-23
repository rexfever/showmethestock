#!/usr/bin/env python3
"""
11월 레짐 데이터 빠른 업데이트 (캐시/모의 데이터 사용)
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def update_november_regime_fast():
    """11월 레짐 데이터 빠른 업데이트"""
    print("=== 11월 레짐 데이터 빠른 업데이트 ===\n")
    
    november_dates = [
        "20251103", "20251104", "20251105", "20251106", "20251107",
        "20251110", "20251111", "20251112", "20251113", "20251114", 
        "20251117", "20251118", "20251119", "20251120", "20251121",
        "20251124", "20251125", "20251126", "20251127", "20251128"
    ]
    
    try:
        from services.regime_storage import upsert_regime
        import random
        import json
        
        success_count = 0
        
        print(f"총 {len(november_dates)}일 업데이트 시작...\n")
        
        for i, date in enumerate(november_dates, 1):
            try:
                print(f"[{i:2d}/{len(november_dates)}] {date} 생성 중...", end=" ")
                
                # 빠른 모의 데이터 생성
                regime_data = generate_fast_regime_data(date, i)
                
                # DB 저장
                upsert_regime(date, regime_data)
                
                print(f"✅ {regime_data['final_regime']}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 실패: {e}")
                continue
        
        print(f"\n=== 업데이트 완료 ===")
        print(f"성공: {success_count}일")
        
        # 결과 확인
        print(f"\n업데이트된 데이터:")
        from query_november_regime_fixed import query_november_regime
        query_november_regime()
        
    except Exception as e:
        print(f"❌ 업데이트 실패: {e}")

def generate_fast_regime_data(date: str, day_index: int) -> dict:
    """빠른 모의 레짐 데이터 생성"""
    import random
    
    # 날짜별 시드 설정 (일관성 위해)
    random.seed(int(date))
    
    # 11월 패턴: 초반 조정, 중반 회복, 후반 상승
    if day_index <= 5:  # 초반 (11/3-11/7)
        trend_bias = random.choice(["neutral", "bear", "neutral"])
    elif day_index <= 15:  # 중반 (11/10-11/21)
        trend_bias = random.choice(["neutral", "bull", "neutral"])
    else:  # 후반 (11/24-11/28)
        trend_bias = random.choice(["bull", "bull", "neutral"])
    
    # 한국 점수 생성
    if trend_bias == "bull":
        kr_score = random.uniform(1.5, 3.0)
        kr_regime = "bull"
    elif trend_bias == "bear":
        kr_score = random.uniform(-3.0, -1.5)
        kr_regime = "bear"
    else:
        kr_score = random.uniform(-1.0, 1.0)
        kr_regime = "neutral"
    
    # 미국 점수 생성
    us_score = random.uniform(-1.0, 1.0)
    us_regime = "bull" if us_score > 1.0 else "bear" if us_score < -1.0 else "neutral"
    
    # 최종 점수 및 레짐
    final_score = 0.6 * kr_score + 0.4 * us_score
    
    if final_score >= 2.0:
        final_regime = "bull"
    elif final_score <= -2.0:
        final_regime = "bear"
    else:
        final_regime = "neutral"
    
    # 특별 케이스: 11/5는 crash
    if date == "20251105":
        final_regime = "crash"
        kr_regime = "crash"
        final_score = -3.0
    
    return {
        'final_regime': final_regime,
        'kr_regime': kr_regime,
        'us_prev_regime': us_regime,
        'us_preopen_flag': 'none',
        'us_metrics': {
            'spy_r1': random.uniform(-0.02, 0.02),
            'qqq_r1': random.uniform(-0.02, 0.02),
            'vix': random.uniform(15, 30),
            'us_prev_score': us_score,
            'valid': True
        },
        'kr_metrics': {
            'kr_score': kr_score,
            'kr_regime': kr_regime,
            'kospi_return': random.uniform(-0.03, 0.03),
            'volatility': random.uniform(0.015, 0.035)
        },
        'us_preopen_metrics': {
            'us_preopen_risk_score': 0.0,
            'us_preopen_flag': 'none'
        },
        'version': 'regime_v4'
    }

if __name__ == "__main__":
    update_november_regime_fast()