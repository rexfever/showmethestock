"""
미국 선물 데이터 CSV 다운로드 서비스
"""
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class USFuturesData:
    def __init__(self, cache_dir="./cache/us_futures"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = 24  # 1일 TTL
        
        self.urls = {
            "ES=F": "https://query1.finance.yahoo.com/v7/finance/download/ES=F?period1=0&period2=9999999999&interval=1d&events=history",
            "NQ=F": "https://query1.finance.yahoo.com/v7/finance/download/NQ=F?period1=0&period2=9999999999&interval=1d&events=history",
            "VX=F": "https://query1.finance.yahoo.com/v7/finance/download/VX=F?period1=0&period2=9999999999&interval=1d&events=history",
            "^VIX": "https://query1.finance.yahoo.com/v7/finance/download/%5EVIX?period1=0&period2=9999999999&interval=1d&events=history",
            "DX-Y.NYB": "https://query1.finance.yahoo.com/v7/finance/download/DX-Y.NYB?period1=0&period2=9999999999&interval=1d&events=history",
            "SPY": "https://query1.finance.yahoo.com/v7/finance/download/SPY?period1=0&period2=9999999999&interval=1d&events=history",
            "QQQ": "https://query1.finance.yahoo.com/v7/finance/download/QQQ?period1=0&period2=9999999999&interval=1d&events=history"
        }
    
    def fetch_csv(self, symbol):
        """CSV 다운로드 및 캐싱"""
        cache_file = self.cache_dir / f"{symbol.replace('=', '_').replace('-', '_').replace('.', '_')}.csv"
        
        # 캐시 확인
        if cache_file.exists():
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age < timedelta(hours=self.ttl_hours):
                logger.info(f"캐시에서 로드: {symbol}")
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # 다운로드
        try:
            url = self.urls.get(symbol)
            if not url:
                raise ValueError(f"지원하지 않는 심볼: {symbol}")
            
            logger.info(f"다운로드 중: {symbol}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # CSV 파싱
            df = pd.read_csv(pd.io.common.StringIO(response.text))
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            # 캐시 저장
            df.to_csv(cache_file)
            logger.info(f"다운로드 완료: {symbol}, {len(df)}개 행")
            
            return df
            
        except Exception as e:
            logger.error(f"다운로드 실패 {symbol}: {e}")
            # 캐시가 있으면 사용
            if cache_file.exists():
                logger.warning(f"캐시 사용: {symbol}")
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return pd.DataFrame()

# 전역 인스턴스
us_futures_data = USFuturesData()