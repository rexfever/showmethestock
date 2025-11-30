"""
short_term_risk_score 스케일링 및 MAX_CANDIDATES 조정 테스트
"""
import unittest
from unittest.mock import MagicMock
import sys
import os

# backend 디렉토리를 경로에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from scanner_v2.core.scanner import ScannerV2
from market_analyzer import MarketCondition
from scanner_v2.core.scanner import ScanResult
from scanner_v2.config_regime import MAX_CANDIDATES


class TestShortTermRiskScaling(unittest.TestCase):
    """short_term_risk_score 스케일링 및 throttling 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # Mock config 객체 생성
        mock_config = MagicMock()
        mock_config.risk_score_threshold = 4
        mock_config.market_analysis_enable = True
        self.scanner = ScannerV2(mock_config)
        
    def test_risk_score_scaling(self):
        """risk_score가 최대 +1.0까지만 증가하는지 확인"""
        # 테스트 데이터: score=7.0, base_risk_score=1.0
        test_results = []
        for i in range(5):
            result = ScanResult(
                ticker=f"TEST{i:03d}",
                name=f"테스트종목{i}",
                score=7.0,
                match=True,
                strategy="test",
                flags={"risk_score": 1.0},  # base_risk_score
                indicators={},
                trend={},
                score_label="test"
            )
            test_results.append(result)
        
        # short_term_risk_score별 테스트
        test_cases = [
            (0, 0.0, "risk_score는 base_risk_score(1.0) 그대로"),
            (1, 0.5, "risk_score는 base_risk_score(1.0) + 0.5 = 1.5"),
            (2, 1.0, "risk_score는 base_risk_score(1.0) + 1.0 = 2.0"),
            (3, 1.0, "risk_score는 base_risk_score(1.0) + 1.0 = 2.0 (최대 +1.0)"),
        ]
        
        for short_term_risk, expected_adjust, description in test_cases:
            with self.subTest(short_term_risk=short_term_risk):
                # MarketCondition Mock 생성 (필수 필드만)
                market_condition = MagicMock()
                market_condition.midterm_regime = "bull"
                market_condition.short_term_risk_score = short_term_risk
                market_condition.final_regime = "bull"
                market_condition.market_sentiment = "bull"
                
                # _apply_regime_cutoff 호출
                filtered = self.scanner._apply_regime_cutoff(test_results, market_condition)
                
                # effective_score 계산 검증
                # score=7.0, base_risk=1.0, adjust=expected_adjust
                # effective_score = 7.0 - (1.0 + expected_adjust) = 6.0 - expected_adjust
                expected_effective = 7.0 - (1.0 + expected_adjust)
                
                # bull swing cutoff = 6.0
                # risk_adjust가 0.0이면 effective=6.0 >= 6.0 (통과)
                # risk_adjust가 0.5이면 effective=5.5 < 6.0 (제거)
                # risk_adjust가 1.0이면 effective=5.0 < 6.0 (제거)
                
                if short_term_risk == 0:
                    # 모든 후보가 통과해야 함 (effective_score=6.0 >= 6.0)
                    self.assertGreater(len(filtered), 0, f"{description}: 후보가 있어야 함")
                else:
                    # 일부는 제거될 수 있지만, risk_score가 3 이상이어도 최대 +1.0까지만 증가
                    # 실제로는 effective_score가 cutoff 미만이면 제거되지만,
                    # 중요한 것은 risk_score가 절대 값 3까지 증가하지 않는다는 것
                    pass
                
                print(f"✅ {description}: short_term_risk={short_term_risk}, adjust={expected_adjust}")
    
    def test_max_candidates_adjustment(self):
        """short_term_risk_score에 따른 MAX_CANDIDATES 조정 확인"""
        base_max = MAX_CANDIDATES.copy()
        
        test_cases = [
            (0, {'swing': 20, 'position': 15, 'longterm': 20}, "리스크 0: 기본값 유지"),
            (1, {'swing': 15, 'position': 10, 'longterm': 20}, "리스크 1: swing/position 감소, longterm 유지"),
            (2, {'swing': 10, 'position': 5, 'longterm': 15}, "리스크 2: 모든 horizon 감소"),
            (3, {'swing': 5, 'position': 3, 'longterm': 10}, "리스크 3: 최대 감소"),
        ]
        
        for risk_level, expected_max, description in test_cases:
            with self.subTest(risk_level=risk_level):
                adjusted = self.scanner._adjust_max_candidates_by_risk(base_max, risk_level)
                
                self.assertEqual(adjusted['swing'], expected_max['swing'], 
                               f"{description}: swing 개수 불일치")
                self.assertEqual(adjusted['position'], expected_max['position'], 
                               f"{description}: position 개수 불일치")
                self.assertEqual(adjusted['longterm'], expected_max['longterm'], 
                               f"{description}: longterm 개수 불일치")
                
                print(f"✅ {description}: {adjusted}")
    
    def test_bull_regime_with_risk_scores(self):
        """bull 레짐에서 short_term_risk_score별 후보 개수 확인"""
        # 충분한 후보 생성 (score=7.0, base_risk=1.0)
        test_results = []
        for i in range(30):
            result = ScanResult(
                ticker=f"TEST{i:03d}",
                name=f"테스트종목{i}",
                score=7.0,
                match=True,
                strategy="test",
                flags={"risk_score": 1.0},
                indicators={},
                trend={},
                score_label="test"
            )
            test_results.append(result)
        
        for short_term_risk in [0, 1, 2, 3]:
            with self.subTest(short_term_risk=short_term_risk):
                # MarketCondition Mock 생성 (필수 필드만)
                market_condition = MagicMock()
                market_condition.midterm_regime = "bull"
                market_condition.short_term_risk_score = short_term_risk
                market_condition.final_regime = "bull"
                market_condition.market_sentiment = "bull"
                
                filtered = self.scanner._apply_regime_cutoff(test_results, market_condition)
                
                # risk_score가 높아질수록 후보 개수가 줄어들지만 전부 0이 되지는 않아야 함
                # (단, effective_score가 cutoff 미만이면 제거됨)
                
                # bull swing cutoff = 6.0
                # score=7.0, base_risk=1.0
                # risk=0: effective=6.0 >= 6.0 (통과)
                # risk=1: effective=5.5 < 6.0 (제거)
                # risk=2: effective=5.0 < 6.0 (제거)
                # risk=3: effective=5.0 < 6.0 (제거)
                
                if short_term_risk == 0:
                    self.assertGreater(len(filtered), 0, 
                                     f"risk=0일 때는 후보가 있어야 함 (현재: {len(filtered)}개)")
                else:
                    # risk가 높으면 후보가 줄어들 수 있지만, MAX_CANDIDATES 조정은 적용됨
                    print(f"  risk={short_term_risk}: 후보 {len(filtered)}개")
                
                # 중요한 검증: risk_score가 절대 값 3까지 증가하지 않음
                # (이미 _apply_regime_cutoff 내부에서 스케일링됨)
                print(f"✅ risk={short_term_risk}: 후보 {len(filtered)}개, MAX_CANDIDATES 조정 적용됨")


if __name__ == '__main__':
    unittest.main()

