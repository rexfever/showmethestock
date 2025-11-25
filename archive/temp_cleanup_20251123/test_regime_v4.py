#!/usr/bin/env python3
"""
Global Regime v4 테스트 스크립트
"""
import sys
import os
from datetime import datetime

# backend 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_cached_data():
    """캐시된 데이터 테스트"""
    print("📊 캐시된 데이터 테스트")
    
    try:
        import pandas as pd
        import pickle
        import os
        
        # 한국 데이터 테스트
        kospi_path = 'backend/data_cache/kospi200_ohlcv.pkl'
        if os.path.exists(kospi_path):
            with open(kospi_path, 'rb') as f:
                kospi_df = pickle.load(f)
            print(f"✅ KOSPI200: {len(kospi_df)}개 행 ({kospi_df.index.min()} ~ {kospi_df.index.max()})")
        
        # 미국 데이터 테스트
        us_files = ['cache/us_futures/SPY.csv', 'cache/us_futures/QQQ.csv', 'cache/us_futures/^VIX.csv']
        for file_path in us_files:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                name = file_path.split('/')[-1].replace('.csv', '')
                print(f"✅ {name}: {len(df)}개 행 ({df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')})")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

def test_regime_v4_analysis():
    """캐시 기반 Regime v4 분석 테스트"""
    print("\n📊 캐시 기반 Global Regime v4 분석 테스트")
    
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        
        # 오늘 날짜로 테스트
        today = datetime.now().strftime('%Y%m%d')
        print(f"🔄 {today} 캐시 분석 중...")
        
        result = regime_analyzer_cached.analyze_regime_v4_cached(today)
        
        print(f"✅ 캐시 분석 완료:")
        print(f"   한국 점수: {result['kr_score']:.2f} ({result['kr_regime']})")
        print(f"   미국 전일: {result['us_prev_score']:.2f} ({result['us_prev_regime']})")
        print(f"   미국 선물: {result['us_futures_score']:.2f} ({result['us_futures_regime']})")
        print(f"   최종 레짐: {result['final_regime']} (점수: {result['final_score']:.2f})")
        
        # 캐시 통계
        cache_stats = regime_analyzer_cached.get_cache_stats()
        print(f"   캐시 파일: {cache_stats.get('total_files', 0)}개")
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

def test_market_analyzer_v4():
    """MarketAnalyzer v4 통합 테스트"""
    print("\n📊 MarketAnalyzer v4 통합 테스트")
    
    try:
        from market_analyzer import market_analyzer
        
        today = datetime.now().strftime('%Y%m%d')
        print(f"🔄 {today} v4 분석 중...")
        
        condition = market_analyzer.analyze_market_condition_v4(today)
        
        print(f"✅ 통합 분석 완료:")
        print(f"   버전: {condition.version}")
        print(f"   최종 레짐: {condition.final_regime}")
        print(f"   최종 점수: {condition.final_score:.2f}")
        print(f"   한국 레짐: {condition.kr_regime}")
        print(f"   미국 레짐: {condition.us_prev_regime}")
        
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_db_storage():
    """DB 저장 테스트"""
    print("\n📊 DB 저장 테스트")
    
    try:
        from services.regime_storage import load_regime
        
        today = datetime.now().strftime('%Y%m%d')
        print(f"🔄 {today} DB 조회 중...")
        
        regime_data = load_regime(today)
        
        if regime_data:
            print(f"✅ DB 조회 성공:")
            print(f"   최종 레짐: {regime_data.get('final_regime')}")
            print(f"   한국 레짐: {regime_data.get('kr_regime')}")
            print(f"   미국 레짐: {regime_data.get('us_prev_regime')}")
            print(f"   선물 레짐: {regime_data.get('us_futures_regime', 'N/A')}")
        else:
            print(f"⚠️ DB에 데이터 없음")
        
    except Exception as e:
        print(f"❌ DB 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Global Regime v4 종합 테스트 시작\n")
    
    test_cached_data()
    test_regime_v4_analysis()
    test_market_analyzer_v4()
    test_db_storage()
    
    print("\n🎯 테스트 완료!")