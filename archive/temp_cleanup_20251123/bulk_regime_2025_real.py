#!/usr/bin/env python3
"""
2025년 전체 레짐 데이터 실제 API로 벌크 생성
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def bulk_regime_2025_real():
    """2025년 전체 레짐 데이터 실제 API로 벌크 생성"""
    print("=== 2025년 레짐 데이터 실제 API 벌크 생성 ===\n")
    
    try:
        from kiwoom_api import api
        from services.regime_storage import upsert_regime
        from services.alphavantage_provider import alpha_vantage
        import pandas as pd
        
        # 1. KOSPI200 ETF 전체 데이터
        print("KOSPI200 데이터 로딩...", end=" ")
        kospi_df = api.get_ohlcv("069500", 300, "20251231")
        print(f"✅ {len(kospi_df)}일")
        
        # 2. 미국 데이터 (SPY, QQQ, VIX)
        print("SPY 데이터 로딩...", end=" ")
        spy_df = alpha_vantage.get_daily_data("SPY", "full")
        print(f"✅ {len(spy_df)}일")
        
        print("QQQ 데이터 로딩...", end=" ")
        qqq_df = alpha_vantage.get_daily_data("QQQ", "full")
        print(f"✅ {len(qqq_df)}일")
        
        print("VIX 데이터 로딩...", end=" ")
        vix_df = alpha_vantage.get_daily_data("VIX", "full")
        print(f"✅ {len(vix_df)}일")
        
        # 3. 2025년 거래일 필터링
        kospi_df['date_str'] = kospi_df['date'].astype(str)
        trading_days_2025 = kospi_df[kospi_df['date_str'].str.startswith('2025')]['date_str'].tolist()
        
        print(f"\n2025년 거래일: {len(trading_days_2025)}일")
        
        success_count = 0
        
        # 4. 일별 레짐 계산
        for i, date in enumerate(trading_days_2025, 1):
            try:
                print(f"[{i:3d}/{len(trading_days_2025)}] {date} 계산...", end=" ")
                
                # KOSPI 데이터
                kospi_data = kospi_df[kospi_df['date_str'] == date]
                prev_kospi = kospi_df[kospi_df['date_str'] < date].tail(1)
                
                if kospi_data.empty or prev_kospi.empty:
                    print("❌ KOSPI 데이터 부족")
                    continue
                
                kospi_return = (kospi_data.iloc[0]['close'] / prev_kospi.iloc[0]['close'] - 1)
                volatility = (kospi_data.iloc[0]['high'] - kospi_data.iloc[0]['low']) / kospi_data.iloc[0]['close']
                
                # 미국 데이터 (날짜 매칭)
                date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                spy_data = spy_df[spy_df['date'] == date_formatted]
                qqq_data = qqq_df[qqq_df['date'] == date_formatted]
                vix_data = vix_df[vix_df['date'] == date_formatted]
                
                # 한국 점수
                kr_score = 0.0
                if kospi_return > 0.015: kr_score += 2.0
                elif kospi_return > 0.005: kr_score += 1.0
                elif kospi_return < -0.015: kr_score -= 2.0
                elif kospi_return < -0.005: kr_score -= 1.0
                
                if volatility < 0.02: kr_score += 1.0
                elif volatility > 0.04: kr_score -= 1.0
                
                kr_regime = "bull" if kr_score >= 2 else "bear" if kr_score <= -2 else "neutral"
                
                # 미국 점수
                us_score = 0.0
                if not spy_data.empty:
                    spy_prev = spy_df[spy_df['date'] < date_formatted].tail(1)
                    if not spy_prev.empty:
                        spy_return = (spy_data.iloc[0]['close'] / spy_prev.iloc[0]['close'] - 1)
                        if spy_return > 0.01: us_score += 1.0
                        elif spy_return < -0.01: us_score -= 1.0
                
                if not vix_data.empty:
                    vix_value = vix_data.iloc[0]['close']
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
                        'spy_r1': spy_data.iloc[0]['close'] / spy_prev.iloc[0]['close'] - 1 if not spy_data.empty and not spy_prev.empty else 0,
                        'vix': vix_data.iloc[0]['close'] if not vix_data.empty else 20,
                        'us_prev_score': us_score,
                        'valid': True
                    },
                    'kr_metrics': {
                        'kr_score': kr_score,
                        'kospi_return': kospi_return,
                        'volatility': volatility
                    },
                    'us_preopen_metrics': {
                        'us_preopen_risk_score': 0.0,
                        'us_preopen_flag': 'none'
                    },
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
    bulk_regime_2025_real()