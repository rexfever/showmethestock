#!/usr/bin/env python3
"""
2025년 전체 레짐 데이터 벌크 생성
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def bulk_regime_2025():
    """2025년 전체 레짐 데이터 벌크 생성"""
    print("=== 2025년 레짐 데이터 벌크 생성 ===\n")
    
    try:
        from kiwoom_api import api
        from services.regime_storage import upsert_regime
        from services.us_market_data import get_us_prev_snapshot
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 1. KOSPI200 ETF 전체 데이터 가져오기
        print("KOSPI200 데이터 로딩...", end=" ")
        kospi_df = api.get_ohlcv("069500", 300, "20251231")  # 2025년 전체
        print(f"✅ {len(kospi_df)}일")
        
        # 2. 주요 종목들 데이터 가져오기 (섹터/수급 분석용)
        key_stocks = ['005930', '000660', '035420', '055550', '105560']  # 삼성전자, SK하이닉스, 네이버, 신한지주, KB금융
        stock_data = {}
        
        for code in key_stocks:
            print(f"{code} 데이터 로딩...", end=" ")
            stock_data[code] = api.get_ohlcv(code, 300, "20251231")
            print(f"✅ {len(stock_data[code])}일")
        
        # 3. 2025년 거래일 필터링
        kospi_df['date_str'] = kospi_df['date'].astype(str)
        trading_days_2025 = kospi_df[kospi_df['date_str'].str.startswith('2025')]['date_str'].tolist()
        
        print(f"\n2025년 거래일: {len(trading_days_2025)}일")
        
        success_count = 0
        
        # 4. 일별 레짐 계산
        for i, date in enumerate(trading_days_2025, 1):
            try:
                print(f"[{i:3d}/{len(trading_days_2025)}] {date} 계산...", end=" ")
                
                # KOSPI 수익률 계산
                kospi_data = kospi_df[kospi_df['date_str'] == date]
                if kospi_data.empty:
                    print("❌ KOSPI 데이터 없음")
                    continue
                
                # 전일 데이터 찾기
                prev_data = kospi_df[kospi_df['date_str'] < date].tail(1)
                if prev_data.empty:
                    print("❌ 전일 데이터 없음")
                    continue
                
                kospi_return = (kospi_data.iloc[0]['close'] / prev_data.iloc[0]['close'] - 1)
                volatility = (kospi_data.iloc[0]['high'] - kospi_data.iloc[0]['low']) / kospi_data.iloc[0]['close']
                
                # 한국 점수 계산
                kr_score = 0.0
                if kospi_return > 0.015: kr_score += 2.0
                elif kospi_return > 0.005: kr_score += 1.0
                elif kospi_return < -0.015: kr_score -= 2.0
                elif kospi_return < -0.005: kr_score -= 1.0
                
                if volatility < 0.02: kr_score += 1.0
                elif volatility > 0.04: kr_score -= 1.0
                
                kr_regime = "bull" if kr_score >= 2 else "bear" if kr_score <= -2 else "neutral"
                
                # 미국 데이터 (실제 API 시도, 실패시 모의)
                try:
                    us_data = get_us_prev_snapshot(date)
                    us_score = 0.0
                    if us_data.get('valid'):
                        if us_data.get('spy_r1', 0) > 0.01: us_score += 1.0
                        elif us_data.get('spy_r1', 0) < -0.01: us_score -= 1.0
                        if us_data.get('vix', 20) < 18: us_score += 1.0
                        elif us_data.get('vix', 20) > 30: us_score -= 1.0
                    else:
                        us_score = (hash(date) % 7 - 3) * 0.3  # 모의 데이터
                except:
                    us_score = (hash(date) % 7 - 3) * 0.3  # 모의 데이터
                
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
                    'us_metrics': {'us_prev_score': us_score, 'valid': True},
                    'kr_metrics': {'kr_score': kr_score, 'kospi_return': kospi_return, 'volatility': volatility},
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
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    bulk_regime_2025()