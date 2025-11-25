#!/usr/bin/env python3
"""
2025년 9월-11월 장세 데이터 생성 스크립트
Global Regime Model v3 데이터를 DB에 채움
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List
import random

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.regime_storage_sqlite import upsert_regime
from services.us_market_data import get_us_prev_snapshot

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """거래일 목록 생성 (주말 제외)"""
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    trading_days = []
    current = start
    
    while current <= end:
        # 주말 제외 (월-금만)
        if current.weekday() < 5:
            trading_days.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    return trading_days

def generate_mock_kospi_data(date: str, trend: str = "neutral") -> tuple:
    """모의 KOSPI 데이터 생성"""
    base_return = 0.0
    base_volatility = 0.025
    
    # 장세별 기본 수익률 설정
    if trend == "bull":
        base_return = random.uniform(0.005, 0.025)  # 0.5% ~ 2.5%
        base_volatility = random.uniform(0.015, 0.030)
    elif trend == "bear":
        base_return = random.uniform(-0.025, -0.005)  # -2.5% ~ -0.5%
        base_volatility = random.uniform(0.020, 0.040)
    elif trend == "crash":
        base_return = random.uniform(-0.050, -0.025)  # -5% ~ -2.5%
        base_volatility = random.uniform(0.030, 0.060)
    else:  # neutral
        base_return = random.uniform(-0.010, 0.010)  # -1% ~ 1%
        base_volatility = random.uniform(0.015, 0.035)
    
    # 저가 기준 수익률 (일반적으로 종가보다 낮음)
    low_return = base_return - random.uniform(0.005, 0.015)
    
    return base_return, base_volatility, low_return

def generate_mock_universe_data(kospi_return: float) -> tuple:
    """모의 유니버스 데이터 생성"""
    # 유니버스 평균은 KOSPI와 유사하지만 약간의 차이
    universe_return = kospi_return + random.uniform(-0.005, 0.005)
    sample_size = random.randint(80, 120)
    
    return universe_return, sample_size

def create_regime_data_for_date(date: str, market_trend: str = "neutral") -> dict:
    """특정 날짜의 장세 데이터 생성"""
    
    # 1. 한국 장세 데이터 생성
    kospi_return, volatility, kospi_low_return = generate_mock_kospi_data(date, market_trend)
    universe_return, sample_size = generate_mock_universe_data(kospi_return)
    
    # intraday drop 계산
    intraday_drop = kospi_low_return if kospi_low_return is not None else kospi_return
    
    # 한국 장세 점수 계산
    kr_trend_score = 0.0
    if kospi_return > 0.015: kr_trend_score += 1.0
    if kospi_return > 0.025: kr_trend_score += 1.0
    if kospi_return < -0.015: kr_trend_score -= 1.0
    if kospi_return < -0.025: kr_trend_score -= 1.0
    
    kr_vol_score = 0.0
    if volatility < 0.02: kr_vol_score += 1.0
    elif volatility > 0.04: kr_vol_score -= 1.0
    
    kr_breadth_score = 0.0
    if universe_return > 0.01: kr_breadth_score += 1.0
    elif universe_return < -0.01: kr_breadth_score -= 1.0
    
    kr_intraday_score = 0.0
    if intraday_drop > -0.01: kr_intraday_score += 1.0
    elif intraday_drop < -0.025: kr_intraday_score -= 1.0
    
    kr_score = kr_trend_score + kr_vol_score + kr_breadth_score + kr_intraday_score
    
    # 한국 레짐 결정
    if intraday_drop <= -0.025 and kospi_return < -0.02:
        kr_regime = "crash"
    elif kr_score >= 2:
        kr_regime = "bull"
    elif kr_score <= -2:
        kr_regime = "bear"
    else:
        kr_regime = "neutral"
    
    # 2. 미국 장세 데이터 생성 (실제 데이터 시도, 실패시 모의 데이터)
    try:
        us_data = get_us_prev_snapshot(date)
        if not us_data.get("valid", False):
            raise Exception("Invalid US data")
        logger.info(f"실제 미국 데이터 사용: {date}")
    except Exception as e:
        logger.warning(f"실제 미국 데이터 로드 실패 ({date}): {e}, 모의 데이터 사용")
        # 장세 트렌드에 따라 미국 모의 데이터 조정
        if market_trend == "bull":
            spy_r3_base = random.uniform(0.005, 0.020)
            vix_base = random.uniform(15, 25)
        elif market_trend == "bear":
            spy_r3_base = random.uniform(-0.020, -0.005)
            vix_base = random.uniform(25, 40)
        elif market_trend == "crash":
            spy_r3_base = random.uniform(-0.040, -0.020)
            vix_base = random.uniform(35, 50)
        else:  # neutral
            spy_r3_base = random.uniform(-0.010, 0.010)
            vix_base = random.uniform(18, 30)
        
        us_data = {
            "spy_r3": spy_r3_base,
            "qqq_r3": spy_r3_base + random.uniform(-0.005, 0.005),
            "spy_r5": spy_r3_base * 1.5 + random.uniform(-0.010, 0.010),
            "qqq_r5": spy_r3_base * 1.8 + random.uniform(-0.015, 0.015),
            "vix": vix_base,
            "ust10y_change": random.uniform(-0.15, 0.15),
            "valid": True
        }
    
    # 미국 장세 점수 계산
    us_trend_score = 0.0
    if us_data["spy_r3"] > 0.015: us_trend_score += 1.0
    if us_data["qqq_r3"] > 0.020: us_trend_score += 1.0
    if us_data["spy_r5"] < -0.03: us_trend_score -= 1.0
    if us_data["qqq_r5"] < -0.04: us_trend_score -= 1.0
    
    us_vol_score = 0.0
    vix = us_data["vix"]
    if vix < 18: us_vol_score += 1.0
    if vix > 30: us_vol_score -= 1.0
    if vix > 35: us_vol_score -= 1.0
    
    us_macro_score = 0.0
    ust10y_change = us_data["ust10y_change"]
    if ust10y_change > 0.10: us_macro_score -= 1.0
    if ust10y_change < -0.10: us_macro_score += 1.0
    
    us_prev_score = us_trend_score + us_vol_score + us_macro_score
    
    # 미국 레짐 결정
    if vix > 35:
        us_prev_regime = "crash"
    elif us_prev_score >= 2:
        us_prev_regime = "bull"
    elif us_prev_score <= -2:
        us_prev_regime = "bear"
    else:
        us_prev_regime = "neutral"
    
    # 3. 글로벌 레짐 조합
    base_score = 0.6 * kr_score + 0.4 * us_prev_score
    
    # Pre-open 리스크는 백테스트에서는 0
    risk_penalty = 0.0
    final_score = base_score - risk_penalty
    
    # 최종 레짐 결정
    if us_prev_regime == "crash" or kr_regime == "crash":
        final_regime = "crash"
    elif final_score >= 2.0:
        final_regime = "bull"
    elif final_score <= -2.0:
        final_regime = "bear"
    else:
        final_regime = "neutral"
    
    # 데이터 구조 생성
    regime_data = {
        'final_regime': final_regime,
        'kr_regime': kr_regime,
        'us_prev_regime': us_prev_regime,
        'us_preopen_flag': 'none',
        'us_metrics': us_data,
        'kr_metrics': {
            'kr_trend_score': kr_trend_score,
            'kr_vol_score': kr_vol_score,
            'kr_breadth_score': kr_breadth_score,
            'kr_intraday_score': kr_intraday_score,
            'kr_score': kr_score,
            'kr_regime': kr_regime,
            'intraday_drop': intraday_drop,
            'kospi_return': kospi_return,
            'volatility': volatility,
            'universe_return': universe_return,
            'sample_size': sample_size
        },
        'us_preopen_metrics': {
            'us_preopen_risk_score': 0.0,
            'us_preopen_flag': 'none'
        }
    }
    
    return regime_data

def generate_market_trend_pattern() -> List[str]:
    """9월-11월 시장 트렌드 패턴 생성"""
    # 실제 2025년 9월-11월 패턴을 모방한 트렌드
    # 9월: 조정 후 회복, 10월: 변동성, 11월: 상승
    
    sep_days = get_trading_days("20250901", "20250930")
    oct_days = get_trading_days("20251001", "20251031") 
    nov_days = get_trading_days("20251101", "20251130")
    
    trends = []
    
    # 9월: 초반 조정, 중반 회복, 후반 안정
    for i, day in enumerate(sep_days):
        if i < len(sep_days) * 0.3:  # 초반 30%
            trends.append(random.choice(["bear", "neutral", "neutral"]))
        elif i < len(sep_days) * 0.7:  # 중반 40%
            trends.append(random.choice(["neutral", "bull", "neutral"]))
        else:  # 후반 30%
            trends.append(random.choice(["neutral", "neutral", "bull"]))
    
    # 10월: 변동성 높음
    for i, day in enumerate(oct_days):
        if i < len(oct_days) * 0.2:  # 초반
            trends.append(random.choice(["bull", "neutral"]))
        elif i < len(oct_days) * 0.6:  # 중반 (변동성)
            trends.append(random.choice(["bear", "neutral", "bull", "neutral"]))
        else:  # 후반
            trends.append(random.choice(["neutral", "bull", "bull"]))
    
    # 11월: 상승 트렌드
    for i, day in enumerate(nov_days):
        if i < len(nov_days) * 0.1:  # 초반 조정
            trends.append(random.choice(["neutral", "bear"]))
        else:  # 대부분 상승
            trends.append(random.choice(["bull", "bull", "neutral"]))
    
    return trends

def main():
    """메인 실행 함수"""
    logger.info("2025년 9월-11월 장세 데이터 생성 시작")
    
    # 거래일 목록 생성
    all_days = get_trading_days("20250901", "20251130")
    trends = generate_market_trend_pattern()
    
    logger.info(f"총 {len(all_days)}개 거래일 처리 예정")
    
    success_count = 0
    error_count = 0
    
    for i, date in enumerate(all_days):
        try:
            # 트렌드 패턴 적용
            trend = trends[i] if i < len(trends) else "neutral"
            
            # 장세 데이터 생성
            regime_data = create_regime_data_for_date(date, trend)
            
            # DB에 저장
            upsert_regime(date, regime_data)
            
            success_count += 1
            
            if success_count % 10 == 0:
                logger.info(f"진행률: {success_count}/{len(all_days)} ({success_count/len(all_days)*100:.1f}%)")
            
        except Exception as e:
            logger.error(f"날짜 {date} 처리 실패: {e}")
            error_count += 1
            continue
    
    logger.info(f"장세 데이터 생성 완료: 성공 {success_count}개, 실패 {error_count}개")
    
    # 결과 요약
    if success_count > 0:
        logger.info("생성된 데이터 샘플:")
        sample_date = all_days[0]
        try:
            from services.regime_storage import load_regime
            sample_data = load_regime(sample_date)
            if sample_data:
                logger.info(f"  {sample_date}: {sample_data['final_regime']} (KR: {sample_data['kr_regime']}, US: {sample_data['us_prev_regime']})")
        except Exception as e:
            logger.warning(f"샘플 데이터 로드 실패: {e}")

if __name__ == "__main__":
    main()