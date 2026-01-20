"""
레짐 분석을 위한 데이터 캐시 시스템
"""
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class RegimeDataCache:
    """레짐 분석 데이터 캐시 관리"""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'regime')
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 캐시 TTL (초)
        self.ttl_seconds = {
            'kospi': 1800,     # 30분 (6개월 데이터는 오래 유지)
            'us_stocks': 7200, # 2시간 (6개월 데이터는 오래 유지)
            'us_futures': 1800, # 30분
            'regime_result': 300, # 5분
        }
    
    def _get_cache_path(self, cache_type: str, symbol: str = None) -> str:
        """캐시 파일 경로 생성"""
        if symbol:
            filename = f"{cache_type}_{symbol}.json"
        else:
            filename = f"{cache_type}.json"
        return os.path.join(self.cache_dir, filename)
    
    def _is_cache_valid(self, cache_path: str, cache_type: str) -> bool:
        """캐시 유효성 검사"""
        if not os.path.exists(cache_path):
            return False
        
        try:
            mtime = os.path.getmtime(cache_path)
            age = datetime.now().timestamp() - mtime
            return age < self.ttl_seconds.get(cache_type, 300)
        except Exception:
            return False
    
    def get_kospi_data(self, date: str = None) -> Optional[pd.DataFrame]:
        """KOSPI 데이터 캐시 조회"""
        cache_path = self._get_cache_path('kospi', 'kospi200')
        
        if self._is_cache_valid(cache_path, 'kospi'):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                df = pd.DataFrame(data['data'])
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                logger.debug(f"KOSPI 캐시 히트: {len(df)}개 행")
                return df
            except Exception as e:
                logger.warning(f"KOSPI 캐시 로드 실패: {e}")
        
        return None
    
    def set_kospi_data(self, df: pd.DataFrame) -> None:
        """KOSPI 데이터 캐시 저장"""
        cache_path = self._get_cache_path('kospi', 'kospi200')
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'data': df.to_dict('records')
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
            logger.debug(f"KOSPI 캐시 저장: {len(df)}개 행")
        except Exception as e:
            logger.error(f"KOSPI 캐시 저장 실패: {e}")
    
    def get_us_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """미국 주식 데이터 캐시 조회"""
        # JSON 캐시 먼저 시도
        cache_path = self._get_cache_path('us_stocks', symbol)
        
        if self._is_cache_valid(cache_path, 'us_stocks'):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                df = pd.DataFrame(data['data'])
                if not df.empty and 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                logger.debug(f"{symbol} JSON 캐시 히트: {len(df)}개 행")
                return df
            except Exception as e:
                logger.warning(f"{symbol} JSON 캐시 로드 실패: {e}")
        
        # CSV 캐시 시도
        csv_path = os.path.join(os.path.dirname(self.cache_dir), 'us_futures', f'{symbol}.csv')
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if not df.empty and 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                logger.debug(f"{symbol} CSV 캐시 히트: {len(df)}개 행")
                return df
            except Exception as e:
                logger.warning(f"{symbol} CSV 캐시 로드 실패: {e}")
        
        return None
    
    def set_us_stock_data(self, symbol: str, df: pd.DataFrame) -> None:
        """미국 주식 데이터 캐시 저장"""
        cache_path = self._get_cache_path('us_stocks', symbol)
        
        try:
            df_copy = df.copy()
            if df_copy.index.name == 'Date' or 'Date' in str(df_copy.index.dtype):
                df_copy = df_copy.reset_index()
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'data': df_copy.to_dict('records')
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
            logger.debug(f"{symbol} 캐시 저장: {len(df)}개 행")
        except Exception as e:
            logger.error(f"{symbol} 캐시 저장 실패: {e}")
    
    def get_us_futures_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """미국 선물 데이터 캐시 조회"""
        # JSON 캐시 먼저 시도
        cache_path = self._get_cache_path('us_futures', symbol.replace('=', '_').replace('^', ''))
        
        if self._is_cache_valid(cache_path, 'us_futures'):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                df = pd.DataFrame(data['data'])
                if not df.empty and 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                logger.debug(f"{symbol} JSON 선물 캐시 히트: {len(df)}개 행")
                return df
            except Exception as e:
                logger.warning(f"{symbol} JSON 선물 캐시 로드 실패: {e}")
        
        # CSV 캐시 시도
        csv_filename = symbol.replace('=', '_').replace('^', '').replace('-', '_').replace('.', '_') + '.csv'
        csv_path = os.path.join(os.path.dirname(self.cache_dir), 'us_futures', csv_filename)
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if not df.empty and 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                logger.debug(f"{symbol} CSV 선물 캐시 히트: {len(df)}개 행")
                return df
            except Exception as e:
                logger.warning(f"{symbol} CSV 선물 캐시 로드 실패: {e}")
        
        return None
    
    def set_us_futures_data(self, symbol: str, df: pd.DataFrame) -> None:
        """미국 선물 데이터 캐시 저장"""
        cache_path = self._get_cache_path('us_futures', symbol.replace('=', '_').replace('^', ''))
        
        try:
            df_copy = df.copy()
            if df_copy.index.name == 'Date' or 'Date' in str(df_copy.index.dtype):
                df_copy = df_copy.reset_index()
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'data': df_copy.to_dict('records')
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
            logger.debug(f"{symbol} 선물 캐시 저장: {len(df)}개 행")
        except Exception as e:
            logger.error(f"{symbol} 선물 캐시 저장 실패: {e}")
    
    def get_regime_result(self, date: str, version: str = 'v4') -> Optional[Dict[str, Any]]:
        """레짐 분석 결과 캐시 조회"""
        cache_path = self._get_cache_path('regime_result', f"{version}_{date}")
        
        if self._is_cache_valid(cache_path, 'regime_result'):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                logger.debug(f"레짐 결과 캐시 히트: {date} {version}")
                return data['result']
            except Exception as e:
                logger.warning(f"레짐 결과 캐시 로드 실패: {e}")
        
        return None
    
    def set_regime_result(self, date: str, result: Dict[str, Any], version: str = 'v4') -> None:
        """레짐 분석 결과 캐시 저장"""
        cache_path = self._get_cache_path('regime_result', f"{version}_{date}")
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'date': date,
                'version': version,
                'result': result
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
            logger.debug(f"레짐 결과 캐시 저장: {date} {version}")
        except Exception as e:
            logger.error(f"레짐 결과 캐시 저장 실패: {e}")
    
    def clear_cache(self, cache_type: str = None) -> None:
        """캐시 클리어"""
        try:
            if cache_type:
                # 특정 타입만 클리어
                pattern = f"{cache_type}_*.json"
                import glob
                files = glob.glob(os.path.join(self.cache_dir, pattern))
                for file in files:
                    os.remove(file)
                logger.info(f"{cache_type} 캐시 클리어: {len(files)}개 파일")
            else:
                # 전체 캐시 클리어
                import shutil
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
                logger.info("전체 레짐 캐시 클리어")
        except Exception as e:
            logger.error(f"캐시 클리어 실패: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'by_type': {}
            }
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    size = os.path.getsize(filepath)
                    mtime = os.path.getmtime(filepath)
                    age = datetime.now().timestamp() - mtime
                    
                    cache_type = filename.split('_')[0]
                    if cache_type not in stats['by_type']:
                        stats['by_type'][cache_type] = {
                            'count': 0,
                            'size': 0,
                            'oldest_age': 0,
                            'newest_age': float('inf')
                        }
                    
                    stats['total_files'] += 1
                    stats['total_size'] += size
                    stats['by_type'][cache_type]['count'] += 1
                    stats['by_type'][cache_type]['size'] += size
                    stats['by_type'][cache_type]['oldest_age'] = max(stats['by_type'][cache_type]['oldest_age'], age)
                    stats['by_type'][cache_type]['newest_age'] = min(stats['by_type'][cache_type]['newest_age'], age)
            
            return stats
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}

# 전역 캐시 인스턴스
regime_cache = RegimeDataCache()