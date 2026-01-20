#!/usr/bin/env python3
"""
2025년 한국 데이터만으로 레짐 분석
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def bulk_regime_korea_only():
    """한국 데이터만으로 2025년 레짐 분석"""
    print("=== 2025년 한국 데이터 레짐 분석 ===\n")
    
    try:
        from kiwoom_api import api
        from services.regime_storage import upsert_regime
        
        # KOSPI200 ETF 전체 데이터
        print("KOSPI200 데이터 로딩...", end=" ")
        kospi_df = api.get_ohlcv("069500", 300, "20251231")
        print(f"✅ {len(kospi_df)}일")
        
        # 2025년 거래일 필터링
        kospi_df['date_str'] = kospi_df['date'].astype(str)
        trading_days_2025 = kospi_df[kospi_df['date_str'].str.startswith('2025')]['date_str'].tolist()
        
        print(f"2025년 거래일: {len(trading_days_2025)}일\n")
        
        success_count = 0
        
        for i, date in enumerate(trading_days_2025, 1):
            try:
                print(f"[{i:3d}/{len(trading_days_2025)}] {date} 계산...", end=" ")
                
                # KOSPI 데이터
                kospi_data = kospi_df[kospi_df['date_str'] == date]
                prev_kospi = kospi_df[kospi_df['date_str'] < date].tail(1)
                
                if kospi_data.empty or prev_kospi.empty:
                    print("❌ 데이터 부족")
                    continue
                
                # 수익률 및 변동성 계산
                kospi_return = (kospi_data.iloc[0]['close'] / prev_kospi.iloc[0]['close'] - 1)
                volatility = (kospi_data.iloc[0]['high'] - kospi_data.iloc[0]['low']) / kospi_data.iloc[0]['close']
                
                # 한국 점수 계산
                kr_score = 0.0
                if kospi_return > 0.015: kr_score += 2.0
                elif kospi_return > 0.005: kr_score += 1.0
                elif kospi_return < -0.015: kr_score -= 2.0
                elif kospi_return < -0.005: kr_score -= 1.0
                
                if volatility < 0.02: kr_score += 1.0
                elif volatility > 0.04: kr_score -= 1.0
                
                # 레짐 결정
                if kr_score >= 2:
                    kr_regime = "bull"
                    final_regime = "bull"
                elif kr_score <= -2:
                    kr_regime = "bear" 
                    final_regime = "bear"
                else:
                    kr_regime = "neutral"
                    final_regime = "neutral"
                
                # DB 저장
                regime_data = {
                    'final_regime': final_regime,
                    'kr_regime': kr_regime,
                    'us_prev_regime': 'neutral',
                    'us_preopen_flag': 'none',
                    'us_metrics': {'us_prev_score': 0.0, 'valid': False},
                    'kr_metrics': {
                        'kr_score': kr_score,
                        'kospi_return': kospi_return,
                        'volatility': volatility
                    },
                    'us_preopen_metrics': {'us_preopen_risk_score': 0.0, 'us_preopen_flag': 'none'},
                    'version': 'regime_v4'
                }
                
                upsert_regime(date, regime_data)
                print(f"✅ {final_regime} (점수:{kr_score:.1f})")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {e}")
                continue
        
        print(f"\n=== 완료 ===")
        print(f"성공: {success_count}/{len(trading_days_2025)}일")
        
        # 11월 결과 확인
        print(f"\n11월 결과:")
        from query_november_regime_fixed import query_november_regime
        query_november_regime()
        
    except Exception as e:
        print(f"❌ 실패: {e}")

if __name__ == "__main__":
    bulk_regime_korea_only()