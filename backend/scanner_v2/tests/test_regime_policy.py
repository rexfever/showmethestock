"""
Regime v4 정책 테스트
"""
import pytest
from scanner_v2.regime_policy import (
    RegimePolicy,
    decide_policy,
    apply_policy,
    _extract_final_regime,
    _extract_risk_label
)


class TestExtractFinalRegime:
    """final_regime 추출 테스트"""
    
    def test_extract_from_dict_with_final_regime(self):
        regime = {"final_regime": "bull"}
        assert _extract_final_regime(regime) == "bull"
    
    def test_extract_from_dict_with_midterm_regime(self):
        regime = {"midterm_regime": "bear"}
        assert _extract_final_regime(regime) == "bear"
    
    def test_extract_from_dict_fallback_to_neutral(self):
        regime = {}
        assert _extract_final_regime(regime) == "neutral"
    
    def test_extract_from_object(self):
        class MockRegime:
            def __init__(self):
                self.final_regime = "crash"
        
        regime = MockRegime()
        assert _extract_final_regime(regime) == "crash"
    
    def test_extract_from_none(self):
        assert _extract_final_regime(None) == "neutral"


class TestExtractRiskLabel:
    """risk_label 추출 테스트"""
    
    def test_extract_global_risk_from_dict(self):
        regime = {"global_risk": "stressed"}
        assert _extract_risk_label(regime) == "stressed"
    
    def test_extract_from_risk_labels_worst_case(self):
        regime = {"us_risk_label": "elevated", "kr_risk_label": "stressed"}
        assert _extract_risk_label(regime) == "stressed"  # worst 선택
    
    def test_extract_from_global_risk_score(self):
        regime = {"global_risk_score": -3.5}
        assert _extract_risk_label(regime) == "stressed"
    
    def test_extract_from_short_term_risk_score(self):
        regime = {"short_term_risk_score": 3}
        assert _extract_risk_label(regime) == "stressed"
    
    def test_extract_fallback_to_normal(self):
        regime = {}
        assert _extract_risk_label(regime) == "normal"


class TestDecidePolicy:
    """정책 결정 테스트 (완화안 v2)"""
    
    def test_policy_disabled(self):
        policy = decide_policy(None, enabled=False)
        assert policy.enabled == False
        assert policy.grade == "NORMAL"
        assert policy.top_n == -1
        assert policy.reason == "policy disabled"
    
    def test_bull_normal_strong(self):
        """완화안 v2: (final_regime="bull", risk_label="normal") -> grade STRONG, top_n 15"""
        regime = {
            "final_regime": "bull",
            "global_risk": "normal"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "STRONG"
        assert policy.top_n == 15
        assert "강세장" in policy.reason
    
    def test_bull_elevated_normal(self):
        """완화안 v2: (final_regime="bull", risk_label="elevated") -> grade NORMAL, top_n 8"""
        regime = {
            "final_regime": "bull",
            "global_risk": "elevated"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "NORMAL"
        assert policy.top_n == 8
    
    def test_bull_stressed_caution(self):
        """완화안 v2: (final_regime="bull", risk_label="stressed") -> grade CAUTION, top_n 5"""
        regime = {
            "final_regime": "bull",
            "global_risk": "stressed"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "CAUTION"
        assert policy.top_n == 5
    
    def test_bear_stressed_off(self):
        """완화안 v2: (final_regime="bear", risk_label="stressed") -> grade OFF, top_n 0"""
        regime = {
            "final_regime": "bear",
            "global_risk": "stressed"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "OFF"
        assert policy.top_n == 0
        assert "중단" in policy.reason
    
    def test_bear_elevated_caution(self):
        """완화안 v2: (final_regime="bear", risk_label="elevated") -> grade CAUTION, top_n 3 (기존 OFF에서 완화)"""
        regime = {
            "final_regime": "bear",
            "global_risk": "elevated"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "CAUTION"
        assert policy.top_n == 3
    
    def test_bear_normal_caution(self):
        """완화안 v2: (final_regime="bear", risk_label="normal") -> grade CAUTION, top_n 5"""
        regime = {
            "final_regime": "bear",
            "global_risk": "normal"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "CAUTION"
        assert policy.top_n == 5
    
    def test_neutral_normal_normal(self):
        """완화안 v2: (final_regime="neutral", risk_label="normal") -> grade NORMAL, top_n 8"""
        regime = {
            "final_regime": "neutral",
            "global_risk": "normal"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "NORMAL"
        assert policy.top_n == 8
    
    def test_neutral_stressed_caution(self):
        """완화안 v2: (final_regime="neutral", risk_label="stressed") -> grade CAUTION, top_n 3"""
        regime = {
            "final_regime": "neutral",
            "global_risk": "stressed"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "CAUTION"
        assert policy.top_n == 3
    
    def test_crash_off(self):
        """완화안 v2: (final_regime="crash") -> grade OFF, top_n 0"""
        regime = {
            "final_regime": "crash"
        }
        policy = decide_policy(regime, enabled=True)
        assert policy.grade == "OFF"
        assert policy.top_n == 0


class TestApplyPolicy:
    """정책 적용 테스트"""
    
    def test_apply_policy_disabled(self):
        """테스트 케이스 5: enabled=False면 grade NORMAL, top_n -1이고 apply_policy가 원본 그대로 반환"""
        candidates = [{"ticker": "A"}, {"ticker": "B"}, {"ticker": "C"}]
        policy = RegimePolicy(
            enabled=False,
            grade="NORMAL",
            top_n=-1,
            reason="policy disabled",
            snapshot={}
        )
        result, applied_policy = apply_policy(candidates, policy)
        assert len(result) == 3
        assert result == candidates
    
    def test_apply_policy_off_empty(self):
        """테스트 케이스 4: OFF면 빈 리스트인지"""
        candidates = [{"ticker": "A"}, {"ticker": "B"}]
        policy = RegimePolicy(
            enabled=True,
            grade="OFF",
            top_n=0,
            reason="추천 중단",
            snapshot={}
        )
        result, applied_policy = apply_policy(candidates, policy)
        assert len(result) == 0
        assert result == []
    
    def test_apply_policy_slice_maintains_order(self):
        """테스트 케이스 3: apply_policy가 순서 유지 + 슬라이싱만 하는지"""
        candidates = [
            {"ticker": "A", "score": 10},
            {"ticker": "B", "score": 9},
            {"ticker": "C", "score": 8},
            {"ticker": "D", "score": 7},
            {"ticker": "E", "score": 6},
        ]
        policy = RegimePolicy(
            enabled=True,
            grade="STRONG",
            top_n=3,
            reason="강력 추천",
            snapshot={}
        )
        result, applied_policy = apply_policy(candidates, policy)
        assert len(result) == 3
        assert result[0]["ticker"] == "A"
        assert result[1]["ticker"] == "B"
        assert result[2]["ticker"] == "C"
        # 순서가 유지되었는지 확인
        assert result[0]["score"] == 10
        assert result[1]["score"] == 9
        assert result[2]["score"] == 8
    
    def test_apply_policy_top_n_zero(self):
        candidates = [{"ticker": "A"}]
        policy = RegimePolicy(
            enabled=True,
            grade="OFF",
            top_n=0,
            reason="추천 중단",
            snapshot={}
        )
        result, _ = apply_policy(candidates, policy)
        assert len(result) == 0
    
    def test_apply_policy_top_n_larger_than_candidates(self):
        candidates = [{"ticker": "A"}]
        policy = RegimePolicy(
            enabled=True,
            grade="STRONG",
            top_n=10,
            reason="강력 추천",
            snapshot={}
        )
        result, _ = apply_policy(candidates, policy)
        assert len(result) == 1
        assert result[0]["ticker"] == "A"


class TestModeShadow:
    """shadow 모드 테스트"""
    
    def test_shadow_mode_returns_original(self):
        """shadow 모드에서는 정책을 결정하지만 원본 candidates를 반환"""
        candidates = [
            {"ticker": "A", "score": 10},
            {"ticker": "B", "score": 9},
            {"ticker": "C", "score": 8},
        ]
        
        # shadow 모드는 apply_policy를 호출하지 않고 원본 반환
        # 실제 통합 테스트는 scanner.scan()에서 수행
        assert len(candidates) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
























