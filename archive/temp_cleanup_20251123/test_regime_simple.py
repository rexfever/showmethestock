#!/usr/bin/env python3
"""
간단한 레짐 분석 테스트 - 2025년 11월
"""
import os
import sys

# backend 디렉토리로 이동하여 실행
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
os.chdir(backend_dir)

# 직접 실행
if __name__ == "__main__":
    exec("""
from market_analyzer import market_analyzer
from services.us_market_data import get_us_prev_snapshot
from services.market_data_provider import market_data_provider

print("=" * 60)
print("2025년 11월 레짐 분석 테스트 (yfinance 제거 후)")
print("=" * 60)

# 테스트 날짜들
test_dates = ["20251105", "20251108", "20251115", "20251122", "20251129"]

for date in test_dates:
    print(f"\\n📅 {date} 분석:")
    
    try:
        # 1. 미국 데이터 확인
        us_data = get_us_prev_snapshot(date)
        print(f"  🇺🇸 미국: valid={us_data['valid']}, SPY r1={us_data['spy_r1']:.3f}, VIX={us_data['vix']:.1f}")
        
        # 2. v3 레짐 분석
        condition_v3 = market_analyzer.analyze_market_condition_v3(date, mode="backtest")
        print(f"  🌍 Global v3: {condition_v3.final_regime} (점수: {condition_v3.final_score:.2f})")
        print(f"     - 한국: {condition_v3.kr_regime} ({condition_v3.kr_score:.1f})")
        print(f"     - 미국: {condition_v3.us_prev_regime} ({condition_v3.us_prev_score:.1f})")
        
        # 3. 기존 v1과 비교
        condition_v1 = market_analyzer.analyze_market_condition(date)
        print(f"  🇰🇷 기존 v1: {condition_v1.market_sentiment} (KOSPI: {condition_v1.kospi_return*100:+.2f}%)")
        
        # 4. 레짐 차이 확인
        if condition_v3.final_regime != condition_v1.market_sentiment:
            print(f"  ⚠️  레짐 차이: v1({condition_v1.market_sentiment}) vs v3({condition_v3.final_regime})")
            
            # 2025년 11월이 bear/crash로 나와야 정상
            if condition_v3.final_regime in ['bear', 'crash']:
                print(f"  ✅ 정상: 2025년 11월은 {condition_v3.final_regime} 레짐이 맞음")
            else:
                print(f"  ❌ 비정상: 2025년 11월이 {condition_v3.final_regime}로 잘못 분류됨")
        else:
            print(f"  ✅ 레짐 일치: {condition_v3.final_regime}")
            
    except Exception as e:
        print(f"  ❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

print("\\n" + "=" * 60)
print("yfinance 제거 확인:")

# yfinance 완전 제거 확인
import sys
yf_modules = [name for name in sys.modules.keys() if 'yfinance' in name.lower()]
if yf_modules:
    print(f"⚠️  yfinance 관련 모듈 발견: {yf_modules}")
else:
    print("✅ yfinance 관련 모듈 없음 - 완전 제거됨")

print("\\n테스트 완료!")
print("=" * 60)
""")