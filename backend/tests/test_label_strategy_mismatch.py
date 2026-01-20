"""
평가와 전략 불일치 문제 분석 테스트
"""
import pytest


def test_bonus_score_affects_strategy_but_not_label():
    """가산점이 적용되면 전략은 재결정되지만 레이블은 재결정되지 않는 문제"""
    
    # 시나리오:
    # 1. scorer에서 adjusted_score = 7.0으로 계산
    #    - 레이블: "관심 종목" (adjusted_score >= 6)
    #    - 전략: "장기" (adjusted_score >= 6)
    # 2. scanner에서 가산점 +1.0 적용
    #    - score = 8.0
    #    - adjusted_score = 8.0 - risk_score
    #    - 전략 재결정: "포지션" (adjusted_score >= 8)
    #    - 레이블은 재결정 안됨 → 여전히 "관심 종목"
    
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
    adjusted_score_before = 7.0
    strategy_before, _, _, _ = determine_trading_strategy(flags, adjusted_score_before)
    
    # 레이블 결정 (scorer.py 로직)
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
    
    # 가산점 적용 후
    # score = 8.0, risk_score = 0
    adjusted_score_after = 8.0
    strategy_after, _, _, _ = determine_trading_strategy(flags, adjusted_score_after)
    
    # 레이블은 재결정 안됨 (scanner.py에서 레이블 재결정 로직 없음)
    # 하지만 adjusted_score_after로 레이블을 재결정하면:
    if adjusted_score_after >= 10:
        label_after = "강한 매수"
    elif adjusted_score_after >= 8:
        label_after = "매수 후보"
    elif adjusted_score_after >= 6:
        label_after = "관심 종목"
    else:
        label_after = "후보 종목"
    
    assert strategy_after == "포지션"
    assert label_after == "매수 후보"  # 하지만 실제로는 재결정 안됨
    
    # 문제: label_before != label_after인데 레이블이 재결정되지 않음
    assert label_before != label_after, "가산점 적용 후 레이블도 재결정되어야 함"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




































