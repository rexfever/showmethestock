#!/usr/bin/env python3
"""
실제 데이터로 Global Regime v4 테스트
"""
import sys
import os
import time
from datetime import datetime

# backend 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_real_futures_data():
    """실제 선물 데이터 다운로드 테스트"""
    print("📊 실제 미국 선물 데이터 다운로드 테스트")
    
    try:
        from services.us_futures_data_v8 import us_futures_data_v8 as us_futures_data
        
        symbols = ["SPY", "QQQ", "ES=F", "NQ=F"]
        
        for i, symbol in enumerate(symbols):
            print(f"\n🔄 {symbol} 다운로드 중...")
            
            # 요청 간격 추가 (Rate limiting 방지)
            if i > 0:
                time.sleep(2)
            
            df = us_futures_data.fetch_data(symbol)
            
            if not df.empty:
                print(f"✅ {symbol}: {len(df)}개 행")
                print(f"   최근 날짜: {df.index[-1].strftime('%Y-%m-%d')}")
                print(f"   최근 종가: {df['Close'].iloc[-1]:.2f}")
                
                # 최근 5일 데이터 확인
                recent_data = df.tail(5)
                print(f"   최근 5일 수익률:")
                for j in range(1, len(recent_data)):
                    prev_close = recent_data['Close'].iloc[j-1]
                    curr_close = recent_data['Close'].iloc[j]
                    ret = (curr_close / prev_close - 1) * 100
                    date_str = recent_data.index[j].strftime('%m-%d')
                    print(f"     {date_str}: {ret:+.2f}%")
            else:
                print(f"❌ {symbol}: 데이터 없음")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def generate_real_regime_v4():
    """실제 데이터로 Regime v4 생성"""
    print("\n📊 실제 데이터로 Global Regime v4 생성")
    
    try:
        from scanner_v2.regime_v4 import analyze_regime_v4
        from services.regime_storage import upsert_regime
        
        # 최근 거래일들 (11월)
        trading_days = ["20241118", "20241119", "20241120", "20241121", "20241122"]
        
        for date_str in trading_days:
            print(f"\n🔄 {date_str} 실제 데이터 분석 중...")
            
            try:
                # 실제 v4 분석 실행
                result = analyze_regime_v4(date_str)
                
                if result['version'] == 'regime_v4':
                    print(f"✅ {date_str} 분석 완료:")
                    print(f"   한국: {result['kr_score']:.2f} ({result['kr_regime']})")
                    print(f"   미국: {result['us_prev_score']:.2f} ({result['us_prev_regime']})")
                    print(f"   선물: {result['us_futures_score']:.2f} ({result['us_futures_regime']})")
                    print(f"   최종: {result['final_regime']} (점수: {result['final_score']:.2f})")
                    
                    # DB 저장
                    regime_data = {
                        'final_regime': result['final_regime'],
                        'kr_regime': result['kr_regime'],
                        'us_prev_regime': result['us_prev_regime'],
                        'us_futures_score': result['us_futures_score'],
                        'us_futures_regime': result['us_futures_regime'],
                        'version': 'regime_v4'
                    }
                    upsert_regime(date_str, regime_data)
                    print(f"   DB 저장 완료")
                else:
                    print(f"⚠️ {date_str}: v4 분석 실패, fallback 사용됨")
                
            except Exception as e:
                print(f"❌ {date_str} 분석 실패: {e}")
        
        print(f"\n🎯 실제 데이터 기반 v4 레짐 생성 완료")
        
        # 결과 확인
        print("\n📋 생성된 실제 v4 레짐:")
        verify_real_v4_data(trading_days)
        
    except Exception as e:
        print(f"❌ 실제 데이터 생성 실패: {e}")
        import traceback
        traceback.print_exc()

def verify_real_v4_data(dates):
    """실제 v4 데이터 검증"""
    try:
        from services.regime_storage import load_regime
        
        for date_str in dates:
            regime_data = load_regime(date_str)
            if regime_data:
                final = regime_data.get('final_regime', 'N/A')
                kr = regime_data.get('kr_regime', 'N/A')
                us = regime_data.get('us_prev_regime', 'N/A')
                fut = regime_data.get('us_futures_regime', 'N/A')
                
                print(f"  {date_str}: {final} (KR:{kr}, US:{us}, FUT:{fut})")
            else:
                print(f"  {date_str}: 데이터 없음")
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")

if __name__ == "__main__":
    print("🚀 실제 데이터 Global Regime v4 테스트 시작\n")
    
    test_real_futures_data()
    time.sleep(3)  # API 제한 방지
    generate_real_regime_v4()
    
    print("\n🎯 실제 데이터 테스트 완료!")