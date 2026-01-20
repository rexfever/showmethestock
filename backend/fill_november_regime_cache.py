#!/usr/bin/env python3
"""
11월 레짐 분석 캐시 데이터 부족분 채우기
- KOSPI (069500) 데이터 업데이트
- KOSDAQ (229200) 데이터 업데이트
- 미국 시장 데이터 (SPY, QQQ, VIX) 수집
"""
import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwoom_api import api
from date_helper import normalize_date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date: str, end_date: str) -> list:
    """거래일 리스트 반환 (주말 제외)"""
    start = pd.to_datetime(start_date, format='%Y%m%d')
    end = pd.to_datetime(end_date, format='%Y%m%d')
    trading_days = pd.bdate_range(start=start, end=end, freq='B')
    return [d.strftime('%Y%m%d') for d in trading_days]

def update_kospi_cache(end_date: str = None) -> bool:
    """KOSPI 캐시 업데이트"""
    try:
        cache_path = Path("data_cache/kospi200_ohlcv.pkl")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 로드
        existing_df = pd.DataFrame()
        if cache_path.exists():
            try:
                existing_df = pd.read_pickle(cache_path)
                logger.info(f"기존 KOSPI 캐시 로드: {len(existing_df)}개 행")
            except Exception as e:
                logger.warning(f"기존 KOSPI 캐시 로드 실패: {e}")
        
        # 최신 날짜 확인
        if not existing_df.empty:
            last_date = existing_df.index.max()
            if isinstance(last_date, str):
                last_date = pd.to_datetime(last_date)
            start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
        else:
            start_date = '20201101'  # 기본 시작일
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 부족한 날짜 확인
        if start_date >= end_date:
            logger.info("KOSPI 캐시가 이미 최신입니다")
            return True
        
        logger.info(f"KOSPI 데이터 수집: {start_date} ~ {end_date}")
        
        # 최근 220일 데이터 가져오기 (충분한 데이터 확보)
        df_new = api.get_ohlcv("069500", count=220, base_dt=end_date)
        
        if df_new.empty:
            logger.warning("KOSPI 데이터 수집 실패")
            return False
        
        # 날짜 컬럼을 인덱스로 변환
        if 'date' in df_new.columns:
            df_new['date'] = pd.to_datetime(df_new['date'], format='%Y%m%d', errors='coerce')
            df_new = df_new.set_index('date')
        elif df_new.index.name == 'date' or df_new.index.dtype == 'datetime64[ns]':
            pass  # 이미 인덱스가 날짜
        else:
            logger.warning("KOSPI 데이터 날짜 인덱스 변환 실패")
            return False
        
        # 기존 데이터와 병합
        if not existing_df.empty:
            # 중복 제거 후 병합
            combined = pd.concat([existing_df, df_new])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
        else:
            combined = df_new.sort_index()
        
        # 캐시 저장
        combined.to_pickle(cache_path)
        logger.info(f"✅ KOSPI 캐시 업데이트 완료: {len(combined)}개 행 (추가: {len(df_new)}개)")
        return True
        
    except Exception as e:
        logger.error(f"KOSPI 캐시 업데이트 실패: {e}", exc_info=True)
        return False

def update_kosdaq_cache(end_date: str = None) -> bool:
    """KOSDAQ 캐시 업데이트"""
    try:
        cache_path = Path("data_cache/ohlcv/229200.csv")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 로드
        existing_df = pd.DataFrame()
        if cache_path.exists():
            try:
                existing_df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                logger.info(f"기존 KOSDAQ 캐시 로드: {len(existing_df)}개 행")
            except Exception as e:
                logger.warning(f"기존 KOSDAQ 캐시 로드 실패: {e}")
        
        # 최신 날짜 확인
        if not existing_df.empty:
            last_date = existing_df.index.max()
            if isinstance(last_date, str):
                last_date = pd.to_datetime(last_date)
            start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
        else:
            start_date = '20201101'  # 기본 시작일
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 부족한 날짜 확인
        if start_date >= end_date:
            logger.info("KOSDAQ 캐시가 이미 최신입니다")
            return True
        
        logger.info(f"KOSDAQ 데이터 수집: {start_date} ~ {end_date}")
        
        # 최근 220일 데이터 가져오기
        df_new = api.get_ohlcv("229200", count=220, base_dt=end_date)
        
        if df_new.empty:
            logger.warning("KOSDAQ 데이터 수집 실패")
            return False
        
        # 날짜 컬럼을 인덱스로 변환
        if 'date' in df_new.columns:
            df_new['date'] = pd.to_datetime(df_new['date'], format='%Y%m%d', errors='coerce')
            df_new = df_new.set_index('date')
        elif df_new.index.name == 'date' or df_new.index.dtype == 'datetime64[ns]':
            pass  # 이미 인덱스가 날짜
        else:
            logger.warning("KOSDAQ 데이터 날짜 인덱스 변환 실패")
            return False
        
        # 컬럼명 소문자로 통일
        df_new.columns = df_new.columns.str.lower()
        
        # 기존 데이터와 병합
        if not existing_df.empty:
            # 중복 제거 후 병합
            combined = pd.concat([existing_df, df_new])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
        else:
            combined = df_new.sort_index()
        
        # CSV로 저장
        combined.to_csv(cache_path)
        logger.info(f"✅ KOSDAQ 캐시 업데이트 완료: {len(combined)}개 행 (추가: {len(df_new)}개)")
        return True
        
    except Exception as e:
        logger.error(f"KOSDAQ 캐시 업데이트 실패: {e}", exc_info=True)
        return False

def fetch_us_market_data(symbol: str, period: str = '6mo') -> pd.DataFrame:
    """미국 시장 데이터 수집 (Yahoo Finance)"""
    try:
        import requests
        
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"{symbol} API 호출 실패: {response.status_code}")
            return pd.DataFrame()
        
        data = response.json()
        if 'chart' not in data or not data['chart']['result']:
            logger.warning(f"{symbol} 데이터 없음")
            return pd.DataFrame()
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        
        df_data = []
        for i, ts in enumerate(timestamps):
            df_data.append({
                'Open': quotes['open'][i],
                'High': quotes['high'][i], 
                'Low': quotes['low'][i],
                'Close': quotes['close'][i],
                'Volume': quotes['volume'][i] or 0
            })
        
        df = pd.DataFrame(df_data, index=pd.to_datetime(timestamps, unit='s'))
        return df.dropna()
        
    except Exception as e:
        logger.error(f"{symbol} 데이터 수집 실패: {e}")
        return pd.DataFrame()

def update_us_market_cache() -> bool:
    """미국 시장 캐시 업데이트"""
    try:
        cache_dir = Path("cache/us_futures")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        symbols = ['SPY', 'QQQ', '^VIX']
        success_count = 0
        
        for symbol in symbols:
            try:
                # 파일명 매핑
                filename_map = {
                    '^VIX': '^VIX.csv',
                }
                filename = filename_map.get(symbol, f"{symbol}.csv")
                cache_path = cache_dir / filename
                
                # 기존 캐시 로드
                existing_df = pd.DataFrame()
                if cache_path.exists():
                    try:
                        existing_df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                        logger.info(f"기존 {symbol} 캐시 로드: {len(existing_df)}개 행")
                    except Exception as e:
                        logger.warning(f"기존 {symbol} 캐시 로드 실패: {e}")
                
                # 최신 데이터 수집
                logger.info(f"{symbol} 데이터 수집 중...")
                df_new = fetch_us_market_data(symbol, period='6mo')
                
                if df_new.empty:
                    logger.warning(f"{symbol} 데이터 수집 실패")
                    continue
                
                # 기존 데이터와 병합
                if not existing_df.empty:
                    combined = pd.concat([existing_df, df_new])
                    combined = combined[~combined.index.duplicated(keep='last')]
                    combined = combined.sort_index()
                else:
                    combined = df_new.sort_index()
                
                # 캐시 저장
                combined.to_csv(cache_path)
                logger.info(f"✅ {symbol} 캐시 업데이트 완료: {len(combined)}개 행")
                success_count += 1
                
                # API 호출 제한 방지
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"{symbol} 캐시 업데이트 실패: {e}")
                continue
        
        logger.info(f"미국 시장 캐시 업데이트 완료: {success_count}/{len(symbols)}개 성공")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"미국 시장 캐시 업데이트 실패: {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("11월 레짐 분석 캐시 데이터 부족분 채우기 시작")
    logger.info("=" * 70)
    
    # 11월 날짜 범위
    nov_start = '20251101'
    nov_end = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {nov_start} ~ {nov_end}")
    
    # 1. KOSPI 캐시 업데이트
    logger.info("\n[1/3] KOSPI 캐시 업데이트")
    update_kospi_cache(nov_end)
    
    # 2. KOSDAQ 캐시 업데이트
    logger.info("\n[2/3] KOSDAQ 캐시 업데이트")
    update_kosdaq_cache(nov_end)
    
    # 3. 미국 시장 캐시 업데이트
    logger.info("\n[3/3] 미국 시장 캐시 업데이트")
    update_us_market_cache()
    
    logger.info("\n" + "=" * 70)
    logger.info("11월 레짐 분석 캐시 데이터 업데이트 완료")
    logger.info("=" * 70)
    
    # 최종 확인
    logger.info("\n최종 캐시 상태:")
    try:
        kospi_path = Path("data_cache/kospi200_ohlcv.pkl")
        if kospi_path.exists():
            df = pd.read_pickle(kospi_path)
            nov_data = df[df.index >= '2025-11-01']
            logger.info(f"  KOSPI: {len(nov_data)}개 행 (11월)")
        
        kosdaq_path = Path("data_cache/ohlcv/229200.csv")
        if kosdaq_path.exists():
            df = pd.read_csv(kosdaq_path, index_col=0, parse_dates=True)
            nov_data = df[df.index >= '2025-11-01']
            logger.info(f"  KOSDAQ: {len(nov_data)}개 행 (11월)")
        
        us_dir = Path("cache/us_futures")
        if us_dir.exists():
            us_files = list(us_dir.glob("*.csv"))
            logger.info(f"  미국 시장: {len(us_files)}개 파일")
    except Exception as e:
        logger.warning(f"최종 확인 실패: {e}")

if __name__ == "__main__":
    main()


