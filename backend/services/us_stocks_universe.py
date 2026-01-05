"""
미국 주식 유니버스 로더
S&P 500, NASDAQ 100 등의 종목 리스트를 가져옵니다.
"""
import pandas as pd
import requests
import logging
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class USStocksUniverse:
    """미국 주식 유니버스 관리"""
    
    def __init__(self):
        self.cache_dir = Path("cache/us_stocks")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_days = 7  # 캐시 유효 기간: 7일
    
    def get_sp500_list(self, use_cache: bool = True) -> List[Dict[str, str]]:
        """
        S&P 500 종목 리스트 가져오기
        
        Returns:
            [{"symbol": "AAPL", "name": "Apple Inc."}, ...]
        """
        cache_path = self.cache_dir / "sp500_list.json"
        
        # 캐시 확인
        if use_cache and cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_date = datetime.fromisoformat(cache_data.get('date', '2000-01-01'))
                
                if (datetime.now() - cache_date).days < self.cache_ttl_days:
                    logger.info(f"S&P 500 리스트 캐시 사용: {len(cache_data.get('stocks', []))}개")
                    return cache_data.get('stocks', [])
            except Exception as e:
                logger.warning(f"S&P 500 캐시 로드 실패: {e}")
        
        # Wikipedia에서 S&P 500 리스트 가져오기
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            # requests로 직접 가져오기 (User-Agent 헤더 필요)
            import requests
            from io import StringIO
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            # lxml 또는 html5lib 사용
            try:
                tables = pd.read_html(StringIO(response.text), flavor='lxml')
            except:
                try:
                    tables = pd.read_html(StringIO(response.text), flavor='html5lib')
                except:
                    # 기본 파서 사용
                    tables = pd.read_html(StringIO(response.text))
            sp500_table = tables[0]  # 첫 번째 테이블이 S&P 500 리스트
            
            stocks = []
            for _, row in sp500_table.iterrows():
                symbol = row.get('Symbol', '').strip()
                name = row.get('Security', '').strip()
                if symbol:
                    stocks.append({
                        'symbol': symbol,
                        'name': name,
                        'sector': row.get('GICS Sector', '').strip(),
                        'industry': row.get('GICS Sub-Industry', '').strip()
                    })
            
            # 캐시 저장
            cache_data = {
                'date': datetime.now().isoformat(),
                'stocks': stocks
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"S&P 500 리스트 수집 완료: {len(stocks)}개")
            return stocks
            
        except Exception as e:
            logger.error(f"S&P 500 리스트 수집 실패: {e}")
            # 캐시가 있으면 사용
            if cache_path.exists():
                try:
                    cache_data = json.load(open(cache_path, 'r', encoding='utf-8'))
                    return cache_data.get('stocks', [])
                except:
                    pass
            return []
    
    def get_nasdaq100_list(self, use_cache: bool = True) -> List[Dict[str, str]]:
        """
        NASDAQ 100 종목 리스트 가져오기
        
        Returns:
            [{"symbol": "AAPL", "name": "Apple Inc."}, ...]
        """
        cache_path = self.cache_dir / "nasdaq100_list.json"
        
        # 캐시 확인
        if use_cache and cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_date = datetime.fromisoformat(cache_data.get('date', '2000-01-01'))
                
                if (datetime.now() - cache_date).days < self.cache_ttl_days:
                    logger.info(f"NASDAQ 100 리스트 캐시 사용: {len(cache_data.get('stocks', []))}개")
                    return cache_data.get('stocks', [])
            except Exception as e:
                logger.warning(f"NASDAQ 100 캐시 로드 실패: {e}")
        
        # Wikipedia에서 NASDAQ 100 리스트 가져오기
        try:
            url = "https://en.wikipedia.org/wiki/NASDAQ-100"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            # lxml 없이도 작동하도록 html5lib 사용
            try:
                tables = pd.read_html(url, flavor='html5lib')
            except:
                # html5lib도 없으면 requests로 직접 가져오기
                import requests
                from io import StringIO
                response = requests.get(url, headers=headers, timeout=10)
                tables = pd.read_html(StringIO(response.text), flavor='html5lib')
            
            # NASDAQ 100 테이블 찾기
            nasdaq_table = None
            for table in tables:
                if 'Ticker' in table.columns or 'Symbol' in table.columns:
                    nasdaq_table = table
                    break
            
            if nasdaq_table is None:
                logger.warning("NASDAQ 100 테이블을 찾을 수 없습니다")
                return []
            
            stocks = []
            symbol_col = 'Ticker' if 'Ticker' in nasdaq_table.columns else 'Symbol'
            name_col = 'Company' if 'Company' in nasdaq_table.columns else 'Name'
            
            for _, row in nasdaq_table.iterrows():
                symbol = str(row.get(symbol_col, '')).strip()
                name = str(row.get(name_col, '')).strip()
                if symbol and symbol != 'nan':
                    stocks.append({
                        'symbol': symbol,
                        'name': name,
                        'sector': row.get('GICS Sector', '').strip() if 'GICS Sector' in row else '',
                        'industry': row.get('GICS Sub-Industry', '').strip() if 'GICS Sub-Industry' in row else ''
                    })
            
            # 캐시 저장
            cache_data = {
                'date': datetime.now().isoformat(),
                'stocks': stocks
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"NASDAQ 100 리스트 수집 완료: {len(stocks)}개")
            return stocks
            
        except Exception as e:
            logger.error(f"NASDAQ 100 리스트 수집 실패: {e}")
            # 캐시가 있으면 사용
            if cache_path.exists():
                try:
                    cache_data = json.load(open(cache_path, 'r', encoding='utf-8'))
                    return cache_data.get('stocks', [])
                except:
                    pass
            return []
    
    def get_combined_universe(self, include_sp500: bool = True, include_nasdaq100: bool = True, 
                             limit: Optional[int] = None) -> List[str]:
        """
        통합 유니버스 가져오기 (심볼 리스트만)
        
        Args:
            include_sp500: S&P 500 포함 여부
            include_nasdaq100: NASDAQ 100 포함 여부
            limit: 최대 종목 수 (None이면 전체)
        
        Returns:
            ["AAPL", "MSFT", ...]
        """
        symbols = set()
        
        if include_sp500:
            sp500_stocks = self.get_sp500_list()
            symbols.update([s['symbol'] for s in sp500_stocks])
        
        if include_nasdaq100:
            nasdaq100_stocks = self.get_nasdaq100_list()
            symbols.update([s['symbol'] for s in nasdaq100_stocks])
        
        symbol_list = sorted(list(symbols))
        
        if limit:
            symbol_list = symbol_list[:limit]
        
        logger.info(f"통합 유니버스: {len(symbol_list)}개 종목")
        return symbol_list
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, str]]:
        """
        특정 종목의 정보 가져오기
        
        Args:
            symbol: 종목 심볼 (예: "AAPL")
        
        Returns:
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "...", "industry": "..."}
        """
        # S&P 500에서 찾기
        sp500_stocks = self.get_sp500_list()
        for stock in sp500_stocks:
            if stock['symbol'] == symbol:
                return stock
        
        # NASDAQ 100에서 찾기
        nasdaq100_stocks = self.get_nasdaq100_list()
        for stock in nasdaq100_stocks:
            if stock['symbol'] == symbol:
                return stock
        
        return None

# 전역 인스턴스
us_stocks_universe = USStocksUniverse()

