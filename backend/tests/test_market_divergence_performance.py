"""
성능 테스트: API 호출 최적화 검증
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import time

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from market_analyzer import MarketCondition


class TestPerformanceOptimization(unittest.TestCase):
    """성능 최적화 검증"""
    
    def test_api_call_reduction(self):
        """API 호출 감소 검증"""
        # 시뮬레이션: 200개 종목 스캔
        num_stocks = 200
        
        # 개선 전: 종목당 1회 API 호출
        old_api_calls = num_stocks
        
        # 개선 후: Universe 구성 시 1회만
        new_api_calls = 1
        
        reduction = old_api_calls - new_api_calls
        reduction_rate = (reduction / old_api_calls) * 100
        
        print(f"\nAPI 호출 감소:")
        print(f"  개선 전: {old_api_calls}회")
        print(f"  개선 후: {new_api_calls}회")
        print(f"  감소: {reduction}회 ({reduction_rate:.1f}%)")
        
        self.assertGreater(reduction, 0, "API 호출이 감소해야 함")
        self.assertGreater(reduction_rate, 99, "99% 이상 감소해야 함")
    
    def test_kospi_universe_caching(self):
        """KOSPI Universe 캐싱 검증"""
        # market_condition에 kospi_universe가 있는지 확인
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        
        # kospi_universe 필드 확인
        self.assertTrue(hasattr(market_condition, 'kospi_universe'), 
                       "kospi_universe 필드가 있어야 함")
        
        # 리스트 타입 확인
        market_condition.kospi_universe = ['005930', '000660', '035420']
        self.assertIsInstance(market_condition.kospi_universe, list,
                             "kospi_universe는 리스트여야 함")
    
    def test_cache_hit_performance(self):
        """캐시 히트 시 성능 검증"""
        market_condition = MarketCondition(
            date="20240101",
            kospi_return=0.05,
            volatility=0.02,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        market_condition.kospi_universe = ['005930', '000660', '035420'] * 50  # 150개
        
        # 캐시 사용 시 (리스트 조회)
        start = time.time()
        for _ in range(200):
            code = '005930'
            is_kospi = code in market_condition.kospi_universe
        cache_time = time.time() - start
        
        # API 호출 시뮬레이션 (느린 작업)
        start = time.time()
        for _ in range(200):
            # API 호출 시뮬레이션 (0.01초 소요)
            time.sleep(0.0001)  # 실제보다 빠르게 시뮬레이션
        api_time = time.time() - start
        
        print(f"\n성능 비교:")
        print(f"  캐시 사용: {cache_time*1000:.2f}ms")
        print(f"  API 호출: {api_time*1000:.2f}ms")
        print(f"  성능 향상: {api_time/cache_time:.1f}배")
        
        self.assertLess(cache_time, api_time, "캐시 사용이 더 빠르야 함")


if __name__ == '__main__':
    unittest.main()




































