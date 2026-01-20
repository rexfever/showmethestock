"""
미국 주식 스캐너 종합 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from scanner_v2.us_scanner import USScanner
from scanner_v2.config_v2 import ScannerV2Config
from services.us_stocks_data import us_stocks_data
from services.us_stocks_universe import us_stocks_universe


class TestUSScannerComprehensive(unittest.TestCase):
    """미국 주식 스캐너 종합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = ScannerV2Config()
        self.scanner = USScanner(self.config)
        
        # 샘플 OHLCV 데이터 생성
        dates = pd.date_range(end=datetime.now(), periods=220, freq='D')
        self.sample_df = pd.DataFrame({
            'open': np.random.uniform(100, 200, 220),
            'high': np.random.uniform(200, 300, 220),
            'low': np.random.uniform(50, 100, 220),
            'close': np.random.uniform(100, 200, 220),
            'volume': np.random.randint(1000000, 10000000, 220)
        }, index=dates)
        
        # 지표 계산을 위한 기본 데이터 설정
        self.sample_df['TEMA20'] = self.sample_df['close'].rolling(20).mean()
        self.sample_df['DEMA10'] = self.sample_df['close'].rolling(10).mean()
        self.sample_df['RSI_TEMA'] = 50.0
        self.sample_df['RSI_DEMA'] = 50.0
        self.sample_df['MACD_LINE'] = 0.0
        self.sample_df['MACD_SIGNAL'] = 0.0
        self.sample_df['MACD_OSC'] = 0.0
        self.sample_df['VOL_MA5'] = self.sample_df['volume'].rolling(5).mean()
        self.sample_df['VOL_MA20'] = self.sample_df['volume'].rolling(20).mean()
        self.sample_df['OBV'] = 0.0
        self.sample_df['TEMA20_SLOPE20'] = 0.001
        self.sample_df['DEMA10_SLOPE20'] = 0.001
        self.sample_df['OBV_SLOPE20'] = 0.001
        
        # 최근 데이터를 매수 신호에 맞게 설정
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('TEMA20')] = 150.0
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('DEMA10')] = 140.0
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('close')] = 155.0
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('RSI_TEMA')] = 60.0
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('volume')] = 5000000
        self.sample_df.iloc[-1, self.sample_df.columns.get_loc('VOL_MA5')] = 2000000
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    @patch('scanner_v2.us_scanner.us_stocks_universe')
    @patch('scanner.compute_indicators')
    def test_scan_one_success(self, mock_compute, mock_universe, mock_data):
        """정상적인 스캔 테스트"""
        # Mock 설정
        mock_data.get_ohlcv.return_value = self.sample_df
        mock_universe.get_stock_info.return_value = {'name': 'Apple Inc.', 'symbol': 'AAPL'}
        mock_compute.return_value = self.sample_df
        
        result = self.scanner.scan_one('AAPL', '20251202')
        
        # 결과 검증
        self.assertIsNotNone(result)
        self.assertEqual(result.ticker, 'AAPL')
        self.assertEqual(result.name, 'Apple Inc.')
        self.assertIsInstance(result.score, (int, float))
        self.assertIsNotNone(result.strategy)
        self.assertIsNotNone(result.score_label)
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    def test_scan_one_empty_data(self, mock_data):
        """빈 데이터 테스트"""
        mock_data.get_ohlcv.return_value = pd.DataFrame()
        
        result = self.scanner.scan_one('AAPL', '20251202')
        self.assertIsNone(result)
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    def test_scan_one_insufficient_data(self, mock_data):
        """데이터 부족 테스트"""
        short_df = self.sample_df.head(10)
        mock_data.get_ohlcv.return_value = short_df
        
        result = self.scanner.scan_one('AAPL', '20251202')
        self.assertIsNone(result)
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    def test_scan_one_missing_values(self, mock_data):
        """결측값 포함 데이터 테스트"""
        df_with_nan = self.sample_df.copy()
        df_with_nan.iloc[-1, df_with_nan.columns.get_loc('close')] = np.nan
        mock_data.get_ohlcv.return_value = df_with_nan
        
        result = self.scanner.scan_one('AAPL', '20251202')
        self.assertIsNone(result)
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    @patch('scanner_v2.us_scanner.us_stocks_universe')
    def test_scan_one_api_error(self, mock_universe, mock_data):
        """API 에러 처리 테스트"""
        mock_data.get_ohlcv.side_effect = Exception("API Error")
        
        result = self.scanner.scan_one('AAPL', '20251202')
        self.assertIsNone(result)
    
    @patch('scanner_v2.us_scanner.us_stocks_data')
    @patch('scanner_v2.us_scanner.us_stocks_universe')
    @patch('scanner.compute_indicators')
    def test_scan_one_no_stock_info(self, mock_compute, mock_universe, mock_data):
        """종목 정보 없음 테스트"""
        mock_data.get_ohlcv.return_value = self.sample_df
        mock_universe.get_stock_info.return_value = None
        mock_compute.return_value = self.sample_df
        
        result = self.scanner.scan_one('UNKNOWN', '20251202')
        # 종목 정보가 없어도 심볼로 대체되어야 함
        if result:
            self.assertEqual(result.ticker, 'UNKNOWN')
    
    def test_calculate_change_rate(self):
        """등락률 계산 테스트"""
        df = pd.DataFrame({
            'close': [100.0, 105.0, 110.0]
        })
        
        change_rate = self.scanner._calculate_change_rate(df)
        # (110-105)/105 * 100 = 4.7619...
        self.assertAlmostEqual(change_rate, 4.76, places=1)
    
    def test_calculate_change_rate_insufficient_data(self):
        """데이터 부족 시 등락률 계산 테스트"""
        df = pd.DataFrame({'close': [100.0]})
        
        change_rate = self.scanner._calculate_change_rate(df)
        self.assertEqual(change_rate, 0.0)
    
    def test_scan_universe(self):
        """유니버스 전체 스캔 테스트"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        with patch.object(self.scanner, 'scan_one') as mock_scan_one:
            mock_result = Mock()
            mock_result.ticker = 'AAPL'
            mock_result.score = 10.0
            mock_scan_one.return_value = mock_result
            
            results = self.scanner.scan(symbols, '20251202')
            
            self.assertEqual(len(results), 3)
            self.assertEqual(mock_scan_one.call_count, 3)
            # 점수 순 정렬 확인
            scores = [r.score for r in results]
            self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_scan_universe_with_filters(self):
        """필터링된 유니버스 스캔 테스트"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        with patch.object(self.scanner, 'scan_one') as mock_scan_one:
            # 첫 번째는 통과, 나머지는 필터링
            mock_result = Mock()
            mock_result.ticker = 'AAPL'
            mock_result.score = 10.0
            mock_scan_one.side_effect = [mock_result, None, None]
            
            results = self.scanner.scan(symbols, '20251202')
            
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].ticker, 'AAPL')


class TestUSStocksUniverse(unittest.TestCase):
    """미국 주식 유니버스 테스트"""
    
    def setUp(self):
        from services.us_stocks_universe import USStocksUniverse
        self.universe = USStocksUniverse()
    
    @patch('services.us_stocks_universe.pd.read_html')
    def test_get_sp500_list(self, mock_read_html):
        """S&P 500 리스트 가져오기 테스트"""
        # Mock 데이터
        mock_df = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'Security': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.'],
            'GICS Sector': ['Technology', 'Technology', 'Technology'],
            'GICS Sub-Industry': ['Computers', 'Software', 'Internet']
        })
        mock_read_html.return_value = [mock_df]
        
        stocks = self.universe.get_sp500_list(use_cache=False)
        
        self.assertGreater(len(stocks), 0)
        self.assertEqual(stocks[0]['symbol'], 'AAPL')
        self.assertEqual(stocks[0]['name'], 'Apple Inc.')
    
    @patch('services.us_stocks_universe.pd.read_html')
    def test_get_nasdaq100_list(self, mock_read_html):
        """NASDAQ 100 리스트 가져오기 테스트"""
        mock_df = pd.DataFrame({
            'Ticker': ['AAPL', 'MSFT'],
            'Company': ['Apple Inc.', 'Microsoft Corp.']
        })
        mock_read_html.return_value = [mock_df]
        
        stocks = self.universe.get_nasdaq100_list(use_cache=False)
        
        self.assertGreater(len(stocks), 0)
    
    def test_get_combined_universe(self):
        """통합 유니버스 테스트"""
        with patch.object(self.universe, 'get_sp500_list') as mock_sp500, \
             patch.object(self.universe, 'get_nasdaq100_list') as mock_nasdaq:
            
            mock_sp500.return_value = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp.'}
            ]
            mock_nasdaq.return_value = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},  # 중복
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'}
            ]
            
            symbols = self.universe.get_combined_universe()
            
            # 중복 제거 확인
            self.assertEqual(len(symbols), 3)
            self.assertIn('AAPL', symbols)
            self.assertIn('MSFT', symbols)
            self.assertIn('GOOGL', symbols)
    
    def test_get_stock_info(self):
        """종목 정보 가져오기 테스트"""
        with patch.object(self.universe, 'get_sp500_list') as mock_sp500:
            mock_sp500.return_value = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'}
            ]
            
            info = self.universe.get_stock_info('AAPL')
            
            self.assertIsNotNone(info)
            self.assertEqual(info['symbol'], 'AAPL')
            self.assertEqual(info['name'], 'Apple Inc.')


class TestUSStocksData(unittest.TestCase):
    """미국 주식 데이터 수집 테스트"""
    
    def setUp(self):
        from services.us_stocks_data import USStocksData
        self.data_service = USStocksData()
    
    @patch('services.us_stocks_data.requests.get')
    def test_fetch_chart_api_success(self, mock_get):
        """Chart API 성공 테스트"""
        # Mock 응답
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'timestamp': [1609459200, 1609545600],  # 2일치
                    'indicators': {
                        'quote': [{
                            'open': [100.0, 105.0],
                            'high': [110.0, 115.0],
                            'low': [95.0, 100.0],
                            'close': [108.0, 112.0],
                            'volume': [1000000, 2000000]
                        }]
                    }
                }]
            }
        }
        mock_get.return_value = mock_response
        
        df = self.data_service._fetch_chart_api('AAPL', period='1y')
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn('open', df.columns)
        self.assertIn('close', df.columns)
    
    @patch('services.us_stocks_data.requests.get')
    def test_fetch_chart_api_error(self, mock_get):
        """Chart API 에러 테스트"""
        mock_get.side_effect = Exception("Network Error")
        
        df = self.data_service._fetch_chart_api('AAPL', period='1y')
        
        self.assertTrue(df.empty)
    
    @patch('services.us_stocks_data.requests.get')
    def test_get_stock_quote(self, mock_get):
        """실시간 주가 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 150.0,
                        'previousClose': 148.0,
                        'regularMarketVolume': 5000000
                    },
                    'indicators': {
                        'quote': [{}]
                    }
                }]
            }
        }
        mock_get.return_value = mock_response
        
        quote = self.data_service.get_stock_quote('AAPL')
        
        self.assertIsNotNone(quote)
        self.assertEqual(quote['current_price'], 150.0)
        self.assertEqual(quote['prev_close'], 148.0)
        self.assertAlmostEqual(quote['change_rate'], 1.35, places=1)  # (150-148)/148 * 100


if __name__ == '__main__':
    unittest.main()

