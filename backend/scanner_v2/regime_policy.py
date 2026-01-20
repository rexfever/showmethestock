"""
Regime v4 기반 추천 강도 제어 정책

Scanner v2의 종목 선정 로직은 변경하지 않고,
Regime v4 분석 결과를 기반으로 추천의 강도(노출 수/등급/중단 OFF)만 제어한다.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegimePolicy:
    """레짐 정책 결과"""
    enabled: bool
    grade: str        # STRONG / NORMAL / CAUTION / OFF
    top_n: int        # 노출 개수 (-1: 비활성, 0: OFF, >0: 실제 개수)
    reason: str       # 사람 읽는 한 줄
    snapshot: Dict[str, Any]  # regime 요약(로그/메타용)


def _extract_final_regime(regime: Any) -> str:
    """
    regime에서 final_regime 추출
    
    Args:
        regime: MarketCondition 객체 또는 dict 또는 analyze_regime_v4 결과
    
    Returns:
        final_regime 문자열 (bull/neutral/bear/crash), 없으면 "neutral"
    """
    if regime is None:
        return "neutral"
    
    # dict인 경우
    if isinstance(regime, dict):
        return regime.get("final_regime") or \
               regime.get("midterm_regime") or \
               "neutral"
    
    # 객체인 경우 (MarketCondition 등)
    if hasattr(regime, 'final_regime'):
        value = getattr(regime, 'final_regime')
        if value:
            return value
    
    if hasattr(regime, 'midterm_regime'):
        value = getattr(regime, 'midterm_regime')
        if value:
            return value
    
    if hasattr(regime, 'market_sentiment'):
        value = getattr(regime, 'market_sentiment')
        if value:
            return value
    
    return "neutral"


def _extract_risk_label(regime: Any) -> str:
    """
    regime에서 risk_label 추출
    
    우선순위:
    1) global_risk
    2) us_risk_label / kr_risk_label (있으면 보수적으로 worst 선택)
    3) global_risk_score / short_term_risk_score로 매핑
    
    Returns:
        risk_label 문자열 (normal/elevated/stressed)
    """
    if regime is None:
        return "normal"
    
    # dict인 경우
    if isinstance(regime, dict):
        # 1. global_risk 우선
        global_risk = regime.get("global_risk")
        if global_risk in ["normal", "elevated", "stressed"]:
            return global_risk
        
        # 2. us_risk_label / kr_risk_label
        us_risk = regime.get("us_risk_label") or regime.get("us_prev_regime")
        kr_risk = regime.get("kr_risk_label")
        
        if us_risk or kr_risk:
            # 보수적으로 worst 선택
            risks = [r for r in [us_risk, kr_risk] if r]
            if "stressed" in risks:
                return "stressed"
            elif "elevated" in risks:
                return "elevated"
            else:
                return "normal"
        
        # 3. score로 매핑
        global_risk_score = regime.get("global_risk_score")
        if global_risk_score is not None:
            if global_risk_score <= -3:
                return "stressed"
            elif global_risk_score <= -1:
                return "elevated"
            else:
                return "normal"
        
        short_term_risk = regime.get("short_term_risk_score")
        if short_term_risk is not None:
            if short_term_risk >= 3:
                return "stressed"
            elif short_term_risk >= 2:
                return "elevated"
            else:
                return "normal"
    
    # 객체인 경우
    if hasattr(regime, 'global_risk'):
        value = getattr(regime, 'global_risk')
        if value in ["normal", "elevated", "stressed"]:
            return value
    
    if hasattr(regime, 'us_risk_label'):
        us_risk = getattr(regime, 'us_risk_label', None)
        kr_risk = getattr(regime, 'kr_risk_label', None) if hasattr(regime, 'kr_risk_label') else None
        
        if us_risk or kr_risk:
            risks = [r for r in [us_risk, kr_risk] if r]
            if "stressed" in risks:
                return "stressed"
            elif "elevated" in risks:
                return "elevated"
            else:
                return "normal"
    
    if hasattr(regime, 'global_risk_score'):
        score = getattr(regime, 'global_risk_score')
        if score is not None:
            if score <= -3:
                return "stressed"
            elif score <= -1:
                return "elevated"
            else:
                return "normal"
    
    if hasattr(regime, 'short_term_risk_score'):
        score = getattr(regime, 'short_term_risk_score')
        if score is not None:
            if score >= 3:
                return "stressed"
            elif score >= 2:
                return "elevated"
            else:
                return "normal"
    
    return "normal"


def decide_policy(regime: Any, enabled: bool) -> RegimePolicy:
    """
    Regime v4 분석 결과를 기반으로 정책 결정
    
    Args:
        regime: MarketCondition 객체 또는 analyze_regime_v4 결과
        enabled: 정책 활성화 여부
    
    Returns:
        RegimePolicy 객체
    """
    if not enabled:
        return RegimePolicy(
            enabled=False,
            grade="NORMAL",
            top_n=-1,
            reason="policy disabled",
            snapshot={}
        )
    
    final_regime = _extract_final_regime(regime)  # bull/neutral/bear/crash
    risk_label = _extract_risk_label(regime)      # normal/elevated/stressed
    
    # 정책 매핑 (완화안 v2)
    if final_regime == "bull" and risk_label == "normal":
        grade = "STRONG"
        top_n = 15
        reason = f"강세장 + 안정적 리스크 → 강력 추천"
    elif final_regime == "bull" and risk_label == "elevated":
        grade = "NORMAL"
        top_n = 8
        reason = f"강세장 + 높은 리스크 → 일반 추천"
    elif final_regime == "bull" and risk_label == "stressed":
        grade = "CAUTION"
        top_n = 5
        reason = f"강세장 + 매우 높은 리스크 → 신중 추천"
    elif final_regime == "neutral" and risk_label == "normal":
        grade = "NORMAL"
        top_n = 8
        reason = f"중립장 + 안정적 리스크 → 일반 추천"
    elif final_regime == "neutral" and risk_label == "elevated":
        grade = "CAUTION"
        top_n = 5
        reason = f"중립장 + 높은 리스크 → 신중 추천"
    elif final_regime == "neutral" and risk_label == "stressed":
        grade = "CAUTION"
        top_n = 3
        reason = f"중립장 + 매우 높은 리스크 → 신중 추천"
    elif final_regime == "bear" and risk_label == "normal":
        grade = "CAUTION"
        top_n = 5
        reason = f"약세장 + 안정적 리스크 → 신중 추천"
    elif final_regime == "bear" and risk_label == "elevated":
        grade = "CAUTION"
        top_n = 3
        reason = f"약세장 + 높은 리스크 → 신중 추천"
    elif final_regime == "bear" and risk_label == "stressed":
        grade = "OFF"
        top_n = 0
        reason = f"약세장 + 매우 높은 리스크 → 추천 중단"
    elif final_regime == "crash":
        grade = "OFF"
        top_n = 0
        reason = f"급락장 → 추천 중단"
    else:
        # 기본값 (예상치 못한 조합)
        grade = "NORMAL"
        top_n = 8
        reason = f"알 수 없는 레짐 조합 ({final_regime}/{risk_label}) → 일반 추천"
    
    # snapshot 구성 (있을 때만 채움)
    snapshot = {}
    
    if isinstance(regime, dict):
        snapshot = {
            "final_regime": regime.get("final_regime"),
            "midterm_regime": regime.get("midterm_regime"),
            "longterm_regime": regime.get("longterm_regime"),
            "risk_label": risk_label,
            "global_trend_score": regime.get("global_trend_score"),
            "global_risk_score": regime.get("global_risk_score"),
            "kr_trend_score": regime.get("kr_trend_score"),
            "us_trend_score": regime.get("us_trend_score"),
            "kr_risk_score": regime.get("kr_risk_score"),
            "us_risk_score": regime.get("us_risk_score"),
            "short_term_risk_score": regime.get("short_term_risk_score"),
            "date": regime.get("date"),
        }
    else:
        # 객체인 경우
        snapshot = {
            "final_regime": getattr(regime, 'final_regime', None),
            "midterm_regime": getattr(regime, 'midterm_regime', None),
            "longterm_regime": getattr(regime, 'longterm_regime', None),
            "risk_label": risk_label,
            "global_trend_score": getattr(regime, 'global_trend_score', None),
            "global_risk_score": getattr(regime, 'global_risk_score', None),
            "kr_trend_score": getattr(regime, 'kr_trend_score', None),
            "us_trend_score": getattr(regime, 'us_trend_score', None),
            "kr_risk_score": getattr(regime, 'kr_risk_score', None),
            "us_risk_score": getattr(regime, 'us_risk_score', None),
            "short_term_risk_score": getattr(regime, 'short_term_risk_score', None),
            "date": getattr(regime, 'date', None),
        }
    
    # None 값 제거
    snapshot = {k: v for k, v in snapshot.items() if v is not None}
    
    return RegimePolicy(
        enabled=True,
        grade=grade,
        top_n=top_n,
        reason=reason,
        snapshot=snapshot
    )


def apply_policy(candidates: List[dict], policy: RegimePolicy) -> Tuple[List[dict], RegimePolicy]:
    """
    정책을 candidates에 적용
    
    Args:
        candidates: 이미 정렬된 리스트 (순서 변경 금지)
        policy: RegimePolicy 객체
    
    Returns:
        (필터링된 candidates, policy)
    """
    # 비활성화된 경우 원본 그대로 반환
    if not policy.enabled and policy.top_n == -1:
        return candidates, policy
    
    # OFF인 경우 빈 리스트 반환
    if policy.grade == "OFF" or policy.top_n == 0:
        return [], policy
    
    # top_n > 0인 경우 슬라이싱만 수행 (순서 유지)
    if policy.top_n > 0:
        return candidates[:policy.top_n], policy
    
    # 그 외의 경우 원본 그대로 반환
    return candidates, policy
























