#!/usr/bin/env python3
"""
2025년 11월 레짐 분석 테스트
yfinance 제거 후 Kiwoom API 기반으로 정확한 장세 분석 확인
"""
import sys
import os

# backend 디렉토리로 이동
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
os.chdir(backend_path)
sys.path.insert(0, backend_path)

try:
    from market_analyzer import market_analyzer
    from services.us_market_data import get_us_prev_snapshot
    from services.market_data_provider import market_data_provider
    print("✅ 모든 모듈 import 성공")
except Exception as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

def test_november_2025_regime():
    """2025년 11월 레짐 분석 테스트"""
    
    # 2025년 11월 주요 날짜들 (실제 시장 상황)
    test_dates = [
        "20251101",  # 11월 첫째 주
        "20251108",  # 11월 둘째 주  
        "20251115",  # 11월 셋째 주
        "20251122",  # 11월 넷째 주
        "20251129",  # 11월 마지막 주
    ]
    
    print("=" * 60)
    print("2025년 11월 레짐 분석 테스트 (Kiwoom API 기반)")
    print("=" * 60)
    
    for date in test_dates:
        print(f"\n📅 {date} 분석:")
        
        try:
            # 1. 미국 시장 데이터 확인
            us_data = get_us_prev_snapshot(date)
            print(f"  🇺🇸 미국 데이터: valid={us_data['valid']}, SPY r1={us_data['spy_r1']:.3f}, VIX={us_data['vix']:.1f}")
            
            # 2. v3 레짐 분석
            condition_v3 = market_analyzer.analyze_market_condition_v3(date, mode="backtest")
            print(f"  🌍 Global Regime v3: {condition_v3.final_regime} (점수: {condition_v3.final_score:.2f})")
            print(f"     - 한국: {condition_v3.kr_regime} ({condition_v3.kr_score:.1f})")
            print(f"     - 미국: {condition_v3.us_prev_regime} ({condition_v3.us_prev_score:.1f})")
            print(f"     - 버전: {condition_v3.version}")
            
            # 3. 기존 v1 분석과 비교
            condition_v1 = market_analyzer.analyze_market_condition(date)
            print(f"  🇰🇷 기존 v1: {condition_v1.market_sentiment} (KOSPI: {condition_v1.kospi_return*100:+.2f}%)")
            
            # 4. 레짐 차이 분석
            if condition_v3.final_regime != condition_v1.market_sentiment:
                print(f"  ⚠️  레짐 차이: v1({condition_v1.market_sentiment}) vs v3({condition_v3.final_regime})")
            else:
                print(f"  ✅ 레짐 일치: {condition_v3.final_regime}")
                
        except Exception as e:
            print(f"  ❌ 분석 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

def test_market_data_provider():
    """Market Data Provider 기본 기능 테스트"""
    
    print("\n📊 Market Data Provider 테스트:")
    
    # 1. 한국 종목 데이터
    try:
        df_kr = market_data_provider.get_ohlcv_korea("005930", "20251101", "20251130")
        print(f"  🇰🇷 삼성전자 데이터: {len(df_kr)}개 행")
        if not df_kr.empty:
            print(f"     최근 종가: {df_kr.iloc[-1]['close']:,.0f}원")
    except Exception as e:
        print(f"  ❌ 한국 데이터 실패: {e}")
    
    # 2. 미국 종목 데이터 (모의)
    try:
        df_us = market_data_provider.get_ohlcv_us("SPY", "20251101", "20251130")
        print(f"  🇺🇸 SPY 데이터: {len(df_us)}개 행 (모의)")
        if not df_us.empty:
            print(f"     최근 종가: ${df_us.iloc[-1]['close']:.2f}")
    except Exception as e:
        print(f"  ❌ 미국 데이터 실패: {e}")
    
    # 3. VIX 데이터
    try:
        df_vix = market_data_provider.get_vix("20251101", "20251130")
        print(f"  📈 VIX 데이터: {len(df_vix)}개 행 (모의)")
        if not df_vix.empty:
            print(f"     최근 VIX: {df_vix.iloc[-1]['close']:.1f}")
    except Exception as e:
        print(f"  ❌ VIX 데이터 실패: {e}")

def check_yfinance_removal():
    """yfinance 완전 제거 확인"""
    
    print("\n🔍 yfinance 제거 확인:")
    
    # 1. import 확인
    try:
        import yfinance
        print("  ❌ yfinance가 여전히 import 가능합니다")
    except ImportError:
        print("  ✅ yfinance import 불가 (정상)")
    
    # 2. 시스템 모듈 확인
    import sys
    yf_modules = [name for name in sys.modules.keys() if 'yfinance' in name.lower()]
    if yf_modules:
        print(f"  ⚠️  yfinance 관련 모듈 발견: {yf_modules}")
    else:
        print("  ✅ yfinance 관련 모듈 없음")
    
    # 3. Market Data Provider 동작 확인
    try:
        snapshot = market_data_provider.get_us_prev_snapshot("20251129")
        if snapshot['valid']:
            print("  ✅ Market Data Provider 정상 동작")
        else:
            print("  ⚠️  Market Data Provider 데이터 무효")
    except Exception as e:
        print(f"  ❌ Market Data Provider 오류: {e}")

if __name__ == "__main__":
    # 테스트 실행
    check_yfinance_removal()
    test_market_data_provider()
    test_november_2025_regime()