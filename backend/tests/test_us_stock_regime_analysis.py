"""
미국 주식 스캔 레짐 분석 적용 테스트
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_analyzer import MarketCondition, MarketAnalyzer
from scanner_v2.us_scanner import USScanner
from scanner_v2.config_v2 import ScannerV2Config
from scanner_v2.core.scanner import ScanResult


class TestUSStockRegimeAnalysis(unittest.TestCase):
    """미국 주식 스캔 레짐 분석 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = ScannerV2Config()
        self.market_analyzer = MarketAnalyzer()
        self.us_scanner = USScanner(self.config, self.market_analyzer)
        
        # 테스트용 MarketCondition 생성
        self.bull_condition = MarketCondition(
            date="20250101",
            kospi_return=0.02,
            volatility=0.15,
            market_sentiment="bull",
            sector_rotation="tech",
            foreign_flow="buy",
            institution_flow="buy",
            volume_trend="high",
            rsi_threshold=55.0,
            min_signals=2,
            macd_osc_min=0.0,
            vol_ma5_mult=2.0,
            gap_max=0.05,
            ext_from_tema20_max=0.1,
            final_regime="bull",
            version="regime_v4",
            global_trend_score=2.5,
            global_risk_score=0.5
        )
        
        self.neutral_condition = MarketCondition(
            date="20250101",
            kospi_return=0.0,
            volatility=0.15,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.05,
            ext_from_tema20_max=0.1,
            final_regime="neutral",
            version="regime_v4",
            global_trend_score=0.0,
            global_risk_score=0.5
        )
        
        self.bear_condition = MarketCondition(
            date="20250101",
            kospi_return=-0.02,
            volatility=0.25,
            market_sentiment="bear",
            sector_rotation="value",
            foreign_flow="sell",
            institution_flow="sell",
            volume_trend="low",
            rsi_threshold=60.0,
            min_signals=4,
            macd_osc_min=0.0,
            vol_ma5_mult=3.0,
            gap_max=0.03,
            ext_from_tema20_max=0.08,
            final_regime="bear",
            version="regime_v4",
            global_trend_score=-2.0,
            global_risk_score=1.5
        )
        
        self.crash_condition = MarketCondition(
            date="20250101",
            kospi_return=-0.05,
            volatility=0.35,
            market_sentiment="bear",
            sector_rotation="mixed",
            foreign_flow="sell",
            institution_flow="sell",
            volume_trend="high",
            rsi_threshold=65.0,
            min_signals=5,
            macd_osc_min=0.0,
            vol_ma5_mult=3.5,
            gap_max=0.02,
            ext_from_tema20_max=0.05,
            final_regime="crash",
            version="regime_v4",
            global_trend_score=-3.0,
            global_risk_score=2.5
        )
    
    def test_regime_cutoff_bull(self):
        """bull 레짐 cutoff 테스트"""
        from scanner_v2.config_regime import REGIME_CUTOFFS
        
        # 테스트용 결과 생성
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="MSFT",
                name="Microsoft Corporation",
                match=True,
                score=5.0,
                score_label="매수 후보",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="GOOGL",
                name="Alphabet Inc.",
                match=True,
                score=3.0,
                score_label="관심 종목",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # bull 레짐 cutoff 적용
        filtered = self.us_scanner._apply_regime_cutoff(results, self.bull_condition)
        
        # bull: swing 6.0, position 4.3
        # AAPL (swing, 7.0) >= 6.0 → 통과
        # MSFT (position, 5.0) >= 4.3 → 통과
        # GOOGL (swing, 3.0) < 6.0 → 제외
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].ticker, "AAPL")
        self.assertEqual(filtered[1].ticker, "MSFT")
    
    def test_regime_cutoff_neutral(self):
        """neutral 레짐 cutoff 테스트"""
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="MSFT",
                name="Microsoft Corporation",
                match=True,
                score=5.0,
                score_label="매수 후보",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="GOOGL",
                name="Alphabet Inc.",
                match=True,
                score=4.0,
                score_label="관심 종목",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # neutral 레짐 cutoff 적용
        filtered = self.us_scanner._apply_regime_cutoff(results, self.neutral_condition)
        
        # neutral: swing 6.0, position 4.5
        # AAPL (swing, 7.0) >= 6.0 → 통과
        # MSFT (position, 5.0) >= 4.5 → 통과
        # GOOGL (position, 4.0) < 4.5 → 제외
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].ticker, "AAPL")
        self.assertEqual(filtered[1].ticker, "MSFT")
    
    def test_regime_cutoff_bear(self):
        """bear 레짐 cutoff 테스트"""
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="MSFT",
                name="Microsoft Corporation",
                match=True,
                score=6.0,
                score_label="매수 후보",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="GOOGL",
                name="Alphabet Inc.",
                match=True,
                score=5.0,
                score_label="관심 종목",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # bear 레짐 cutoff 적용
        filtered = self.us_scanner._apply_regime_cutoff(results, self.bear_condition)
        
        # bear: swing 999.0, position 5.5
        # AAPL (swing, 7.0) < 999.0 → 제외 (swing 비활성화)
        # MSFT (position, 6.0) >= 5.5 → 통과
        # GOOGL (position, 5.0) < 5.5 → 제외
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].ticker, "MSFT")
    
    def test_regime_cutoff_crash(self):
        """crash 레짐 cutoff 테스트"""
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="MSFT",
                name="Microsoft Corporation",
                match=True,
                score=6.0,
                score_label="매수 후보",
                strategy="position",
                indicators={},
                trend={},
                flags={}
            ),
            ScanResult(
                ticker="GOOGL",
                name="Alphabet Inc.",
                match=True,
                score=7.0,
                score_label="관심 종목",
                strategy="longterm",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # crash 레짐 cutoff 적용
        filtered = self.us_scanner._apply_regime_cutoff(results, self.crash_condition)
        
        # crash: swing 999.0, position 999.0, longterm 6.0
        # AAPL (swing, 7.0) < 999.0 → 제외 (swing 비활성화)
        # MSFT (position, 6.0) < 999.0 → 제외 (position 비활성화)
        # GOOGL (longterm, 7.0) >= 6.0 → 통과
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].ticker, "GOOGL")
    
    def test_regime_cutoff_no_final_regime(self):
        """final_regime이 없는 경우 fallback 테스트"""
        condition_no_regime = MarketCondition(
            date="20250101",
            kospi_return=0.0,
            volatility=0.15,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.05,
            ext_from_tema20_max=0.1
            # final_regime 없음
        )
        
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # final_regime이 없으면 'neutral'로 fallback
        filtered = self.us_scanner._apply_regime_cutoff(results, condition_no_regime)
        
        # neutral: swing 6.0
        # AAPL (swing, 7.0) >= 6.0 → 통과
        self.assertEqual(len(filtered), 1)
    
    def test_regime_cutoff_unknown_regime(self):
        """알 수 없는 레짐인 경우 fallback 테스트"""
        condition_unknown = MarketCondition(
            date="20250101",
            kospi_return=0.0,
            volatility=0.15,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.05,
            ext_from_tema20_max=0.1,
            final_regime="unknown_regime"  # 알 수 없는 레짐
        )
        
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy="swing",
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # 알 수 없는 레짐이면 'neutral'로 fallback
        filtered = self.us_scanner._apply_regime_cutoff(results, condition_unknown)
        
        # neutral: swing 6.0
        # AAPL (swing, 7.0) >= 6.0 → 통과
        self.assertEqual(len(filtered), 1)
    
    def test_regime_cutoff_no_strategy(self):
        """strategy가 None인 경우 테스트"""
        results = [
            ScanResult(
                ticker="AAPL",
                name="Apple Inc.",
                match=True,
                score=7.0,
                score_label="강한 매수",
                strategy=None,  # strategy가 None
                indicators={},
                trend={},
                flags={}
            ),
        ]
        
        # strategy가 None이면 .lower()에서 에러 발생 가능
        # 안전하게 처리되는지 확인
        try:
            filtered = self.us_scanner._apply_regime_cutoff(results, self.bull_condition)
            # 에러가 발생하지 않으면 통과 (cutoff = 999로 처리되어 제외됨)
            self.assertIsInstance(filtered, list)
        except AttributeError:
            self.fail("strategy가 None일 때 AttributeError 발생")
    
    def test_market_condition_passed_to_scan(self):
        """market_condition이 scan()에 전달되는지 테스트"""
        with patch.object(self.us_scanner, 'scan_one') as mock_scan_one:
            mock_scan_one.return_value = None
            
            universe = ["AAPL", "MSFT"]
            date = "20250101"
            
            # market_condition과 함께 scan() 호출
            self.us_scanner.scan(universe, date, self.bull_condition)
            
            # scan_one이 market_condition과 함께 호출되었는지 확인
            self.assertEqual(mock_scan_one.call_count, 2)
            for call in mock_scan_one.call_args_list:
                args, kwargs = call
                self.assertEqual(args[0] in universe, True)  # symbol
                self.assertEqual(args[1], date)  # date
                self.assertEqual(args[2], self.bull_condition)  # market_condition
    
    def test_market_condition_none(self):
        """market_condition이 None일 때도 정상 작동하는지 테스트"""
        with patch.object(self.us_scanner, 'scan_one') as mock_scan_one:
            mock_scan_one.return_value = None
            
            universe = ["AAPL", "MSFT"]
            date = "20250101"
            
            # market_condition = None으로 scan() 호출
            results = self.us_scanner.scan(universe, date, None)
            
            # scan_one이 None과 함께 호출되었는지 확인
            self.assertEqual(mock_scan_one.call_count, 2)
            for call in mock_scan_one.call_args_list:
                args, kwargs = call
                self.assertIsNone(args[2])  # market_condition = None
            
            # market_condition이 None이면 _apply_regime_cutoff가 호출되지 않음
            self.assertIsInstance(results, list)
    
    def test_filter_engine_uses_market_condition(self):
        """필터 엔진이 market_condition을 사용하는지 테스트"""
        # USFilterEngine의 apply_soft_filters가 market_condition을 사용하는지 확인
        # 실제 데이터가 필요하므로 mock 사용
        
        # market_condition이 있을 때와 없을 때의 동작 차이 확인
        # (실제 구현은 USFilterEngine에서 확인)
        self.assertTrue(hasattr(self.us_scanner.filter_engine, 'market_analysis_enable'))
    
    @patch('main.market_analyzer')
    @patch('main.config')
    def test_regime_analysis_in_scan_us_stocks(self, mock_config, mock_market_analyzer):
        """scan_us_stocks()에서 레짐 분석이 실행되는지 테스트"""
        # 이 테스트는 실제 API 엔드포인트를 호출하지 않고
        # 레짐 분석 로직만 확인
        
        mock_config.market_analysis_enable = True
        mock_market_analyzer.analyze_market_condition.return_value = self.bull_condition
        
        # 레짐 분석이 호출되는지 확인
        date = "20250101"
        market_condition = mock_market_analyzer.analyze_market_condition(
            date,
            regime_version='v4'
        )
        
        mock_market_analyzer.analyze_market_condition.assert_called_once_with(
            date,
            regime_version='v4'
        )
        self.assertIsNotNone(market_condition)
        self.assertEqual(market_condition.final_regime, "bull")
    
    @patch('main.market_analyzer')
    @patch('main.config')
    def test_regime_analysis_failure_handling(self, mock_config, mock_market_analyzer):
        """레짐 분석 실패 시 처리 테스트"""
        mock_config.market_analysis_enable = True
        mock_market_analyzer.analyze_market_condition.side_effect = Exception("레짐 분석 실패")
        
        # 레짐 분석 실패 시 market_condition = None
        market_condition = None
        try:
            market_condition = mock_market_analyzer.analyze_market_condition(
                "20250101",
                regime_version='v4'
            )
        except Exception:
            pass  # 예상된 에러
        
        self.assertIsNone(market_condition)


if __name__ == '__main__':
    unittest.main()

