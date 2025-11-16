from __future__ import annotations

"""
scanner_v2.integrator.market_condition_adapter

기존 market_analyzer를 호출하여 scanner_v2에서 사용하기 쉬운
단순 Dict 형태로 변환하는 어댑터.
"""

from typing import Any, Dict

from market_analyzer import market_analyzer


def load_market_condition(date: str) -> Dict[str, Any]:
    """
    주어진 날짜(YYYYMMDD)에 대한 시장 상황 요약 정보를 반환한다.
    """
    cond = market_analyzer.analyze_market_condition(date)
    return {
        "date": cond.date,
        "market_sentiment": getattr(cond, "market_sentiment", "neutral"),
        "kospi_return": float(getattr(cond, "kospi_return", 0.0)),
        "volatility": float(getattr(cond, "volatility", 0.0)),
        "trend_metrics": getattr(cond, "trend_metrics", {}),
        "breadth_metrics": getattr(cond, "breadth_metrics", {}),
        "flow_metrics": getattr(cond, "flow_metrics", {}),
        "sector_metrics": getattr(cond, "sector_metrics", {}),
        "volatility_metrics": getattr(cond, "volatility_metrics", {}),
    }


