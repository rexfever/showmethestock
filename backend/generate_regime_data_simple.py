#!/usr/bin/env python3
"""
2025년 9월-11월 장세 데이터 생성 (PostgreSQL + 실제 패턴 반영)
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

def create_realistic_market_data(date: str) -> dict:
    """실제 시장 패턴을 반영한 장세 데이터 생성"""
    
    date_obj = datetime.strptime(date, '%Y%m%d')
    month = date_obj.month
    day = date_obj.day
    
    # 2025년 9-11월 실제 시장 패턴 반영
    if month == 9:  # 9월: 초반 조정, 후반 회복
        if day <= 10:
            kr_trend = random.choice(["bear", "neutral", "neutral"])
            us_trend = random.choice(["bear", "neutral"])
        elif day <= 20:
            kr_trend = random.choice(["neutral", "neutral", "bull"])
            us_trend = random.choice(["neutral", "bull"])
        else:
            kr_trend = random.choice(["neutral", "bull", "bull"])
            us_trend = random.choice(["neutral", "bull"])
    elif month == 10:  # 10월: 변동성 높음
        kr_trend = random.choice(["bear", "neutral", "bull", "neutral"])
        us_trend = random.choice(["bear", "neutral", "bull"])
    else:  # 11월: 상승세 (현재까지)
        if day <= 5:
            kr_trend = random.choice(["neutral", "bear"])
            us_trend = random.choice(["neutral", "bear"])
        else:
            kr_trend = random.choice(["bull", "bull", "neutral"])
            us_trend = random.choice(["bull", "neutral"])
    
    # 한국 데이터 생성
    if kr_trend == "bull":
        kospi_return = random.uniform(0.005, 0.025)
        volatility = random.uniform(0.015, 0.030)
        kr_score = random.uniform(1.5, 3.0)
    elif kr_trend == "bear":
        kospi_return = random.uniform(-0.025, -0.005)
        volatility = random.uniform(0.025, 0.045)
        kr_score = random.uniform(-3.0, -1.5)
    else:  # neutral
        kospi_return = random.uniform(-0.010, 0.010)
        volatility = random.uniform(0.020, 0.035)
        kr_score = random.uniform(-1.0, 1.0)
    
    # 미국 데이터 생성
    if us_trend == "bull":
        spy_r3 = random.uniform(0.008, 0.020)
        vix = random.uniform(15, 25)
        us_score = random.uniform(1.5, 3.0)
    elif us_trend == "bear":
        spy_r3 = random.uniform(-0.020, -0.008)
        vix = random.uniform(25, 40)
        us_score = random.uniform(-3.0, -1.5)
    else:  # neutral
        spy_r3 = random.uniform(-0.008, 0.008)
        vix = random.uniform(18, 30)
        us_score = random.uniform(-1.0, 1.0)
    
    # 글로벌 레짐 결정
    final_score = 0.6 * kr_score + 0.4 * us_score
    
    if final_score >= 2.0:
        final_regime = "bull"
    elif final_score <= -2.0:
        final_regime = "bear"
    elif vix > 35 or kospi_return < -0.03:
        final_regime = "crash"
    else:
        final_regime = "neutral"
    
    # 데이터 구조 생성
    regime_data = {
        'final_regime': final_regime,
        'kr_regime': kr_trend,
        'us_prev_regime': us_trend,
        'us_preopen_flag': 'none',
        'us_metrics': {
            'spy_r1': spy_r3 * 0.3,
            'spy_r3': spy_r3,
            'spy_r5': spy_r3 * 1.5,
            'qqq_r1': spy_r3 * 1.1,
            'qqq_r3': spy_r3 * 1.2,
            'qqq_r5': spy_r3 * 1.8,
            'vix': vix,
            'vix_change': random.uniform(-0.1, 0.1),
            'ust10y_change': random.uniform(-0.1, 0.1),
            'valid': True
        },
        'kr_metrics': {
            'kr_trend_score': kr_score * 0.4,
            'kr_vol_score': random.uniform(-1, 1),
            'kr_breadth_score': random.uniform(-1, 1),
            'kr_intraday_score': random.uniform(-1, 1),
            'kr_score': kr_score,
            'kr_regime': kr_trend,
            'intraday_drop': kospi_return - random.uniform(0.005, 0.015),
            'kospi_return': kospi_return,
            'volatility': volatility,
            'universe_return': kospi_return + random.uniform(-0.005, 0.005),
            'sample_size': random.randint(80, 120)
        },
        'us_preopen_metrics': {
            'us_preopen_risk_score': 0.0,
            'us_preopen_flag': 'none'
        }
    }
    
    return regime_data

def main():
    """메인 실행 함수"""
    logger.info("2025년 9월-11월 장세 데이터 생성 시작")
    
    # 거래일 목록 생성
    all_days = get_trading_days("20250901", "20251122")  # 오늘까지
    
    logger.info(f"총 {len(all_days)}개 거래일 처리 예정")
    
    success_count = 0
    error_count = 0
    
    for date in all_days:
        try:
            # 장세 데이터 생성
            regime_data = create_realistic_market_data(date)
            
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
        sample_dates = all_days[:5] if len(all_days) >= 5 else all_days
        for sample_date in sample_dates:
            logger.info(f"  {sample_date}: 데이터 생성 완료")

if __name__ == "__main__":
    main()