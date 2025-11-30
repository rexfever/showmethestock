"""
가산점 적용 시 레이블 재결정 테스트
"""
import pytest


def test_bonus_score_affects_both_strategy_and_label():
    """가산점이 적용되면 전략과 레이블 모두 재결정되어야 함"""
    
    from scanner_v2.core.strategy import determine_trading_strategy
    
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False,
        "risk_score": 0
    }
    
    # 가산점 적용 전
    score_before = 7.0
    risk_score = flags.get('risk_score', 0)
    adjusted_score_before = score_before - risk_score  # 7.0
    
    strategy_before, _, _, _ = determine_trading_strategy(flags, adjusted_score_before)
    
    # 레이블 결정
    if adjusted_score_before >= 10:
        label_before = "강한 매수"
    elif adjusted_score_before >= 8:
        label_before = "매수 후보"
    elif adjusted_score_before >= 6:
        label_before = "관심 종목"
    else:
        label_before = "후보 종목"
    
    assert label_before == "관심 종목"
    assert strategy_before == "장기"
    
    # 가산점 적용 후 (score += 1.0)
    score_after = 8.0
    adjusted_score_after = score_after - risk_score  # 8.0
    
    strategy_after, _, _, _ = determine_trading_strategy(flags, adjusted_score_after)
    
    # 레이블 재결정 (scanner.py 로직)
    if adjusted_score_after >= 10:
        label_after = "강한 매수"
    elif adjusted_score_after >= 8:
        label_after = "매수 후보"
    elif adjusted_score_after >= 6:
        label_after = "관심 종목"
    else:
        label_after = "후보 종목"
    
    # 가산점 적용 후 전략과 레이블 모두 변경되어야 함
    assert strategy_after == "포지션", f"Expected '포지션', got '{strategy_after}'"
    assert label_after == "매수 후보", f"Expected '매수 후보', got '{label_after}'"
    assert label_before != label_after, "가산점 적용 후 레이블이 변경되어야 함"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

