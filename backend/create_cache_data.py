#!/usr/bin/env python3
"""
백필용 캐시 데이터 생성 스크립트
- KOSPI200, SPY, QQQ, VIX 데이터 수집
- 유니버스 데이터 생성
"""
import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """샘플 OHLCV 데이터 생성"""
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # 거래일만 생성 (주말 제외)
    dates = pd.bdate_range(start=start_dt, end=end_dt, freq='B')
    
    # 기본 가격 설정
    base_prices = {
        'KOSPI200': 250.0,
        'SPY': 400.0,
        'QQQ': 350.0,
        'VIX': 20.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    
    # 랜덤 워크로 가격 생성
    np.random.seed(42)  # 재현 가능한 결과
    returns = np.random.normal(0.0005, 0.02, len(dates))  # 일일 수익률
    
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    prices = prices[1:]  # 첫 번째 제거
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 일중 변동성
        volatility = np.random.uniform(0.01, 0.03)
        high = price * (1 + volatility/2)
        low = price * (1 - volatility/2)
        open_price = prices[i-1] if i > 0 else price
        
        # 거래량 (심볼별 다르게)
        if symbol == 'KOSPI200':
            volume = np.random.randint(50000, 200000)
        elif symbol in ['SPY', 'QQQ']:
            volume = np.random.randint(30000000, 100000000)
        else:  # VIX
            volume = np.random.randint(100000, 500000)
        
        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df

def create_universe_data(num_stocks: int = 200) -> dict:
    """유니버스 데이터 생성"""
    universe_data = {}
    
    # 샘플 종목 코드 생성
    codes = [f"{i:06d}" for i in range(5930, 5930 + num_stocks)]
    
    for code in codes:
        try:
            # 각 종목별로 다른 시드 사용
            np.random.seed(int(code))
            
            df = create_sample_data(f"STOCK_{code}", "2020-01-01", "2025-11-22")
            universe_data[code] = df
            
            if len(universe_data) % 50 == 0:
                logger.info(f"생성 완료: {len(universe_data)}/{num_stocks}")
                
        except Exception as e:
            logger.error(f"종목 {code} 데이터 생성 실패: {e}")
            continue
    
    return universe_data

def main():
    """메인 함수"""
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)
    
    logger.info("캐시 데이터 생성 시작")
    
    # 1. KOSPI200 데이터
    logger.info("KOSPI200 데이터 생성 중...")
    kospi_data = create_sample_data("KOSPI200", "2020-01-01", "2025-11-22")
    with open(cache_dir / "kospi200_ohlcv.pkl", 'wb') as f:
        pickle.dump(kospi_data, f)
    logger.info(f"KOSPI200 데이터 저장 완료: {len(kospi_data)} 레코드")
    
    # 2. SPY 데이터
    logger.info("SPY 데이터 생성 중...")
    spy_data = create_sample_data("SPY", "2020-01-01", "2025-11-22")
    with open(cache_dir / "spy_ohlcv.pkl", 'wb') as f:
        pickle.dump(spy_data, f)
    logger.info(f"SPY 데이터 저장 완료: {len(spy_data)} 레코드")
    
    # 3. QQQ 데이터
    logger.info("QQQ 데이터 생성 중...")
    qqq_data = create_sample_data("QQQ", "2020-01-01", "2025-11-22")
    with open(cache_dir / "qqq_ohlcv.pkl", 'wb') as f:
        pickle.dump(qqq_data, f)
    logger.info(f"QQQ 데이터 저장 완료: {len(qqq_data)} 레코드")
    
    # 4. VIX 데이터
    logger.info("VIX 데이터 생성 중...")
    vix_data = create_sample_data("VIX", "2020-01-01", "2025-11-22")
    with open(cache_dir / "vix_ohlcv.pkl", 'wb') as f:
        pickle.dump(vix_data, f)
    logger.info(f"VIX 데이터 저장 완료: {len(vix_data)} 레코드")
    
    # 5. 유니버스 데이터
    logger.info("유니버스 데이터 생성 중...")
    universe_data = create_universe_data(200)
    with open(cache_dir / "universe_ohlcv.pkl", 'wb') as f:
        pickle.dump(universe_data, f)
    logger.info(f"유니버스 데이터 저장 완료: {len(universe_data)} 종목")
    
    logger.info("모든 캐시 데이터 생성 완료!")
    
    # 생성된 파일 목록 출력
    cache_files = list(cache_dir.glob("*.pkl"))
    logger.info(f"생성된 캐시 파일: {len(cache_files)}개")
    for file in cache_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        logger.info(f"  - {file.name}: {size_mb:.1f}MB")

if __name__ == "__main__":
    main()