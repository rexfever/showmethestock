#!/usr/bin/env python3
"""
외부 의존성 목업
"""

class MockKiwoomAPI:
    def get_top_codes(self, market, limit):
        return ['005930', '000660', '035420'][:limit]
    
    def get_stock_name(self, code):
        names = {'005930': '삼성전자', '000660': 'SK하이닉스', '035420': 'NAVER'}
        return names.get(code, f'종목{code}')
    
    def get_ohlcv(self, code, count, base_dt=None):
        import pandas as pd
        return pd.DataFrame({
            'open': [100] * count,
            'high': [110] * count,
            'low': [90] * count,
            'close': [105] * count,
            'volume': [1000] * count,
            'date': [f'2025-01-{i+1:02d}' for i in range(count)]
        })

class MockConfig:
    universe_kospi = 3
    universe_kosdaq = 3
    ohlcv_count = 20
    market_analysis_enable = False
    fallback_enable = False
    score_level_strong = 8
    score_level_watch = 6
    rsi_setup_min = 57
    environment = 'local'
    is_local = True
    is_server = False

def mock_compute_indicators(df):
    df['TEMA20'] = 100
    df['DEMA10'] = 95
    df['MACD_OSC'] = 1.5
    df['MACD_LINE'] = 2.0
    df['MACD_SIGNAL'] = 1.8
    df['RSI_TEMA'] = 60
    df['RSI_DEMA'] = 55
    df['OBV'] = 1000
    df['VOL_MA5'] = 1200
    return df

def mock_match_stats(df):
    return True, 5, 7

def mock_score_conditions(df):
    return 8.5, {'match': True, 'label': 'Strong', 'details': {}}

def mock_strategy_text(df):
    return 'Mock Strategy'

def mock_get_recurrence_data(tickers, date):
    return {ticker: {'count': 2, 'dates': ['2025-01-01', '2025-01-02']} for ticker in tickers}

def mock_execute_scan_with_fallback(universe, date, market_condition):
    items = []
    for i, code in enumerate(universe[:3]):
        items.append({
            'ticker': code,
            'name': f'종목{code}',
            'match': True,
            'score': 8.0 + i,
            'score_label': 'Strong',
            'strategy': 'Mock Strategy',
            'indicators': {
                'TEMA': 100, 'DEMA': 95, 'MACD_OSC': 1.5,
                'MACD_LINE': 2.0, 'MACD_SIGNAL': 1.8,
                'RSI_TEMA': 60, 'RSI_DEMA': 55, 'OBV': 1000,
                'VOL': 1000, 'VOL_MA5': 1200, 'close': 105,
                'change_rate': 2.5
            },
            'trend': {
                'TEMA20_SLOPE20': 0.5, 'OBV_SLOPE20': 0.3,
                'ABOVE_CNT5': 3, 'DEMA10_SLOPE20': 0.4
            },
            'flags': {'match': True, 'label': 'Strong', 'details': {}}
        })
    return items, 'step1'

# 목업 적용
import sys
sys.path.insert(0, 'backend')

# 모듈 목업
import types

# kiwoom_api 목업
kiwoom_api_mock = types.ModuleType('kiwoom_api')
kiwoom_api_mock.KiwoomAPI = MockKiwoomAPI
sys.modules['kiwoom_api'] = kiwoom_api_mock

# config 목업
config_mock = types.ModuleType('config')
config_mock.config = MockConfig()
config_mock.reload_from_env = lambda: None
sys.modules['config'] = config_mock

# scanner 목업
scanner_mock = types.ModuleType('scanner')
scanner_mock.compute_indicators = mock_compute_indicators
scanner_mock.match_condition = lambda df: True
scanner_mock.match_stats = mock_match_stats
scanner_mock.strategy_text = mock_strategy_text
scanner_mock.score_conditions = mock_score_conditions
sys.modules['scanner'] = scanner_mock

# services 목업
services_mock = types.ModuleType('services')
services_mock.get_recurrence_data = mock_get_recurrence_data
services_mock.save_scan_snapshot = lambda *args: None
services_mock.execute_scan_with_fallback = mock_execute_scan_with_fallback
services_mock.calculate_returns = lambda *args: {'current_return': 5.2, 'max_return': 8.1}
services_mock.calculate_returns_batch = lambda *args: {}
services_mock.clear_cache = lambda: None

sys.modules['services.returns_service'] = services_mock
sys.modules['services.scan_service'] = services_mock

print("✅ 목업 설정 완료")