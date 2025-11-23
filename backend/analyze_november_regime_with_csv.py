"""
CSV 캐시 데이터를 이용한 11월 레짐 분석
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

def load_csv_data():
    """CSV 캐시 데이터 로드"""
    cache_dir = "/Users/rexsmac/workspace/stock-finder/cache/us_futures"
    
    data = {}
    symbols = {
        'SPY': 'SPY.csv',
        'QQQ': 'QQQ.csv', 
        'ES=F': 'ES_F.csv',
        'NQ=F': 'NQ_F.csv',
        '^VIX': '^VIX.csv',
        'DX-Y.NYB': 'DX_Y_NYB.csv'
    }
    
    for symbol, filename in symbols.items():
        filepath = os.path.join(cache_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            data[symbol] = df
            print(f"✅ {symbol}: {len(df)}개 행 로드")
        else:
            print(f"❌ {symbol}: 파일 없음")
    
    return data

def get_kospi_data():
    """KOSPI 데이터 로드 (키움 API 대신 임시 데이터)"""
    # 11월 KOSPI 임시 데이터 (실제로는 키움 API에서 가져와야 함)
    dates = pd.date_range('2024-11-01', '2024-11-23', freq='D')
    # 11월 KOSPI 하락 추세 반영
    base_price = 2500
    prices = []
    for i, date in enumerate(dates):
        # 11월 10일부터 하락 추세
        if i < 9:  # 11월 1~9일
            price = base_price + np.random.normal(0, 10)
        else:  # 11월 10일 이후
            price = base_price - (i-9) * 5 + np.random.normal(0, 15)
        prices.append(max(price, 2300))  # 최소값 설정
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    df.set_index('date', inplace=True)
    return df

def compute_kr_score_v4(df_kospi, target_date):
    """한국 장세 점수 계산 v4"""
    if df_kospi.empty or len(df_kospi) < 5:
        return {"kr_score": 0.0, "kr_regime": "neutral"}
    
    try:
        # 해당 날짜까지의 데이터만 사용
        df_filtered = df_kospi[df_kospi.index <= target_date]
        if len(df_filtered) < 2:
            return {"kr_score": 0.0, "kr_regime": "neutral"}
        
        # 수익률 계산
        r1 = df_filtered['close'].iloc[-1] / df_filtered['close'].iloc[-2] - 1
        
        # 3일 EMA 변화율
        if len(df_filtered) >= 4:
            ema3 = df_filtered['close'].ewm(span=3).mean()
            r3 = ema3.iloc[-1] / ema3.iloc[-4] - 1
        else:
            r3 = 0
        
        # 5일 평균 수익률
        if len(df_filtered) >= 5:
            r5 = df_filtered['close'].pct_change().tail(5).mean()
        else:
            r5 = 0
        
        # 점수 계산
        score = 0.0
        if r1 > 0.015: score += 2.0
        elif r1 > 0.005: score += 1.0
        elif r1 < -0.015: score -= 2.0
        elif r1 < -0.005: score -= 1.0
        
        if r3 > 0.02: score += 1.0
        elif r3 < -0.02: score -= 1.0
        
        if r5 > 0.01: score += 1.0
        elif r5 < -0.01: score -= 1.0
        
        # 레짐 결정
        if score >= 2.0:
            regime = "bull"
        elif score <= -2.0:
            regime = "bear"
        else:
            regime = "neutral"
        
        return {"kr_score": score, "kr_regime": regime}
        
    except Exception as e:
        print(f"한국 점수 계산 실패: {e}")
        return {"kr_score": 0.0, "kr_regime": "neutral"}

def compute_us_prev_score_v4(us_data, target_date):
    """미국 전일 장세 점수 계산 v4"""
    try:
        score = 0.0
        
        # SPY 수익률
        if 'SPY' in us_data:
            df_spy = us_data['SPY'][us_data['SPY'].index <= target_date]
            if len(df_spy) >= 2:
                spy_r1 = df_spy['Close'].iloc[-1] / df_spy['Close'].iloc[-2] - 1
                if spy_r1 > 0.01: score += 1.0
                elif spy_r1 < -0.01: score -= 1.0
        
        # QQQ 수익률
        if 'QQQ' in us_data:
            df_qqq = us_data['QQQ'][us_data['QQQ'].index <= target_date]
            if len(df_qqq) >= 2:
                qqq_r1 = df_qqq['Close'].iloc[-1] / df_qqq['Close'].iloc[-2] - 1
                if qqq_r1 > 0.012: score += 1.0
                elif qqq_r1 < -0.012: score -= 1.0
        
        # VIX 변화율
        if '^VIX' in us_data:
            df_vix = us_data['^VIX'][us_data['^VIX'].index <= target_date]
            if len(df_vix) >= 2:
                vix_change = df_vix['Close'].iloc[-1] / df_vix['Close'].iloc[-2] - 1
                if vix_change < -0.05: score += 1.0
                elif vix_change > 0.1: score -= 2.0
                elif vix_change > 0.05: score -= 1.0
        
        # 레짐 결정
        if score >= 2.0:
            regime = "bull"
        elif score <= -2.0:
            regime = "bear"
        else:
            regime = "neutral"
        
        return {"us_prev_score": score, "us_prev_regime": regime}
        
    except Exception as e:
        print(f"미국 전일 점수 계산 실패: {e}")
        return {"us_prev_score": 0.0, "us_prev_regime": "neutral"}

def compute_us_futures_score_v4(us_data, target_date):
    """미국 선물 점수 계산 v4"""
    try:
        score = 0.0
        
        # ES=F 변화율
        if 'ES=F' in us_data:
            df_es = us_data['ES=F'][us_data['ES=F'].index <= target_date]
            if len(df_es) >= 2:
                es_change = df_es['Close'].iloc[-1] / df_es['Close'].iloc[-2] - 1
                if es_change > 0.008: score += 1.5
                elif es_change > 0.003: score += 0.5
                elif es_change < -0.008: score -= 1.5
                elif es_change < -0.003: score -= 0.5
        
        # NQ=F 변화율
        if 'NQ=F' in us_data:
            df_nq = us_data['NQ=F'][us_data['NQ=F'].index <= target_date]
            if len(df_nq) >= 2:
                nq_change = df_nq['Close'].iloc[-1] / df_nq['Close'].iloc[-2] - 1
                if nq_change > 0.01: score += 1.5
                elif nq_change > 0.004: score += 0.5
                elif nq_change < -0.01: score -= 1.5
                elif nq_change < -0.004: score -= 0.5
        
        # VIX 변화율
        if '^VIX' in us_data:
            df_vix = us_data['^VIX'][us_data['^VIX'].index <= target_date]
            if len(df_vix) >= 2:
                vix_change = df_vix['Close'].iloc[-1] / df_vix['Close'].iloc[-2] - 1
                if vix_change < -0.03: score += 1.0
                elif vix_change > 0.05: score -= 1.5
                elif vix_change > 0.02: score -= 0.5
        
        # DXY 변화율
        if 'DX-Y.NYB' in us_data:
            df_dxy = us_data['DX-Y.NYB'][us_data['DX-Y.NYB'].index <= target_date]
            if len(df_dxy) >= 2:
                dxy_change = df_dxy['Close'].iloc[-1] / df_dxy['Close'].iloc[-2] - 1
                if dxy_change > 0.005: score -= 0.5
                elif dxy_change < -0.005: score += 0.5
        
        # 레짐 결정
        if score >= 2.0:
            regime = "bull"
        elif score <= -2.0:
            regime = "bear"
        else:
            regime = "neutral"
        
        return {"us_futures_score": score, "us_futures_regime": regime}
        
    except Exception as e:
        print(f"미국 선물 점수 계산 실패: {e}")
        return {"us_futures_score": 0.0, "us_futures_regime": "neutral"}

def combine_global_regime_v4(kr_result, us_prev_result, us_futures_result):
    """글로벌 레짐 v4 조합"""
    try:
        # 가중 평균 점수
        final_score = (0.6 * kr_result["kr_score"] + 
                      0.2 * us_prev_result["us_prev_score"] + 
                      0.2 * us_futures_result["us_futures_score"])
        
        # 최종 레짐 결정
        if final_score < -2.0:
            final_regime = "crash"
        elif final_score < -0.3:
            final_regime = "bear"
        elif final_score > 0.3:
            final_regime = "bull"
        else:
            final_regime = "neutral"
        
        return {
            "final_score": final_score,
            "final_regime": final_regime
        }
        
    except Exception as e:
        print(f"글로벌 레짐 조합 실패: {e}")
        return {"final_score": 0.0, "final_regime": "neutral"}

def analyze_november_regime_with_csv():
    """CSV 데이터를 이용한 11월 레짐 분석"""
    print("📊 CSV 캐시 데이터를 이용한 11월 레짐 분석 시작")
    
    # 데이터 로드
    us_data = load_csv_data()
    kospi_data = get_kospi_data()
    
    # 11월 날짜 범위
    november_dates = pd.date_range('2024-11-01', '2024-11-23', freq='D')
    
    results = {}
    
    print(f"📅 분석 대상: {len(november_dates)}일")
    
    for i, date in enumerate(november_dates, 1):
        try:
            date_str = date.strftime('%Y%m%d')
            print(f"  [{i:2d}/{len(november_dates)}] {date_str} 분석 중...")
            
            # 점수 계산
            kr_result = compute_kr_score_v4(kospi_data, date)
            us_prev_result = compute_us_prev_score_v4(us_data, date)
            us_futures_result = compute_us_futures_score_v4(us_data, date)
            
            # 글로벌 조합
            global_result = combine_global_regime_v4(kr_result, us_prev_result, us_futures_result)
            
            # 결과 저장
            results[date_str] = {
                'date': date_str,
                'final_regime': global_result['final_regime'],
                'final_score': global_result['final_score'],
                'kr_score': kr_result['kr_score'],
                'kr_regime': kr_result['kr_regime'],
                'us_prev_score': us_prev_result['us_prev_score'],
                'us_prev_regime': us_prev_result['us_prev_regime'],
                'us_futures_score': us_futures_result['us_futures_score'],
                'us_futures_regime': us_futures_result['us_futures_regime']
            }
            
            print(f"    결과: {global_result['final_regime']} (점수: {global_result['final_score']:.2f})")
            
        except Exception as e:
            print(f"    오류: {e}")
            results[date_str] = {
                'date': date_str,
                'error': str(e)
            }
    
    # 결과 통계
    regime_counts = {}
    total_score = 0
    valid_results = 0
    
    for date, result in results.items():
        if 'final_regime' in result:
            regime = result['final_regime']
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            total_score += result['final_score']
            valid_results += 1
    
    avg_score = total_score / valid_results if valid_results > 0 else 0
    
    print(f"\n📈 11월 레짐 분석 결과 (CSV 데이터 기반):")
    print(f"  총 분석일: {valid_results}일")
    print(f"  평균 점수: {avg_score:.2f}")
    print(f"  레짐 분포:")
    for regime, count in regime_counts.items():
        percentage = (count / valid_results * 100) if valid_results > 0 else 0
        print(f"    {regime}: {count}일 ({percentage:.1f}%)")
    
    # 결과 저장
    output_file = f"november_regime_analysis_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'period': 'November 2024',
        'data_source': 'CSV Cache',
        'total_days': valid_results,
        'average_score': avg_score,
        'regime_distribution': regime_counts,
        'daily_results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {output_file}")
    
    return summary

if __name__ == "__main__":
    analyze_november_regime_with_csv()