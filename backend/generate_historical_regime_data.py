#!/usr/bin/env python3
"""
2025년 9월-11월 과거 장세 데이터 생성 스크립트 (실제 미국 데이터 사용)
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List
import random

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.regime_storage import upsert_regime
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
    """모의 KOSPI 데이터 생성 (과거 데이터 패턴 반영)"""
    base_return = 0.0
    base_volatility = 0.025
    
    # 2025년 9-11월 실제 시장 패턴 반영
    date_obj = datetime.strptime(date, '%Y%m%d')
    month = date_obj.month
    
    if month == 9:  # 9월: 조정 후 회복
        if date_obj.day < 15:
            base_return = random.uniform(-0.015, 0.005)  # 초반 조정
        else:
            base_return = random.uniform(-0.005, 0.015)  # 후반 회복
        base_volatility = random.uniform(0.020, 0.035)
    elif month == 10:  # 10월: 변동성
        base_return = random.uniform(-0.020, 0.020)
        base_volatility = random.uniform(0.025, 0.040)
    else:  # 11월: 상승 (현재까지)
        base_return = random.uniform(0.000, 0.020)
        base_volatility = random.uniform(0.015, 0.030)
    
    # 저가 기준 수익률
    low_return = base_return - random.uniform(0.005, 0.015)
    
    return base_return, base_volatility, low_return

def create_regime_data_for_date(date: str) -> dict:
    """특정 날짜의 장세 데이터 생성 (실제 미국 데이터 + 모의 한국 데이터)"""
    
    # 1. 실제 미국 장세 데이터 가져오기
    try:
        us_data = get_us_prev_snapshot(date)
        if us_data.get("valid", False):
            logger.info(f"실제 미국 데이터 사용: {date}")
        else:
            raise Exception("Invalid US data")
    except Exception as e:
        logger.warning(f"실제 미국 데이터 로드 실패 ({date}): {e}")
        return None
    
    # 2. 한국 장세 데이터 생성 (모의)
    kospi_return, volatility, kospi_low_return = generate_mock_kospi_data(date)
    universe_return = kospi_return + random.uniform(-0.005, 0.005)
    sample_size = random.randint(80, 120)
    
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
    
    # 3. 미국 장세 점수 계산
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
    
    # 4. 글로벌 레짐 조합
    base_score = 0.6 * kr_score + 0.4 * us_prev_score
    final_score = base_score  # 백테스트에서는 pre-open 리스크 없음
    
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

def main():
    """메인 실행 함수"""
    logger.info("2025년 9월-11월 과거 장세 데이터 생성 시작")
    
    # 거래일 목록 생성
    all_days = get_trading_days("20250901", "20251122")  # 오늘까지
    
    logger.info(f"총 {len(all_days)}개 거래일 처리 예정")
    
    success_count = 0
    error_count = 0
    
    for date in all_days:
        try:
            # 장세 데이터 생성
            regime_data = create_regime_data_for_date(date)
            
            if regime_data is None:
                logger.warning(f"날짜 {date} 데이터 생성 실패 (미국 데이터 없음)")
                error_count += 1
                continue
            
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

if __name__ == "__main__":
    main()