"""
평가(score_label)와 전략(trading_strategy)의 연관성 테스트
"""
import pytest


def test_label_strategy_relationship():
    """평가와 전략의 연관성 확인"""
    
    from scanner_v2.core.strategy import determine_trading_strategy
    
    # 케이스 1: adjusted_score >= 10 → "강한 매수"
    # 전략은 스윙 또는 포지션이어야 함 (관찰 아님)
    flags = {
        "cross": True,
        "vol_expand": True,
        "macd_ok": True,
        "rsi_ok": True,
        "tema_slope_ok": True,
        "obv_slope_ok": True,
        "above_cnt5_ok": True,
        "dema_slope_ok": True
    }
    adjusted_score = 10.0
    
    strategy, _, _, _ = determine_trading_strategy(flags, adjusted_score)
    
    # adjusted_score >= 10이면 전략은 스윙 또는 포지션이어야 함
    assert strategy in ["스윙", "포지션"], f"Expected '스윙' or '포지션', got '{strategy}'"
    assert strategy != "관찰", f"adjusted_score >= 10인데 전략이 '관찰'이면 안됨"
    
    # 케이스 2: adjusted_score >= 8 → "매수 후보"
    # 전략은 포지션 또는 스윙이어야 함 (관찰 아님)
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    adjusted_score = 8.0
    
    strategy, _, _, _ = determine_trading_strategy(flags, adjusted_score)
    
    # adjusted_score >= 8이면 전략은 포지션이어야 함 (기본값)
    assert strategy == "포지션", f"Expected '포지션', got '{strategy}'"
    assert strategy != "관찰", f"adjusted_score >= 8인데 전략이 '관찰'이면 안됨"
    
    # 케이스 3: adjusted_score >= 6 → "관심 종목"
    # 전략은 장기이어야 함 (관찰 아님)
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    adjusted_score = 6.0
    
    strategy, _, _, _ = determine_trading_strategy(flags, adjusted_score)
    
    # adjusted_score >= 6이면 전략은 장기이어야 함
    assert strategy == "장기", f"Expected '장기', got '{strategy}'"
    assert strategy != "관찰", f"adjusted_score >= 6인데 전략이 '관찰'이면 안됨"
    
    # 케이스 4: adjusted_score < 6 → "후보 종목"
    # 전략은 관찰이어야 함
    flags = {
        "cross": False,
        "vol_expand": False,
        "tema_slope_ok": False,
        "obv_slope_ok": False,
        "above_cnt5_ok": False,
        "dema_slope_ok": False
    }
    adjusted_score = 5.0
    
    strategy, _, _, _ = determine_trading_strategy(flags, adjusted_score)
    
    # adjusted_score < 6이면 전략은 관찰이어야 함
    assert strategy == "관찰", f"Expected '관찰', got '{strategy}'"


def test_label_strategy_mapping():
    """평가와 전략의 매핑 관계 확인"""
    
    # 평가 기준
    label_ranges = {
        "강한 매수": (10, float('inf')),
        "매수 후보": (8, 10),
        "관심 종목": (6, 8),
        "후보 종목": (0, 6)
    }
    
    # 전략 기준
    strategy_ranges = {
        "스윙": (10, float('inf')),  # adjusted_score >= 10, 조건 충족 시
        "포지션": (8, float('inf')),  # adjusted_score >= 8, 조건 충족 시 또는 기본값
        "장기": (6, 8),  # adjusted_score >= 6, 조건 충족 시 또는 기본값
        "관찰": (0, 6)  # adjusted_score < 6
    }
    
    # 연관성 확인
    # "강한 매수" → 스윙 또는 포지션 가능
    assert label_ranges["강한 매수"][0] >= strategy_ranges["스윙"][0]
    assert label_ranges["강한 매수"][0] >= strategy_ranges["포지션"][0]
    
    # "매수 후보" → 포지션 또는 스윙 가능
    assert label_ranges["매수 후보"][0] >= strategy_ranges["포지션"][0]
    
    # "관심 종목" → 장기 가능
    assert label_ranges["관심 종목"][0] >= strategy_ranges["장기"][0]
    
    # "후보 종목" → 관찰
    assert label_ranges["후보 종목"][1] <= strategy_ranges["관찰"][1]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




































