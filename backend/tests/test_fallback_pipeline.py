import unittest
from unittest.mock import patch

from market_analyzer import MarketCondition
from config import config
from services.scan_service import execute_scan_with_fallback


def make_condition(sentiment: str = "neutral") -> MarketCondition:
    return MarketCondition(
        date="20251024",
        kospi_return=0.01,
        volatility=0.02,
        market_sentiment=sentiment,
        sector_rotation="tech",
        foreign_flow="buy",
        institution_flow="buy",
        volume_trend="normal",
        rsi_threshold=58.0,
        min_signals=3,
        macd_osc_min=0.0,
        vol_ma5_mult=1.6,
        gap_min=-1.0,
        gap_max=4.0,
        ext_from_tema20_max=3.0,
        atr_pct_min=1.5,
        atr_pct_max=7.0,
        ema60_slope_min=0.0,
        tema20_slope_min=0.0,
        dema20_slope_min=-0.001,
        require_dema_slope="optional",
        overheat_rsi_tema=70.0,
        overheat_vol_mult=3.0,
        score_cut=10.0,
        sentiment_score=0.0,
        trend_metrics={},
        breadth_metrics={},
        flow_metrics={},
        sector_metrics={},
        volatility_metrics={},
        foreign_flow_label="buy",
        institution_flow_label="buy",
        volume_trend_label="normal",
        adjusted_params={},
        analysis_notes="",
    )


class FallbackPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.universe = ["AAA", "BBB", "CCC"]
        self.condition = make_condition("neutral")

    @patch("services.scan_service.scan_with_preset")
    def test_step1_rescan_occurs_when_step0_insufficient(self, mock_scan):
        mock_scan.side_effect = [
            [{"score": 9}],  # Step0: 후보 부족
            [{"score": 12}, {"score": 11}],  # Step1: 재스캔으로 확보
        ]
        with patch.object(
            config,
            "get_fallback_profile",
            return_value={"target_min": 1, "target_max": 3},
        ), patch.object(config, "top_k", 5), patch.object(config, "fallback_enable", True):
            items, step = execute_scan_with_fallback(
                self.universe, "20251024", self.condition
            )

        self.assertEqual(step, 1, "Step1에서 목표를 달성해야 함")
        self.assertEqual(len(items), 2)
        self.assertEqual(mock_scan.call_count, 2, "각 Step마다 재스캔해야 함")

    @patch("services.scan_service.scan_with_preset")
    def test_step3_ranked_results_respect_target_max(self, mock_scan):
        mock_scan.side_effect = [
            [],  # Step0
            [],  # Step1
            [],  # Step2
            [
                {"score": 8.5, "risk_score": 2, "ticker": "A"},
                {"score": 9.0, "risk_score": 3, "ticker": "B"},
                {"score": 9.0, "risk_score": 1, "ticker": "C"},
            ],
        ]
        with patch.object(
            config,
            "get_fallback_profile",
            return_value={"target_min": 1, "target_max": 2},
        ), patch.object(config, "top_k", 5), patch.object(config, "fallback_enable", True):
            items, step = execute_scan_with_fallback(
                self.universe, "20251024", self.condition
            )

        self.assertEqual(step, 3)
        self.assertEqual(len(items), 2, "target_max만큼만 반환해야 함")
        self.assertEqual(
            [item["ticker"] for item in items],
            ["C", "B"],
            "Step3 결과는 score 내림차순, risk_score 오름차순으로 정렬되어야 함",
        )
        self.assertEqual(mock_scan.call_count, 4)


if __name__ == "__main__":
    unittest.main()

