from __future__ import annotations

"""
scanner_v2.integrator.market_integrator

Horizon별 스코어와 시장 상황을 합쳐 최종 후보를 선정한다.
"""

from typing import Any, Dict, List


# 장세별 기본 cutoff 설정
CUTOFF_CONFIG: Dict[str, Dict[str, float]] = {
    "bull": {
        "swing": 6.0,
        "position": 4.3,
        "longterm": 5.0,
    },
    "neutral": {
        "swing": 6.0,
        "position": 4.5,
        "longterm": 6.0,
    },
    "bear": {
        "swing": 999.0,  # 사실상 OFF
        "position": 5.5,
        "longterm": 6.0,
    },
    "crash": {
        "swing": 999.0,
        "position": 999.0,
        "longterm": 999.0,
    },
}

MAX_CANDIDATES_POSITION: int = 15

MAX_CANDIDATES: Dict[str, int] = {
    "swing": 20,
    "position": MAX_CANDIDATES_POSITION,
    "longterm": 20,
}


def integrate_scores(
    date: str,
    market_condition: Dict[str, Any],
    horizon_scores: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    장세 + Horizon별 점수를 기반으로 최종 후보군을 생성한다.

    Args:
        date: YYYYMMDD
        market_condition: market_condition_adapter.load_market_condition() 결과
        horizon_scores: 각 심볼별 점수 dict 리스트.

    Returns:
        {
          "date": ...,
          "market_sentiment": ...,
          "swing_candidates": [...],
          "position_candidates": [...],
          "longterm_candidates": [...],
        }
    """
    sentiment = market_condition.get("market_sentiment", "neutral")
    cutoff = CUTOFF_CONFIG.get(sentiment, CUTOFF_CONFIG["neutral"])

    swing_items: List[Dict[str, Any]] = []
    position_items: List[Dict[str, Any]] = []
    longterm_items: List[Dict[str, Any]] = []

    for item in horizon_scores:
        symbol = item.get("symbol")
        risk = float(item.get("risk_score", 0.0))
        swing_score = float(item.get("swing_score", 0.0))
        position_score = float(item.get("position_score", 0.0))
        longterm_score = float(item.get("longterm_score", 0.0))

        if swing_score >= cutoff["swing"]:
            swing_items.append(
                {
                    "symbol": symbol,
                    "swing_score": swing_score,
                    "risk_score": risk,
                }
            )
        if position_score >= cutoff["position"]:
            position_items.append(
                {
                    "symbol": symbol,
                    "position_score": position_score,
                    "risk_score": risk,
                }
            )
        if longterm_score >= cutoff["longterm"]:
            longterm_items.append(
                {
                    "symbol": symbol,
                    "longterm_score": longterm_score,
                    "risk_score": risk,
                }
            )

    # 정렬 및 상위 N개 제한 (score desc, risk asc)
    swing_items.sort(key=lambda x: (-x["swing_score"], x["risk_score"]))
    position_items.sort(key=lambda x: (-x["position_score"], x["risk_score"]))
    longterm_items.sort(key=lambda x: (-x["longterm_score"], x["risk_score"]))

    swing_items = swing_items[: MAX_CANDIDATES["swing"]]
    position_items = position_items[: MAX_CANDIDATES["position"]]
    longterm_items = longterm_items[: MAX_CANDIDATES["longterm"]]

    return {
        "date": date,
        "market_sentiment": sentiment,
        "swing_candidates": swing_items,
        "position_candidates": position_items,
        "longterm_candidates": longterm_items,
    }


