#!/usr/bin/env python3
"""
Yahoo Finance CSV 다운로드로 2025년 레짐 분석
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def bulk_regime_yahoo_csv():
    """Yahoo Finance CSV로 2025년 레짐 분석"""
    print("=== Yahoo Finance CSV 2025년 레짐 분석 ===\n")
    
    try:
        import pandas as pd
        import requests
        from services.regime_storage import upsert_regime
        from kiwoom_api import api
        
        # 1. 한국 KOSPI200 데이터
        print("KOSPI200 데이터 로딩...", end=" ")
        kospi_df = api.get_ohlcv("069500", 300, "20251231")
        print(f"✅ {len(kospi_df)}일")
        
        # 2. Yahoo Finance CSV 다운로드
        symbols = {
            'SPY': 'SPY',
            'QQQ': 'QQQ', 
            '^VIX': '%5EVIX'
        }
        
        us_data = {}
        for symbol, yahoo_symbol in symbols.items():
            try:
                print(f"{symbol} CSV 다운로드...", end=" ")
                url = f"https://query1.finance.yahoo.com/v7/finance/download/{yahoo_symbol}?period1=1640995200&period2=1735689600&interval=1d&events=history"
                response = requests.get(url)
                
                if response.status_code == 200:
                    from io import StringIO
                    df = pd.read_csv(StringIO(response.text))
                    df['Date'] = pd.to_datetime(df['Date'])
                    us_data[symbol] = df
                    print(f"✅ {len(df)}일")
                else:
                    print(f"❌ {response.status_code}")
                    us_data[symbol] = pd.DataFrame()
            except Exception as e:
                print(f"❌ {e}")
                us_data[symbol] = pd.DataFrame()
        
        # 3. 2025년 거래일 필터링
        kospi_df['date_str'] = kospi_df['date'].astype(str)
        trading_days_2025 = kospi_df[kospi_df['date_str'].str.startswith('2025')]['date_str'].tolist()
        
        print(f"\n2025년 거래일: {len(trading_days_2025)}일\n")
        
        success_count = 0
        
        for i, date in enumerate(trading_days_2025, 1):
            try:
                print(f"[{i:3d}/{len(trading_days_2025)}] {date} 계산...", end=" ")
                
                # 한국 데이터
                kospi_data = kospi_df[kospi_df['date_str'] == date]
                prev_kospi = kospi_df[kospi_df['date_str'] < date].tail(1)
                
                if kospi_data.empty or prev_kospi.empty:
                    print("❌ KOSPI 데이터 부족")
                    continue
                
                kospi_return = (kospi_data.iloc[0]['close'] / prev_kospi.iloc[0]['close'] - 1)
                volatility = (kospi_data.iloc[0]['high'] - kospi_data.iloc[0]['low']) / kospi_data.iloc[0]['close']
                
                # 한국 점수
                kr_score = 0.0
                if kospi_return > 0.015: kr_score += 2.0
                elif kospi_return > 0.005: kr_score += 1.0
                elif kospi_return < -0.015: kr_score -= 2.0
                elif kospi_return < -0.005: kr_score -= 1.0
                
                if volatility < 0.02: kr_score += 1.0
                elif volatility > 0.04: kr_score -= 1.0
                
                kr_regime = "bull" if kr_score >= 2 else "bear" if kr_score <= -2 else "neutral"
                
                # 미국 데이터 (날짜 매칭)
                date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                us_score = 0.0
                spy_return = 0.0
                vix_value = 20.0
                
                # SPY 수익률
                if not us_data['SPY'].empty:
                    spy_today = us_data['SPY'][us_data['SPY']['Date'] == date_formatted]
                    spy_prev = us_data['SPY'][us_data['SPY']['Date'] < date_formatted].tail(1)
                    
                    if not spy_today.empty and not spy_prev.empty:
                        spy_return = (spy_today.iloc[0]['Close'] / spy_prev.iloc[0]['Close'] - 1)
                        if spy_return > 0.01: us_score += 1.0
                        elif spy_return < -0.01: us_score -= 1.0
                
                # VIX
                if not us_data['^VIX'].empty:
                    vix_today = us_data['^VIX'][us_data['^VIX']['Date'] == date_formatted]
                    if not vix_today.empty:
                        vix_value = vix_today.iloc[0]['Close']
                        if vix_value < 18: us_score += 1.0
                        elif vix_value > 30: us_score -= 1.0
                
                us_regime = "bull" if us_score >= 1 else "bear" if us_score <= -1 else "neutral"
                
                # 최종 레짐
                final_score = 0.6 * kr_score + 0.4 * us_score
                final_regime = "bull" if final_score >= 1.5 else "bear" if final_score <= -1.5 else "neutral"
                
                # DB 저장
                regime_data = {
                    'final_regime': final_regime,
                    'kr_regime': kr_regime,
                    'us_prev_regime': us_regime,
                    'us_preopen_flag': 'none',
                    'us_metrics': {
                        'spy_r1': spy_return,
                        'vix': vix_value,
                        'us_prev_score': us_score,
                        'valid': True
                    },
                    'kr_metrics': {
                        'kr_score': kr_score,
                        'kospi_return': kospi_return,
                        'volatility': volatility
                    },
                    'us_preopen_metrics': {'us_preopen_risk_score': 0.0, 'us_preopen_flag': 'none'},
                    'version': 'regime_v4'
                }
                
                upsert_regime(date, regime_data)
                print(f"✅ {final_regime}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {e}")
                continue
        
        print(f"\n=== 완료 ===")
        print(f"성공: {success_count}/{len(trading_days_2025)}일")
        
    except Exception as e:
        print(f"❌ 실패: {e}")

if __name__ == "__main__":
    bulk_regime_yahoo_csv()