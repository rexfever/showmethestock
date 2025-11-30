"""
점수 9.0점인데 전략이 "관찰"로 나오는 문제 테스트
"""
import pytest


def test_strategy_with_score_9():
    """점수 9.0점인 경우 전략 결정 테스트"""
    
    # 케이스 1: adjusted_score = 9.0, trend_score >= 4
    flags = {
        "cross": True,
        "tema_slope_ok": True,
        "obv_slope_ok": True,
        "above_cnt5_ok": True,
        "dema_slope_ok": False
    }
    adjusted_score = 9.0
    
    from scanner_v2.core.strategy import determine_trading_strategy
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
    
    # trend_score = 2 + 2 + 2 = 6 >= 4
    # adjusted_score >= 8이므로 "포지션"이어야 함
    assert strategy == "포지션", f"Expected '포지션', got '{strategy}'"
    
    # 케이스 2: adjusted_score = 9.0, trend_score < 4, vol_expand와 momentum_score >= 5
    flags = {
        "cross": False,
        "vol_expand": True,
        "macd_ok": True,
        "rsi_ok": True,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    adjusted_score = 9.0
    
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
    
    # momentum_score = 2 + 1 + 1 = 4 < 5
    # trend_score = 0 < 4
    # adjusted_score >= 8이므로 기본값 "포지션"이어야 함
    assert strategy == "포지션", f"Expected '포지션', got '{strategy}' (adjusted_score={adjusted_score}, momentum_score=4, trend_score=0)"
    
    # 케이스 3: adjusted_score = 6.0 (risk_score 차감 후), trend_score < 2
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    adjusted_score = 6.0
    
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
    
    # trend_score = 0 < 2
    # adjusted_score >= 6이면 "장기" 전략 부여 (수정 후)
    assert strategy == "장기", f"Expected '장기', got '{strategy}'"


def test_adjusted_score_calculation():
    """adjusted_score 계산 테스트"""
    # 원본 점수 9.0
    score = 9.0
    
    # risk_score가 3.0이면
    risk_score = 3.0
    adjusted_score = score - risk_score
    
    assert adjusted_score == 6.0
    
    # 이 경우 전략은?
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    
    from scanner_v2.core.strategy import determine_trading_strategy
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
    
    # adjusted_score = 6.0, trend_score = 0 < 2
    # 하지만 adjusted_score >= 6이므로 "장기" (수정 후)
    assert strategy == "장기", f"Expected '장기', got '{strategy}'"
    
    # 하지만 trend_score >= 2이면?
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": True,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(flags, adjusted_score)
    
    # trend_score = 2 >= 2
    # adjusted_score >= 6이므로 "장기"
    assert strategy == "장기", f"Expected '장기', got '{strategy}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

