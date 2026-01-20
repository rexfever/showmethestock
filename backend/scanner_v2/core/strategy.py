"""
전략 결정 모듈 (scanner_v2 전용)
"""
from typing import Tuple, Optional


def determine_trading_strategy(flags: dict, adjusted_score: float) -> Tuple[str, Optional[float], Optional[float], Optional[str]]:
    """점수 구성에 따라 매매 전략 결정
    
    Args:
        flags: 점수 계산 결과 플래그 딕셔너리
        adjusted_score: 조정된 점수 (신호 보너스 포함, 위험도 차감 전)
    
    Returns:
        tuple: (전략명, 목표수익률, 손절기준, 보유기간)
    """
    # 모멘텀 지표 점수 (단기)
    momentum_score = 0
    if flags.get("cross"):
        momentum_score += 3
    if flags.get("vol_expand"):
        momentum_score += 2
    if flags.get("macd_ok"):
        momentum_score += 1
    if flags.get("rsi_ok"):
        momentum_score += 1
    
    # 추세 지표 점수 (중장기)
    trend_score = 0
    if flags.get("tema_slope_ok"):
        trend_score += 2
    if flags.get("obv_slope_ok"):
        trend_score += 2
    if flags.get("above_cnt5_ok"):
        trend_score += 2
    if flags.get("dema_slope_ok"):
        trend_score += 2
    
    # 전략 판단
    if adjusted_score >= 10:
        # 스윙: 골든크로스 + 거래량 + 모멘텀 지표 중심
        if flags.get("cross") and flags.get("vol_expand") and momentum_score >= 6:
            return "스윙", 0.05, -0.05, "3~10일"
        # 포지션: 추세 지표 중심
        elif trend_score >= 5:
            return "포지션", 0.10, -0.07, "2주~3개월"
        else:
            return "스윙", 0.05, -0.05, "3~10일"  # 기본값
    
    elif adjusted_score >= 8:
        # 포지션: 골든크로스 + 추세 지표
        if flags.get("cross") and trend_score >= 4:
            return "포지션", 0.10, -0.07, "2주~3개월"
        # 스윙: 거래량 + 모멘텀
        elif flags.get("vol_expand") and momentum_score >= 5:
            return "스윙", 0.05, -0.05, "3~10일"
        else:
            # adjusted_score >= 8이면 기본값으로 "포지션" 부여
            # 점수가 높으면 최소한 중기 투자 전략은 부여
            return "포지션", 0.10, -0.07, "2주~3개월"  # 기본값
    
    elif adjusted_score >= 6:
        # 6-8점 구간 성과 개선됨 (-0.04%, 승률 49.6%)
        # 장기 전략 조건 강화: trend_score >= 3, RSI < 65
        rsi_tema = flags.get("rsi_tema", 0) if isinstance(flags, dict) else 0
        if trend_score >= 3 and rsi_tema < 65:
            # 추세 지표가 충분하고 RSI가 낮으면 장기
            return "장기", 0.15, -0.10, "3개월 이상"
        else:
            # 조건 미충족 시 관찰로 분류 (6-8점 구간도 관찰이 더 안전)
            return "관찰", None, None, None
    
    elif adjusted_score >= 4:
        # 4-6점 구간이 최우수 성과 (+1.03%, 승률 63.7%)
        # 추세 지표가 있으면 장기, 없으면 관찰 (관찰 우선)
        if trend_score >= 2 and flags.get("rsi_tema", 100) < 65:
            # 추세 지표가 충분하고 RSI가 낮으면 장기
            return "장기", 0.15, -0.10, "3개월 이상"
        else:
            # 기본적으로 관찰 전략 우선 (4-6점 구간의 관찰 전략이 좋은 성과)
            return "관찰", None, None, None
    
    else:
        return "관찰", None, None, None

